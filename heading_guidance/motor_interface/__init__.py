"""교체 가능한 진동모터 출력 구현."""

from .base import MotorOutput
from .console_motor import ConsoleMotorController
from .serial_motor import SerialMotorController

__all__ = ["MotorOutput", "ConsoleMotorController", "SerialMotorController"]
