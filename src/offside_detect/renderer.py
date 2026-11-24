"""Bird's-eye frame rendering."""

from __future__ import annotations

import cv2
import numpy as np

from .geometry import FieldCalibration
from .models import PlayerObservation
from .rules import EffectivePoint, OffsideDecision, effective_point


PART_COLORS = {
    "head": (40, 40, 230),
    "neck": (40, 40, 230),
    "torso": (30, 190, 230),
    "left_shoulder": (30, 190, 230),
    "right_shoulder": (30, 190, 230),
    "left_hip": (40, 210, 80),
    "right_hip": (40, 210, 80),
    "left_foot": (230, 150, 30),
    "right_foot": (230, 150, 30),
    "foot": (230, 150, 30),
}
TEAM_COLORS = {"attack": (0, 140, 255), "defense": (255, 120, 0), "A": (0, 140, 255), "D": (255, 120, 0)}
STATUS_COLORS = {
    "onside": (100, 220, 100),
    "offside_receiver": (0, 0, 255),
    "offside_interference": (0, 0, 255),
    "potential_interference": (0, 200, 255),
    "insufficient_defensive_visibility": (150, 150, 150),
    "position_uncertain": (0, 200, 255),
    "insufficient_ball_position": (150, 150, 150),
}


def draw_field(canvas: np.ndarray, calibration: FieldCalibration) -> None:
    """Draw a simple metric field overlay in the configured bird's-eye frame."""
    transform = calibration.field_to_canvas()

    def point(x: float, y: float) -> tuple[int, int]:
        value = cv2.perspectiveTransform(np.asarray([[[x, y]]], dtype=np.float32), transform)[0, 0]
        return int(round(value[0])), int(round(value[1]))

    green = (45, 115, 45)
    white = (235, 235, 235)
    cv2.rectangle(canvas, (0, 0), (canvas.shape[1] - 1, canvas.shape[0] - 1), green, -1)
    cv2.rectangle(canvas, point(0, 0), point(calibration.width_m, calibration.length_m), white, 2)
    cv2.line(canvas, point(0, calibration.length_m / 2), point(calibration.width_m, calibration.length_m / 2), white, 1)
    cv2.circle(canvas, point(calibration.width_m / 2, calibration.length_m / 2), max(1, int(canvas.shape[1] * 9.15 / calibration.width_m)), white, 1)
    # Penalty areas are visual guidance; dimensions follow the conventional full-size field.
    for y in (0.0, calibration.length_m):
        direction = 1 if y == 0 else -1
        box_depth = min(16.5, calibration.length_m / 4)
        box_width = min(40.32, calibration.width_m * 0.8)
        y2 = y + direction * box_depth
        cv2.rectangle(canvas, point((calibration.width_m - box_width) / 2, min(y, y2)), point((calibration.width_m + box_width) / 2, max(y, y2)), white, 1)


def _status_color(status: str) -> tuple[int, int, int]:
    return STATUS_COLORS.get(status, (200, 200, 200))


def draw_decision(canvas: np.ndarray, calibration: FieldCalibration, decision: OffsideDecision) -> None:
    if decision.offside_line_y is not None:
        p = calibration.field_to_canvas_point((calibration.width_m / 2, decision.offside_line_y))
        cv2.line(canvas, (0, int(round(p[1]))), (canvas.shape[1] - 1, int(round(p[1]))), _status_color(decision.status), 4)
        cv2.putText(canvas, "offside line", (18, max(22, int(round(p[1])) - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, _status_color(decision.status), 2, cv2.LINE_AA)

    for player_id, effective in decision.effective_points.items():
        p = calibration.field_to_canvas_point(effective.field_point)
        center = (int(round(p[0])), int(round(p[1])))
        part_color = PART_COLORS.get(effective.part, (220, 220, 220))
        team_color = TEAM_COLORS.get(effective.player.team, (210, 210, 210))
        if effective.uncertainty_m > 0:
            radius = max(1, int(round(effective.uncertainty_m * canvas.shape[1] / calibration.width_m)))
            cv2.circle(canvas, center, radius, team_color, 1, cv2.LINE_AA)
        cv2.circle(canvas, center, 9, team_color, 2, cv2.LINE_AA)
        cv2.circle(canvas, center, 5, part_color, -1, cv2.LINE_AA)
        if player_id in decision.offside_players:
            cv2.circle(canvas, center, 13, _status_color(decision.status), 2, cv2.LINE_AA)
        cv2.putText(canvas, player_id, (center[0] + 8, center[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

    if decision.ball_field_point is not None:
        p = calibration.field_to_canvas_point(decision.ball_field_point)
        center = (int(round(p[0])), int(round(p[1])))
        cv2.circle(canvas, center, 5, (245, 245, 245), -1, cv2.LINE_AA)
        cv2.circle(canvas, center, 7, (20, 20, 20), 1, cv2.LINE_AA)


def draw_track_observation(
    canvas: np.ndarray,
    calibration: FieldCalibration,
    players: list[PlayerObservation],
    attack_direction: int,
    attacking_team: str,
    defending_team: str,
    ball_field_point: tuple[float, float] | None,
) -> None:
    """Draw tracked player and ball positions for one video frame."""
    for player in players:
        point = effective_point(player, calibration, attack_direction)
        if point is None:
            continue
        projected = calibration.field_to_canvas_point(point.field_point)
        center = (int(round(projected[0])), int(round(projected[1])))
        team_color = (0, 140, 255) if player.team == attacking_team else (255, 120, 0) if player.team == defending_team else (180, 180, 180)
        part_color = PART_COLORS.get(point.part, (220, 220, 220))
        if point.uncertainty_m > 0:
            radius = max(1, int(round(point.uncertainty_m * canvas.shape[1] / calibration.width_m)))
            cv2.circle(canvas, center, radius, team_color, 1, cv2.LINE_AA)
        cv2.circle(canvas, center, 9, team_color, 2, cv2.LINE_AA)
        cv2.circle(canvas, center, 5, part_color, -1, cv2.LINE_AA)
        cv2.putText(canvas, player.player_id, (center[0] + 8, center[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
    if ball_field_point is not None:
        projected = calibration.field_to_canvas_point(ball_field_point)
        center = (int(round(projected[0])), int(round(projected[1])))
        cv2.circle(canvas, center, 5, (245, 245, 245), -1, cv2.LINE_AA)
        cv2.circle(canvas, center, 7, (20, 20, 20), 1, cv2.LINE_AA)

    banner = f"{decision.status}: {decision.message}"
    cv2.rectangle(canvas, (10, 10), (min(canvas.shape[1] - 10, 920), 42), (20, 20, 20), -1)
    cv2.putText(canvas, banner[:120], (18, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.52, _status_color(decision.status), 1, cv2.LINE_AA)


def render_frame(frame: np.ndarray, calibration: FieldCalibration, decision: OffsideDecision | None = None) -> np.ndarray:
    # The primary output is a tactical bird's-eye canvas. Warping the source
    # frame would distort elevated player bodies, so render the metric field.
    canvas = np.zeros((calibration.output_size[1], calibration.output_size[0], 3), dtype=np.uint8)
    draw_field(canvas, calibration)
    if decision is not None:
        draw_decision(canvas, calibration, decision)
    return canvas
