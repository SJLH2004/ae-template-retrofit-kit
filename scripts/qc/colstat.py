# -*- coding: utf-8 -*-
"""色彩量化统计：灰色占比 / 饱和度 / 色相分布 / k-means 主色。

用途：判断画面色彩是否符合主题。比如"新青年·芳草行"这类片子，
若灰色占比 > 70%、彩色像素里没有绿色，就说明配色跑偏了。

用法（两种都行）:
  python colstat.py --video out.mp4 --out-dir ./seg          # 自动抽帧后统计
  python colstat.py --frames-dir ./seg --pattern 's_*.png'    # 对已抽好的帧统计
"""
import argparse
import glob
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


def analyze(img, tag):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0].astype(float), hsv[..., 1].astype(float), hsv[..., 2].astype(float)
    n = h.size
    gray_ratio = float((s < 25).sum()) / n * 100
    colored = s >= 25
    line = "%-10s V=%3.0f  S_mean=%5.1f  灰色=%5.1f%%" % (tag, v.mean(), s.mean(), gray_ratio)
    if colored.sum() > 100:
        hh = h[colored]
        total = hh.size
        bins = [(0, 15, "红"), (15, 45, "橙黄"), (45, 75, "黄绿"), (75, 105, "绿"),
                (105, 135, "青"), (135, 165, "蓝"), (165, 181, "品红")]
        parts = []
        for a, b, name in bins:
            r = float(((hh >= a) & (hh < b)).sum()) / total
            if r > 0.02:
                parts.append("%s%.0f%%" % (name, r * 100))
        line += "  色相: " + " ".join(parts)
    print(line)

    small = cv2.resize(img, (120, 68))
    Z = cv2.cvtColor(small, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 25, 1.0)
    _, _, cent = cv2.kmeans(Z, 5, None, crit, 8, cv2.KMEANS_PP_CENTERS)
    bgr = cv2.cvtColor(cent.reshape(1, -1, 3).astype(np.uint8),
                       cv2.COLOR_LAB2BGR).reshape(-1, 3)
    counts = np.bincount(np.argmin(((Z[:, None, :] - cent[None, :, :]) ** 2).sum(-1), axis=1),
                         minlength=5)
    hexes = []
    for i in np.argsort(-counts):
        b, g, r = bgr[i]
        hexes.append("#%02X%02X%02X(%d%%)" % (r, g, b, counts[i] * 100 // Z.shape[0]))
    print("           主色:", " ".join(hexes))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default="")
    ap.add_argument("--frames-dir", default="./seg")
    ap.add_argument("--pattern", default="s_*.png")
    ap.add_argument("--step", type=int, default=1, help="配合 --video：每 N 秒一帧")
    args = ap.parse_args()

    if args.video:
        os.makedirs(args.frames_dir, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-i", args.video,
                        "-vf", "fps=1/%d,scale=320:-1" % args.step,
                        os.path.join(args.frames_dir, "s_%02d.png")],
                       capture_output=True)

    files = sorted(glob.glob(os.path.join(args.frames_dir, args.pattern)))
    if not files:
        print("FAIL: 没有可分析的帧（检查 --frames-dir / --pattern）")
        raise SystemExit(1)
    for f in files:
        img = load(f)
        if img is not None:
            analyze(img, os.path.basename(f))


if __name__ == "__main__":
    main()
