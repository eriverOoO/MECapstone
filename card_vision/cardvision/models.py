"""Device-independent observation and command contracts."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Status(str, Enum):
    CORRECT = "CORRECT"
    REVERSED = "REVERSED"
    CHIP_NOT_VISIBLE = "CHIP_NOT_VISIBLE"
    UNKNOWN = "UNKNOWN"


class Action(str, Enum):
    FLIP = "FLIP"
    ROTATE_180 = "ROTATE_180"
    INSERT = "INSERT"
    RECHECK = "RECHECK"
    ERROR = "ERROR"


CARD_CLASSES = {Status.CORRECT:("FRONT_CORRECT","앞면 정방향"),
                Status.REVERSED:("FRONT_REVERSED","앞면 반대방향"),
                Status.CHIP_NOT_VISIBLE:("BACK_LIKELY","뒷면 추정"),
                Status.UNKNOWN:("UNKNOWN","판단 보류")}


@dataclass
class Observation:
    frame: int
    timestamp: float
    status: Status = Status.UNKNOWN
    card_detected: bool = False
    chip_detected: bool = False
    card_score: float = 0.0
    score: float = 0.0
    reason: str = "no_card"
    card_quad: Any = None
    inspection_roi: tuple[int,int,int,int] | None = None
    chip_box: tuple[int, int, int, int] | None = None
    chip_center: tuple[float, float] | None = None
    chip_relative: tuple[float, float] | None = None
    chip_polygon: Any = None
    expected_chip_regions: list = field(default_factory=list)
    rejected_chips: list[dict] = field(default_factory=list)
    processing_ms: float = 0.0
    debug: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def card_class(self) -> str:
        return CARD_CLASSES[self.status][0]

    @property
    def card_label(self) -> str:
        return CARD_CLASSES[self.status][1]

    def record(self) -> dict:
        """Metadata only; never serialize source pixels or card text."""
        return {"frame": self.frame, "timestamp": self.timestamp,
                "status": self.status.value, "card_detected": self.card_detected,
                "card_class":self.card_class,"card_label":self.card_label,
                "chip_detected": self.chip_detected, "card_score": self.card_score,
                "score": self.score, "reason": self.reason,
                "card_quad": self.card_quad.tolist() if self.card_quad is not None else None,
                "inspection_roi": self.inspection_roi,
                "chip_polygon": self.chip_polygon.tolist() if self.chip_polygon is not None else None,
                "expected_chip_regions":self.expected_chip_regions,"rejected_chips":self.rejected_chips,
                "chip_box": self.chip_box, "chip_center": self.chip_center,
                "chip_relative": self.chip_relative, "processing_ms": self.processing_ms}


@dataclass(frozen=True)
class Command:
    command_id: int
    card_status: Status
    action: Action
    requires_recheck: bool

    def record(self) -> dict:
        return {"command_id": self.command_id, "card_status": self.card_status.value,
                "action": self.action.value, "requires_recheck": self.requires_recheck}
