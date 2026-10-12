# -*- coding: utf-8 -*-
"""AE 常驻服务客户端（旁路通道）。

与 ae_bridge.run() 的区别：run() 每次都要投递一段脚本并等待 AE 处理
（AE 没开时还要拉起进程）；本模块先注入一次的常驻任务，之后所有命令都通过
文件队列下发，AE 里已有定时器在跑，来回更快，也不会反复启动进程。

典型用法:
    from ae_daemon import submit
    r = submit("RESULT.layers = app.project.activeItem.numLayers")
    print(r)                      # {'layers': 42}

依赖：scripts/ae/persistent/install_daemon.jsx
前置：AE 需在「首选项 > 常规」里勾选「允许脚本写入文件和访问网络」。
"""
import json
import os
import time
import uuid

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
sys_path_added = False
try:
    from ae_bridge import AFTERFX, WORK, ae_running  # noqa: F401
except ImportError:
    import sys
    sys.path.insert(0, os.path.join(HERE, ".."))
    from ae_bridge import AFTERFX, WORK, ae_running  # noqa: F401

INSTALL_JSX = os.path.join(HERE, "install_daemon.jsx")
QUEUE_DIR = os.path.join(WORK, "ae_daemon_queue")
_state = {"installed": False}


def _install():
    os.makedirs(QUEUE_DIR, exist_ok=True)
    src = open(INSTALL_JSX, encoding="ascii", errors="ignore").read()
    src = src.replace("__DIR__", QUEUE_DIR.replace("\\", "/"))
    tmp = os.path.join(WORK, "_ae_install_daemon.jsx")
    with open(tmp, "w", encoding="ascii", errors="ignore") as f:
        f.write(src)
    import subprocess
    cmd = [AFTERFX]
    if not ae_running():
        cmd.append("-noui")
    cmd += ["-r", tmp]
    subprocess.run(cmd, capture_output=True)
    _state["installed"] = True


def submit(code, timeout=180):
    """下发一段 ExtendScript，返回 RESULT dict。code 里给 RESULT 赋值即可。"""
    if not _state["installed"]:
        _install()
        time.sleep(2.0)          # 等 scheduleTask 起来

    cid = uuid.uuid4().hex[:12]
    cmd_path = os.path.join(QUEUE_DIR, cid + ".cmd.jsx")
    res_path = os.path.join(QUEUE_DIR, cid + ".json")
    if os.path.exists(res_path):
        os.remove(res_path)

    with open(cmd_path, "w", encoding="utf-8") as f:
        f.write(code)

    t0 = time.time()
    while time.time() - t0 < timeout:
        if os.path.exists(res_path) and os.path.getsize(res_path) > 0:
            time.sleep(0.1)
            break
        time.sleep(0.2)
    else:
        if os.path.exists(cmd_path):
            os.remove(cmd_path)
        raise TimeoutError("daemon 在 %ss 内没回结果：%s" % (timeout, res_path))

    return json.loads(open(res_path, encoding="utf-8").read())


if __name__ == "__main__":
    import sys
    code = sys.argv[1] if len(sys.argv) > 1 else "RESULT.pong = __aeDaePing ? __aeDaePing() : 'no-daemon';"
    print(json.dumps(submit(code), ensure_ascii=False, indent=1))
