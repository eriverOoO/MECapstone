"""모터 출력 인터페이스."""

from typing import Protocol
from heading_controller import GuidanceCommand


class MotorOutput(Protocol):
    def send(self, command: GuidanceCommand) -> None: ...

    def stop(self) -> None: ...

