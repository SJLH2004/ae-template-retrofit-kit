# -*- coding: utf-8 -*-
"""在总合成顶部挂一个调色调整层（Color Balance），把工程配色固化进去。

幂等：重复运行会先删掉同名的旧图层再重建。

用法:
  python add_grade_layer.py --project <工程.aep> [--width 1920] [--height 1080] \
      [--dur-min 29.5] [--dur-max 30.5] [--layer QINGLV_GRADE] \
      [--cb -12,16,8]

--cb 三个值对应「红色平衡 / 绿色平衡 / 蓝色平衡」（-100..100）。
示例（青绿设色，配 ffmpeg 同款思路）：--cb -12,16,8
偏重就加大绿色、减小红色，例如 --cb -18,24,10。
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ae_bridge import AFTERFX, WORK, ae_running  # noqa: E402

# Windows 控制台/管道默认非 UTF-8（常见 cp1252），直接 print 中文会抛
# UnicodeEncodeError 使脚本以退出码 1 结束；Linux/macOS 默认 UTF-8 不受影响。
# 统一在处理前改掉，保证跨平台输出一致。
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

JSX = os.path.join(HERE, "jsx", "add_grade_layer.jsx")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--dur-min", type=float, default=29.5)
    ap.add_argument("--dur-max", type=float, default=30.5)
    ap.add_argument("--layer", default="QINGLV_GRADE")
    ap.add_argument("--cb", default="-12,16,8", help="red,green,blue balance")
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()

    cb = [int(x) for x in args.cb.split(",")]
    if len(cb) != 3:
        ap.error("--cb needs exactly 3 numbers")

    work = WORK
    os.makedirs(work, exist_ok=True)
    out_path = os.path.join(work, "grade_layer_result.json").replace("\\", "/")
    local_out = os.path.join(work, "grade_layer_result.json")
    if os.path.exists(local_out):
        os.remove(local_out)

    cfg = {"w": args.width, "h": args.height, "durMin": args.dur_min,
           "durMax": args.dur_max, "layer": args.layer, "cb": cb}
    src = open(JSX, encoding="ascii", errors="ignore").read()
    src = (src.replace("__OUT__", out_path)
              .replace("__AEP__", args.project.replace("\\", "/"))
              .replace("__CFG__", json.dumps(cfg)))
    tmp = os.path.join(work, "_ae_grade_layer.jsx")
    with open(tmp, "w", encoding="ascii", errors="ignore") as f:
        f.write(src)

    cmd = [AFTERFX]
    if not ae_running():
        cmd.append("-noui")
    cmd += ["-r", tmp]
    subprocess.Popen(cmd)

    t0 = time.time()
    while time.time() - t0 < args.timeout:
        if os.path.exists(local_out) and os.path.getsize(local_out) > 0:
            time.sleep(0.3)
            break
        time.sleep(1)
    else:
        print("TIMEOUT: AE 在 %ss 内没回写结果（AE 弹模态框会卡住，去点掉）" % args.timeout)
        sys.exit(1)

    d = json.loads(open(local_out, encoding="utf-8").read())
    print(json.dumps(d, ensure_ascii=False, indent=1))
    if not d.get("ok"):
        sys.exit(1)


if __name__ == "__main__":
    main()
