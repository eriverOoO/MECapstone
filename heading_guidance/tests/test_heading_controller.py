"""heading 계산, deadband, hysteresis 단위 테스트."""

import unittest

from heading_controller import Direction, HeadingController, calculate_heading_error


class HeadingErrorTests(unittest.TestCase):
    def test_basic_and_wrapped_errors(self) -> None:
        cases = (
            (90.0, 0.0, 90.0),
            (0.0, 350.0, 10.0),
            (350.0, 0.0, -10.0),
            (10.0, 350.0, 20.0),
            (350.0, 10.0, -20.0),
        )
        for target, current, expected in cases:
            with self.subTest(target=target, current=current):
                self.assertEqual(calculate_heading_error(target, current), expected)

    def test_exactly_180_uses_negative_180_convention(self) -> None:
        self.assertEqual(calculate_heading_error(180.0, 0.0), -180.0)


class HeadingControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = HeadingController(5.0, 8.0, 45.0, 255)

    def test_direction_intensity_and_pwm(self) -> None:
        right = self.controller.update(90.0, 60.0)
        self.assertEqual(right.direction, Direction.RIGHT)
        self.assertAlmostEqual(right.intensity, 30.0 / 45.0)
        self.assertEqual(right.left_pwm, 0)
        self.assertEqual(right.right_pwm, 170)

        left = self.controller.update(0.0, 45.0)
        self.assertEqual(left.direction, Direction.LEFT)
        self.assertEqual(left.intensity, 1.0)
        self.assertEqual(left.left_pwm, 255)
        self.assertEqual(left.right_pwm, 0)

    def test_deadband_turns_vibration_off(self) -> None:
        self.assertEqual(self.controller.update(20.0, 0.0).direction, Direction.RIGHT)
        command = self.controller.update(5.0, 0.0)
        self.assertEqual(command.direction, Direction.OFF)
        self.assertEqual(command.intensity, 0.0)

    def test_hysteresis_requires_eight_degrees_to_restart(self) -> None:
        self.controller.update(4.0, 0.0)  # OFF
        self.assertEqual(self.controller.update(7.9, 0.0).direction, Direction.OFF)
        self.assertEqual(self.controller.update(8.0, 0.0).direction, Direction.RIGHT)

    def test_active_state_stays_on_between_thresholds(self) -> None:
        self.controller.update(10.0, 0.0)  # ON
        self.assertEqual(self.controller.update(6.0, 0.0).direction, Direction.RIGHT)
        self.assertEqual(self.controller.update(5.0, 0.0).direction, Direction.OFF)


if __name__ == "__main__":
    unittest.main()

