"""Video pipeline using calibrated observations/events as its stable interface."""

from __future__ import annotations

from pathlib import Path
import json

import cv2

from .geometry import FieldCalibration
from .models import DecisionEvent, PlayerObservation
from .renderer import draw_decision, draw_track_observation, render_frame
from .rules import evaluate


def load_events(path: str | Path) -> list[DecisionEvent]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    raw_events = data.get("events", data) if isinstance(data, dict) else data
    if not isinstance(raw_events, list):
        raise ValueError("events JSON must be a list or an object with an 'events' list")
    return [DecisionEvent.from_json(value) for value in raw_events]


def load_tracks(path: str | Path) -> dict[int, dict[str, object]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    raw_tracks = data.get("tracks", []) if isinstance(data, dict) else []
    result: dict[int, dict[str, object]] = {}
    for item in raw_tracks:
        players = [PlayerObservation.from_json(player) for player in item.get("players", [])]
        ball = item.get("ball_field_point")
        result[int(item["frame"])] = {
            "players": players,
            "ball_field_point": (float(ball[0]), float(ball[1])) if ball else None,
            "attack_direction": 1 if int(item.get("attack_direction", 1)) >= 0 else -1,
            "attacking_team": str(item.get("attacking_team", "attack")),
            "defending_team": str(item.get("defending_team", "defense")),
        }
    return result


def run_video(
    video_path: str | Path,
    calibration: FieldCalibration,
    events: list[DecisionEvent],
    output_path: str | Path,
    interference_threshold: float = 0.7,
    tracks: dict[int, dict[str, object]] | None = None,
) -> dict[str, object]:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"could not open video: {video_path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 25.0)
    width, height = calibration.output_size
    writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        capture.release()
        raise ValueError(f"could not create output video: {output_path}")

    indexed = sorted(
        ((event.frame, event.end_frame if event.end_frame is not None else event.frame, event) for event in events),
        key=lambda item: (item[0], item[1]),
    )
    decisions: dict[int, object] = {}
    for _, _, event in indexed:
        decisions[event.frame] = evaluate(event, calibration, interference_threshold)

    frame_index = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            active = None
            for start, end, event in indexed:
                if start <= frame_index <= end:
                    active = decisions[event.frame]
            output = render_frame(frame, calibration, None)
            observation = (tracks or {}).get(frame_index)
            if observation is not None:
                draw_track_observation(
                    output,
                    calibration,
                    observation["players"],
                    observation["attack_direction"],
                    observation["attacking_team"],
                    observation["defending_team"],
                    observation["ball_field_point"],
                )
            if active is not None:
                draw_decision(output, calibration, active)
            writer.write(output)
            frame_index += 1
    finally:
        capture.release()
        writer.release()
    return {
        "input": str(video_path),
        "output": str(output_path),
        "frames_read": frame_index,
        "fps": fps,
        "events": [{"frame": event.frame, "status": decisions[event.frame].status} for event in events],
    }
