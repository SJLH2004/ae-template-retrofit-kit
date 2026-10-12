# -*- coding: utf-8 -*-
"""修正总合成时间轴：pre1 从 0 起播，pre2 在切点接上，总时长截断。

坑：嵌套 precomp 层的 startTime 可能是负值（模板刻意跳过开头），
只改 outPoint 不改 startTime 会导致画面偏移、第一组内容被跳过。

用法:
  python fix_timeline.py --project <工程.aep> [--main 总合成] \
      [--pre1 1] [--pre2 2] [--split 24.8] [--total 30]
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
var F = "__F__";
try { app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES); } catch (e) {}
var proj = app.open(new File(F));
function findComp(n){ for(var k=1;k<=app.project.numItems;k++){ var it=app.project.item(k); if(it instanceof CompItem && it.name===n) return it; } return null; }
var total = findComp("__MAIN__");
if (!total) throw new Error("合成不存在: __MAIN__");
var done = [];
for (var j = 1; j <= total.numLayers; j++) {
  var L = total.layer(j);
  var sn = L.source ? String(L.source.name) : "";
  if (sn === "__PRE1__") { L.startTime = 0; L.inPoint = 0; L.outPoint = __SPLIT__; done.push("__PRE1__:st=0,out=__SPLIT__"); }
  else if (sn === "__PRE2__") { L.startTime = __SPLIT__; L.inPoint = __SPLIT__; L.outPoint = __TOTAL__; done.push("__PRE2__:st=__SPLIT__,out=__TOTAL__"); }
}
total.duration = __TOTAL__;
proj.save();
RESULT.done = done;
RESULT.dur = total.duration;
RESULT.after = [];
for (var j2 = 1; j2 <= total.numLayers; j2++) {
  var L2 = total.layer(j2);
  RESULT.after.push({ n: L2.source ? String(L2.source.name) : "?", st: L2.startTime, inP: L2.inPoint, outP: L2.outPoint });
}
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--main", default="总合成")
    ap.add_argument("--pre1", default="1")
    ap.add_argument("--pre2", default="2")
    ap.add_argument("--split", type=float, default=24.8)
    ap.add_argument("--total", type=float, default=30)
    args = ap.parse_args()

    body = (BODY.replace("__F__", args.project.replace("\\", "/"))
                .replace("__MAIN__", args.main)
                .replace("__PRE1__", args.pre1)
                .replace("__PRE2__", args.pre2)
                .replace("__SPLIT__", str(args.split))
                .replace("__TOTAL__", str(args.total)))
    r = run(body, "fix_timeline_result.json", timeout=900)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    if "__error" in r:
        sys.exit(1)


if __name__ == "__main__":
    main()
