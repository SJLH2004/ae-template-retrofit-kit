# -*- coding: utf-8 -*-
"""AE 模板工程批量改造（配置驱动）。

打开原始模板 -> 另存为新工程（原文件不动）-> 按配置替换：
  * N 组分镜文案（横排词 / 竖排上下字 / 拼音 / 诗句）
  * 落版标题（竖排 N 字 + 横排主标题，多余竖排字停用）
  * 结尾语
  * N 张图片（replaceSource + 缩放补偿，保持显示尺寸不变）
  * 时间轴重排（precomp 衔接点 + 总时长）

用法:
  python retrofit_project.py --src <模板.aep> --save <新工程.aep> --config content.json

配置结构见 config/example_content.json。markers / title_y / comp_names 必须先用
probe_project.py 探明你的模板实际结构再填——不同模板的占位文字关键词不一样。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ae_bridge import run  # noqa: E402

BODY = r'''
var D = __DATA__;
var log = [];

function findComp(n) {
  for (var k = 1; k <= app.project.numItems; k++) {
    var it = app.project.item(k);
    if (it instanceof CompItem && it.name === n) return it;
  }
  return null;
}
function setTxt(lay, s) {
  if (!lay || !(lay instanceof TextLayer)) { log.push("skip not text"); return false; }
  var td = lay.property("Source Text").value;
  td.text = s;
  lay.property("Source Text").setValue(td);
  return true;
}
function inAny(s, arr) {
  for (var i = 0; i < arr.length; i++) { if (s.indexOf(arr[i]) >= 0) return true; }
  return false;
}
var M = D.markers, CN = D.comp_names;

// ---------- 1. 打开并另存 ----------
try { app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES); } catch (e) {}
var proj = app.open(new File("__SRC__"));
RESULT.opened = proj.file ? proj.file.name : "?";
proj.save(new File("__SAVE__"));
RESULT.savedAs = "__SAVE__";

// ---------- 2. N 组分镜文案 ----------
RESULT.groups = [];
for (var g = 0; g < D.groups.length; g++) {
  var G = D.groups[g];
  var c = findComp(G.comp);
  if (!c) { RESULT.groups.push(G.comp + ":NOTFOUND"); continue; }
  var ok = 0;
  for (var j = 1; j <= c.numLayers; j++) {
    var lay = c.layer(j);
    if (!(lay instanceof TextLayer)) continue;
    var cur = String(lay.property("Source Text").value.text);
    if (cur.indexOf(M.l1) >= 0 && cur.length <= 4) { if (setTxt(lay, G.l1)) ok++; }
    else if (inAny(cur, M.updown)) {
      var y = lay.property("Transform").property("Position").value[1];
      if (setTxt(lay, (y < 400 ? G.up : G.dn))) ok++;
    }
    else if (inAny(cur, M.pinyin)) { if (setTxt(lay, G.py)) ok++; }
    else if (cur.indexOf(M.poem) >= 0) { if (setTxt(lay, G.po)) ok++; }
  }
  RESULT.groups.push(G.comp + ":" + ok);
}

// ---------- 3. 落版标题 ----------
var tc = findComp(CN.title);
if (tc) {
  var tn = 0, nUp = D.title.up.length;
  for (var j2 = 1; j2 <= tc.numLayers; j2++) {
    var L = tc.layer(j2);
    if (!(L instanceof TextLayer)) continue;
    var cur2 = String(L.property("Source Text").value.text);
    var y2 = L.property("Transform").property("Position").value[1];
    if (cur2.indexOf(M.title_main) >= 0) { if (setTxt(L, D.title.l1)) tn++; }
    else {
      var hit = -1;
      for (var q = 0; q < D.title_y.length; q++) {
        if (Math.abs(y2 - D.title_y[q]) < 60) { hit = q; break; }
      }
      if (hit >= 0) {
        if (hit < nUp) {
          var keepStrip = cur2.replace(/[^0-9A-Za-z\u4e00-\u9fa5]/g, "");
          var tail = cur2.substring(keepStrip.length);
          if (setTxt(L, D.title.up[hit] + tail)) tn++;
        } else {
          L.enabled = false; tn++;
        }
      }
    }
  }
  RESULT.title = tn;
}

// ---------- 4. 结尾语 ----------
var c2 = findComp(CN.ending_comp);
if (c2) {
  for (var j3 = 1; j3 <= c2.numLayers; j3++) {
    var L3 = c2.layer(j3);
    if (!(L3 instanceof TextLayer)) continue;
    var cur3 = String(L3.property("Source Text").value.text);
    if (cur3.indexOf(M.ending) >= 0) { setTxt(L3, D.end); RESULT.end = 1; }
  }
}

// ---------- 5. 换图 + 缩放补偿 ----------
RESULT.imgs = [];
for (var s = 0; s < D.imgs.length; s++) {
  var scName = CN.img_prefix + ((s + 1) < 10 ? "0" : "") + (s + 1);
  var sc = findComp(scName);
  if (!sc) { RESULT.imgs.push(scName + ":NOTFOUND"); continue; }
  var nf = new File(D.imgs[s]);
  if (!nf.exists) { RESULT.imgs.push(scName + ":NOFILE " + D.imgs[s]); continue; }
  var io = new ImportOptions(nf);
  var newItem = app.project.importFile(io);
  var replaced = 0;
  for (var j4 = 1; j4 <= sc.numLayers; j4++) {
    var L4 = sc.layer(j4);
    if (!(L4 instanceof AVLayer)) continue;
    if (!L4.source || !(L4.source instanceof FootageItem)) continue;
    var nm = String(L4.source.name).toLowerCase();
    if (nm.indexOf(".jpg") < 0 && nm.indexOf(".jpeg") < 0 && nm.indexOf(".png") < 0) continue;
    var oldW = L4.source.width;
    var ratio = oldW / newItem.width;
    L4.replaceSource(newItem, false);
    var sp = L4.property("Transform").property("Scale");
    var sv = sp.value;
    sp.setValue([sv[0] * ratio, sv[1] * ratio, sv[2]]);
    replaced++;
  }
  RESULT.imgs.push(scName + ":" + replaced);
}

// ---------- 6. 时间轴 ----------
var IE = D.timeline.img_early;
if (IE && IE.comp) {
  var pE = findComp(IE.comp);
  if (pE) {
    for (var j5 = 1; j5 <= pE.numLayers; j5++) {
      var L5 = pE.layer(j5);
      if (L5.inPoint > IE.detect_min && L5.inPoint < IE.detect_max) L5.inPoint = IE.set;
    }
    RESULT.imgEarly = IE.comp;
  }
}
var total = findComp(CN.main);
if (total) {
  for (var j6 = 1; j6 <= total.numLayers; j6++) {
    var L6 = total.layer(j6);
    var sn = L6.source ? String(L6.source.name) : "";
    if (sn === CN.pre1) { L6.startTime = 0; L6.inPoint = 0; L6.outPoint = D.timeline.split; }
    else if (sn === CN.pre2) { L6.startTime = D.timeline.split; L6.inPoint = D.timeline.split; L6.outPoint = D.timeline.total; }
  }
  total.duration = D.timeline.total;
  RESULT.totalDur = total.duration;
}

proj.save();
RESULT.log = log;
'''


def main():
    ap = argparse.ArgumentParser(description="AE template retrofit (config driven)")
    ap.add_argument("--src", required=True, help="source template .aep")
    ap.add_argument("--save", required=True, help="output .aep (source stays untouched)")
    ap.add_argument("--config", required=True, help="content JSON, see config/example_content.json")
    args = ap.parse_args()

    cfg = json.load(open(args.config, encoding="utf-8"))
    data = {
        "comp_names": cfg["comp_names"],
        "markers": cfg["markers"],
        "title_y": cfg["title_y"],
        "timeline": cfg["timeline"],
        "groups": [
            {"comp": g["comp"], "l1": g["l1"], "up": g["up"], "dn": g["dn"],
             "py": g["py"], "po": g["po"]} for g in cfg["groups"]
        ],
        "title": cfg["title"],
        "end": cfg["end"],
        "imgs": [p.replace("\\", "/") for p in cfg["imgs"]],
    }

    body = (BODY
            .replace("__SRC__", args.src.replace("\\", "/"))
            .replace("__SAVE__", args.save.replace("\\", "/"))
            .replace("__DATA__", json.dumps(data, ensure_ascii=False)))

    r = run(body, "retrofit_result.json", timeout=1800)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    if "__error" in r:
        sys.exit(1)


if __name__ == "__main__":
    main()
