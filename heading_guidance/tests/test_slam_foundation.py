"""SLAM I/O baseline and route boundary tests."""

import pytest

from route import Position, RouteNavigator
from vision.models import LocalizationStatus, Pose2D
from vision.slam_foundation import (
    LandmarkObservation,
    OdometryDelta,
    OdometryLandmarkBaseline,
    SlamInput,
    update_route_from_slam,
)


def test_body_motion_rotates_into_world_frame() -> None:
    backend = OdometryLandmarkBaseline(Pose2D(0.0, 0.0, 90.0, 0.0))
    result = backend.process(SlamInput(1.0, OdometryDelta(2.0, 0.0, 0.0)))
    pose = result.localization.pose
    assert pose is not None
    assert pose.x == pytest.approx(0.0, abs=1e-9)
    assert pose.y == pytest.approx(2.0)
    assert pose.yaw_deg == 90.0


def test_landmark_observation_builds_a_small_map() -> None:
    backend = OdometryLandmarkBaseline()
    first = backend.process(
        SlamInput(1.0, OdometryDelta(1.0, 0.0, 0.0), (LandmarkObservation(7, 4.0, 0.0),))
    )
    second = backend.process(
        SlamInput(2.0, OdometryDelta(1.0, 0.0, 0.0), (LandmarkObservation(7, 3.0, 0.0),))
    )
    assert first.landmarks[0].x == pytest.approx(5.0)
    assert second.landmarks[0].x == pytest.approx(5.0)
    assert second.landmarks[0].observations == 2


def test_missing_odometry_returns_lost_without_moving_route() -> None:
    backend = OdometryLandmarkBaseline()
    navigator = RouteNavigator([(0.0, 0.0), (5.0, 0.0)], 0.5)
    tracked = backend.process(SlamInput(1.0, OdometryDelta(1.0, 0.0, 0.0)))
    assert update_route_from_slam(navigator, tracked) == pytest.approx(0.0)
    lost = backend.process(SlamInput(2.0, None))
    assert lost.localization.status == LocalizationStatus.LOST
    assert update_route_from_slam(navigator, lost) is None
    assert navigator.position == Position(1.0, 0.0)


def test_out_of_order_observation_is_rejected() -> None:
    backend = OdometryLandmarkBaseline()
    backend.process(SlamInput(1.0, OdometryDelta(0.0, 0.0, 0.0)))
    with pytest.raises(ValueError, match="timestamps"):
        backend.process(SlamInput(1.0, OdometryDelta(1.0, 0.0, 0.0)))


def test_landmark_without_pose_update_is_rejected() -> None:
    with pytest.raises(ValueError, match="require an odometry"):
        SlamInput(1.0, None, (LandmarkObservation(1, 2.0, 0.0),))


def test_replay_file_loads() -> None:
    from pathlib import Path

    from slam_replay import load_inputs

    path = Path(__file__).resolve().parents[1] / "samples" / "slam_replay.jsonl"
    inputs = load_inputs(path)
    assert len(inputs) == 4
    assert inputs[2].odometry is None
