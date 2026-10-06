"""Replay synthetic odometry/landmark JSONL through the SLAM foundation."""

import argparse
import json
from pathlib import Path

import config
from route import RouteNavigator
from vision.slam_foundation import (
    LandmarkObservation,
    OdometryDelta,
    OdometryLandmarkBaseline,
    SlamInput,
    update_route_from_slam,
)


def load_inputs(path: str | Path) -> list[SlamInput]:
    """Load an offline recording; no sensor or camera is opened."""

    inputs: list[SlamInput] = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                odometry_data = item.get("odometry")
                odometry = (
                    None
                    if odometry_data is None
                    else OdometryDelta(
                        float(odometry_data["forward"]),
                        float(odometry_data.get("left", 0.0)),
                        float(odometry_data.get("yaw_deg", 0.0)),
                    )
                )
                landmarks = tuple(
                    LandmarkObservation(
                        int(entry["id"]),
                        float(entry["forward"]),
                        float(entry.get("left", 0.0)),
                    )
                    for entry in item.get("landmarks", [])
                )
                inputs.append(SlamInput(float(item["timestamp_seconds"]), odometry, landmarks))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                raise ValueError(f"invalid replay line {line_number}: {error}") from error
    return inputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay synthetic 2D SLAM inputs")
    parser.add_argument(
        "recording", nargs="?", default="samples/slam_replay.jsonl"
    )
    args = parser.parse_args()
    backend = OdometryLandmarkBaseline()
    navigator = RouteNavigator(
        config.DEFAULT_WAYPOINTS,
        config.WAYPOINT_REACHED_DISTANCE,
    )
    for observation in load_inputs(args.recording):
        update = backend.process(observation)
        heading = update_route_from_slam(navigator, update)
        pose = update.localization.pose
        position = "unavailable" if pose is None else f"({pose.x:.2f}, {pose.y:.2f})"
        target = "none" if heading is None else f"{heading:.1f} deg"
        print(
            f"t={observation.timestamp_seconds:.1f}s "
            f"status={update.localization.status.value} "
            f"pose={position} landmarks={len(update.landmarks)} "
            f"target_heading={target}"
        )


if __name__ == "__main__":
    main()
