"""프로젝트에서 사용하는 설정값.

모든 각도 단위는 degree이며, 하드웨어 튜닝 시 이 파일의 값만 바꾸면 된다.
"""

DEFAULT_TARGET_HEADING_DEG: float = 90.0
DEFAULT_CURRENT_HEADING_DEG: float = 0.0
HEADING_STEP_DEG: float = 5.0

DEADBAND_DEG: float = 5.0
HYSTERESIS_REENTRY_DEG: float = 8.0
MAX_INTENSITY_ERROR_DEG: float = 45.0

PWM_MAX: int = 255
LOG_DIRECTORY: str = "logs"
RESULTS_DIRECTORY: str = "results"

# IMU error model and angle filter
IMU_NOISE_ENABLED: bool = True
IMU_NOISE_STD_DEG: float = 1.0
IMU_DRIFT_ENABLED: bool = True
IMU_DRIFT_RATE_DEG_PER_SEC: float = 0.05
OUTLIER_ENABLED: bool = True
OUTLIER_PROBABILITY: float = 0.005
OUTLIER_MAGNITUDE_DEG: float = 10.0
FILTER_TYPE: str = "low_pass"  # none, moving_average, low_pass
MOVING_AVERAGE_WINDOW: int = 5
LOW_PASS_ALPHA: float = 0.25

# Guidance algorithm
DEFAULT_GUIDANCE_ALGORITHM: str = "continuous"
DISCRETE_LOW_BOUND_DEG: float = 15.0
DISCRETE_HIGH_BOUND_DEG: float = 30.0
DISCRETE_LOW_INTENSITY: float = 0.30
DISCRETE_MEDIUM_INTENSITY: float = 0.60
PULSE_INTENSITY: float = 0.75
PULSE_DURATION_SEC: float = 0.10
PULSE_SLOW_INTERVAL_SEC: float = 1.0
PULSE_MEDIUM_INTERVAL_SEC: float = 0.5
PULSE_FAST_INTERVAL_SEC: float = 0.2

# Route simulator
DEFAULT_WAYPOINTS: tuple[tuple[float, float], ...] = (
    (0.0, 0.0),
    (5.0, 0.0),
    (5.0, 5.0),
    (10.0, 5.0),
)
POSITION_STEP: float = 0.5
WAYPOINT_REACHED_DISTANCE: float = 0.5

# Automatic experiment and metrics
SIMULATION_DT_SEC: float = 0.02
SIMULATION_MAX_TIME_SEC: float = 20.0
USER_MAX_TURN_RATE_DEG_PER_SEC: float = 60.0
USER_REACTION_DELAY_SEC: float = 0.3
USER_TURN_NOISE_STD_DEG_PER_SEC: float = 1.0
SETTLING_HOLD_TIME_SEC: float = 2.0
MONTE_CARLO_SEED: int = 20260923

# Camera/localization software simulator (no physical camera is accessed)
CAMERA_POSITION_NOISE_STD: float = 0.08
CAMERA_YAW_NOISE_STD_DEG: float = 1.5
CAMERA_DROPOUT_PROBABILITY: float = 0.03
CAMERA_LOCALIZATION_LATENCY_SEC: float = 0.08
CAMERA_MAX_POSE_AGE_SEC: float = 0.30
CAMERA_SIMULATION_DT_SEC: float = 0.05
CAMERA_SIMULATION_SPEED_UNITS_PER_SEC: float = 1.0
CAMERA_SIMULATION_MAX_TIME_SEC: float = 30.0
CAMERA_SIMULATION_SEED: int = 20260924

# Offline ArUco detector defaults. Calibration values come from a JSON file.
ARUCO_DICTIONARY: str = "DICT_4X4_50"
ARUCO_MARKER_SIZE_M: float = 0.15
CAMERA_CALIBRATION_PATH: str = "camera_config/camera_calibration.example.json"
ARUCO_MARKER_MAP_PATH: str = "camera_config/marker_map.example.json"
CALIBRATION_BOARD_COLUMNS: int = 9  # chessboard inner corners
CALIBRATION_BOARD_ROWS: int = 6
CALIBRATION_SQUARE_SIZE_M: float = 0.024
