"""Planar field calibration and image-to-bird's-eye transforms."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

import cv2
import numpy as np


@dataclass
class FieldCalibration:
    """A homography from source pixels to a metric football-field plane."""

    length_m: float
    width_m: float
    image_points: np.ndarray
    field_points: np.ndarray
    homography: np.ndarray
    output_size: tuple[int, int]

    @classmethod
    def from_json(cls, path: str | Path) -> "FieldCalibration":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        image = np.asarray(data["image_points"], dtype=np.float32)
        field = np.asarray(data["field_points"], dtype=np.float32)
        if image.shape != field.shape or image.ndim != 2 or image.shape[1] != 2:
            raise ValueError("image_points and field_points must both be Nx2 arrays")
        if len(image) < 4:
            raise ValueError("at least four non-degenerate field correspondences are required")
        homography, mask = cv2.findHomography(image, field, method=cv2.RANSAC)
        if homography is None or mask is None or int(mask.sum()) < 4:
            raise ValueError("could not estimate a valid field homography")
        length_m = float(data.get("length_m", 105.0))
        width_m = float(data.get("width_m", 68.0))
        output = data.get("output_size", [1260, 816])
        if len(output) != 2 or output[0] <= 0 or output[1] <= 0:
            raise ValueError("output_size must be [width_px, height_px]")
        return cls(length_m, width_m, image, field, homography, (int(output[0]), int(output[1])))

    def field_to_canvas(self) -> np.ndarray:
        """Return a metric-field-to-output-pixel transform."""
        out_w, out_h = self.output_size
        # Field coordinates are (across width x, toward the +length goal y).
        src = np.array([[0, 0], [self.width_m, 0], [self.width_m, self.length_m], [0, self.length_m]], dtype=np.float32)
        dst = np.array([[0, 0], [out_w, 0], [out_w, out_h], [0, out_h]], dtype=np.float32)
        return cv2.getPerspectiveTransform(src, dst)

    def image_to_field(self, point: tuple[float, float]) -> tuple[float, float]:
        value = cv2.perspectiveTransform(np.asarray([[point]], dtype=np.float32), self.homography)[0, 0]
        return float(value[0]), float(value[1])

    def image_to_canvas(self, point: tuple[float, float]) -> tuple[float, float]:
        field = self.image_to_field(point)
        value = cv2.perspectiveTransform(
            np.asarray([[field]], dtype=np.float32), self.field_to_canvas()
        )[0, 0]
        return float(value[0]), float(value[1])

    def field_to_canvas_point(self, point: tuple[float, float]) -> tuple[float, float]:
        value = cv2.perspectiveTransform(
            np.asarray([[point]], dtype=np.float32), self.field_to_canvas()
        )[0, 0]
        return float(value[0]), float(value[1])

    def warp_frame(self, frame: np.ndarray) -> np.ndarray:
        matrix = self.field_to_canvas() @ self.homography
        return cv2.warpPerspective(frame, matrix, self.output_size)

    def reprojection_errors(self) -> list[float]:
        projected = cv2.perspectiveTransform(self.image_points[None, :, :], self.homography)[0]
        return [float(np.linalg.norm(a - b)) for a, b in zip(projected, self.field_points)]
