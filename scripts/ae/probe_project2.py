# -*- coding: utf-8 -*-
"""二次探测：分镜合成时间轴 + 图片层缩放 + 文字层排版参数（改文案/换图前必看）。

用法:
  python probe_project2.py --project <工程.aep> --main <主合成名> \
      --group-count 6 --text-prefix 文字合成 --img-prefix 图片 \
      [--title-comp 标题] [--end-comp 2] [--out probe2.json]
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
var i, j, it, c, lay, out = {};

function findComp(n) {
  for (var k = 1; k <= app.project.numItems; k++) {
    it = app.project.item(k);
    if (it instanceof CompItem && it.name === n) return it;
  }
  return null;
}
function pad(n) { return (n < 10 ? "0" : "") + n; }

c = findComp("__MAIN__");
if (c) {
  var all = [];
  for (j = 1; j <= c.numLayers; j++) {
    lay = c.layer(j);
    all.push({ i: j, n: String(lay.name), inP: lay.inPoint, outP: lay.outPoint,
               st: lay.startTime,
               src: lay.source ? String(lay.source.name) : "",
               t: (lay instanceof TextLayer) ? "text" :
                  ((lay instanceof AVLayer && lay.source instanceof CompItem) ? "precomp" : "av") });
  }
  out.comp1 = { dur: c.duration, fps: c.frameRate, layers: all };
}

var shots = [], s;
for (s = 1; s <= __GC__; s++) {
  c = findComp("__IP__" + pad(s));
  if (!c) continue;
  var ls = [];
  for (j = 1; j <= c.numLayers; j++) {
    lay = c.layer(j);
    var tr = lay.property("Transform");
    var sc = [0,0], ps = [0,0], an = [0,0];
    try { sc = tr.property("Scale").value; } catch(e){}
    try { ps = tr.property("Position").value; } catch(e){}
    try { an = tr.property("Anchor Point").value; } catch(e){}
    ls.push({ i: j, n: String(lay.name), src: lay.source ? String(lay.source.name) : "",
              inP: lay.inPoint, outP: lay.outPoint,
              scale: sc, pos: ps, anchor: an,
              sw: lay.source ? lay.source.width : 0, sh: lay.source ? lay.source.height : 0 });
  }
  shots.push({ comp: "__IP__" + pad(s), dur: c.duration, layers: ls });
}
out.shots = shots;

var tc = [];
for (i = 1; i <= __GC__; i++) {
  c = findComp("__TP__" + pad(i));
  if (!c) continue;
  var tl = [];
  for (j = 1; j <= c.numLayers; j++) {
    lay = c.layer(j);
    if (!(lay instanceof TextLayer)) continue;
    var td = lay.property("Source Text").value;
    tr = lay.property("Transform");
    var p2 = [0,0];
    try { p2 = tr.property("Position").value; } catch(e){}
    tl.push({ i: j, n: String(lay.name), text: String(td.text),
              font: String(td.font), size: td.fontSize,
              pos: p2, justify: String(td.justification),
              box: (td.boxText ? [td.boxTextSize[0], td.boxTextSize[1]] : null) });
  }
  tc.push({ comp: "__TP__" + pad(i), texts: tl });
}
out.textComps = tc;

c = findComp("__TC__");
if (c) {
  var t2 = [];
  for (j = 1; j <= c.numLayers; j++) {
    lay = c.layer(j);
    if (!(lay instanceof TextLayer)) continue;
    var td2 = lay.property("Source Text").value;
    var tr2 = lay.property("Transform");
    var p3=[0,0], s3=[0,0];
    try { p3 = tr2.property("Position").value; } catch(e){}
    try { s3 = tr2.property("Scale").value; } catch(e){}
    t2.push({ i: j, n: String(lay.name), text: String(td2.text),
              font: String(td2.font), size: td2.fontSize, pos: p3, scale: s3,
              box: (td2.boxText ? [td2.boxTextSize[0], td2.boxTextSize[1]] : null) });
  }
  out.title = t2;
}

c = findComp("__EC__");
if (c) {
  var e2 = [];
  for (j = 1; j <= c.numLayers; j++) {
    lay = c.layer(j);
    if (lay instanceof TextLayer) {
      var td3 = lay.property("Source Text").value;
      e2.push({ i: j, n: String(lay.name), text: String(td3.text),
                font: String(td3.font), size: td3.fontSize });
    }
  }
  out.comp2Texts = e2;
  out.comp2Dur = c.duration;
}
RESULT = out;
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--main", default="1", help="分镜主 precomp 名")
    ap.add_argument("--group-count", type=int, default=6)
    ap.add_argument("--text-prefix", default="文字合成")
    ap.add_argument("--img-prefix", default="图片")
    ap.add_argument("--title-comp", default="标题")
    ap.add_argument("--end-comp", default="2")
    ap.add_argument("--out", default="probe_project2.json")
    args = ap.parse_args()

    body = (BODY.replace("__F__", args.project.replace("\\", "/"))
                .replace("__MAIN__", args.main)
                .replace("__GC__", str(args.group_count))
                .replace("__IP__", args.img_prefix)
                .replace("__TP__", args.text_prefix)
                .replace("__TC__", args.title_comp)
                .replace("__EC__", args.end_comp))
    r = run(body, "probe2_result.json", timeout=900)
    json.dump(r, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if "__error" in r:
        print("ERROR:", r["__error"])
        sys.exit(1)
    print("comp layers:", len(r.get("comp1", {}).get("layers", [])))
    print("shots:", len(r.get("shots", [])))
    print("textComps:", len(r.get("textComps", [])))
    print("title texts:", len(r.get("title", [])))
    print("saved ->", args.out)


if __name__ == "__main__":
    main()
