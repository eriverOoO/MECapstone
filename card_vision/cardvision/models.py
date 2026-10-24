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
    processing_ms: float = 0.0
    debug: dict[str, Any] = field(default_factory=dict, repr=False)

    def record(self) -> dict:
        """Metadata only; never serialize source pixels or card text."""
        return {"frame": self.frame, "timestamp": self.timestamp,
                "status": self.status.value, "card_detected": self.card_detected,
                "chip_detected": self.chip_detected, "card_score": self.card_score,
                "score": self.score, "reason": self.reason,
                "card_quad": self.card_quad.tolist() if self.card_quad is not None else None,
                "inspection_roi": self.inspection_roi,
                "chip_polygon": self.chip_polygon.tolist() if self.chip_polygon is not None else None,
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
