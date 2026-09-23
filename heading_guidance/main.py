"""착용형 heading 안내 소프트웨어 프로토타입 실행 프로그램."""

import argparse
from pathlib import Path

import config
from guidance_algorithms import create_guidance_algorithm
from heading_controller import GuidanceCommand, HeadingController, normalize_heading
from imu_simulator import HeadingReading, IMUSimulator, ImmediateKeyboard
from logger import CSVGuidanceLogger
from motor_controller import ConsoleMotorController


def build_controller(guidance_name: str = config.DEFAULT_GUIDANCE_ALGORITHM) -> HeadingController:
    """config 값으로 controller를 생성한다."""

    return HeadingController(
        deadband_deg=config.DEADBAND_DEG,
        reentry_deg=config.HYSTERESIS_REENTRY_DEG,
        max_intensity_error_deg=config.MAX_INTENSITY_ERROR_DEG,
        pwm_max=config.PWM_MAX,
        guidance_algorithm=create_guidance_algorithm(guidance_name),
    )


def print_status(
    target: float, reading: HeadingReading, command: GuidanceCommand
) -> None:
    """현재 제어 상태를 읽기 쉬운 형식으로 출력한다."""

    print("\n" + "-" * 38)
    print(f"Target Heading : {target:6.1f} deg")
    print(f"True Heading   : {reading.true_heading:6.1f} deg")
    print(f"Measured       : {reading.measured_heading:6.1f} deg")
    print(f"Filtered       : {reading.filtered_heading:6.1f} deg")
    print(f"Heading Error  : {command.error_deg:+6.1f} deg")
    print(f"Direction      : {command.direction.value}")
    print(f"State          : {command.system_state.value}")
    print(f"Algorithm      : {command.guidance_algorithm}")
    print(f"Intensity      : {command.intensity:.2f}")
    print(f"LEFT_PWM       : {command.left_pwm}")
    print(f"RIGHT_PWM      : {command.right_pwm}")


def parse_target(text: str) -> float:
    """사용자 입력 target이 0~360도 범위인지 검사한다."""

    value = float(text)
    if not 0.0 <= value <= 360.0:
        raise ValueError("target heading must be between 0 and 360 degrees")
    return normalize_heading(value)


def run_simulation(
    target_heading: float,
    initial_heading: float,
    step_deg: float,
    log_directory: str | Path,
    guidance_name: str = config.DEFAULT_GUIDANCE_ALGORITHM,
    filter_type: str = config.FILTER_TYPE,
) -> Path:
    """A/D/T/Q 키를 처리하는 대화형 시뮬레이션을 실행한다."""

    imu = IMUSimulator(initial_heading, filter_type=filter_type)
    controller = build_controller(guidance_name)
    motors = ConsoleMotorController()

    print("Controls: A=left, D=right, T=target, E=emergency stop, R=resume, Q=quit")
    with CSVGuidanceLogger(log_directory) as data_logger:
        def update() -> None:
            reading = imu.sample()
            command = controller.update(target_heading, reading.filtered_heading)
            motors.send(command)
            data_logger.log(target_heading, reading, command)
            print_status(target_heading, reading, command)

        update()
        try:
            with ImmediateKeyboard() as keyboard:
                while True:
                    key = keyboard.read_key()
                    if key == "a":
                        imu.rotate_left(step_deg)
                    elif key == "d":
                        imu.rotate_right(step_deg)
                    elif key == "t":
                        try:
                            target_heading = parse_target(
                                keyboard.read_line("New target heading (0-360): ")
                            )
                        except ValueError as error:
                            print(f"Invalid target: {error}")
                            continue
                    elif key == "e":
                        controller.emergency_stop()
                    elif key == "r":
                        controller.resume()
                    elif key == "q":
                        break
                    else:
                        continue
                    update()
        finally:
            motors.stop()

        return data_logger.path


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive heading guidance simulator")
    parser.add_argument("--target", type=parse_target, default=config.DEFAULT_TARGET_HEADING_DEG)
    parser.add_argument("--current", type=parse_target, default=config.DEFAULT_CURRENT_HEADING_DEG)
    parser.add_argument("--step", type=float, default=config.HEADING_STEP_DEG)
    parser.add_argument(
        "--guidance",
        choices=("continuous", "discrete", "pulse"),
        default=config.DEFAULT_GUIDANCE_ALGORITHM,
    )
    parser.add_argument(
        "--filter",
        choices=("none", "moving_average", "low_pass"),
        default=config.FILTER_TYPE,
    )
    parser.add_argument("--no-plot", action="store_true", help="do not create/show graphs on exit")
    args = parser.parse_args()
    if args.step <= 0.0:
        parser.error("--step must be positive")

    log_path = run_simulation(
        args.target,
        args.current,
        args.step,
        config.LOG_DIRECTORY,
        args.guidance,
        args.filter,
    )
    print(f"\nLog saved: {log_path}")

    if not args.no_plot:
        try:
            from plot_logs import plot_log

            graph_path = plot_log(log_path)
            print(f"Graph saved: {graph_path}")
        except (ImportError, RuntimeError) as error:
            print(f"Could not display graph ({error}). Run plot_logs.py later.")


if __name__ == "__main__":
    main()
