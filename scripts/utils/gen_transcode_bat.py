# -*- coding: utf-8 -*-
"""生成一键转码 bat（双击即用）。

编码注意：bat 内容含中文路径时必须用 GBK 编码写盘，CMD 才不会啃碎命令；
脚本自己的源码可以是 UTF-8（Python 读），只有写出去的 bat 要 GBK。

用法:
  python gen_transcode_bat.py --src "D:\\MP4\\片头.mov" \
      --dst "D:\\MP4\\片头_1920x1080.mp4" --out "D:\\MP4\\转MP4.bat" \
      [--crf 18] [--fps 25] [--ffmpeg ffmpeg]
"""
import argparse
import os

BAT = """@echo off
chcp 936 >nul
title Transcode to MP4

set "SRC=__SRC__"
set "DST=__DST__"

if not exist "%SRC%" (
  echo.
  echo   [X] Source not found:
  echo   %SRC%
  echo.
  pause
  exit /b 1
)

echo.
echo   Source: %SRC%
echo   Output: %DST%
echo.
echo   Encoding... please wait

__FFMPEG__ -y -i "%SRC%" -c:v libx264 -preset slow -crf __CRF__ -pix_fmt yuv420p -r __FPS__ -movflags +faststart -an "%DST%"

if errorlevel 1 (
  echo.
  echo   [X] FAILED - see the message above
  pause
  exit /b 1
)

echo.
echo   [OK] Done:
echo   %DST%
echo.
pause
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--out", required=True, help="bat 输出路径")
    ap.add_argument("--crf", default="18")
    ap.add_argument("--fps", default="25")
    ap.add_argument("--ffmpeg", default="ffmpeg")
    args = ap.parse_args()

    content = (BAT.replace("__SRC__", args.src)
                  .replace("__DST__", args.dst)
                  .replace("__FFMPEG__", args.ffmpeg)
                  .replace("__CRF__", args.crf)
                  .replace("__FPS__", args.fps))

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="gbk", newline="\r\n") as f:
        f.write(content)
    print("written:", args.out)


if __name__ == "__main__":
    main()
