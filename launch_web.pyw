"""Double-click launcher: no console window, with actionable GUI errors."""

from pathlib import Path
import json
import os
import sys
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))


def launch():
    from offside_detect.web import AppServer, Workspace

    state = ROOT / ".local" / "web-address.json"
    if state.is_file():
        try:
            port = int(json.loads(state.read_text(encoding="utf-8"))["port"])
            if not 1 <= port <= 65535:
                raise ValueError("invalid saved port")
            url = f"http://127.0.0.1:{port}"
            with urlopen(url + "/api/health", timeout=1) as response:
                if json.load(response).get("app") == "offside-studio-v005":
                    webbrowser.open(url)
                    return
        except Exception:
            pass
    workspace = Workspace(ROOT / ".local" / "web-jobs")
    server = AppServer(("127.0.0.1", 0), workspace)
    state.write_text(json.dumps({"port": server.server_port}), encoding="utf-8")
    webbrowser.open(f"http://127.0.0.1:{server.server_port}")
    try:
        server.serve_forever()
    finally:
        server.server_close()
        workspace.executor.shutdown(wait=True)


try:
    launch()
except Exception:
    import traceback
    import tkinter.messagebox

    directory = ROOT / ".local"
    directory.mkdir(exist_ok=True)
    (directory / "startup-error.log").write_text(traceback.format_exc(), encoding="utf-8")
    tkinter.messagebox.showerror("越位分析工作台", "启动失败。请确认此 Python 已安装 OpenCV 和 NumPy。\n\n详细错误已保存至：\n" + str(directory / "startup-error.log"))
