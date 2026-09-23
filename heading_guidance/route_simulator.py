"""키보드 위치 이동으로 waypoint navigation 계층을 시험한다."""

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt

import config
from imu_simulator import IMUSimulator, ImmediateKeyboard
from logger import CSVGuidanceLogger
from main import build_controller, print_status
from motor_interface import ConsoleMotorController
from route import Position, RouteNavigator


def save_route_plot(
    navigator: RouteNavigator,
    history: list[Position],
    headings: list[float],
    output_path: Path,
) -> Path:
    """경로, 이동 궤적, 마지막 heading 화살표를 PNG로 저장한다."""

    waypoint_x = [point.x for point in navigator.waypoints]
    waypoint_y = [point.y for point in navigator.waypoints]
    history_x = [point.x for point in history]
    history_y = [point.y for point in history]
    figure, axis = plt.subplots(figsize=(8, 6))
    axis.plot(waypoint_x, waypoint_y, "o--", label="Planned waypoints")
    axis.plot(history_x, history_y, ".-", label="Simulated position")
    current = history[-1]
    heading_rad = math.radians(headings[-1])
    axis.arrow(
        current.x,
        current.y,
        math.cos(heading_rad),
        math.sin(heading_rad),
        width=0.04,
        length_includes_head=True,
        color="tab:red",
        label="Current heading",
    )
    target = navigator.target_waypoint
    if target is not None:
        axis.scatter([target.x], [target.y], s=160, facecolors="none", edgecolors="green", label="Next waypoint")
    axis.set_aspect("equal", adjustable="datalim")
    axis.set_xlabel("X")
    axis.set_ylabel("Y")
    axis.grid(True, alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
    return output_path


def run_route_simulator(guidance_name: str, show_plot: bool) -> tuple[Path, Path]:
    navigator = RouteNavigator(
        config.DEFAULT_WAYPOINTS, config.WAYPOINT_REACHED_DISTANCE
    )
    imu = IMUSimulator(config.DEFAULT_CURRENT_HEADING_DEG)
    controller = build_controller(guidance_name)
    motors = ConsoleMotorController()
    history = [navigator.position]
    headings = [imu.true_heading]

    print("Position: W/S=+Y/-Y, A/D=-X/+X | Heading: J/L=left/right")
    print("Safety: E=emergency stop, R=resume | Q=quit")
    with CSVGuidanceLogger(config.LOG_DIRECTORY) as data_logger:
        def update() -> None:
            reading = imu.sample()
            target_heading = navigator.target_heading()
            if target_heading is None:
                target_heading = reading.filtered_heading
            command = controller.update(target_heading, reading.filtered_heading)
            motors.send(command)
            waypoint = navigator.target_waypoint
            data_logger.log(
                target_heading,
                reading,
                command,
                current_x=navigator.position.x,
                current_y=navigator.position.y,
                target_waypoint_x=None if waypoint is None else waypoint.x,
                target_waypoint_y=None if waypoint is None else waypoint.y,
            )
            print_status(target_heading, reading, command)
            print(
                f"Position       : ({navigator.position.x:.1f}, {navigator.position.y:.1f})"
            )
            print(f"Next waypoint  : {waypoint if waypoint else 'ROUTE COMPLETE'}")
            history.append(navigator.position)
            headings.append(reading.true_heading)

        update()
        try:
            with ImmediateKeyboard() as keyboard:
                while True:
                    key = keyboard.read_key()
                    if key == "w":
                        navigator.move(0.0, config.POSITION_STEP)
                    elif key == "s":
                        navigator.move(0.0, -config.POSITION_STEP)
                    elif key == "a":
                        navigator.move(-config.POSITION_STEP, 0.0)
                    elif key == "d":
                        navigator.move(config.POSITION_STEP, 0.0)
                    elif key == "j":
                        imu.rotate_left(config.HEADING_STEP_DEG)
                    elif key == "l":
                        imu.rotate_right(config.HEADING_STEP_DEG)
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
        log_path = data_logger.path

    plot_path = Path(config.LOG_DIRECTORY) / f"{log_path.stem}_route.png"
    save_route_plot(navigator, history, headings, plot_path)
    if show_plot:
        image = plt.imread(plot_path)
        plt.figure(figsize=(8, 6))
        plt.imshow(image)
        plt.axis("off")
        plt.show()
    return log_path, plot_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive 2D waypoint simulator")
    parser.add_argument(
        "--guidance",
        choices=("continuous", "discrete", "pulse"),
        default=config.DEFAULT_GUIDANCE_ALGORITHM,
    )
    parser.add_argument("--no-show", action="store_true")
    args = parser.parse_args()
    log_path, plot_path = run_route_simulator(args.guidance, not args.no_show)
    print(f"Log saved: {log_path}")
    print(f"Route graph saved: {plot_path}")


if __name__ == "__main__":
    main()
