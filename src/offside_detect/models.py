"""Data models shared by geometry, rule evaluation, and rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlayerObservation:
    """One player's visible body points at a decision frame.

    ``image_points`` uses pixel coordinates in the source frame.  The keys
    should be body-part names such as ``head``, ``torso``, ``left_foot`` and
    ``right_foot``.  Hands and arms are ignored by the rule evaluator.
    """

    player_id: str
    team: str
    image_points: dict[str, tuple[float, float]] = field(default_factory=dict)
    role: str | None = None
    receives_pass: bool = False
    visible: bool = True
    uncertainty_m: float = 0.0
    effective_part: str | None = None
    effective_field_point: tuple[float, float] | None = None

    @classmethod
    def from_json(cls, value: dict[str, Any]) -> "PlayerObservation":
        raw_points = value.get("image_points", {})
        points = {
            name: (float(point[0]), float(point[1]))
            for name, point in raw_points.items()
            if point is not None and len(point) >= 2
        }
        explicit = value.get("effective_field_point")
        return cls(
            player_id=str(value["player_id"]),
            team=str(value["team"]),
            image_points=points,
            role=value.get("role"),
            receives_pass=bool(value.get("receives_pass", False)),
            visible=bool(value.get("visible", True)),
            uncertainty_m=float(value.get("uncertainty_m", 0.0)),
            effective_part=value.get("effective_part"),
            effective_field_point=(float(explicit[0]), float(explicit[1]))
            if explicit is not None
            else None,
        )


@dataclass
class DecisionEvent:
    """A pass/contact event and the observations used to judge it."""

    frame: int
    players: list[PlayerObservation]
    ball_image_point: tuple[float, float] | None = None
    ball_is_on_ground: bool = False
    ball_field_point: tuple[float, float] | None = None
    attacking_team: str = "attack"
    defending_team: str = "defense"
    attack_direction: int = 1
    defensive_line_complete: bool = True
    llm_interference_probability: float | None = None
    label: str | None = None
    end_frame: int | None = None

    @classmethod
    def from_json(cls, value: dict[str, Any]) -> "DecisionEvent":
        ball = value.get("ball_field_point")
        ball_image = value.get("ball_image_point")
        return cls(
            frame=int(value["frame"]),
            end_frame=int(value["end_frame"]) if value.get("end_frame") is not None else None,
            players=[PlayerObservation.from_json(item) for item in value.get("players", [])],
            ball_image_point=(float(ball_image[0]), float(ball_image[1])) if ball_image else None,
            ball_is_on_ground=bool(value.get("ball_is_on_ground", False)),
            ball_field_point=(float(ball[0]), float(ball[1])) if ball else None,
            attacking_team=str(value.get("attacking_team", "attack")),
            defending_team=str(value.get("defending_team", "defense")),
            attack_direction=1 if int(value.get("attack_direction", 1)) >= 0 else -1,
            defensive_line_complete=bool(value.get("defensive_line_complete", True)),
            llm_interference_probability=(
                float(value["llm_interference_probability"])
                if value.get("llm_interference_probability") is not None
                else None
            ),
            label=value.get("label"),
        )
