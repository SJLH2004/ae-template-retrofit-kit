# -*- coding: utf-8 -*-
"""清理运行产物，让工作区回到可提交状态。

会删除：out/ seg/ grade/ preview/、__pycache__/、tests/_work/、
包内散落的临时 json/png（config/ 下的配置文件保留）。

用法:
  python tools/clean_workspace.py [--dry-run]
"""
import argparse
import os
import shutil

# Windows 控制台/管道默认非 UTF-8（常见 cp1252），直接 print 中文会抛
# UnicodeEncodeError 使脚本以退出码 1 结束；Linux/macOS 默认 UTF-8 不受影响。
# 统一在处理前改掉，保证跨平台输出一致。
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DIRS = ["out", "seg", "grade", "preview", "tests/_work", "tests/sample"]
PATS_DIR = "__pycache__"
PATS_FILE = (".pyc",)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--keep-sample", action="store_true", help="保留样例视频")
    args = ap.parse_args()

    removed = []

    for d in DIRS:
        p = os.path.join(ROOT, d)
        if d == "tests/sample" and args.keep_sample:
            continue
        if os.path.isdir(p):
            if d == "tests/sample":
                for f in os.listdir(p):
                    if f.endswith(".mp4"):
                        fp = os.path.join(p, f)
                        removed.append(fp)
                        if not args.dry_run:
                            os.remove(fp)
                continue
            removed.append(p + os.sep)
            if not args.dry_run:
                shutil.rmtree(p, ignore_errors=True)

    for dp, dns, fns in os.walk(ROOT):
        for dn in list(dns):
            if dn == PATS_DIR:
                p = os.path.join(dp, dn)
                removed.append(p + os.sep)
                if not args.dry_run:
                    shutil.rmtree(p, ignore_errors=True)
        if "__pycache__" in dp:
            continue
        for f in fns:
            if f.endswith(PATS_FILE):
                p = os.path.join(dp, f)
                removed.append(p)
                if not args.dry_run:
                    os.remove(p)

    print(("将删除" if args.dry_run else "已删除") + " %d 项:" % len(removed))
    for r in removed:
        print("   ", os.path.relpath(r, ROOT))
    if not removed:
        print("    (工作区已经是干净的)")


if __name__ == "__main__":
    main()
