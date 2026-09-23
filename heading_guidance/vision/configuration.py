"""Camera calibration과 ArUco marker map JSON loader."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CameraCalibration:
    image_width: int
    image_height: int
    camera_matrix: tuple[tuple[float, float, float], ...]
    distortion_coefficients: tuple[float, ...]
    calibrated: bool

    @classmethod
    def from_json(cls, path: str | Path) -> "CameraCalibration":
        with Path(path).open(encoding="utf-8") as input_file:
            data = json.load(input_file)
        matrix = tuple(tuple(float(value) for value in row) for row in data["camera_matrix"])
        distortion = tuple(float(value) for value in data["distortion_coefficients"])
        if len(matrix) != 3 or any(len(row) != 3 for row in matrix):
            raise ValueError("camera_matrix must be 3x3")
        if len(distortion) < 4:
            raise ValueError("at least four distortion coefficients are required")
        return cls(
            int(data["image_width"]),
            int(data["image_height"]),
            matrix,
            distortion,
            bool(data.get("calibrated", False)),
        )


@dataclass(frozen=True)
class MarkerDefinition:
    marker_id: int
    x: float
    y: float
    z: float
    yaw_deg: float


class MarkerMap:
    """world frame에 고정된 ArUco marker pose 모음."""

    def __init__(self, markers: list[MarkerDefinition]) -> None:
        if not markers:
            raise ValueError("marker map cannot be empty")
        ids = [marker.marker_id for marker in markers]
        if len(ids) != len(set(ids)):
            raise ValueError("marker ids must be unique")
        self.markers = {marker.marker_id: marker for marker in markers}

    @classmethod
    def from_json(cls, path: str | Path) -> "MarkerMap":
        with Path(path).open(encoding="utf-8") as input_file:
            data = json.load(input_file)
        markers = [
            MarkerDefinition(
                marker_id=int(item["id"]),
                x=float(item["x"]),
                y=float(item["y"]),
                z=float(item.get("z", 0.0)),
                yaw_deg=float(item.get("yaw_deg", 0.0)),
            )
            for item in data["markers"]
        ]
        return cls(markers)

    def get(self, marker_id: int) -> MarkerDefinition | None:
        return self.markers.get(marker_id)

