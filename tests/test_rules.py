import unittest
from pathlib import Path

import numpy as np

from offside_detect.geometry import FieldCalibration
from offside_detect.models import DecisionEvent
from offside_detect.rules import evaluate


def identity_calibration():
    image = np.asarray([[0, 0], [68, 0], [68, 105], [0, 105]], dtype=np.float32)
    field = image.copy()
    return FieldCalibration(105, 68, image, field, np.eye(3, dtype=np.float32), (680, 1050))


def event(players, **overrides):
    value = {
        "frame": 10,
        "attacking_team": "A",
        "defending_team": "D",
        "attack_direction": 1,
        "defensive_line_complete": True,
        "players": players,
    }
    value.update(overrides)
    return DecisionEvent.from_json(value)


class RuleTests(unittest.TestCase):
    def setUp(self):
        self.calibration = identity_calibration()

    def test_hand_and_arm_are_ignored_when_selecting_effective_point(self):
        current = event([
            {"player_id": "a1", "team": "A", "image_points": {"right_foot": [20, 70], "right_hand": [50, 100], "right_arm": [50, 95]}},
            {"player_id": "d1", "team": "D", "effective_part": "head", "effective_field_point": [20, 80]},
            {"player_id": "d2", "team": "D", "effective_part": "head", "effective_field_point": [20, 75]},
        ], ball_field_point=[20, 68])
        result = evaluate(current, self.calibration)
        self.assertEqual(result.status, "onside")
        self.assertEqual(result.effective_points["a1"].part, "right_foot")

    def test_offside_receiver_beyond_ball_and_second_last_defender(self):
        current = event([
            {"player_id": "a1", "team": "A", "receives_pass": True, "effective_part": "head", "effective_field_point": [20, 90]},
            {"player_id": "d1", "team": "D", "effective_part": "head", "effective_field_point": [20, 85]},
            {"player_id": "d2", "team": "D", "effective_part": "head", "effective_field_point": [20, 80]},
        ], ball_field_point=[20, 82])
        result = evaluate(current, self.calibration)
        self.assertEqual(result.status, "offside_receiver")
        self.assertEqual(result.second_last_defender.player.player_id, "d2")

    def test_attacker_in_own_half_is_not_offside(self):
        current = event([
            {"player_id": "a1", "team": "A", "effective_part": "head", "effective_field_point": [20, 48]},
            {"player_id": "d1", "team": "D", "effective_part": "head", "effective_field_point": [20, 55]},
            {"player_id": "d2", "team": "D", "effective_part": "head", "effective_field_point": [20, 52]},
        ], ball_field_point=[20, 48])
        self.assertEqual(evaluate(current, self.calibration).status, "onside")

    def test_incomplete_defense_line_is_refused(self):
        current = event([
            {"player_id": "a1", "team": "A", "image_points": {"head": [20, 90]}},
            {"player_id": "d1", "team": "D", "image_points": {"head": [20, 85]}},
            {"player_id": "d2", "team": "D", "image_points": {"head": [20, 80]}},
        ], defensive_line_complete=False)
        self.assertEqual(evaluate(current, self.calibration).status, "insufficient_defensive_visibility")

    def test_close_decision_with_declared_uncertainty_is_not_forced(self):
        current = event([
            {"player_id": "a1", "team": "A", "uncertainty_m": 0.3, "effective_part": "head", "effective_field_point": [20, 80.1]},
            {"player_id": "d1", "team": "D", "effective_part": "head", "effective_field_point": [20, 90]},
            {"player_id": "d2", "team": "D", "uncertainty_m": 0.2, "effective_part": "head", "effective_field_point": [20, 80]},
        ], ball_field_point=[20, 70])
        self.assertEqual(evaluate(current, self.calibration).status, "position_uncertain")

    def test_missing_ball_position_is_refused(self):
        current = event([
            {"player_id": "a1", "team": "A", "effective_part": "head", "effective_field_point": [20, 90]},
            {"player_id": "d1", "team": "D", "effective_part": "head", "effective_field_point": [20, 85]},
            {"player_id": "d2", "team": "D", "effective_part": "head", "effective_field_point": [20, 80]},
        ])
        self.assertEqual(evaluate(current, self.calibration).status, "insufficient_ball_position")

    def test_reverse_attack_direction_uses_the_other_goal(self):
        current = event([
            {"player_id": "a1", "team": "A", "receives_pass": True, "effective_part": "head", "effective_field_point": [20, 15]},
            {"player_id": "d1", "team": "D", "effective_part": "head", "effective_field_point": [20, 20]},
            {"player_id": "d2", "team": "D", "effective_part": "head", "effective_field_point": [20, 25]},
        ], attack_direction=-1, ball_field_point=[20, 18])
        self.assertEqual(evaluate(current, self.calibration).status, "offside_receiver")


class CalibrationTests(unittest.TestCase):
    def test_json_calibration_maps_corners_to_field(self):
        calibration = FieldCalibration.from_json(Path("examples/calibration.example.json"))
        x, y = calibration.image_to_field((1450, 770))
        self.assertAlmostEqual(x, 68, places=2)
        self.assertAlmostEqual(y, 105, places=2)


if __name__ == "__main__":
    unittest.main()
