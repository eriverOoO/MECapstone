"""실제 카메라 없이 위치 noise, latency, dropout을 재현한다."""

import random

import config
from .models import LocalizationResult, LocalizationStatus, Pose2D


class SyntheticPoseProvider:
    """외부가 지정한 true pose를 noisy camera localization처럼 출력한다."""

    def __init__(
        self,
        initial_pose: Pose2D,
        *,
        position_noise_std: float = config.CAMERA_POSITION_NOISE_STD,
        yaw_noise_std_deg: float = config.CAMERA_YAW_NOISE_STD_DEG,
        dropout_probability: float = config.CAMERA_DROPOUT_PROBABILITY,
        latency_seconds: float = config.CAMERA_LOCALIZATION_LATENCY_SEC,
        random_seed: int | None = None,
    ) -> None:
        if position_noise_std < 0.0 or yaw_noise_std_deg < 0.0:
            raise ValueError("noise standard deviation cannot be negative")
        if not 0.0 <= dropout_probability <= 1.0:
            raise ValueError("dropout_probability must be between 0 and 1")
        if latency_seconds < 0.0:
            raise ValueError("latency_seconds cannot be negative")
        self.position_noise_std = position_noise_std
        self.yaw_noise_std_deg = yaw_noise_std_deg
        self.dropout_probability = dropout_probability
        self.latency_seconds = latency_seconds
        self._true_pose = initial_pose
        self._random = random.Random(random_seed)

    def set_true_pose(self, pose: Pose2D) -> None:
        self._true_pose = pose

    def estimate(self, timestamp_seconds: float) -> LocalizationResult:
        if self._random.random() < self.dropout_probability:
            return LocalizationResult(
                LocalizationStatus.LOST,
                None,
                message="synthetic camera localization dropout",
            )
        pose = Pose2D(
            x=self._true_pose.x + self._random.gauss(0.0, self.position_noise_std),
            y=self._true_pose.y + self._random.gauss(0.0, self.position_noise_std),
            yaw_deg=self._true_pose.yaw_deg
            + self._random.gauss(0.0, self.yaw_noise_std_deg),
            timestamp_seconds=max(0.0, timestamp_seconds - self.latency_seconds),
            source="synthetic_camera",
            confidence=1.0,
        )
        return LocalizationResult(LocalizationStatus.TRACKING, pose)

