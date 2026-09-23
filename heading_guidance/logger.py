"""실험 데이터를 CSV로 기록하는 모듈."""

import csv
from datetime import datetime
from pathlib import Path
from time import monotonic

from heading_controller import GuidanceCommand
from imu_simulator import HeadingReading


class CSVGuidanceLogger:
    """한 실행의 heading 및 모터 데이터를 별도 CSV 파일에 기록한다."""

    FIELDNAMES = (
        "timestamp",
        "elapsed_seconds",
        "true_heading",
        "measured_heading",
        "filtered_heading",
        "target_heading",
        "current_heading",
        "heading_error",
        "direction",
        "intensity",
        "left_intensity",
        "right_intensity",
        "left_motor_intensity",
        "right_motor_intensity",
        "left_pwm",
        "right_pwm",
        "guidance_algorithm",
        "system_state",
        "current_x",
        "current_y",
        "target_waypoint_x",
        "target_waypoint_y",
    )

    def __init__(self, log_directory: str | Path) -> None:
        directory = Path(log_directory)
        directory.mkdir(parents=True, exist_ok=True)
        filename = datetime.now().strftime("heading_log_%Y%m%d_%H%M%S_%f.csv")
        self.path = directory / filename
        self._file = self.path.open("w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=self.FIELDNAMES)
        self._writer.writeheader()
        self._start_time = monotonic()

    def log(
        self,
        target_heading: float,
        reading: HeadingReading,
        command: GuidanceCommand,
        *,
        current_x: float | None = None,
        current_y: float | None = None,
        target_waypoint_x: float | None = None,
        target_waypoint_y: float | None = None,
    ) -> None:
        """한 제어 주기의 값을 기록하고 즉시 디스크에 반영한다."""

        self._writer.writerow(
            {
                "timestamp": datetime.now().isoformat(timespec="milliseconds"),
                "elapsed_seconds": f"{monotonic() - self._start_time:.6f}",
                "true_heading": f"{reading.true_heading:.3f}",
                "measured_heading": f"{reading.measured_heading:.3f}",
                "filtered_heading": f"{reading.filtered_heading:.3f}",
                "target_heading": f"{target_heading:.3f}",
                "current_heading": f"{reading.filtered_heading:.3f}",
                "heading_error": f"{command.error_deg:.3f}",
                "direction": command.direction.value,
                "intensity": f"{command.intensity:.6f}",
                "left_intensity": f"{command.left_intensity:.6f}",
                "right_intensity": f"{command.right_intensity:.6f}",
                "left_motor_intensity": f"{command.left_intensity:.6f}",
                "right_motor_intensity": f"{command.right_intensity:.6f}",
                "left_pwm": command.left_pwm,
                "right_pwm": command.right_pwm,
                "guidance_algorithm": command.guidance_algorithm,
                "system_state": command.system_state.value,
                "current_x": "" if current_x is None else f"{current_x:.3f}",
                "current_y": "" if current_y is None else f"{current_y:.3f}",
                "target_waypoint_x": (
                    "" if target_waypoint_x is None else f"{target_waypoint_x:.3f}"
                ),
                "target_waypoint_y": (
                    "" if target_waypoint_y is None else f"{target_waypoint_y:.3f}"
                ),
            }
        )
        self._file.flush()

    def close(self) -> None:
        if not self._file.closed:
            self._file.close()

    def __enter__(self) -> "CSVGuidanceLogger":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
