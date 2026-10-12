# -*- coding: utf-8 -*-
"""从成品抽若干时间点拼成联系表，快速目视验收全片内容。

用法:
  python preview_mp4.py --video out.mp4 --out-dir ./preview \
      --times 0.5,3,8,14,19,27 [--cols 3] [--cell 640x360]
"""
import argparse
import os
import subprocess

from PIL import Image, ImageDraw

# Windows 控制台/管道默认非 UTF-8（常见 cp1252），直接 print 中文会抛
# UnicodeEncodeError 使脚本以退出码 1 结束；Linux/macOS 默认 UTF-8 不受影响。
# 统一在处理前改掉，保证跨平台输出一致。
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out-dir", default="./preview")
    ap.add_argument("--times", default="0.5,3,8,14,19,27", help="逗号分隔的秒数")
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--cell", default="640x360")
    ap.add_argument("--ffmpeg", default="ffmpeg")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    cw, ch = [int(x) for x in args.cell.lower().split("x")]
    times = [float(t) for t in args.times.split(",") if t.strip()]

    tiles = []
    for t in times:
        p = os.path.join(args.out_dir, "t_%05.1f.png" % t)
        subprocess.run([args.ffmpeg, "-y", "-ss", str(t), "-i", args.video,
                        "-frames:v", "1", "-vf", "scale=%d:-1" % cw, p],
                       capture_output=True)
        if os.path.exists(p):
            im = Image.open(p).convert("RGB")
            if im.size != (cw, ch):
                im = im.resize((cw, ch))
            tiles.append(("%.1fs" % t, im))
        else:
            print("miss", t)

    if not tiles:
        print("FAIL: 一帧都没抽到")
        raise SystemExit(1)

    rows = (len(tiles) + args.cols - 1) // args.cols
    pad = 24
    grid = Image.new("RGB", (cw * args.cols, (ch + pad) * rows), (24, 24, 24))
    dr = ImageDraw.Draw(grid)
    for i, (label, im) in enumerate(tiles):
        x = (i % args.cols) * cw
        y = (i // args.cols) * (ch + pad)
        grid.paste(im, (x, y))
        dr.text((x + 8, y + ch + 4), label, fill=(220, 220, 220))

    gp = os.path.join(args.out_dir, "grid.png")
    grid.save(gp)
    print("grid ->", gp, grid.size)


if __name__ == "__main__":
    main()
