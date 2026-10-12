# -*- coding: utf-8 -*-
"""列出 AE 输出模块（OM）与渲染设置（RS）模板名。

出片前先跑这个，确认本机到底有哪些输出模板——很多机器并没有 PNG 序列模板，
用 om_keyword="PNG" 会落到「多机序列」= PSD 序列（4MB/帧）。

用法:
  python probe_output_modules.py [--project <工程.aep>] [--comp 总合成]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ae_bridge import run  # noqa: E402

# Windows 控制台/管道默认非 UTF-8（常见 cp1252），直接 print 中文会抛
# UnicodeEncodeError 使脚本以退出码 1 结束；Linux/macOS 默认 UTF-8 不受影响。
# 统一在处理前改掉，保证跨平台输出一致。
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

BODY = r'''
var proj = app.project;
var F = "__F__";
if (F !== "") {
  try { app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES); } catch (e) {}
  proj = app.open(new File(F));
}
var c = null, i, it;
for (i = 1; i <= proj.numItems; i++) {
  it = proj.item(i);
  if (it instanceof CompItem && it.name === "__COMP__") { c = it; break; }
}
if (!c) {
  for (i = 1; i <= proj.numItems; i++) {
    it = proj.item(i);
    if (it instanceof CompItem) { c = it; break; }
  }
}
if (!c) { throw new Error("工程里没有可用的合成"); }
var rq = proj.renderQueue;
while (rq.numItems > 0) { rq.item(rq.numItems).remove(); }
var rqi = rq.items.add(c);
var om = rqi.outputModule(1);
var names = om.templates, arr = [];
for (var t = 0; t < names.length; t++) arr.push(names[t]);
RESULT.comp = c.name;
RESULT.omTemplates = arr;
RESULT.rsTemplates = rqi.templates;
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="", help="可选；不填则用当前已打开的工程")
    ap.add_argument("--comp", default="总合成")
    args = ap.parse_args()

    body = BODY.replace("__F__", args.project.replace("\\", "/")).replace("__COMP__", args.comp)
    r = run(body, "probe_om_result.json", timeout=600)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    if "__error" in r:
        sys.exit(1)


if __name__ == "__main__":
    main()
