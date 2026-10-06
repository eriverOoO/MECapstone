"""Offline 2D SLAM integration baseline.

This module deliberately uses odometry and observed landmarks only. It has no
camera feature extraction, data association, loop closure, or map optimization.
Its contracts allow a future SLAM backend to replace the baseline while keeping
the existing Pose2D → RouteNavigator boundary.
"""

import math
from dataclasses import dataclass
from typing import Protocol

from heading_controller import normalize_heading
from route import Position, RouteNavigator

from .models import LocalizationResult, LocalizationStatus, Pose2D


def _require_finite(value: float, name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True)
class OdometryDelta:
    """Motion since the previous update, expressed in the previous body frame.

    +X is forward, +Y is left, and positive yaw rotates counterclockwise.
    Distances use the same unit as route waypoints (meters when calibrated).
    """

    forward: float
    left: float
    yaw_deg: float

    def __post_init__(self) -> None:
        for name, value in (
            ("forward", self.forward),
            ("left", self.left),
            ("yaw_deg", self.yaw_deg),
        ):
            _require_finite(value, name)


@dataclass(frozen=True)
class LandmarkObservation:
    """One landmark's position relative to the current body frame."""

    landmark_id: int
    forward: float
    left: float

    def __post_init__(self) -> None:
        if self.landmark_id < 0:
            raise ValueError("landmark_id must be nonnegative")
        _require_finite(self.forward, "landmark forward")
        _require_finite(self.left, "landmark left")


@dataclass(frozen=True)
class SlamInput:
    """Time-ordered odometry with optional landmark observations."""

    timestamp_seconds: float
    odometry: OdometryDelta | None
    landmarks: tuple[LandmarkObservation, ...] = ()

    def __post_init__(self) -> None:
        _require_finite(self.timestamp_seconds, "timestamp_seconds")
        if self.odometry is None and self.landmarks:
            raise ValueError("landmarks require an odometry update in this baseline")
        ids = [item.landmark_id for item in self.landmarks]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate landmark IDs in one update")


@dataclass(frozen=True)
class MappedLandmark:
    landmark_id: int
    x: float
    y: float
    observations: int


@dataclass(frozen=True)
class SlamUpdate:
    localization: LocalizationResult
    landmarks: tuple[MappedLandmark, ...]


class SlamBackend(Protocol):
    """Contract for a later visual/visual-inertial SLAM implementation."""

    def process(self, observation: SlamInput) -> SlamUpdate:
        """Consume one ordered observation and return pose plus map snapshot."""
        ...

    def reset(self, initial_pose: Pose2D | None = None) -> None:
        """Start a new localization/map session."""
        ...


class OdometryLandmarkBaseline:
    """Dead-reckon a pose and average observed landmark positions.

    This baseline does not correct accumulated pose drift from landmarks. It
    exists to exercise SLAM I/O, coordinate conventions, and route integration.
    """

    def __init__(self, initial_pose: Pose2D | None = None) -> None:
        self.reset(initial_pose)

    def reset(self, initial_pose: Pose2D | None = None) -> None:
        self._pose = initial_pose or Pose2D(0.0, 0.0, 0.0, 0.0, "odom_landmark_baseline")
        self._last_timestamp = self._pose.timestamp_seconds
        self._landmarks: dict[int, MappedLandmark] = {}

    @property
    def pose(self) -> Pose2D:
        return self._pose

    def process(self, observation: SlamInput) -> SlamUpdate:
        if observation.timestamp_seconds <= self._last_timestamp:
            raise ValueError("SLAM input timestamps must increase strictly")
        self._last_timestamp = observation.timestamp_seconds

        if observation.odometry is None:
            return SlamUpdate(
                LocalizationResult(
                    LocalizationStatus.LOST,
                    None,
                    message="odometry unavailable; pose was not advanced",
                ),
                self._map_snapshot(),
            )

        motion = observation.odometry
        heading = math.radians(self._pose.yaw_deg)
        world_dx = math.cos(heading) * motion.forward - math.sin(heading) * motion.left
        world_dy = math.sin(heading) * motion.forward + math.cos(heading) * motion.left
        self._pose = Pose2D(
            self._pose.x + world_dx,
            self._pose.y + world_dy,
            normalize_heading(self._pose.yaw_deg + motion.yaw_deg),
            observation.timestamp_seconds,
            "odom_landmark_baseline",
        )

        for landmark in observation.landmarks:
            x, y = self._body_to_world(landmark.forward, landmark.left)
            previous = self._landmarks.get(landmark.landmark_id)
            count = 1 if previous is None else previous.observations + 1
            mean_x = x if previous is None else previous.x + (x - previous.x) / count
            mean_y = y if previous is None else previous.y + (y - previous.y) / count
            self._landmarks[landmark.landmark_id] = MappedLandmark(
                landmark.landmark_id, mean_x, mean_y, count
            )

        return SlamUpdate(
            LocalizationResult(LocalizationStatus.TRACKING, self._pose),
            self._map_snapshot(),
        )

    def _body_to_world(self, forward: float, left: float) -> tuple[float, float]:
        heading = math.radians(self._pose.yaw_deg)
        return (
            self._pose.x + math.cos(heading) * forward - math.sin(heading) * left,
            self._pose.y + math.sin(heading) * forward + math.cos(heading) * left,
        )

    def _map_snapshot(self) -> tuple[MappedLandmark, ...]:
        return tuple(self._landmarks[key] for key in sorted(self._landmarks))


def update_route_from_slam(
    navigator: RouteNavigator, update: SlamUpdate
) -> float | None:
    """Pass a valid SLAM pose into the existing route planner boundary."""

    result = update.localization
    if result.status != LocalizationStatus.TRACKING or result.pose is None:
        return None
    navigator.update_position(Position(result.pose.x, result.pose.y))
    return navigator.target_heading()
