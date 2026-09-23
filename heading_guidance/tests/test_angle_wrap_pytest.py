"""요구된 네 가지 angle wrapping 경우를 명시적으로 검증한다."""

import pytest

from heading_controller import calculate_heading_error


@pytest.mark.parametrize(
    ("current", "target", "expected"),
    [(350.0, 10.0, 20.0), (10.0, 350.0, -20.0), (0.0, 180.0, -180.0), (180.0, 0.0, -180.0)],
)
def test_angle_wrap(current: float, target: float, expected: float) -> None:
    assert calculate_heading_error(target, current) == expected

