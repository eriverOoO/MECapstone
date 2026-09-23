"""일시적인 localization dropout과 오래된 pose를 안전하게 처리한다."""

from .models import LocalizationResult, LocalizationStatus, Pose2D


class PoseTracker:
    """마지막 유효 pose를 보관하되 허용 age를 넘으면 STALE로 표시한다."""

    def __init__(self, max_pose_age_seconds: float) -> None:
        if max_pose_age_seconds <= 0.0:
            raise ValueError("max_pose_age_seconds must be positive")
        self.max_pose_age_seconds = max_pose_age_seconds
        self._last_pose: Pose2D | None = None

    def update(
        self, result: LocalizationResult, now_seconds: float
    ) -> LocalizationResult:
        if result.status == LocalizationStatus.TRACKING and result.pose is not None:
            # 미래 timestamp는 clock mismatch이므로 허용하지 않는다.
            if result.pose.timestamp_seconds > now_seconds:
                return LocalizationResult(
                    LocalizationStatus.STALE,
                    None,
                    result.detected_marker_ids,
                    "pose timestamp is in the future",
                )
            self._last_pose = result.pose

        if self._last_pose is None:
            return LocalizationResult(
                LocalizationStatus.LOST,
                None,
                result.detected_marker_ids,
                result.message or "no valid pose received",
            )

        age = now_seconds - self._last_pose.timestamp_seconds
        if age > self.max_pose_age_seconds:
            return LocalizationResult(
                LocalizationStatus.STALE,
                None,
                result.detected_marker_ids,
                f"last pose is {age:.3f}s old",
            )
        return LocalizationResult(
            LocalizationStatus.TRACKING,
            self._last_pose,
            result.detected_marker_ids,
            "using last valid pose" if result.pose is None else result.message,
        )

    def reset(self) -> None:
        self._last_pose = None
