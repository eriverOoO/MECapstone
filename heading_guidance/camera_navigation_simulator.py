"""물리 카메라 없이 localization → route → target heading 연결을 검증한다."""

import argparse
import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt

import config
from route import Position, RouteNavigator, distance
from vision import LocalizationStatus, Pose2D, PoseTracker, SyntheticPoseProvider


def _move_toward(current: Position, target: Position, maximum_distance: float) -> Position:
    remaining = distance(current, target)
    if remaining == 0.0 or remaining <= maximum_distance:
        return target
    ratio = maximum_distance / remaining
    return Position(
        current.x + (target.x - current.x) * ratio,
        current.y + (target.y - current.y) * ratio,
    )


def run_camera_navigation_simulation(
    output_directory: str | Path = config.RESULTS_DIRECTORY,
    random_seed: int = config.CAMERA_SIMULATION_SEED,
) -> tuple[Path, Path]:
    """noisy/dropout camera pose로 waypoint target heading을 계산해 기록한다."""

    waypoints = [Position(*point) for point in config.DEFAULT_WAYPOINTS]
    true_position = waypoints[0]
    true_target_index = 1 if len(waypoints) > 1 else len(waypoints)
    initial_pose = Pose2D(true_position.x, true_position.y, 0.0, 0.0, "ground_truth")
    camera = SyntheticPoseProvider(initial_pose, random_seed=random_seed)
    tracker = PoseTracker(config.CAMERA_MAX_POSE_AGE_SEC)
    navigator = RouteNavigator(
        config.DEFAULT_WAYPOINTS,
        config.WAYPOINT_REACHED_DISTANCE,
        initial_position=true_position,
    )

    rows: list[dict[str, str | float | int]] = []
    true_history: list[Position] = []
    estimated_history: list[Position] = []
    dt = config.CAMERA_SIMULATION_DT_SEC
    maximum_steps = round(config.CAMERA_SIMULATION_MAX_TIME_SEC / dt)

    for step in range(maximum_steps + 1):
        now = step * dt
        if true_target_index < len(waypoints):
            target = waypoints[true_target_index]
            dx = target.x - true_position.x
            dy = target.y - true_position.y
            yaw = math.degrees(math.atan2(dy, dx)) % 360.0
            true_position = _move_toward(
                true_position,
                target,
                config.CAMERA_SIMULATION_SPEED_UNITS_PER_SEC * dt,
            )
            if true_position == target:
                true_target_index += 1
        else:
            yaw = 0.0

        true_pose = Pose2D(
            true_position.x, true_position.y, yaw, now, "ground_truth"
        )
        camera.set_true_pose(true_pose)
        raw_result = camera.estimate(now)
        tracked_result = tracker.update(raw_result, now)

        estimated_position: Position | None = None
        if (
            tracked_result.status == LocalizationStatus.TRACKING
            and tracked_result.pose is not None
        ):
            estimated_position = Position(
                tracked_result.pose.x, tracked_result.pose.y
            )
            navigator.update_position(estimated_position)
            estimated_history.append(estimated_position)

        target_heading = navigator.target_heading()
        target_waypoint = navigator.target_waypoint
        position_error = (
            distance(true_position, estimated_position)
            if estimated_position is not None
            else math.nan
        )
        rows.append(
            {
                "time_seconds": f"{now:.3f}",
                "true_x": f"{true_position.x:.4f}",
                "true_y": f"{true_position.y:.4f}",
                "estimated_x": "" if estimated_position is None else f"{estimated_position.x:.4f}",
                "estimated_y": "" if estimated_position is None else f"{estimated_position.y:.4f}",
                "position_error": "" if math.isnan(position_error) else f"{position_error:.4f}",
                "raw_localization_status": raw_result.status.value,
                "tracked_localization_status": tracked_result.status.value,
                "target_heading": "" if target_heading is None else f"{target_heading:.3f}",
                "target_waypoint_x": "" if target_waypoint is None else f"{target_waypoint.x:.3f}",
                "target_waypoint_y": "" if target_waypoint is None else f"{target_waypoint.y:.3f}",
            }
        )
        true_history.append(true_position)
        if true_target_index >= len(waypoints) and navigator.completed:
            break

    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    csv_path = directory / "camera_navigation_simulation.csv"
    plot_path = directory / "camera_navigation_simulation.png"
    with csv_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    _save_plot(waypoints, true_history, estimated_history, rows, plot_path)
    return csv_path, plot_path


def _save_plot(
    waypoints: list[Position],
    true_history: list[Position],
    estimated_history: list[Position],
    rows: list[dict[str, str | float | int]],
    output_path: Path,
) -> None:
    figure, axes = plt.subplots(2, 1, figsize=(9, 10))
    axes[0].plot(
        [point.x for point in waypoints],
        [point.y for point in waypoints],
        "o--",
        label="Waypoints",
    )
    axes[0].plot(
        [point.x for point in true_history],
        [point.y for point in true_history],
        label="True path",
    )
    if estimated_history:
        axes[0].scatter(
            [point.x for point in estimated_history],
            [point.y for point in estimated_history],
            s=6,
            alpha=0.5,
            label="Camera estimated pose",
        )
    axes[0].set_aspect("equal", adjustable="datalim")
    axes[0].set_xlabel("X")
    axes[0].set_ylabel("Y")
    axes[0].set_title("Synthetic Camera Localization and Route")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    valid_rows = [row for row in rows if row["position_error"] != ""]
    axes[1].plot(
        [float(row["time_seconds"]) for row in valid_rows],
        [float(row["position_error"]) for row in valid_rows],
        label="Position error",
    )
    axes[1].set_xlabel("Time (s)")
    axes[1].set_ylabel("Position error")
    axes[1].set_title("Localization Error")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run camera/localization pipeline without camera hardware"
    )
    parser.add_argument("--seed", type=int, default=config.CAMERA_SIMULATION_SEED)
    args = parser.parse_args()
    csv_path, plot_path = run_camera_navigation_simulation(random_seed=args.seed)
    print(f"Camera simulation CSV: {csv_path}")
    print(f"Camera simulation graph: {plot_path}")


if __name__ == "__main__":
    main()

