"""카메라 및 localization 계층에서 공유하는 데이터 모델."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from heading_controller import normalize_heading


class LocalizationStatus(str, Enum):
    TRACKING = "TRACKING"
    LOST = "LOST"
    STALE = "STALE"


@dataclass(frozen=True)
class Pose2D:
    """평면상의 위치와 yaw. timestamp는 simulation/monotonic seconds다."""

    x: float
    y: float
    yaw_deg: float
    timestamp_seconds: float
    source: str = "unknown"
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(self, "yaw_deg", normalize_heading(self.yaw_deg))


@dataclass(frozen=True)
class FramePacket:
    """frame 데이터와 취득 시각을 함께 전달하는 장치 독립 컨테이너."""

    image: Any
    timestamp_seconds: float
    sequence: int


@dataclass(frozen=True)
class LocalizationResult:
    status: LocalizationStatus
    pose: Pose2D | None
    detected_marker_ids: tuple[int, ...] = ()
    message: str = ""

