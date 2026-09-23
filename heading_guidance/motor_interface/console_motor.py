"""하드웨어 없이 마지막 PWM을 보관하는 motor mock."""

from heading_controller import GuidanceCommand


class ConsoleMotorController:
    def __init__(self, verbose: bool = False) -> None:
        self.left_pwm = 0
        self.right_pwm = 0
        self.verbose = verbose

    def send(self, command: GuidanceCommand) -> None:
        self.left_pwm = command.left_pwm
        self.right_pwm = command.right_pwm
        if self.verbose:
            print(f"MOTOR L={self.left_pwm}, R={self.right_pwm}")

    def stop(self) -> None:
        self.left_pwm = 0
        self.right_pwm = 0
        if self.verbose:
            print("MOTOR L=0, R=0")

