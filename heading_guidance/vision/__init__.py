"""하드웨어와 분리된 카메라 localization 소프트웨어 계층."""

from .interfaces import FrameSource, PoseProvider
from .models import LocalizationResult, LocalizationStatus, Pose2D
from .pose_tracker import PoseTracker
from .slam_foundation import (
    LandmarkObservation,
    MappedLandmark,
    OdometryDelta,
    OdometryLandmarkBaseline,
    SlamBackend,
    SlamInput,
    SlamUpdate,
    update_route_from_slam,
)
from .synthetic_localizer import SyntheticPoseProvider

__all__ = [
    "FrameSource",
    "PoseProvider",
    "LocalizationResult",
    "LocalizationStatus",
    "Pose2D",
    "PoseTracker",
    "LandmarkObservation",
    "MappedLandmark",
    "OdometryDelta",
    "OdometryLandmarkBaseline",
    "SlamBackend",
    "SlamInput",
    "SlamUpdate",
    "update_route_from_slam",
    "SyntheticPoseProvider",
]
