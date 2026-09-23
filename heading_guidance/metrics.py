"""자동 heading 실험의 정량 성능 지표."""

import math
from dataclasses import dataclass

import config


@dataclass(frozen=True)
class ExperimentSample:
    time_seconds: float
    heading_error: float
    motor_intensity: float


@dataclass(frozen=True)
class PerformanceMetrics:
    mae: float
    rmse: float
    maximum_error: float
    time_to_alignment: float
    settling_time: float
    overshoot: float
    motor_activations: int
    total_vibration_time: float

    def as_dict(self) -> dict[str, float | int]:
        return {
            "mae": self.mae,
            "rmse": self.rmse,
            "maximum_error": self.maximum_error,
            "time_to_alignment": self.time_to_alignment,
            "settling_time": self.settling_time,
            "overshoot": self.overshoot,
            "motor_activations": self.motor_activations,
            "total_vibration_time": self.total_vibration_time,
        }


def calculate_metrics(
    samples: list[ExperimentSample],
    deadband_deg: float = config.DEADBAND_DEG,
    settling_hold_seconds: float = config.SETTLING_HOLD_TIME_SEC,
) -> PerformanceMetrics:
    """한 trial의 오차/모터 시계열에서 성능 지표를 계산한다."""

    if not samples:
        raise ValueError("at least one experiment sample is required")
    errors = [sample.heading_error for sample in samples]
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = math.sqrt(sum(error * error for error in errors) / len(errors))
    maximum_error = max(abs(error) for error in errors)

    aligned_indices = [
        index for index, error in enumerate(errors) if abs(error) <= deadband_deg
    ]
    time_to_alignment = (
        samples[aligned_indices[0]].time_seconds if aligned_indices else math.nan
    )

    settling_time = math.nan
    inside_start: int | None = None
    for index, sample in enumerate(samples):
        if abs(sample.heading_error) <= deadband_deg:
            if inside_start is None:
                inside_start = index
            duration = sample.time_seconds - samples[inside_start].time_seconds
            if duration >= settling_hold_seconds:
                settling_time = samples[inside_start].time_seconds
                break
        else:
            inside_start = None

    initial_sign = 1 if errors[0] > 0.0 else -1 if errors[0] < 0.0 else 0
    opposite_errors = [
        abs(error)
        for error in errors
        if initial_sign != 0 and error * initial_sign < 0.0
    ]
    overshoot = max(opposite_errors, default=0.0)

    activations = 0
    previously_on = False
    vibration_time = 0.0
    for index, sample in enumerate(samples):
        is_on = sample.motor_intensity > 0.0
        if is_on and not previously_on:
            activations += 1
        previously_on = is_on
        if index + 1 < len(samples) and is_on:
            vibration_time += samples[index + 1].time_seconds - sample.time_seconds

    return PerformanceMetrics(
        mae=mae,
        rmse=rmse,
        maximum_error=maximum_error,
        time_to_alignment=time_to_alignment,
        settling_time=settling_time,
        overshoot=overshoot,
        motor_activations=activations,
        total_vibration_time=vibration_time,
    )
