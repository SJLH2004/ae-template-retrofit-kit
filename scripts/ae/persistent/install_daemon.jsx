/* AE persistent task daemon (bypass channel).
   Inject once via: AfterFX.exe [-noui] -r install_daemon.jsx
   It then stays alive for the whole AE session because ExtendScript shares a
   global environment across scripts, and app.scheduleTask keeps firing.

   Protocol (file queue, no network permission needed):
     * client writes   <dir>/<id>.cmd.jsx   (ExtendScript source; RESULT = {...})
     * daemon evals it, writes <dir>/<id>.json, removes the .cmd.jsx
   ASCII only. */

(function () {
    if (typeof __aeDaeTick === "function") {
        __aeDaeStatus = "already-installed:" + __aeDaeDir;
        return;
    }

    __aeDaeDir = "__DIR__";
    __aeDaeCount = 0;

    function esc(s) {
        s = String(s);
        s = s.replace(/\\/g, "\\\\").replace(/"/g, "\\\"");
        s = s.replace(/\n/g, "\\n").replace(/\r/g, "\\r").replace(/\t/g, "\\t");
        return s;
    }
    function str(v) {
        var t = typeof v, i, a, k;
        if (v === null || v === undefined) { return "null"; }
        if (t === "string") { return "\"" + esc(v) + "\""; }
        if (t === "number" || t === "boolean") { return String(v); }
        if (v instanceof Array) {
            a = [];
            for (i = 0; i < v.length; i++) { a.push(str(v[i])); }
            return "[" + a.join(",") + "]";
        }
        if (t === "object") {
            a = [];
            for (k in v) {
                if (typeof v[k] !== "function" && v[k] !== undefined) {
                    a.push(str(k) + ":" + str(v[k]));
                }
            }
            return "{" + a.join(",") + "}";
        }
        return "\"" + esc(v) + "\"";
    }
    __aeDaeStr = str;

    __aeDaeTick = function () {
        try {
            var f = new Folder(__aeDaeDir);
            if (!f || !f.exists) { return; }
            var files = f.getFiles("*.cmd.jsx");
            if (!files || files.length === 0) { return; }
            for (var i = 0; i < files.length; i++) {
                var cf = files[i];
                var code = "";
                try {
                    cf.open("r");
                    cf.encoding = "UTF-8";
                    code = cf.read();
                    cf.close();
                } catch (e1) { try { cf.close(); } catch (e1b) {} }

                var RESULT = {};
                try { eval(code); } catch (e2) { RESULT.__error = String(e2); }

                var outPath = String(cf.fsName).replace(/\.cmd\.jsx$/i, ".json");
                try {
                    var of = new File(outPath);
                    of.encoding = "UTF-8";
                    of.open("w");
                    of.write(str(RESULT));
                    of.close();
                } catch (e3) {}
                try { cf.remove(); } catch (e4) {}
                __aeDaeCount++;
            }
        } catch (e5) {}
    };

    __aeDaePing = function () { return "pong:" + __aeDaeCount; };

    app.scheduleTask("__aeDaeTick()", 500, true);
    __aeDaeStatus = "installed:" + __aeDaeDir;
})();
