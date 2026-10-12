# -*- coding: utf-8 -*-
"""回读改造后的工程，确认文字 / 图片 / 时长都改对了。只读。

用法:
  python verify_project.py --project <工程.aep> [--out verify.json] \
      [--group-count 6] [--title-comp 标题] [--end-comp 2] [--main 总合成]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ae_bridge import run  # noqa: E402

BODY = r'''
var F = "__F__";
try { app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES); } catch (e) {}
var proj = app.open(new File(F));
var out = { comps: [], total: null };
function findComp(n) {
  for (var k = 1; k <= app.project.numItems; k++) {
    var it = app.project.item(k);
    if (it instanceof CompItem && it.name === n) return it;
  }
  return null;
}
function pad(n) { return (n < 10 ? "0" : "") + n; }
for (var i = 1; i <= __GC__; i++) {
  var nm = "文字合成" + pad(i);
  var c = findComp(nm);
  if (!c) continue;
  var ts = [];
  for (var j = 1; j <= c.numLayers; j++) {
    var L = c.layer(j);
    if (L instanceof TextLayer) {
      ts.push(String(L.property("Source Text").value.text).replace(/\r/g, " | "));
    }
  }
  out.comps.push({ n: nm, t: ts });
}
var tc = findComp("__TC__");
if (tc) {
  var ts2 = [];
  for (var j2 = 1; j2 <= tc.numLayers; j2++) {
    var L2 = tc.layer(j2);
    if (L2 instanceof TextLayer) {
      ts2.push({ txt: String(L2.property("Source Text").value.text).replace(/\r/g, "/"),
                 en: L2.enabled });
    }
  }
  out.title = ts2;
}
var c2 = findComp("__EC__");
if (c2) {
  for (var j3 = 1; j3 <= c2.numLayers; j3++) {
    var L3 = c2.layer(j3);
    if (L3 instanceof TextLayer) {
      out.end = String(L3.property("Source Text").value.text).replace(/\r/g, " | ");
    }
  }
}
var imgs = [];
for (var s = 1; s <= __GC__; s++) {
  var sn = "图片" + pad(s);
  var sc = findComp(sn);
  if (!sc) continue;
  for (var j4 = 1; j4 <= sc.numLayers; j4++) {
    var L4 = sc.layer(j4);
    if (L4.source && L4.source instanceof FootageItem) {
      var ln = String(L4.source.name).toLowerCase();
      if (ln.indexOf(".jpg") >= 0 || ln.indexOf(".jpeg") >= 0 || ln.indexOf(".png") >= 0) {
        imgs.push(sn + " -> " + String(L4.source.name) + " scale=" + Math.round(L4.property("Transform").property("Scale").value[0]));
      }
    }
  }
}
out.imgs = imgs;
var tt = findComp("__MAIN__");
if (tt) {
  out.total = { dur: tt.duration, w: tt.width, h: tt.height, fps: tt.frameRate };
  var ls = [];
  for (var j5 = 1; j5 <= tt.numLayers; j5++) {
    var L5 = tt.layer(j5);
    ls.push(String(L5.source ? L5.source.name : "?") + " in=" + L5.inPoint.toFixed(2) + " out=" + L5.outPoint.toFixed(2));
  }
  out.total.layers = ls;
}
RESULT = out;
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--out", default="verify_project.json")
    ap.add_argument("--group-count", type=int, default=6)
    ap.add_argument("--title-comp", default="标题")
    ap.add_argument("--end-comp", default="2")
    ap.add_argument("--main", default="总合成")
    args = ap.parse_args()

    body = (BODY.replace("__F__", args.project.replace("\\", "/"))
                .replace("__GC__", str(args.group_count))
                .replace("__TC__", args.title_comp)
                .replace("__EC__", args.end_comp)
                .replace("__MAIN__", args.main))
    r = run(body, "verify_result.json", timeout=900)
    json.dump(r, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if "__error" in r:
        print("ERROR:", r["__error"])
        sys.exit(1)
    for c in r.get("comps", []):
        print("[%s]" % c["n"])
        for t in c["t"]:
            print("   ", t)
    print("\n[标题]")
    for t in r.get("title", []):
        print("   %r enabled=%s" % (t["txt"], t["en"]))
    print("\n[结尾]", r.get("end"))
    print("\n[图片]")
    for i in r.get("imgs", []):
        print("   ", i)
    print("\n[总合成]", r.get("total"))


if __name__ == "__main__":
    main()
