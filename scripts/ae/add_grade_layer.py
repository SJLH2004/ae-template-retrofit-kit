# -*- coding: utf-8 -*-
"""在总合成顶部挂一个调色调整层（Color Balance），把工程配色固化进去。

幂等：重复运行会先删掉同名的旧图层再重建。

用法:
  python add_grade_layer.py --project <工程.aep> [--mode gamma|global] [参数]

两种模式：
  gamma（推荐）  用 Levels 分通道 gamma 染色：纯黑纯白端点不动，只有中间调
                 被染色——宣纸白底不会被染绿。参数 --gammas R,G,B
                 注意方向：gamma>1 = 提亮该通道（中间调最敏感），<1 = 压暗。
                 青绿设色（压红提绿）：--gammas 0.90,1.12,1.00
                 （已用 ffmpeg eq=gamma_r/gamma_g/gamma_b 同原理验证：
                  高光偏色 25 vs 全局偏移 41，暗部呈墨绿而非红棕）
  global         旧方案：Color Balance 三个滑块做全局 RGB 偏移。实现简单，
                 但会把接近白色的宣纸底一起染色（实测白底偏色 41 vs 分区 25），
                 这就是"整幅发绿发怪"的原因。保留只为兼容。

示例:
  python add_grade_layer.py --project 新工程.aep --mode gamma --gammas 0.90,1.12,1.00
  python add_grade_layer.py --project 新工程.aep --mode global --cb -12,16,8
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
    ap.add_argument("--mode", choices=["gamma", "global"], default="gamma")
    ap.add_argument("--gammas", default="0.90,1.12,1.00",
                    help="gamma 模式：红,绿,蓝。gamma>1 提亮该通道（中间调最敏感），"
                         "<1 压暗。青绿设色（压红提绿）：0.90,1.12,1.00")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--dur-min", type=float, default=29.5)
    ap.add_argument("--dur-max", type=float, default=30.5)
    ap.add_argument("--layer", default="QINGLV_GRADE")
    ap.add_argument("--cb", default="-12,16,8", help="global 模式：红,绿,蓝平衡")
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()

    cb = [int(x) for x in args.cb.split(",")]
    gammas = [float(x) for x in args.gammas.split(",")]
    if len(cb) != 3 or len(gammas) != 3:
        ap.error("--cb and --gammas each need exactly 3 numbers")

    work = WORK
    os.makedirs(work, exist_ok=True)
    out_path = os.path.join(work, "grade_layer_result.json").replace("\\", "/")
    local_out = os.path.join(work, "grade_layer_result.json")
    if os.path.exists(local_out):
        os.remove(local_out)

    cfg = {"w": args.width, "h": args.height, "durMin": args.dur_min,
           "durMax": args.dur_max, "layer": args.layer, "cb": cb,
           "mode": args.mode, "gammas": gammas}
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
