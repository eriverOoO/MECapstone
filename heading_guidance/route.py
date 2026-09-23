"""SLAM 없이 상위 navigation 출력을 모사하는 2D waypoint 로직."""

import math
from dataclasses import dataclass
from typing import Sequence

from heading_controller import normalize_heading


@dataclass(frozen=True)
class Position:
    x: float
    y: float


def distance(a: Position, b: Position) -> float:
    return math.hypot(b.x - a.x, b.y - a.y)


def calculate_waypoint_heading(current: Position, target: Position) -> float:
    """+X=0도, +Y=90도 좌표계에서 target heading을 계산한다."""

    if current == target:
        raise ValueError("current position and target waypoint are identical")
    return normalize_heading(
        math.degrees(math.atan2(target.y - current.y, target.x - current.x))
    )


class RouteNavigator:
    """현재 위치에서 다음 waypoint 선택과 도달 판정을 담당한다."""

    def __init__(
        self,
        waypoints: Sequence[tuple[float, float]],
        reached_distance: float,
        initial_position: Position | None = None,
    ) -> None:
        if not waypoints:
            raise ValueError("at least one waypoint is required")
        self.waypoints = [Position(*point) for point in waypoints]
        self.reached_distance = reached_distance
        self.position = initial_position or Position(0.0, 0.0)
        self.target_index = 0
        self._advance_reached_waypoints()

    @property
    def target_waypoint(self) -> Position | None:
        if self.target_index >= len(self.waypoints):
            return None
        return self.waypoints[self.target_index]

    @property
    def completed(self) -> bool:
        return self.target_waypoint is None

    def move(self, dx: float, dy: float) -> None:
        self.position = Position(self.position.x + dx, self.position.y + dy)
        self._advance_reached_waypoints()

    def update_position(self, position: Position) -> None:
        """카메라/SLAM 등 외부 localization 결과로 현재 위치를 갱신한다."""

        self.position = position
        self._advance_reached_waypoints()

    def target_heading(self) -> float | None:
        target = self.target_waypoint
        if target is None:
            return None
        return calculate_waypoint_heading(self.position, target)

    def _advance_reached_waypoints(self) -> None:
        while self.target_waypoint is not None and distance(
            self.position, self.target_waypoint
        ) <= self.reached_distance:
            self.target_index += 1
