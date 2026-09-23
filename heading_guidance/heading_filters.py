"""360도 wrap-around를 고려하는 heading 필터."""

import math
from collections import deque
from typing import Protocol

from heading_controller import calculate_heading_error, normalize_heading


class HeadingFilter(Protocol):
    def update(self, heading_deg: float) -> float:
        """새 측정값을 반영한 filtered heading을 반환한다."""
        ...

    def reset(self) -> None:
        """필터 내부 상태를 비운다."""
        ...


class NoFilter:
    def update(self, heading_deg: float) -> float:
        return normalize_heading(heading_deg)

    def reset(self) -> None:
        pass


class CircularMovingAverage:
    """sin/cos 벡터 평균을 이용해 0/360 경계를 올바르게 처리한다."""

    def __init__(self, window_size: int) -> None:
        if window_size <= 0:
            raise ValueError("window_size must be positive")
        self._values: deque[float] = deque(maxlen=window_size)

    def update(self, heading_deg: float) -> float:
        self._values.append(math.radians(normalize_heading(heading_deg)))
        sin_mean = sum(math.sin(value) for value in self._values) / len(self._values)
        cos_mean = sum(math.cos(value) for value in self._values) / len(self._values)
        return normalize_heading(math.degrees(math.atan2(sin_mean, cos_mean)))

    def reset(self) -> None:
        self._values.clear()


class CircularLowPassFilter:
    """최단 각도 차이에 EMA를 적용하는 1차 저역통과 필터."""

    def __init__(self, alpha: float) -> None:
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = alpha
        self._value: float | None = None

    def update(self, heading_deg: float) -> float:
        measured = normalize_heading(heading_deg)
        if self._value is None:
            self._value = measured
        else:
            delta = calculate_heading_error(measured, self._value)
            self._value = normalize_heading(self._value + self.alpha * delta)
        return self._value

    def reset(self) -> None:
        self._value = None


def create_heading_filter(filter_type: str, window_size: int, alpha: float) -> HeadingFilter:
    normalized = filter_type.lower()
    if normalized == "none":
        return NoFilter()
    if normalized == "moving_average":
        return CircularMovingAverage(window_size)
    if normalized == "low_pass":
        return CircularLowPassFilter(alpha)
    raise ValueError(f"unknown filter type: {filter_type}")
