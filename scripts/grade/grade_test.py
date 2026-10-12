# -*- coding: utf-8 -*-
"""调色试色：对若干时间点做多档滤镜，拼成对比图供挑选。

原理（重要）：
  画面若大部分是纯灰，单纯 eq=saturation 提饱和是无效的——灰色提饱和还是灰。
  必须先用 colorbalance 按明度分区打破 R=G=B：
      阴影染墨青 / 中间调染主色 / 高光染暖白
  再提饱和度，才有"染色 + 提亮"的效果。

用法:
  python grade_test.py --video out.mp4 --out-dir ./grade --times 3,9,20,27 \
      --presets light,mid,heavy
选好档位后，用同样的滤镜串对全片转码即可。
"""
import argparse
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

# shadow染墨青 / midtone染主色 / highlight染暖白（绢本设色感）
PRESETS = {
    "light": "colorbalance=rs=-0.08:gs=0.10:bs=0.06:rm=-0.04:gm=0.08:bm=0.03"
             ":rh=0.02:gh=0.01:bh=-0.03,eq=saturation=1.15:contrast=1.03",
    "mid":   "colorbalance=rs=-0.15:gs=0.20:bs=0.10:rm=-0.08:gm=0.16:bm=0.05"
             ":rh=0.03:gh=0.01:bh=-0.05,eq=saturation=1.30:contrast=1.06",
    "heavy": "colorbalance=rs=-0.22:gs=0.26:bs=0.15:rm=-0.12:gm=0.21:bm=0.08"
             ":rh=0.04:gh=0.02:bh=-0.07,eq=saturation=1.45:contrast=1.09",
}


def load(p):
    return cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out-dir", default="./grade")
    ap.add_argument("--times", default="3,9,20,27")
    ap.add_argument("--presets", default="light,mid,heavy")
    ap.add_argument("--width", type=int, default=640)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    times = [float(t) for t in args.times.split(",") if t.strip()]
    names = [p.strip() for p in args.presets.split(",") if p.strip()]

    raws = {}
    for t in times:
        p = os.path.join(args.out_dir, "raw_%05.1f.png" % t)
        subprocess.run(["ffmpeg", "-y", "-ss", str(t), "-i", args.video, "-frames:v", "1",
                        "-vf", "scale=%d:-1" % args.width, p], capture_output=True)
        if os.path.exists(p):
            raws[t] = p
    if not raws:
        print("FAIL: 没抽到原始帧")
        raise SystemExit(1)

    for name in names:
        vf = PRESETS.get(name)
        if not vf:
            print("skip unknown preset:", name)
            continue
        for t, src in raws.items():
            dst = os.path.join(args.out_dir, "%s_%05.1f.png" % (name, t))
            subprocess.run(["ffmpeg", "-y", "-i", src, "-vf", vf, dst], capture_output=True)

    cell_w, cell_h = args.width, int(args.width * 9 / 16)
    canvas = np.full((cell_h * len(names), cell_w * len(times), 3), 255, np.uint8)
    for i, name in enumerate(names):
        for j, t in enumerate(times):
            img = load(os.path.join(args.out_dir, "%s_%05.1f.png" % (name, t)))
            if img is None:
                continue
            img = cv2.resize(img, (cell_w, cell_h))
            canvas[i * cell_h:(i + 1) * cell_h, j * cell_w:(j + 1) * cell_w] = img

    grid_p = os.path.join(args.out_dir, "grade_compare.png")
    cv2.imencode(".png", canvas)[1].tofile(grid_p)
    print("行 = 档位", names)
    print("列 = 时间", times)
    print("grid ->", grid_p, canvas.shape)


if __name__ == "__main__":
    main()
