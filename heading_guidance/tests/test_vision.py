"""hardware-free camera localization 계층 테스트."""

import json

import pytest

from route import Position, RouteNavigator
from vision.configuration import CameraCalibration, MarkerMap
from vision.models import LocalizationResult, LocalizationStatus, Pose2D
from vision.pose_tracker import PoseTracker
from vision.synthetic_localizer import SyntheticPoseProvider


def test_synthetic_localizer_without_noise_is_exact() -> None:
    truth = Pose2D(1.0, 2.0, 359.0, 1.0, "truth")
    provider = SyntheticPoseProvider(
        truth,
        position_noise_std=0.0,
        yaw_noise_std_deg=0.0,
        dropout_probability=0.0,
        latency_seconds=0.1,
        random_seed=1,
    )
    result = provider.estimate(2.0)
    assert result.status == LocalizationStatus.TRACKING
    assert result.pose is not None
    assert result.pose.x == 1.0
    assert result.pose.y == 2.0
    assert result.pose.yaw_deg == 359.0
    assert result.pose.timestamp_seconds == pytest.approx(1.9)


def test_pose_tracker_bridges_short_dropout_then_becomes_stale() -> None:
    tracker = PoseTracker(max_pose_age_seconds=0.3)
    pose = Pose2D(1.0, 2.0, 0.0, 1.0, "camera")
    tracked = tracker.update(
        LocalizationResult(LocalizationStatus.TRACKING, pose), 1.1
    )
    assert tracked.status == LocalizationStatus.TRACKING
    held = tracker.update(LocalizationResult(LocalizationStatus.LOST, None), 1.2)
    assert held.status == LocalizationStatus.TRACKING
    assert held.pose == pose
    stale = tracker.update(LocalizationResult(LocalizationStatus.LOST, None), 1.31)
    assert stale.status == LocalizationStatus.STALE
    assert stale.pose is None


def test_camera_pose_updates_route_position() -> None:
    navigator = RouteNavigator([(0.0, 0.0), (2.0, 0.0)], 0.25)
    pose = Pose2D(1.0, 0.0, 0.0, 0.0, "camera")
    navigator.update_position(Position(pose.x, pose.y))
    assert navigator.position == Position(1.0, 0.0)
    assert navigator.target_heading() == pytest.approx(0.0)


def test_camera_calibration_and_marker_map_loaders(tmp_path) -> None:
    calibration_path = tmp_path / "calibration.json"
    calibration_path.write_text(
        json.dumps(
            {
                "calibrated": True,
                "image_width": 640,
                "image_height": 480,
                "camera_matrix": [[600, 0, 320], [0, 600, 240], [0, 0, 1]],
                "distortion_coefficients": [0, 0, 0, 0, 0],
            }
        ),
        encoding="utf-8",
    )
    marker_path = tmp_path / "markers.json"
    marker_path.write_text(
        json.dumps({"markers": [{"id": 7, "x": 1, "y": 2, "yaw_deg": 90}]}),
        encoding="utf-8",
    )
    calibration = CameraCalibration.from_json(calibration_path)
    marker_map = MarkerMap.from_json(marker_path)
    assert calibration.camera_matrix[0][0] == 600.0
    assert calibration.calibrated
    assert marker_map.get(7) is not None
    assert marker_map.get(7).yaw_deg == 90.0


def test_marker_map_rejects_duplicate_ids(tmp_path) -> None:
    marker_path = tmp_path / "duplicates.json"
    marker_path.write_text(
        json.dumps(
            {
                "markers": [
                    {"id": 1, "x": 0, "y": 0},
                    {"id": 1, "x": 1, "y": 1},
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unique"):
        MarkerMap.from_json(marker_path)
