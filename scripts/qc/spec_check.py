# -*- coding: utf-8 -*-
"""成品规格校验（ffprobe）。交片前跑一遍，避免"尺寸/帧率/时长不对"被退回。

用法:
  python spec_check.py --video out.mp4 --expect 1920x1080@25 --codec h264 \
      --pix-fmt yuv420p --min-duration 15
  python spec_check.py --video out.mp4 --expect 1920x1080@25 --json-out spec.json
"""
import argparse
import json
import subprocess
import sys

# Windows 控制台/管道默认非 UTF-8（常见 cp1252），直接 print 中文会抛
# UnicodeEncodeError 使脚本以退出码 1 结束；Linux/macOS 默认 UTF-8 不受影响。
# 统一在处理前改掉，保证跨平台输出一致。
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def probe(path):
    cmd = ["ffprobe", "-v", "error", "-show_streams", "-show_format",
           "-of", "json", path]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("ffprobe 失败: " + (r.stderr or b"").decode("utf-8", "replace")[-400:])
    return json.loads((r.stdout or b"").decode("utf-8", "replace"))


def parse_ratio(s):
    if "/" in s:
        a, b = s.split("/")
        try:
            return float(a) / float(b)
        except ZeroDivisionError:
            return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--expect", default="1920x1080@25", help="宽x高@帧率")
    ap.add_argument("--codec", default="h264")
    ap.add_argument("--pix-fmt", default="yuv420p")
    ap.add_argument("--min-duration", type=float, default=0)
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    info = probe(args.video)
    v = None
    for s in info.get("streams", []):
        if s.get("codec_type") == "video":
            v = s
            break
    if not v:
        print("FAIL: 没有视频流")
        sys.exit(1)

    ew, eh = 1920, 1080
    efps = 25.0
    try:
        dims, fps_part = args.expect.split("@")
        ew, eh = [int(x) for x in dims.lower().split("x")]
        efps = float(fps_part)
    except Exception:
        pass

    got = {
        "codec": v.get("codec_name"),
        "width": v.get("width"),
        "height": v.get("height"),
        "pix_fmt": v.get("pix_fmt"),
        "fps": round(parse_ratio(str(v.get("r_frame_rate", "0/1"))), 3),
        "frames": int(v.get("nb_frames") or 0),
        "duration": round(float(info.get("format", {}).get("duration") or 0), 3),
        "size_mb": round(int(info.get("format", {}).get("size") or 0) / 1048576, 2),
    }
    has_audio = any(s.get("codec_type") == "audio" for s in info.get("streams", []))
    got["has_audio"] = has_audio

    checks = [
        ("编码", got["codec"], args.codec),
        ("分辨率", "%sx%s" % (got["width"], got["height"]), "%sx%s" % (ew, eh)),
        ("帧率", got["fps"], efps),
        ("像素格式", got["pix_fmt"], args.pix_fmt),
    ]
    print("=" * 46)
    print("  规格校验:", args.video)
    print("=" * 46)
    ok = True
    for name, got_v, exp_v in checks:
        same = str(got_v) == str(exp_v)
        ok = ok and same
        print("  %-8s 实测=%-12s 期望=%-12s %s" % (name, got_v, exp_v, "OK" if same else "FAIL"))
    d_ok = got["duration"] >= args.min_duration
    ok = ok and d_ok
    print("  %-8s 实测=%-12s 期望>=%-11s %s" % ("时长", got["duration"], args.min_duration,
                                                "OK" if d_ok else "FAIL"))
    print("  %-8s %s" % ("音轨", "有" if has_audio else "无"))
    print("  %-8s %s 帧 / %.2f MB" % ("其他", got["frames"], got["size_mb"]))
    print("=" * 46)
    print("RESULT:", "PASS" if ok else "FAIL")

    if args.json_out:
        got["ok"] = ok
        json.dump(got, open(args.json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
