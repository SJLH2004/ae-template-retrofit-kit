# -*- coding: utf-8 -*-
"""AE 链路只读探针：验证桥接层可用。只读，不修改、不保存任何工程。"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts", "ae"))

from ae_bridge import AFTERFX, AERENDER, ae_running, run  # noqa: E402

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
    print("AfterFX :", AFTERFX)
    print("aerender:", AERENDER)
    if not AFTERFX:
        print("RESULT: SKIP - After Effects not installed")
        return 0
    if not ae_running():
        if "--allow-launch" not in sys.argv:
            print("RESULT: SKIP - AE is not running now")
            print("       (start AE manually, or rerun with --allow-launch to auto-start it)")
            return 0
        print("AE not running -> launching (first launch can take 1-2 min)...")

    r = run("""
    RESULT.hasJSON = (typeof JSON !== "undefined");
    RESULT.version = app.version;
    RESULT.projName = app.project.file ? app.project.file.name : "(none)";
    RESULT.numItems = app.project.numItems;
    RESULT.comps = 0;
    for (var i = 1; i <= app.project.numItems; i++) {
        if (app.project.item(i) instanceof CompItem) { RESULT.comps++; }
    }
    """, "ae_link_probe.json", timeout=180)

    print(json.dumps(r, ensure_ascii=False, indent=1))
    if "__error" in r:
        print("RESULT: FAIL -", r["__error"])
        return 1
    if "version" not in r:
        print("RESULT: FAIL - no version in result (bridge returned nothing)")
        return 1
    print("hasJSON (AE has built-in JSON):", r.get("hasJSON"))
    print("RESULT: PASS - bridge roundtrip works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
