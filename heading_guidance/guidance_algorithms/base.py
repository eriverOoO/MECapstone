"""Guidance intensity 전략의 공통 인터페이스."""

from abc import ABC, abstractmethod


class GuidanceAlgorithm(ABC):
    """오차 크기를 0~1 진동 세기로 변환하는 전략."""

    name: str

    @abstractmethod
    def intensity(self, error_magnitude_deg: float, now_seconds: float) -> float:
        """현재 오차와 시간에 해당하는 순간 진동 세기를 반환한다."""

    def reset(self, now_seconds: float = 0.0) -> None:
        """상태가 있는 알고리즘을 초기화한다."""

