"""wrap-around 안전 heading filter 테스트."""

import pytest

from heading_filters import CircularLowPassFilter, CircularMovingAverage
from imu_simulator import IMUSimulator


def test_circular_moving_average_across_zero() -> None:
    angle_filter = CircularMovingAverage(2)
    angle_filter.update(359.0)
    result = angle_filter.update(1.0)
    assert result == pytest.approx(0.0, abs=1e-6) or result == pytest.approx(360.0, abs=1e-6)


def test_low_pass_takes_short_path_across_zero() -> None:
    angle_filter = CircularLowPassFilter(alpha=0.25)
    assert angle_filter.update(350.0) == 350.0
    assert angle_filter.update(10.0) == pytest.approx(355.0)


def test_noise_free_imu_keeps_three_headings_equal() -> None:
    imu = IMUSimulator(
        42.0,
        noise_enabled=False,
        drift_enabled=False,
        outlier_enabled=False,
        filter_type="none",
    )
    reading = imu.sample(10.0)
    assert reading.true_heading == 42.0
    assert reading.measured_heading == 42.0
    assert reading.filtered_heading == 42.0

