"""오차가 클수록 짧은 간격으로 pulse를 내는 진동 전략."""

import config
from .base import GuidanceAlgorithm


class PulseGuidance(GuidanceAlgorithm):
    name = "pulse"

    def __init__(self) -> None:
        self._epoch = 0.0

    def reset(self, now_seconds: float = 0.0) -> None:
        self._epoch = now_seconds

    def intensity(self, error_magnitude_deg: float, now_seconds: float) -> float:
        if error_magnitude_deg <= config.DISCRETE_LOW_BOUND_DEG:
            interval = config.PULSE_SLOW_INTERVAL_SEC
        elif error_magnitude_deg <= config.DISCRETE_HIGH_BOUND_DEG:
            interval = config.PULSE_MEDIUM_INTERVAL_SEC
        else:
            interval = config.PULSE_FAST_INTERVAL_SEC

        phase = (now_seconds - self._epoch) % interval
        return config.PULSE_INTENSITY if phase < config.PULSE_DURATION_SEC else 0.0
