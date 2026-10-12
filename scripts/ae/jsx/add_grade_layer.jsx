/* Add a colour-grading adjustment layer on top of the target comp. ASCII only.

   Placeholders filled by scripts/ae/add_grade_layer.py:
     __OUT__  result JSON path
     __AEP__  project path
     __CFG__  JSON object

   Notes learned the hard way:
     * ExtendScript is ES3 -> there is no JSON object. Result is serialised by hand.
     * addSolid puts the new layer at index 1 already; calling
       moveBefore(comp.layer(1)) moves it before ITSELF and throws
       "Unable to move layer". Always guard with an identity check.
     * On AE 2023 "ADBE Color Balance" exposes 3 sliders (red/green/blue
       balance), not a 3-zone shadow/mid/high control.
     * Hue/Saturation could not be added on this build - all three candidate
       matchNames fail - so saturation is handled on the ffmpeg side instead.
*/
var OUT = "__OUT__";
var AEP = "__AEP__";
var CFG = __CFG__;
var res = { ok: false, steps: [], err: "" };

function esc(s) {
    s = String(s);
    s = s.replace(/\\/g, "\\\\").replace(/"/g, "\\\"");
    s = s.replace(/\n/g, " ").replace(/\r/g, " ");
    return s;
}
function arrJson(a) {
    var b = [], i;
    for (i = 0; i < a.length; i++) { b.push("\"" + esc(a[i]) + "\""); }
    return "[" + b.join(",") + "]";
}
function writeRes() {
    var f = new File(OUT);
    f.encoding = "UTF-8";
    f.open("w");
    var s = "{\"ok\":" + (res.ok ? "true" : "false") +
        ",\"steps\":" + arrJson(res.steps) +
        ",\"err\":\"" + esc(res.err) + "\"";
    if (res.cbParams) { s += ",\"cbParams\":" + arrJson(res.cbParams); }
    s += "}";
    f.write(s);
    f.close();
}

try {
    if (app.project && app.project.file && app.project.dirty) {
        app.project.save();
        res.steps.push("saved previous dirty project");
    }
    app.beginUndoGroup("grade layer");
    app.open(new File(AEP));

    var proj = app.project, comp = null, i, it;
    for (i = 1; i <= proj.numItems; i++) {
        it = proj.item(i);
        if (it instanceof CompItem && it.width === CFG.w && it.height === CFG.h &&
            it.duration >= CFG.durMin && it.duration <= CFG.durMax) {
            comp = it;
            break;
        }
    }
    if (!comp) {
        throw new Error("no comp matches " + CFG.w + "x" + CFG.h +
                        " dur " + CFG.durMin + "~" + CFG.durMax);
    }
    res.steps.push("comp: " + comp.name + " dur=" + comp.duration);

    for (var j = comp.numLayers; j >= 1; j--) {
        if (comp.layer(j).name === CFG.layer) {
            comp.layer(j).remove();
            res.steps.push("removed old " + CFG.layer);
        }
    }

    var adj = comp.layers.addSolid([1, 1, 1], CFG.layer, comp.width, comp.height,
                                   comp.pixelAspect, comp.duration);
    adj.adjustmentLayer = true;
    if (comp.layer(1) !== adj) { adj.moveBefore(comp.layer(1)); }
    res.steps.push("adjustment layer added on top");

    var fx = adj.property("ADBE Effect Parade").addProperty(
        CFG.mode === "gamma" ? "ADBE Easy Levels" : "ADBE Color Balance");
    var names = [], setCount = 0, p, pr;
    for (p = 1; p <= fx.numProperties; p++) {
        pr = fx.property(p);
        names.push(p + ":" + pr.name + "[" + pr.matchName + "]");
    }
    res.cbParams = names;

    if (CFG.mode === "gamma") {
        /* Easy Levels per-channel gamma: endpoints (0/255) stay put, midtones shift
           the most -> paper-white highlights are NOT tinted. This is the AE-side
           equivalent of ffmpeg's zoned colorbalance.
           Params verified on AE 2023: -0001 channel popup, -0005 gamma.
           ("ADBE Levels" / "ADBE Curves" do NOT exist on this build.) */
        function setGamma(ch, g) {
            fx.property("ADBE Easy Levels-0001").setValue(ch);
            fx.property("ADBE Easy Levels-0005").setValue(g);
        }
        try {
            setGamma(2, CFG.gammas[0]);   // Red   <1 darkens red midtones (>1 lifts)
            setGamma(3, CFG.gammas[1]);   // Green >1 lifts green midtones
            setGamma(4, CFG.gammas[2]);   // Blue  ~1 = neutral
            setCount = 3;
            var rb = [];
            for (var cc = 1; cc <= 5; cc++) {
                fx.property("ADBE Easy Levels-0001").setValue(cc);
                rb.push("ch" + cc + "=" + fx.property("ADBE Easy Levels-0005").value);
            }
            res.readback = rb;
            res.steps.push("gamma set R=" + CFG.gammas[0] + " G=" + CFG.gammas[1] +
                           " B=" + CFG.gammas[2] + " | readback " + rb.join(" "));
        } catch (eG) {
            res.steps.push("WARN gamma set failed: " + String(eG));
        }
    } else {
        for (p = 1; p <= fx.numProperties; p++) {
            pr = fx.property(p);
            if (pr.propertyType === PropertyType.PROPERTY && pr.value !== null &&
                typeof pr.value === "number" && setCount < CFG.cb.length) {
                try { pr.setValue(CFG.cb[setCount]); setCount++; } catch (e1) {}
            }
        }
        res.steps.push("color balance sliders set: " + setCount);
    }
    res.setCount = setCount;

    app.project.save();
    res.steps.push("project saved");
    app.endUndoGroup();
    res.ok = true;
} catch (e) {
    res.err = String(e);
    try { app.endUndoGroup(); } catch (e2) {}
}
writeRes();
