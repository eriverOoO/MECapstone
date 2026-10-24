"""Consecutive evidence filter; no camera or OpenCV dependency."""
from collections import deque
from ..models import Status


class Stabilizer:
    def __init__(self, frames: int):
        if frames < 1:
            raise ValueError("frames must be positive")
        self.history = deque(maxlen=frames)

    def reset(self) -> None:
        self.history.clear()

    def update(self, status: Status) -> Status:
        self.history.append(status)
        if len(self.history) == self.history.maxlen and len(set(self.history)) == 1:
            return status
        return Status.UNKNOWN
