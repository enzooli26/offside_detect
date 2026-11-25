"""Exercise real HTTP uploads, validation, jobs, rendering, and downloads."""

from http.client import HTTPConnection
from pathlib import Path
from threading import Thread
import json
import tempfile
import time
import unittest

import cv2
import numpy as np

from offside_detect.web import AppServer, Workspace


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Path(".local").mkdir(exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(dir=".local")
        cls.workspace = Workspace(Path(cls.directory.name) / "jobs")
        cls.server = AppServer(("127.0.0.1", 0), cls.workspace)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.workspace.executor.shutdown(wait=True)
        cls.directory.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=20)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        data = response.read()
        status = response.status
        connection.close()
        return status, data

    def wait_for_job(self, job_id):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            status, body = self.request("GET", f"/api/jobs/{job_id}")
            self.assertEqual(status, 200)
            job = json.loads(body)
            if job["status"] in ("complete", "failed"):
                self.assertEqual(job["status"], "complete", job)
                return job
            time.sleep(.05)
        self.fail("job did not complete in 30 seconds")

    def test_demo_generates_three_events_images_and_video(self):
        status, body = self.request("POST", "/api/demo")
        self.assertEqual(status, 202, body)
        job_id = json.loads(body)["id"]
        job = self.wait_for_job(job_id)
        self.assertEqual(job["progress"], 100)
        self.assertEqual([e["status"] for e in job["result"]["events"]],
                         ["onside", "offside_receiver", "insufficient_defensive_visibility"])
        for name in ("event-1.jpg", "source-1.jpg", "analysis.mp4", "report.json"):
            code, data = self.request("GET", f"/files/{job_id}/{name}")
            self.assertEqual(code, 200)
            self.assertGreater(len(data), 100)

    def test_upload_and_tracks_pipeline_then_reject_out_of_range_frame(self):
        source = Path(self.directory.name) / "upload.mp4"
        writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"mp4v"), 8, (160, 120))
        self.assertTrue(writer.isOpened())
        for _ in range(4):
            writer.write(np.full((120, 160, 3), 90, np.uint8))
        writer.release()
        _, body = self.request("POST", "/api/jobs")
        job_id = json.loads(body)["id"]
        calibration = {"image_points": [[0, 0], [159, 0], [159, 119], [0, 119]],
                       "field_points": [[0, 0], [68, 0], [68, 105], [0, 105]], "output_size": [272, 420]}
        players = [{"player_id": "A9", "team": "A", "effective_part": "head", "effective_field_point": [25, 80]}]
        observation = {"frame": 1, "players": players, "ball_field_point": [30, 70], "defensive_line_complete": False}
        events = {"events": [observation], "tracks": [observation]}
        for kind, data in [("video", source.read_bytes()), ("calibration", json.dumps(calibration).encode()), ("events", json.dumps(events).encode())]:
            code, response = self.request("POST", f"/api/jobs/{job_id}/{kind}", data)
            self.assertEqual(code, 200, response)
        code, data = self.request("POST", f"/api/jobs/{job_id}/start", b'{"threshold":0.7}')
        self.assertEqual(code, 202, data)
        self.wait_for_job(job_id)
        _, body = self.request("POST", "/api/jobs")
        other = json.loads(body)["id"]
        for name in ("input.video", "calibration.json", "events.json"):
            (self.workspace.root / other / name).write_bytes((self.workspace.root / job_id / name).read_bytes())
        events["events"][0]["frame"] = 9999
        (self.workspace.root / other / "events.json").write_text(json.dumps(events), encoding="utf-8")
        code, data = self.request("POST", f"/api/jobs/{other}/start", b'{}')
        self.assertEqual(code, 400)
        self.assertIn("超出", json.loads(data)["error"])

    def test_page_and_cross_origin_and_private_inputs(self):
        code, body = self.request("GET", "/")
        self.assertEqual(code, 200)
        self.assertIn("鸟瞰视图", body.decode())
        code, _ = self.request("POST", "/api/jobs", headers={"Origin": "https://example.com"})
        self.assertEqual(code, 403)
        code, _ = self.request("GET", "/files/" + "a" * 32 + "/input.video")
        self.assertEqual(code, 404)


if __name__ == "__main__":
    unittest.main()
