# -*- coding: utf-8 -*-
"""离线自检：不依赖 AE，跑通 ffmpeg 全链路 + 包完整性检查。

用法:
  python tests/test_offline.py [--keep]      # --keep 保留临时产物

覆盖：
  1. 生成样例素材（3 段拼接，模拟分段片头）
  2. spec_check  /  3. segcheck  /  4. colstat  /  5. grade_test  /  6. preview_mp4
  7. 生成两个 bat 并校验是 GBK 编码
  8. 全部 .py 语法编译
  9. 全部 .jsx 必须是纯 ASCII
  10. 包内不得残留个人信息（用户名等）
"""
import argparse
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile

# Windows 控制台/管道默认非 UTF-8（常见 cp1252），直接 print 中文会抛
# UnicodeEncodeError 使脚本以退出码 1 结束；Linux/macOS 默认 UTF-8 不受影响。
# 统一在处理前改掉，保证跨平台输出一致。
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable

results = []


def step(name, fn):
    try:
        fn()
        results.append((name, "PASS", ""))
        print("[PASS] %s" % name)
    except Exception as e:
        results.append((name, "FAIL", str(e)[:200]))
        print("[FAIL] %s -> %s" % (name, e))


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", **kw)
    if r.returncode != 0:
        raise RuntimeError("cmd failed (%d): %s\n%s" % (r.returncode, " ".join(cmd)[:200],
                                                        (r.stderr or "")[-800:]))
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--work", default=os.path.join(ROOT, "tests", "_work"))
    args = ap.parse_args()

    work = args.work
    if os.path.isdir(work) and not args.keep:
        shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)
    sample = os.path.join(HERE, "sample")
    os.makedirs(sample, exist_ok=True)
    print("work dir:", work)

    video = os.path.join(sample, "sample_head.mp4")

    # ---- 1. 生成样例素材 ----
    def gen():
        if os.path.exists(video) and os.path.getsize(video) > 0:
            return
        run(["ffmpeg", "-y",
             "-f", "lavfi", "-i", "color=c=0xF2F4F4:s=960x540:r=25:d=3",
             "-f", "lavfi", "-i", "color=c=0x8B877F:s=960x540:r=25:d=3",
             "-f", "lavfi", "-i", "testsrc2=s=960x540:r=25:d=4",
             "-filter_complex",
             "[0][1][2]concat=n=3:v=1:a=0,hue=s=0,scale=960:540",
             "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
             "-pix_fmt", "yuv420p", "-r", "25", video])
    step("1. 生成样例素材", gen)

    # ---- 2. 规格校验 ----
    step("2. spec_check", lambda: run(
        [PY, os.path.join(ROOT, "scripts", "qc", "spec_check.py"),
         "--video", video, "--expect", "960x540@25", "--min-duration", "10",
         "--json-out", os.path.join(work, "spec.json")]))

    # ---- 3. 分段节奏 ----
    def seg():
        out = run([PY, os.path.join(ROOT, "scripts", "qc", "segcheck.py"),
                   "--video", video, "--out-dir", os.path.join(work, "seg"),
                   "--json-out", os.path.join(work, "seg.json")])
        # 样例在 3s / 6s 处有硬切换，应至少检测到 1 个
        import json
        d = json.load(open(os.path.join(work, "seg.json"), encoding="utf-8"))
        if len(d.get("cuts", [])) < 1:
            raise RuntimeError("未检测到任何切换点: %s" % d.get("cuts"))
        print("    cuts:", d["cuts"])
    step("3. segcheck", seg)

    # ---- 4. 色彩统计 ----
    step("4. colstat", lambda: run(
        [PY, os.path.join(ROOT, "scripts", "qc", "colstat.py"),
         "--frames-dir", os.path.join(work, "seg")]))

    # ---- 5. 调色对比 ----
    def grade():
        run([PY, os.path.join(ROOT, "scripts", "grade", "grade_test.py"),
             "--video", video, "--times", "1,4,8",
             "--out-dir", os.path.join(work, "grade"), "--width", "480"])
        g = os.path.join(work, "grade", "grade_compare.png")
        if not os.path.exists(g):
            raise RuntimeError("对比图未生成")
    step("5. grade_test", grade)

    # ---- 6. 联系表 ----
    def preview():
        run([PY, os.path.join(ROOT, "scripts", "qc", "preview_mp4.py"),
             "--video", video, "--times", "1,4,8",
             "--out-dir", os.path.join(work, "preview"), "--cell", "480x270"])
        g = os.path.join(work, "preview", "grid.png")
        if not os.path.exists(g):
            raise RuntimeError("联系表未生成")
    step("6. preview_mp4", preview)

    # ---- 7. 生成 bat 并校验 GBK ----
    def bats():
        b1 = os.path.join(work, "转MP4.bat")
        b2 = os.path.join(work, "加配乐.bat")
        run([PY, os.path.join(ROOT, "scripts", "utils", "gen_transcode_bat.py"),
             "--src", os.path.join(work, "片头.mov"),
             "--dst", os.path.join(work, "片头.mp4"), "--out", b1])
        run([PY, os.path.join(ROOT, "scripts", "utils", "gen_bgm_bat.py"),
             "--video", os.path.join(work, "片头.mp4"), "--out", b2])
        for b in (b1, b2):
            raw = open(b, "rb").read()
            txt = raw.decode("gbk")
            if "片头" not in txt:
                raise RuntimeError("中文路径丢失: %s" % b)
    step("7. 生成 bat（GBK 校验）", bats)

    # ---- 8. py 语法编译 ----
    def compile_py():
        bad = []
        for dp, dns, fns in os.walk(ROOT):
            if "_work" in dp or "__pycache__" in dp:
                continue
            for f in fns:
                if f.endswith(".py"):
                    try:
                        py_compile.compile(os.path.join(dp, f), doraise=True)
                    except Exception as e:
                        bad.append("%s: %s" % (f, e))
        if bad:
            raise RuntimeError("; ".join(bad))
    step("8. 全部 py 语法编译", compile_py)

    # ---- 9. jsx 必须纯 ASCII ----
    def jsx_ascii():
        bad = []
        for dp, dns, fns in os.walk(ROOT):
            for f in fns:
                if f.endswith(".jsx"):
                    raw = open(os.path.join(dp, f), "rb").read()
                    over = [b for b in raw if b > 126]
                    if over:
                        bad.append("%s 含 %d 个非 ASCII 字节" % (f, len(over)))
        if bad:
            raise RuntimeError("; ".join(bad))
    step("9. jsx 纯 ASCII", jsx_ascii)

    # ---- 10. 不得残留个人信息 ----
    def no_pii():
        import re
        home = os.path.expanduser("~")
        user = os.path.basename(home)
        pats = [user, "WorkBuddy", "aelink"]
        hits = []
        for dp, dns, fns in os.walk(ROOT):
            if "_work" in dp or "__pycache__" in dp:
                continue
            for f in fns:
                if not f.endswith((".py", ".jsx", ".md", ".json", ".txt", ".bat")):
                    continue
                if f == os.path.basename(__file__):
                    continue      # 跳过检查器自身（pattern 字面量就在它里面）
                p = os.path.join(dp, f)
                try:
                    t = open(p, encoding="utf-8", errors="ignore").read()
                except Exception:
                    continue
                for pat in pats:
                    if pat and pat in t:
                        hits.append("%s <- %s" % (os.path.relpath(p, ROOT), pat))
        if hits:
            raise RuntimeError("残留个人信息: " + "; ".join(hits))
    step("10. 无个人信息残留", no_pii)

    # ---- 11. 桥接层序列化往返（需 node，没有则跳过）----
    def esc_probe():
        if shutil.which("node") is None:
            print("   (node 未安装，跳过)")
            return
        run([PY, os.path.join(HERE, "_esc_probe.py")])
    step("11. 序列化往返（Windows 路径/引号/换行/中文）", esc_probe)

    print("\n" + "=" * 52)
    ok = all(r[1] == "PASS" for r in results)
    for n, s, m in results:
        print("  %-28s %s %s" % (n, s, m))
    print("=" * 52)
    print("RESULT:", "PASS" if ok else "FAIL")
    if not args.keep and os.path.isdir(work):
        shutil.rmtree(work, ignore_errors=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
