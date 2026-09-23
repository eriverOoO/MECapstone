"""실제 IMU 대신 키보드로 heading을 변경하는 시뮬레이터."""

import sys
import termios
import tty
import random
from dataclasses import dataclass
from time import monotonic
from types import TracebackType
from typing import Protocol, TextIO

from heading_controller import normalize_heading
from heading_filters import HeadingFilter, create_heading_filter
import config


class HeadingSource(Protocol):
    """시뮬레이터와 실제 IMU가 따라야 할 최소 인터페이스."""

    def get_heading(self) -> float:
        """0 이상 360 미만의 현재 heading을 반환한다."""
        ...


@dataclass(frozen=True)
class HeadingReading:
    """한 시점의 실제값, 센서 측정값, 필터 출력."""

    true_heading: float
    measured_heading: float
    filtered_heading: float


class IMUSimulator:
    """noise, drift, outlier와 필터를 선택적으로 모사하는 IMU."""

    def __init__(
        self,
        initial_heading_deg: float = 0.0,
        *,
        noise_enabled: bool = config.IMU_NOISE_ENABLED,
        noise_std_deg: float = config.IMU_NOISE_STD_DEG,
        drift_enabled: bool = config.IMU_DRIFT_ENABLED,
        drift_rate_deg_per_sec: float = config.IMU_DRIFT_RATE_DEG_PER_SEC,
        outlier_enabled: bool = config.OUTLIER_ENABLED,
        outlier_probability: float = config.OUTLIER_PROBABILITY,
        outlier_magnitude_deg: float = config.OUTLIER_MAGNITUDE_DEG,
        filter_type: str = config.FILTER_TYPE,
        random_seed: int | None = None,
    ) -> None:
        self._true_heading = normalize_heading(initial_heading_deg)
        self.noise_enabled = noise_enabled
        self.noise_std_deg = noise_std_deg
        self.drift_enabled = drift_enabled
        self.drift_rate_deg_per_sec = drift_rate_deg_per_sec
        self.outlier_enabled = outlier_enabled
        self.outlier_probability = outlier_probability
        self.outlier_magnitude_deg = outlier_magnitude_deg
        self._random = random.Random(random_seed)
        self._filter: HeadingFilter = create_heading_filter(
            filter_type, config.MOVING_AVERAGE_WINDOW, config.LOW_PASS_ALPHA
        )
        self._start_time = monotonic()
        self._last_reading = HeadingReading(
            self._true_heading, self._true_heading, self._true_heading
        )

    def get_heading(self) -> float:
        """기존 API 호환: 새 sample의 filtered heading만 반환한다."""

        return self.sample().filtered_heading

    @property
    def true_heading(self) -> float:
        return self._true_heading

    @property
    def last_reading(self) -> HeadingReading:
        return self._last_reading

    def set_true_heading(self, heading_deg: float) -> None:
        self._true_heading = normalize_heading(heading_deg)

    def sample(self, elapsed_seconds: float | None = None) -> HeadingReading:
        """현재 실제 heading으로부터 오염 및 필터링된 측정값을 만든다."""

        elapsed = (
            monotonic() - self._start_time
            if elapsed_seconds is None
            else max(0.0, elapsed_seconds)
        )
        noise = self._random.gauss(0.0, self.noise_std_deg) if self.noise_enabled else 0.0
        drift = self.drift_rate_deg_per_sec * elapsed if self.drift_enabled else 0.0
        outlier = 0.0
        if self.outlier_enabled and self._random.random() < self.outlier_probability:
            outlier = self._random.choice((-1.0, 1.0)) * self.outlier_magnitude_deg

        measured = normalize_heading(self._true_heading + noise + drift + outlier)
        filtered = self._filter.update(measured)
        self._last_reading = HeadingReading(self._true_heading, measured, filtered)
        return self._last_reading

    def rotate_left(self, step_deg: float) -> float:
        self._true_heading = normalize_heading(self._true_heading - step_deg)
        return self._true_heading

    def rotate_right(self, step_deg: float) -> float:
        self._true_heading = normalize_heading(self._true_heading + step_deg)
        return self._true_heading


class ImmediateKeyboard:
    """Ubuntu 터미널에서 Enter 없이 한 글자를 읽는다.

    target 입력 때는 일시적으로 일반(cooked) 터미널 모드로 돌아간다.
    """

    def __init__(self, stream: TextIO = sys.stdin) -> None:
        self.stream = stream
        self._fd = stream.fileno()
        self._original_settings: list[object] | None = None

    def __enter__(self) -> "ImmediateKeyboard":
        if not self.stream.isatty():
            raise RuntimeError("interactive mode requires a TTY terminal")
        self._original_settings = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._restore_terminal()

    def read_key(self) -> str:
        """키 하나를 즉시 읽어 소문자로 반환한다."""

        return self.stream.read(1).lower()

    def read_line(self, prompt: str) -> str:
        """일반 터미널 모드에서 한 줄을 받은 뒤 즉시 입력 모드로 복귀한다."""

        self._restore_terminal()
        try:
            return input(prompt)
        finally:
            tty.setcbreak(self._fd)

    def _restore_terminal(self) -> None:
        if self._original_settings is not None:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._original_settings)
