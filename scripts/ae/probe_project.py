# -*- coding: utf-8 -*-
"""探测 AE 工程结构：合成 / 图层 / 文字内容 / 素材引用。只读，不保存。

用法:
  python probe_project.py --project <工程.aep> [--out probe.json] [--max-comp 40] [--max-layer 80]
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
var MAXC = __MAXC__, MAXL = __MAXL__;
try { app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES); } catch (e) { RESULT.closeErr = String(e); }
var proj = app.open(new File(F));
RESULT.file = F;
RESULT.appVersion = app.version;
RESULT.numItems = app.project.numItems;

var comps = [], i, j, it, c, lay, txt, srcName;
for (i = 1; i <= app.project.numItems && comps.length < MAXC; i++) {
    it = app.project.item(i);
    if (!(it instanceof CompItem)) continue;
    c = it;
    var info = { name: c.name, w: c.width, h: c.height, dur: c.duration,
                 fps: c.frameRate, layers: c.numLayers, bg: String(c.bgColor), items: [] };
    for (j = 1; j <= c.numLayers && info.items.length < MAXL; j++) {
        lay = c.layer(j);
        srcName = ""; txt = "";
        if (lay.source) { srcName = lay.source.name; }
        if (lay instanceof TextLayer) {
            try { txt = lay.property("Source Text").value.text; } catch (e) { txt = "(read err)"; }
            if (txt.length > 120) txt = txt.substring(0, 120) + "...";
        }
        var ty = "other";
        if (lay instanceof TextLayer) ty = "text";
        else if (lay instanceof AVLayer && lay.source instanceof CompItem) ty = "precomp";
        else if (lay instanceof AVLayer) ty = "footage";
        else if (lay instanceof ShapeLayer) ty = "shape";
        else if (lay instanceof CameraLayer) ty = "camera";
        else if (lay instanceof LightLayer) ty = "light";
        info.items.push({ i: j, n: String(lay.name), t: ty,
                          inP: lay.inPoint, outP: lay.outPoint, st: lay.startTime,
                          src: String(srcName), txt: txt,
                          en: lay.enabled, sole: (lay.solo ? true : false) });
    }
    comps.push(info);
}
RESULT.comps = comps;

var ft = [], k;
for (k = 1; k <= app.project.numItems && ft.length < 60; k++) {
    it = app.project.item(k);
    if (it instanceof FootageItem) {
        ft.push({ name: it.name, w: it.width, h: it.height,
                  dur: it.duration, fps: it.frameRate,
                  miss: (it.footageMissing ? true : false) });
    }
}
RESULT.footage = ft;
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--out", default="probe_project.json")
    ap.add_argument("--max-comp", type=int, default=40)
    ap.add_argument("--max-layer", type=int, default=80)
    args = ap.parse_args()

    body = (BODY.replace("__F__", args.project.replace("\\", "/"))
                .replace("__MAXC__", str(args.max_comp))
                .replace("__MAXL__", str(args.max_layer)))
    r = run(body, "probe_result.json", timeout=900)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)

    if "__error" in r:
        print("ERROR:", r["__error"])
        sys.exit(1)
    for c in r.get("comps", []):
        print("  [%s] %sx%s %.2fs %.3ffps 图层%d" %
              (c["name"], c["w"], c["h"], c["dur"], c["fps"], c["layers"]))
    print("素材数:", len(r.get("footage", [])))
    print("JSON ->", args.out)


if __name__ == "__main__":
    main()
