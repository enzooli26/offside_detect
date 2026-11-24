"""Law-11-inspired position classification for the prototype."""

from __future__ import annotations

from dataclasses import dataclass, field

from .geometry import FieldCalibration
from .models import DecisionEvent, PlayerObservation


VALID_PARTS = {
    "head",
    "neck",
    "torso",
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
    "left_foot",
    "right_foot",
    "foot",
}


@dataclass
class EffectivePoint:
    player: PlayerObservation
    part: str
    field_point: tuple[float, float]
    uncertainty_m: float


@dataclass
class OffsideDecision:
    status: str
    message: str
    effective_points: dict[str, EffectivePoint] = field(default_factory=dict)
    second_last_defender: EffectivePoint | None = None
    ball_field_point: tuple[float, float] | None = None
    offside_players: list[str] = field(default_factory=list)
    receiving_players: list[str] = field(default_factory=list)
    interference_probability: float | None = None
    offside_line_y: float | None = None


def _directed_y(point: tuple[float, float], direction: int, field_length: float) -> float:
    """Distance from the attacking team's own goal line toward its target."""
    return point[1] if direction == 1 else field_length - point[1]


def effective_point(player: PlayerObservation, calibration: FieldCalibration, direction: int) -> EffectivePoint | None:
    if not player.visible:
        return None
    if player.effective_field_point is not None and player.effective_part in VALID_PARTS:
        return EffectivePoint(player, player.effective_part, player.effective_field_point, player.uncertainty_m)
    candidates: list[tuple[str, tuple[float, float]]] = []
    for part, image_point in player.image_points.items():
        # The ground-plane homography is valid for foot contacts, not elevated
        # body landmarks. Those require a 3-D estimate supplied as a field point.
        if part in {"left_foot", "right_foot", "foot"}:
            candidates.append((part, calibration.image_to_field(image_point)))
    if not candidates:
        return None
    part, point = max(candidates, key=lambda item: _directed_y(item[1], direction, calibration.length_m))
    return EffectivePoint(player, part, point, player.uncertainty_m)


def evaluate(event: DecisionEvent, calibration: FieldCalibration, interference_threshold: float = 0.7) -> OffsideDecision:
    points = {
        player.player_id: value
        for player in event.players
        if (value := effective_point(player, calibration, event.attack_direction)) is not None
    }
    defenders = [p for p in points.values() if p.player.team == event.defending_team]
    attackers = [p for p in points.values() if p.player.team == event.attacking_team]
    ball = event.ball_field_point
    if ball is None and event.ball_image_point is not None and event.ball_is_on_ground:
        ball = calibration.image_to_field(event.ball_image_point)
    if not event.defensive_line_complete:
        return OffsideDecision(
            "insufficient_defensive_visibility",
            "防线可能不完整，画外球员可能改变倒数第二位防守队员。",
            points,
            ball_field_point=ball,
        )
    if len(defenders) < 2:
        return OffsideDecision(
            "insufficient_defensive_visibility",
            "可见对方防守队员少于两名，无法确定倒数第二位防守队员。",
            points,
            ball_field_point=ball,
        )
    if ball is None and event.ball_image_point is not None and event.ball_is_on_ground:
        ball = calibration.image_to_field(event.ball_image_point)
    if ball is None:
        return OffsideDecision(
            "insufficient_ball_position",
            "缺少可靠球场坐标的足球位置，无法比较球与倒数第二位防守队员。",
            points,
        )
    defenders.sort(key=lambda p: _directed_y(p.field_point, event.attack_direction, calibration.length_m), reverse=True)
    second_last = defenders[1]
    threshold = _directed_y(second_last.field_point, event.attack_direction, calibration.length_m)
    threshold = max(threshold, _directed_y(ball, event.attack_direction, calibration.length_m))
    halfway = calibration.length_m / 2
    offside = [
        p
        for p in attackers
        if _directed_y(p.field_point, event.attack_direction, calibration.length_m) > halfway
        and _directed_y(p.field_point, event.attack_direction, calibration.length_m) > threshold
    ]
    if not offside:
        return OffsideDecision(
            "onside",
            "未发现越位位置。",
            points,
            second_last,
            ball,
            offside_line_y=threshold if event.attack_direction == 1 else calibration.length_m - threshold,
        )
    receiving = [p for p in offside if p.player.receives_pass]
    uncertain = [
        p
        for p in attackers
        if _directed_y(p.field_point, event.attack_direction, calibration.length_m) > halfway
        and abs(_directed_y(p.field_point, event.attack_direction, calibration.length_m) - threshold)
        <= p.uncertainty_m + second_last.uncertainty_m
    ]
    if uncertain:
        return OffsideDecision(
            "position_uncertain",
            "身体位置或防守线的不确定范围跨越判定线，无法可靠二分。",
            points,
            second_last,
            ball,
            [p.player.player_id for p in offside],
            [p.player.player_id for p in receiving],
            offside_line_y=threshold if event.attack_direction == 1 else calibration.length_m - threshold,
        )
    if receiving:
        return OffsideDecision(
            "offside_receiver",
            "越位位置球员被标记为接下该次传球。",
            points,
            second_last,
            ball,
            [p.player.player_id for p in offside],
            [p.player.player_id for p in receiving],
            offside_line_y=threshold if event.attack_direction == 1 else calibration.length_m - threshold,
        )
    probability = event.llm_interference_probability
    if probability is not None and probability >= interference_threshold:
        status = "offside_interference"
        message = f"越位位置且干扰概率 {probability:.2f} 达到阈值。"
    else:
        status = "potential_interference"
        message = "存在越位位置球员，但未标记为接球；需复核是否干扰对手。"
    return OffsideDecision(
        status,
        message,
        points,
        second_last,
        ball,
        [p.player.player_id for p in offside],
        [],
        probability,
        threshold if event.attack_direction == 1 else calibration.length_m - threshold,
    )
