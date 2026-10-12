# -*- coding: utf-8 -*-
"""验证桥接层内置 __str/__esc 的序列化往返（重点是 Windows 路径、引号、换行、中文）。

ExtendScript 是 ES3，没有 JSON 对象，ae_bridge 靠模板内置的 __str() 回传结果。
这个测试把那段逻辑抽出来喂复杂数据，确认输出能被标准 json 解析器读回且值不变。
需要 node；没有 node 时 test_offline.py 会跳过本项。
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts", "ae"))
from ae_bridge import TEMPLATE  # noqa: E402

# Windows 控制台/管道默认非 UTF-8（常见 cp1252），直接 print 中文会抛
# UnicodeEncodeError 使脚本以退出码 1 结束；Linux/macOS 默认 UTF-8 不受影响。
# 统一在处理前改掉，保证跨平台输出一致。
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

m = re.search(r"function __esc.*?\n    \}\n    function __str.*?\n    \}\n", TEMPLATE, re.S)
if not m:
    print("FAIL: 无法从 TEMPLATE 提取序列化函数")
    sys.exit(1)
code = m.group(0)

JS = code + r'''
var cases = {
  winpath: "C:\\projects\\demo.aep",
  quote:   'he said "hi"',
  backsl:  "a\\b",
  newline: "line1\nline2",
  cjk:     "总合成 标题",
  empty:   "",
  num:     -12.5,
  nul:     null,
  arr:     [1, "two", false],
  nested:  { a: { b: "deep" } }
};
console.log(__str(cases));
'''

p = os.path.join(HERE, "_esc_tmp.js")
open(p, "w", encoding="utf-8").write(JS)

r = subprocess.run(["node", p], capture_output=True, text=True, encoding="utf-8")
if os.path.exists(p):
    os.remove(p)
if r.returncode != 0:
    print("NODE ERR:", r.stderr[:400])
    sys.exit(1)

raw = r.stdout.strip()
print("RAW :", raw[:200])

try:
    d = json.loads(raw)
except Exception as e:
    print("PARSE FAIL:", e)
    sys.exit(1)

print("PARSE OK")
expect = {
    "winpath": "C:\\projects\\demo.aep",
    "quote": 'he said "hi"',
    "backsl": "a\\b",
    "newline": "line1\nline2",
    "cjk": "总合成 标题",
    "empty": "",
}
ok = True
for k, v in expect.items():
    good = d.get(k) == v
    ok = ok and good
    print("  %-8s %-6s got=%r" % (k, "OK" if good else "FAIL", d.get(k)))

print("  num     %-6s got=%r" % ("OK" if d.get("num") == -12.5 else "FAIL", d.get("num")))
print("  null    %-6s got=%r" % ("OK" if d.get("nul") is None else "FAIL", d.get("nul")))
print("  nested  %-6s got=%r" % ("OK" if d.get("nested", {}).get("a", {}).get("b") == "deep" else "FAIL",
                                 d.get("nested")))
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
