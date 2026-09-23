"""오차에 비례하는 연속형 진동 전략."""

import config
from .base import GuidanceAlgorithm


class ContinuousGuidance(GuidanceAlgorithm):
    name = "continuous"

    def __init__(self, full_scale_error_deg: float = config.MAX_INTENSITY_ERROR_DEG) -> None:
        self.full_scale_error_deg = full_scale_error_deg

    def intensity(self, error_magnitude_deg: float, now_seconds: float) -> float:
        del now_seconds
        return min(error_magnitude_deg / self.full_scale_error_deg, 1.0)
