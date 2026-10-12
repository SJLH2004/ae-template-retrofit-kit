# -*- coding: utf-8 -*-
"""把 probe_project.py 的输出压成人能读的摘要：结构 / 文案占位 / 素材清单。

用法:
  python summarize_project.py --probe probe_project.json [--out summary.txt] \
      [--mains 总合成,1,2] [--group-count 6]
"""
import argparse
import io
import json
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", required=True, help="probe_project.py 输出的 JSON")
    ap.add_argument("--out", default="project_summary.txt")
    ap.add_argument("--mains", default="总合成,1,2")
    ap.add_argument("--group-count", type=int, default=6)
    args = ap.parse_args()

    D = json.load(open(args.probe, encoding="utf-8"))
    out = io.StringIO()
    P = lambda *a: print(*a, file=out)  # noqa: E731

    comps = {c["name"]: c for c in D.get("comps", [])}

    P("=" * 60)
    P("一、主输出合成结构")
    P("=" * 60)
    for n in [x for x in args.mains.split(",") if x]:
        c = comps.get(n)
        if not c:
            continue
        P("\n[%s] %sx%s  %.2fs  %sfps  %d层" % (n, c["w"], c["h"], c["dur"], c["fps"], c["layers"]))
        for it in c["items"][:30]:
            P("   %2d %-8s %-28s in=%.2f out=%.2f st=%.2f src=%s" %
              (it["i"], it["t"], it["n"][:28], it["inP"], it["outP"], it["st"], it["src"][:40]))

    P("\n" + "=" * 60)
    P("二、文字占位（要改的文案）")
    P("=" * 60)
    for i in range(1, args.group_count + 1):
        n = "文字合成%02d" % i
        c = comps.get(n)
        if not c:
            continue
        P("\n[%s] %.2fs %d层" % (n, c["dur"], c["layers"]))
        for it in c["items"]:
            t = it["txt"]
            P("   %2d %-6s %-22s %s" % (it["i"], it["t"], it["n"][:22], ("txt=%r" % t) if t else ""))

    P("\n" + "=" * 60)
    P("三、图片占位（要换的素材）")
    P("=" * 60)
    for i in range(1, args.group_count + 1):
        n = "图片%02d" % i
        c = comps.get(n)
        if not c:
            continue
        P("\n[%s] %.2fs %d层" % (n, c["dur"], c["layers"]))
        for it in c["items"]:
            P("   %2d %-8s %-24s src=%s  in=%.2f out=%.2f" %
              (it["i"], it["t"], it["n"][:24], it["src"], it["inP"], it["outP"]))

    P("\n" + "=" * 60)
    P("四、素材清单")
    P("=" * 60)
    for f in D.get("footage", []):
        P("   %-32s %sx%s %.2fs %sfps %s" %
          (f["name"][:32], f["w"], f["h"], f["dur"], f["fps"], "缺失!" if f["miss"] else ""))

    txt = out.getvalue()
    open(args.out, "w", encoding="utf-8").write(txt)
    print(txt)
    print("saved ->", args.out)


if __name__ == "__main__":
    main()
