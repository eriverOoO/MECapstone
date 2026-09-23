"""저장 이미지나 외부 frame을 처리하는 OpenCV ArUco detector.

이 모듈은 카메라 장치를 열지 않는다. OpenCV는 detector 생성 시에만 필요하다.
"""

from dataclasses import dataclass
from typing import Any

import config
from .configuration import CameraCalibration


@dataclass(frozen=True)
class ArucoDetection:
    marker_id: int
    corners_px: tuple[tuple[float, float], ...]
    rotation_vector: tuple[float, float, float] | None = None
    translation_vector_m: tuple[float, float, float] | None = None


class ArucoDetector:
    """ArUco ID/corner 및 calibration이 있을 때 marker 상대 pose를 계산한다."""

    def __init__(
        self,
        dictionary_name: str = config.ARUCO_DICTIONARY,
        marker_size_m: float = config.ARUCO_MARKER_SIZE_M,
        calibration: CameraCalibration | None = None,
    ) -> None:
        if marker_size_m <= 0.0:
            raise ValueError("marker_size_m must be positive")
        if calibration is not None and not calibration.calibrated:
            raise ValueError(
                "placeholder calibration cannot be used for pose estimation"
            )
        try:
            import cv2
            import numpy as np
        except ImportError as error:
            raise RuntimeError(
                "offline ArUco detection requires opencv-contrib-python and numpy"
            ) from error
        if not hasattr(cv2, "aruco"):
            raise RuntimeError("installed OpenCV does not include the aruco module")
        if not hasattr(cv2.aruco, dictionary_name):
            raise ValueError(f"unknown ArUco dictionary: {dictionary_name}")

        self._cv2 = cv2
        self._np = np
        self.marker_size_m = marker_size_m
        self.calibration = calibration
        dictionary_id = getattr(cv2.aruco, dictionary_name)
        self._dictionary = cv2.aruco.getPredefinedDictionary(dictionary_id)
        self._parameters = cv2.aruco.DetectorParameters()
        self._detector = (
            cv2.aruco.ArucoDetector(self._dictionary, self._parameters)
            if hasattr(cv2.aruco, "ArucoDetector")
            else None
        )

    def detect(self, frame: Any) -> list[ArucoDetection]:
        """BGR/grayscale numpy frame에서 marker를 검출한다."""

        if frame is None:
            raise ValueError("frame cannot be None")
        if self._detector is not None:
            corners, ids, _ = self._detector.detectMarkers(frame)
        else:
            corners, ids, _ = self._cv2.aruco.detectMarkers(
                frame, self._dictionary, parameters=self._parameters
            )
        if ids is None:
            return []

        detections: list[ArucoDetection] = []
        for marker_corners, marker_id in zip(corners, ids.flatten()):
            pixel_corners = marker_corners.reshape(4, 2)
            rotation = None
            translation = None
            if self.calibration is not None:
                rotation, translation = self._estimate_relative_pose(pixel_corners)
            detections.append(
                ArucoDetection(
                    int(marker_id),
                    tuple((float(point[0]), float(point[1])) for point in pixel_corners),
                    rotation,
                    translation,
                )
            )
        return detections

    def _estimate_relative_pose(
        self, pixel_corners: Any
    ) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        assert self.calibration is not None
        half = self.marker_size_m / 2.0
        object_points = self._np.array(
            [(-half, half, 0.0), (half, half, 0.0), (half, -half, 0.0), (-half, -half, 0.0)],
            dtype=self._np.float32,
        )
        camera_matrix = self._np.array(self.calibration.camera_matrix, dtype=self._np.float64)
        distortion = self._np.array(
            self.calibration.distortion_coefficients, dtype=self._np.float64
        )
        success, rotation, translation = self._cv2.solvePnP(
            object_points,
            pixel_corners.astype(self._np.float32),
            camera_matrix,
            distortion,
            flags=self._cv2.SOLVEPNP_IPPE_SQUARE,
        )
        if not success:
            raise RuntimeError("solvePnP could not estimate marker pose")
        return (
            tuple(float(value) for value in rotation.reshape(3)),
            tuple(float(value) for value in translation.reshape(3)),
        )
