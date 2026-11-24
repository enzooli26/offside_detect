"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .geometry import FieldCalibration
from .pipeline import load_events, load_tracks, run_video


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a bird's-eye offside analysis video")
    parser.add_argument("--video", required=True, type=Path, help="input fixed-camera video")
    parser.add_argument("--calibration", required=True, type=Path, help="field calibration JSON")
    parser.add_argument("--events", required=True, type=Path, help="pass/contact events JSON; optional tracks list can drive every output frame")
    parser.add_argument("--output", required=True, type=Path, help="bird's-eye output MP4")
    parser.add_argument("--interference-threshold", type=float, default=0.7)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    calibration = FieldCalibration.from_json(args.calibration)
    events = load_events(args.events)
    result = run_video(args.video, calibration, events, args.output, args.interference_threshold, load_tracks(args.events))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
