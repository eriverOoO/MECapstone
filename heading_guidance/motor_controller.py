"""이전 import 경로를 보존하는 호환 모듈.

새 코드는 `motor_interface` 패키지를 직접 사용하는 것을 권장한다.
"""

from motor_interface import ConsoleMotorController, MotorOutput, SerialMotorController

__all__ = ["MotorOutput", "ConsoleMotorController", "SerialMotorController"]
