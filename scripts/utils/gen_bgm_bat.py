# -*- coding: utf-8 -*-
"""生成"把音乐拖进来自动配乐"的 bat（双击/拖拽即用）。

生成的 bat 逻辑：
  * -stream_loop -1 循环铺满整片
  * afade 头尾淡入淡出
  * -c:v copy 视频流不重压（画质零损失）
  * -shortest 以视频长度为准

用法:
  python gen_bgm_bat.py --video "D:\\MP4\\片头.mp4" --out "D:\\MP4\\加配乐.bat" \
      [--dst "D:\\MP4\\片头_配乐版.mp4"] [--fade-out-start 28.3] [--fade-out-dur 1.7]
"""
import argparse
import os

# Windows 控制台/管道默认非 UTF-8（常见 cp1252），直接 print 中文会抛
# UnicodeEncodeError 使脚本以退出码 1 结束；Linux/macOS 默认 UTF-8 不受影响。
# 统一在处理前改掉，保证跨平台输出一致。
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

BAT = """@echo off
chcp 936 >nul
title Add BGM

if "%~1"=="" (
  echo.
  echo   [!] Please DRAG a music file onto this .bat
  echo.
  echo   Supported: mp3 / wav / m4a / aac / flac
  echo.
  pause
  exit /b 1
)

set "VID=__VID__"
set "OUT=__DST__"

if not exist "%VID%" (
  echo [X] Video not found: %VID%
  pause
  exit /b 1
)

echo.
echo   Video : %VID%
echo   Music : %~1
echo   Output: %OUT%
echo.
echo   Rendering... please wait

ffmpeg -y -i "%VID%" -stream_loop -1 -i "%~1" ^
  -map 0:v:0 -map 1:a:0 ^
  -c:v copy -c:a aac -b:a 192k ^
  -af "afade=t=in:st=0:d=1,afade=t=out:st=__FOSTART__:d=__FODUR__" ^
  -shortest -movflags +faststart "%OUT%"

if errorlevel 1 (
  echo.
  echo   [X] FAILED - see the message above
  pause
  exit /b 1
)

echo.
echo   [OK] Done:
echo   %OUT%
echo.
pause
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True, help="bat 输出路径")
    ap.add_argument("--dst", default="", help="配乐版输出；默认在原名后加 _配乐版")
    ap.add_argument("--fade-out-start", default="28.3")
    ap.add_argument("--fade-out-dur", default="1.7")
    args = ap.parse_args()

    dst = args.dst
    if not dst:
        base, ext = os.path.splitext(args.video)
        dst = base + "_配乐版" + ext

    content = (BAT.replace("__VID__", args.video)
                  .replace("__DST__", dst)
                  .replace("__FOSTART__", args.fade_out_start)
                  .replace("__FODUR__", args.fade_out_dur))

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="gbk", newline="\r\n") as f:
        f.write(content)
    print("written:", args.out)
    print("  video:", args.video)
    print("  output:", dst)


if __name__ == "__main__":
    main()
