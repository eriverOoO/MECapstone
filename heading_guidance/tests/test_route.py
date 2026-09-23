"""waypoint heading과 route 전환 테스트."""

import pytest

from route import Position, RouteNavigator, calculate_waypoint_heading


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        (Position(1.0, 0.0), 0.0),
        (Position(0.0, 1.0), 90.0),
        (Position(-1.0, 0.0), 180.0),
        (Position(0.0, -1.0), 270.0),
    ],
)
def test_cardinal_waypoint_headings(target: Position, expected: float) -> None:
    assert calculate_waypoint_heading(Position(0.0, 0.0), target) == pytest.approx(expected)


def test_route_advances_when_threshold_is_reached() -> None:
    route = RouteNavigator([(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)], 0.5)
    assert route.target_waypoint == Position(1.0, 0.0)
    route.move(0.5, 0.0)
    assert route.target_waypoint == Position(2.0, 0.0)

