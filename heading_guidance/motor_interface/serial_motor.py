"""Raspberry Pi에서 ESP32로 PWM을 보낼 serial 구현 골격."""

from heading_controller import GuidanceCommand


class SerialMotorController:
    """`LEFT_PWM=n,RIGHT_PWM=n` 한 줄 프로토콜을 사용한다.

    pyserial은 이 클래스를 실제 생성할 때만 필요하므로 simulator 실행에는
    설치할 필요가 없다.
    """

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0) -> None:
        try:
            import serial
        except ImportError as error:
            raise RuntimeError(
                "serial mode requires pyserial: pip install pyserial"
            ) from error
        self._serial = serial.Serial(port, baudrate=baudrate, timeout=timeout)

    def send(self, command: GuidanceCommand) -> None:
        message = (
            f"LEFT_PWM={command.left_pwm},RIGHT_PWM={command.right_pwm}\n"
        )
        self._serial.write(message.encode("ascii"))

    def stop(self) -> None:
        self._serial.write(b"LEFT_PWM=0,RIGHT_PWM=0\n")

    def close(self) -> None:
        self.stop()
        self._serial.close()

