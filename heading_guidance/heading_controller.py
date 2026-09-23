"""하드웨어와 독립적인 heading 및 진동 명령 계산 모듈."""

from dataclasses import dataclass
from enum import Enum
from time import monotonic

from guidance_algorithms import GuidanceAlgorithm
from guidance_algorithms.continuous import ContinuousGuidance


class Direction(str, Enum):
    """사용자에게 안내할 회전 방향."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"
    OFF = "OFF"


class SystemState(str, Enum):
    """명시적인 guidance 상태 머신 상태."""

    IDLE = "IDLE"
    GUIDING = "GUIDING"
    ALIGNED = "ALIGNED"
    EMERGENCY_STOP = "EMERGENCY_STOP"


@dataclass(frozen=True)
class GuidanceCommand:
    """heading controller가 모터 출력 계층에 전달하는 명령."""

    error_deg: float
    direction: Direction
    intensity: float
    left_intensity: float
    right_intensity: float
    left_pwm: int
    right_pwm: int
    system_state: SystemState = SystemState.IDLE
    guidance_algorithm: str = "continuous"


def normalize_heading(heading_deg: float) -> float:
    """임의의 각도를 0 이상 360 미만 범위로 정규화한다."""

    return heading_deg % 360.0


def calculate_heading_error(target_deg: float, current_deg: float) -> float:
    """목표까지의 최소 회전 오차를 [-180, 180) 범위로 계산한다.

    양수는 우회전, 음수는 좌회전을 의미한다. 정확히 180도 차이인
    경우에는 공식의 일관성을 위해 -180도(좌회전)를 반환한다.
    """

    return (target_deg - current_deg + 180.0) % 360.0 - 180.0


class HeadingController:
    """deadband와 hysteresis를 적용하여 진동 안내 명령을 생성한다."""

    def __init__(
        self,
        deadband_deg: float,
        reentry_deg: float,
        max_intensity_error_deg: float,
        pwm_max: int = 255,
        guidance_algorithm: GuidanceAlgorithm | None = None,
    ) -> None:
        if not 0.0 <= deadband_deg < reentry_deg:
            raise ValueError("deadband_deg must be >= 0 and smaller than reentry_deg")
        if max_intensity_error_deg <= 0.0:
            raise ValueError("max_intensity_error_deg must be positive")
        if pwm_max <= 0:
            raise ValueError("pwm_max must be positive")

        self.deadband_deg = deadband_deg
        self.reentry_deg = reentry_deg
        self.max_intensity_error_deg = max_intensity_error_deg
        self.pwm_max = pwm_max
        self.guidance_algorithm = guidance_algorithm or ContinuousGuidance(
            max_intensity_error_deg
        )
        self._vibration_active = False
        self._state = SystemState.IDLE
        self._emergency_stopped = False

    @property
    def vibration_active(self) -> bool:
        """현재 hysteresis 상태를 반환한다."""

        return self._vibration_active

    @property
    def state(self) -> SystemState:
        return self._state

    def reset(self) -> None:
        """진동 상태를 OFF로 초기화한다."""

        self._vibration_active = False
        self._state = SystemState.IDLE
        self._emergency_stopped = False
        self.guidance_algorithm.reset()

    def emergency_stop(self) -> None:
        """안전 정지를 latch하여 이후 모든 모터 명령을 차단한다."""

        self._emergency_stopped = True
        self._vibration_active = False
        self._state = SystemState.EMERGENCY_STOP

    def resume(self) -> None:
        """사용자의 명시적인 재시작 명령으로 emergency latch를 해제한다."""

        self._emergency_stopped = False
        self._vibration_active = False
        self._state = SystemState.IDLE
        self.guidance_algorithm.reset()

    def update(
        self,
        target_deg: float,
        current_deg: float,
        now_seconds: float | None = None,
    ) -> GuidanceCommand:
        """현재 각도로부터 좌/우 모터 명령을 한 번 계산한다."""

        error_deg = calculate_heading_error(target_deg, current_deg)
        error_magnitude = abs(error_deg)
        current_time = monotonic() if now_seconds is None else now_seconds

        if self._emergency_stopped:
            return self._off_command(error_deg, SystemState.EMERGENCY_STOP)

        # ON 상태는 deadband 안에 들어오면 꺼지고, OFF 상태는 더 큰
        # reentry 경계를 넘어야 다시 켜진다. 두 경계 사이는 이전 상태 유지다.
        if error_magnitude <= self.deadband_deg:
            self._vibration_active = False
            self._state = SystemState.ALIGNED
        elif not self._vibration_active and error_magnitude >= self.reentry_deg:
            self._vibration_active = True
            self._state = SystemState.GUIDING

        # Hysteresis 사이 구간에서는 이전 논리 상태를 유지한다.
        if self._vibration_active:
            self._state = SystemState.GUIDING
        elif self._state == SystemState.IDLE:
            self._state = SystemState.ALIGNED

        if not self._vibration_active:
            return self._off_command(error_deg, self._state)

        intensity = self.guidance_algorithm.intensity(error_magnitude, current_time)
        pwm = round(intensity * self.pwm_max)

        # pulse OFF 구간에도 상태는 GUIDING이지만 실제 모터 출력은 0이다.
        if intensity <= 0.0:
            return self._off_command(error_deg, SystemState.GUIDING)

        if error_deg > 0.0:
            return GuidanceCommand(
                error_deg,
                Direction.RIGHT,
                intensity,
                0.0,
                intensity,
                0,
                pwm,
                self._state,
                self.guidance_algorithm.name,
            )
        return GuidanceCommand(
            error_deg,
            Direction.LEFT,
            intensity,
            intensity,
            0.0,
            pwm,
            0,
            self._state,
            self.guidance_algorithm.name,
        )

    def _off_command(
        self, error_deg: float, state: SystemState
    ) -> GuidanceCommand:
        return GuidanceCommand(
            error_deg,
            Direction.OFF,
            0.0,
            0.0,
            0.0,
            0,
            0,
            state,
            self.guidance_algorithm.name,
        )
