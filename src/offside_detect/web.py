"""Loopback-only web app. Uses the existing video pipeline without extra dependencies."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, Thread
from urllib.parse import urlsplit
import argparse
import json
import math
import re
import shutil
import uuid
import webbrowser

import cv2
import numpy as np

from .geometry import FieldCalibration
from .pipeline import load_events, load_tracks, run_video
from .renderer import render_frame
from .rules import evaluate


STATIC = Path(__file__).with_name("static")
NAMES = {"video": "input.video", "calibration": "calibration.json", "events": "events.json"}


def write_image(path: Path, frame: np.ndarray) -> None:
    ok, encoded = cv2.imencode(".jpg", frame)
    if not ok:
        raise ValueError("预览图片生成失败。")
    path.write_bytes(encoded.tobytes())


class Workspace:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, dict] = {}
        self.lock = Lock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="offside")

    def create(self) -> str:
        job_id = uuid.uuid4().hex
        (self.root / job_id).mkdir()
        with self.lock:
            self.jobs[job_id] = {"id": job_id, "status": "uploading", "progress": 0, "message": "等待导入素材"}
        return job_id

    def update(self, job_id: str, **values) -> None:
        with self.lock:
            self.jobs[job_id].update(values)

    def snapshot(self, job_id: str) -> dict:
        with self.lock:
            if job_id not in self.jobs:
                raise ValueError("任务不存在；服务重启后请重新导入。")
            return dict(self.jobs[job_id])

    def validate(self, job_id: str, threshold: float) -> tuple:
        directory = self.root / job_id
        if not math.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError("干扰提示阈值必须在 0 到 1 之间。")
        if any(not (directory / name).is_file() for name in NAMES.values()):
            raise ValueError("请提供视频、标定和事件三个文件。")
        calibration = FieldCalibration.from_json(directory / NAMES["calibration"])
        w, h = calibration.output_size
        if w < 100 or h < 100 or w > 3840 or h > 3840 or w % 2 or h % 2:
            raise ValueError("鸟瞰输出宽高须为 100–3840 之间的偶数。")
        if not np.isfinite(calibration.homography).all() or calibration.length_m <= 0 or calibration.width_m <= 0:
            raise ValueError("球场尺寸或标定矩阵无效。")
        events = load_events(directory / NAMES["events"])
        tracks = load_tracks(directory / NAMES["events"])
        if not events:
            raise ValueError("事件文件里没有传球事件，请至少提供一个事件。")
        capture = cv2.VideoCapture(str(directory / NAMES["video"]))
        try:
            ok, frame = capture.read()
            fps = float(capture.get(cv2.CAP_PROP_FPS))
            count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            if not ok or not math.isfinite(fps) or fps <= 0 or count <= 0:
                raise ValueError("无法读取视频，请更换为可解码的视频。")
            seen = set()
            for event in events:
                if event.frame in seen:
                    raise ValueError("同一帧包含重复事件，请合并后重新导入。")
                seen.add(event.frame)
                end = event.end_frame if event.end_frame is not None else event.frame
                if event.frame < 0 or end < event.frame or end >= count:
                    raise ValueError(f"事件帧 {event.frame} 超出视频范围（0–{count - 1}）或结束帧无效。")
            if any(index < 0 or index >= count for index in tracks):
                raise ValueError("跟踪帧号超出视频范围。")
            write_image(directory / "source.jpg", frame)
        finally:
            capture.release()
        return calibration, events, tracks, fps, count

    def start(self, job_id: str, threshold: float) -> None:
        if self.snapshot(job_id)["status"] != "uploading":
            raise ValueError("该任务已经开始，请新建任务。")
        inputs = self.validate(job_id, threshold)
        self.update(job_id, status="queued", message="等待生成", fps=inputs[3], frame_count=inputs[4])
        self.executor.submit(self.process, job_id, threshold, inputs)

    def process(self, job_id: str, threshold: float, inputs: tuple) -> None:
        directory = self.root / job_id
        calibration, events, tracks, fps, count = inputs
        self.update(job_id, status="running", message="正在生成鸟瞰视频")
        try:
            def progress(done, total):
                self.update(job_id, progress=min(96, round(done * 96 / max(total, 1))), frames_done=done)

            result = run_video(directory / NAMES["video"], calibration, events,
                               directory / "analysis.mp4", threshold, tracks, progress)
            result["input"] = "用户导入视频"
            result["output"] = "analysis.mp4"
            result["threshold"] = threshold
            result["events"] = []
            capture = cv2.VideoCapture(str(directory / NAMES["video"]))
            try:
                for i, event in enumerate(events):
                    decision = evaluate(event, calibration, threshold)
                    image_name = f"event-{i}.jpg"
                    write_image(directory / image_name, render_frame(np.zeros((1, 1, 3), np.uint8), calibration, decision))
                    capture.set(cv2.CAP_PROP_POS_FRAMES, event.frame)
                    ok, source = capture.read()
                    source_name = f"source-{i}.jpg"
                    if ok:
                        write_image(directory / source_name, source)
                    result["events"].append({
                        "frame": event.frame, "time_seconds": round(event.frame / fps, 3),
                        "status": decision.status, "message": decision.message,
                        "offside_players": decision.offside_players,
                        "preview": image_name, "source": source_name if ok else "source.jpg",
                    })
            finally:
                capture.release()
            (directory / "report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            self.update(job_id, status="complete", progress=100, message="鸟瞰结果已生成", result=result)
        except Exception as error:
            self.update(job_id, status="failed", message=f"生成失败：{error}")

    def demo(self) -> str:
        job_id = self.create()
        directory = self.root / job_id
        calibration = {"length_m": 105, "width_m": 68,
                       "image_points": [[0, 0], [319, 0], [319, 239], [0, 239]],
                       "field_points": [[0, 0], [68, 0], [68, 105], [0, 105]],
                       "output_size": [544, 840]}
        events = []
        for i, (y, complete) in enumerate([(69, True), (81, True), (79, False)]):
            events.append({"frame": i * 8, "end_frame": i * 8 + 7,
                           "attacking_team": "A", "defending_team": "D",
                           "ball_field_point": [34, 64], "defensive_line_complete": complete,
                           "players": [
                               {"player_id": "A9", "team": "A", "effective_part": "head", "effective_field_point": [28, y], "receives_pass": True},
                               {"player_id": "D4", "team": "D", "effective_part": "torso", "effective_field_point": [31, 74]},
                               {"player_id": "D1", "team": "D", "effective_part": "foot", "effective_field_point": [34, 94]},
                           ]})
        (directory / NAMES["calibration"]).write_text(json.dumps(calibration), encoding="utf-8")
        (directory / NAMES["events"]).write_text(json.dumps({"events": events}), encoding="utf-8")
        writer = cv2.VideoWriter(str(directory / "demo.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 8, (320, 240))
        try:
            if not writer.isOpened():
                raise ValueError("无法创建演示视频。")
            for i in range(24):
                frame = np.full((240, 320, 3), (36, 92, 44), np.uint8)
                cv2.putText(frame, "SYNTHETIC DEMO", (20, 110), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 2)
                writer.write(frame)
        finally:
            writer.release()
        (directory / "demo.mp4").rename(directory / NAMES["video"])
        self.start(job_id, .7)
        return job_id


class AppServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, workspace: Workspace):
        self.workspace = workspace
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server: AppServer

    def log_message(self, *args):
        pass

    def json_response(self, value: dict, status=200) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def trusted_request(self) -> bool:
        expected = f"127.0.0.1:{self.server.server_port}"
        if self.headers.get("Host") != expected:
            return False
        origin = self.headers.get("Origin")
        return origin is None or origin == f"http://{expected}"

    def send_file(self, path: Path, content_type: str, download=False) -> None:
        if not path.is_file():
            self.json_response({"error": "文件尚未生成或不存在。"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.send_header("X-Content-Type-Options", "nosniff")
        if download:
            self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.end_headers()
        with path.open("rb") as file:
            shutil.copyfileobj(file, self.wfile)

    def do_GET(self):
        try:
            if not self.trusted_request():
                self.json_response({"error": "仅允许本机页面访问。"}, 403)
                return
            route = urlsplit(self.path).path
            if route == "/api/health":
                self.json_response({"app": "offside-studio-v005"})
            elif route in ("/", "/app.css", "/app.js"):
                name, mime = {"/": ("index.html", "text/html; charset=utf-8"),
                              "/app.css": ("app.css", "text/css"),
                              "/app.js": ("app.js", "text/javascript")}[route]
                self.send_file(STATIC / name, mime)
            elif match := re.fullmatch(r"/api/jobs/([a-f0-9]{32})", route):
                self.json_response(self.server.workspace.snapshot(match[1]))
            elif match := re.fullmatch(r"/files/([a-f0-9]{32})/(analysis\.mp4|report\.json|(?:event|source)-\d+\.jpg|source\.jpg)", route):
                self.server.workspace.snapshot(match[1])
                name = match[2]
                self.send_file(self.server.workspace.root / match[1] / name,
                               "image/jpeg" if name.endswith(".jpg") else "video/mp4" if name.endswith(".mp4") else "application/json",
                               download=not name.endswith(".jpg"))
            else:
                self.json_response({"error": "页面不存在。"}, 404)
        except (ValueError, OSError) as error:
            self.json_response({"error": str(error)}, 400)

    def do_POST(self):
        try:
            if not self.trusted_request():
                self.json_response({"error": "仅允许本机页面访问。"}, 403)
                return
            route = urlsplit(self.path).path
            workspace = self.server.workspace
            if route == "/api/jobs":
                self.json_response({"id": workspace.create()}, 201)
            elif route == "/api/demo":
                self.json_response({"id": workspace.demo()}, 202)
            elif match := re.fullmatch(r"/api/jobs/([a-f0-9]{32})/(video|calibration|events)", route):
                job_id, kind = match.groups()
                if workspace.snapshot(job_id)["status"] != "uploading":
                    raise ValueError("任务已开始，不能修改输入。")
                length = int(self.headers.get("Content-Length", "0"))
                limit = 4 * 1024**3 if kind == "video" else 20 * 1024**2
                if not 0 < length <= limit:
                    raise ValueError("文件为空或过大（视频限 4 GB，JSON 限 20 MB）。")
                path = workspace.root / job_id / NAMES[kind]
                with path.open("wb") as file:
                    remaining = length
                    while remaining:
                        chunk = self.rfile.read(min(1024**2, remaining))
                        if not chunk:
                            raise ValueError("文件传输中断，请重新导入。")
                        file.write(chunk)
                        remaining -= len(chunk)
                self.json_response({"ok": True})
            elif match := re.fullmatch(r"/api/jobs/([a-f0-9]{32})/start", route):
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 4096:
                    raise ValueError("请求参数无效。")
                data = json.loads(self.rfile.read(length))
                workspace.start(match[1], float(data.get("threshold", .7)))
                self.json_response(workspace.snapshot(match[1]), 202)
            elif route == "/api/shutdown":
                self.json_response({"ok": True})
                Thread(target=self.server.shutdown, daemon=True).start()
            else:
                self.json_response({"error": "接口不存在。"}, 404)
        except Exception as error:
            self.json_response({"error": f"无法继续：{error}"}, 400)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local offside analysis web UI")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--data-dir", type=Path, default=Path(".local/web-jobs"))
    args = parser.parse_args(argv)
    workspace = Workspace(args.data_dir)
    server = AppServer(("127.0.0.1", args.port), workspace)
    url = f"http://127.0.0.1:{server.server_port}"
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        workspace.executor.shutdown(wait=True)


if __name__ == "__main__":
    main()
