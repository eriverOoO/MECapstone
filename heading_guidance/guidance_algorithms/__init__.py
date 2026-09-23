"""진동 guidance 전략 생성 도우미."""

from .base import GuidanceAlgorithm
from .continuous import ContinuousGuidance
from .discrete import DiscreteGuidance
from .pulse import PulseGuidance


def create_guidance_algorithm(name: str) -> GuidanceAlgorithm:
    """설정/CLI 이름에 맞는 전략 객체를 생성한다."""

    normalized = name.lower()
    if normalized == "continuous":
        return ContinuousGuidance()
    if normalized == "discrete":
        return DiscreteGuidance()
    if normalized == "pulse":
        return PulseGuidance()
    raise ValueError(f"unknown guidance algorithm: {name}")


__all__ = [
    "GuidanceAlgorithm",
    "ContinuousGuidance",
    "DiscreteGuidance",
    "PulseGuidance",
    "create_guidance_algorithm",
]
