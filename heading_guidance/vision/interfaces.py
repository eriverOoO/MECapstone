"""실제 카메라, 저장 영상, simulator가 공유할 인터페이스."""

from typing import Protocol

from .models import FramePacket, LocalizationResult


class FrameSource(Protocol):
    """향후 USB/CSI camera 또는 video file reader가 구현할 인터페이스."""

    def read(self) -> FramePacket | None:
        """다음 frame을 반환하며 stream 종료/실패 시 None을 반환한다."""
        ...

    def close(self) -> None:
        """source resource를 해제한다."""
        ...


class PoseProvider(Protocol):
    """frame 기반 및 synthetic localizer가 구현할 공통 인터페이스."""

    def estimate(self, timestamp_seconds: float) -> LocalizationResult:
        """해당 시각의 위치추정 결과를 반환한다."""
        ...

