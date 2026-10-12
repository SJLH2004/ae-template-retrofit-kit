# -*- coding: utf-8 -*-
"""分段节奏检测：每秒抽 1 帧，用直方图距离找场景切换点。

用途：验证成片分段是否落在设计的时间点上（比如 0/6/12/17/23 秒进场），
也可以用来确认渲的是不是修正时间轴之后的版本。

用法:
  python segcheck.py --video out.mp4 --out-dir ./seg [--step 1] [--threshold 0.18]
"""
import argparse
import json
import os
import subprocess

import cv2
import numpy as np

# Windows 控制台/管道默认非 UTF-8（常见 cp1252），直接 print 中文会抛
# UnicodeEncodeError 使脚本以退出码 1 结束；Linux/macOS 默认 UTF-8 不受影响。
# 统一在处理前改掉，保证跨平台输出一致。
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def load(p):
    return cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out-dir", default="./seg")
    ap.add_argument("--step", type=int, default=1, help="每 N 秒抽一帧")
    ap.add_argument("--threshold", type=float, default=0.18)
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-i", args.video,
                    "-vf", "fps=1/%d,scale=320:-1" % args.step,
                    os.path.join(args.out_dir, "s_%02d.png")],
                   capture_output=True)

    files = sorted([f for f in os.listdir(args.out_dir)
                    if f.startswith("s_") and f.endswith(".png")],
                   key=lambda x: int(x[2:-4]))
    if not files:
        print("FAIL: 没抽到帧")
        raise SystemExit(1)

    prev, rows = None, []
    for i, f in enumerate(files):
        img = load(os.path.join(args.out_dir, f))
        if img is None:
            continue
        gray = cv2.cvtColor(cv2.resize(img, (160, 90)), cv2.COLOR_BGR2GRAY)
        lum = float(gray.mean())
        if prev is None:
            diff, hist = 0.0, 0.0
        else:
            diff = float(cv2.absdiff(gray, prev).mean())
            h1 = cv2.calcHist([gray], [0], None, [32], [0, 256]).flatten()
            h2 = cv2.calcHist([prev], [0], None, [32], [0, 256]).flatten()
            h1 = h1 / (h1.sum() + 1e-9)
            h2 = h2 / (h2.sum() + 1e-9)
            hist = float(cv2.compareHist(h1.astype(np.float32), h2.astype(np.float32),
                                         cv2.HISTCMP_BHATTACHARYYA))
        rows.append({"sec": i * args.step, "lum": round(lum, 1),
                     "pixdiff": round(diff, 2), "histdist": round(hist, 3)})
        prev = gray

    print("\n sec   lum    pixDiff  histDist")
    for r in rows:
        print("%4d  %6.1f  %6.2f  %6.3f %s" %
              (r["sec"], r["lum"], r["pixdiff"], r["histdist"],
               "#" * int(min(r["histdist"], 1.0) * 40)))

    vals = [r["histdist"] for r in rows]
    cuts = [rows[i]["sec"] for i in range(1, len(vals))
            if vals[i] > args.threshold and vals[i] >= vals[i - 1]]
    print("\n候选切换点(秒):", cuts)

    if args.json_out:
        json.dump({"rows": rows, "cuts": cuts},
                  open(args.json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
