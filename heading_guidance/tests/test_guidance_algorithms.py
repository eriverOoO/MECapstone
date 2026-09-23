"""세 guidance 전략과 상태 머신 테스트."""

import pytest

import config
from guidance_algorithms import ContinuousGuidance, DiscreteGuidance, PulseGuidance
from heading_controller import Direction, HeadingController, SystemState


def test_continuous_intensity() -> None:
    strategy = ContinuousGuidance(45.0)
    assert strategy.intensity(15.0, 0.0) == pytest.approx(1.0 / 3.0)
    assert strategy.intensity(90.0, 0.0) == 1.0


@pytest.mark.parametrize(
    ("error", "expected"),
    [(5.0, 0.0), (10.0, 0.3), (20.0, 0.6), (31.0, 1.0)],
)
def test_discrete_intensity(error: float, expected: float) -> None:
    assert DiscreteGuidance().intensity(error, 0.0) == expected


def test_pulse_frequency_logic() -> None:
    strategy = PulseGuidance()
    strategy.reset(0.0)
    assert strategy.intensity(10.0, 0.0) == config.PULSE_INTENSITY
    assert strategy.intensity(10.0, 0.2) == 0.0
    assert strategy.intensity(10.0, 1.0) == config.PULSE_INTENSITY
    assert strategy.intensity(40.0, 0.2) == config.PULSE_INTENSITY


def test_emergency_stop_latches_until_resume() -> None:
    controller = HeadingController(5.0, 8.0, 45.0)
    assert controller.update(90.0, 0.0).direction == Direction.RIGHT
    controller.emergency_stop()
    stopped = controller.update(90.0, 0.0)
    assert stopped.direction == Direction.OFF
    assert stopped.system_state == SystemState.EMERGENCY_STOP
    controller.resume()
    resumed = controller.update(90.0, 0.0)
    assert resumed.direction == Direction.RIGHT
    assert resumed.system_state == SystemState.GUIDING

