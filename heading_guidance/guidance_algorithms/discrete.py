"""오차 구간별로 고정 세기를 사용하는 진동 전략."""

import config
from .base import GuidanceAlgorithm


class DiscreteGuidance(GuidanceAlgorithm):
    name = "discrete"

    def intensity(self, error_magnitude_deg: float, now_seconds: float) -> float:
        del now_seconds
        if error_magnitude_deg <= config.DEADBAND_DEG:
            return 0.0
        if error_magnitude_deg <= config.DISCRETE_LOW_BOUND_DEG:
            return config.DISCRETE_LOW_INTENSITY
        if error_magnitude_deg <= config.DISCRETE_HIGH_BOUND_DEG:
            return config.DISCRETE_MEDIUM_INTENSITY
        return 1.0
