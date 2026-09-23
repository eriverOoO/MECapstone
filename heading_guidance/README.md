# Heading Guidance Testbed

시각장애인용 착용형 방향 안내 시스템의 heading 제어 알고리즘을 개발하고 정량
비교하기 위한 Python 테스트베드다. 현재 단계에서는 실제 IMU, ESP32, 카메라,
SLAM을 사용하지 않는다. 대신 카메라 localization interface, synthetic pose,
offline ArUco 검출과 calibration 도구까지 하드웨어 없이 준비되어 있다. 모든 각도
단위는 degree다.

## 시스템 구조

현재 구현은 다음처럼 각 계층을 분리한다.

```text
IMU / Synthetic Camera / Route Simulator
        ↓
Heading / Waypoint Logic
        ↓
Guidance Algorithm (continuous / discrete / pulse)
        ↓
Motor Interface (console mock / optional serial skeleton)
        ↓
CSV Logging, Metrics, Graphs
```

향후 실제 시스템의 연결 위치는 다음과 같다.

```text
Camera / ArUco / SLAM
        ↓ Position
Route Planner ─────────────→ Target Heading
                                  ↑
IMU ─→ calibrated Current Heading │
                                  ↓
                         Heading Controller
                                  ↓
                         Vibration Guidance
                                  ↓
                   Raspberry Pi → ESP32 → Motors
```

SLAM은 이 프로젝트의 범위가 아니다. localization/route planner는 target heading을
공급하는 상위 모듈이고, 이 프로젝트의 controller는 위치추정 방식과 독립적으로
target/current heading만 처리한다.

## 설치

Ubuntu 일반 터미널에서 실행한다. 즉시 키 입력은 TTY가 필요하다.

```bash
cd heading_guidance
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Ubuntu에서 venv 모듈이 없다면 먼저 `sudo apt install python3-venv`가 필요할 수 있다.
`pyserial`은 기본 의존성이 아니며 실제 serial mode를 사용할 때만
`pip install pyserial`로 설치한다.

저장 이미지 기반 ArUco 검출·camera calibration 도구는 선택 의존성을 사용한다.

```bash
pip install -r requirements-vision.txt
```

## 실행 모드

### 1. 수동 heading 테스트

```bash
python3 main.py
python3 main.py --guidance discrete --filter moving_average
python3 main.py --guidance pulse --target 180 --current 30 --step 10
```

조작 키는 `A/D` heading 좌/우 회전, `T` target 변경, `E` emergency stop,
`R` 안전 정지 해제, `Q` 종료다. 기본 종료 시 CSV와 세 개의 시계열 그래프 PNG를
만들고 그래프 창을 연다. 화면 없는 환경은 `--no-plot`을 사용한다.

### 2. 2D route simulator

```bash
python3 route_simulator.py
python3 route_simulator.py --guidance pulse --no-show
```

위치는 `W/S`(+Y/-Y), `A/D`(-X/+X), heading은 `J/L`(좌/우)로 조작한다.
`E/R/Q`는 수동 모드와 같다. waypoint 반경 0.5 이내에 들어오면 다음 waypoint로
넘어가며, 경로·실제 이동·현재 heading·다음 waypoint를 route PNG로 저장한다.

### 3. 자동 알고리즘 비교 / Monte Carlo

```bash
python3 experiment.py
python3 experiment.py --runs 100
python3 experiment.py --runs 100 --initial 350 --target 10 --seed 42
```

가상 사용자는 reaction delay 이후 진동 방향으로 회전하며, 최대 각속도에 진동
세기를 곱한 값으로 움직인다. 같은 run에서는 세 알고리즘에 동일한 random seed를
사용한다. 이 모델은 실제 사용자 실험의 대체물이 아니라 초기 설계 후보를 동일
조건에서 비교하기 위한 도구다.

### 4. Hardware-free camera/navigation simulator

```bash
python3 camera_navigation_simulator.py
python3 camera_navigation_simulator.py --seed 123
```

실제 카메라 대신 위치 noise, yaw noise, latency, 확률적 dropout이 있는 synthetic
camera pose를 만든다. `PoseTracker`가 짧은 dropout에는 마지막 pose를 유지하고,
오래된 pose는 `STALE`로 거부한다. 유효한 위치는 `RouteNavigator`에 전달되어 다음
waypoint와 target heading을 계산한다. CSV와 true/estimated route 그래프가 생성된다.

### 5. Offline camera 도구

물리 카메라를 프로그램에서 열지 않고 파일만 처리한다.

```bash
# 인쇄용 marker 생성
python3 generate_aruco_markers.py 0 1 2

# 저장 이미지에서 ID/corner만 검출
python3 aruco_offline.py sample.png --without-pose

# 촬영해 둔 chessboard 이미지로 intrinsic calibration
python3 calibrate_camera.py "calibration_images/*.jpg"

# 실제 calibration JSON으로 marker relative pose까지 계산
python3 aruco_offline.py sample.png \
  --calibration camera_config/camera_calibration.json
```

`camera_calibration.example.json`의 값은 형식 예시일 뿐 실제 측정값이 아니다.
`calibrated: false`이므로 pose 계산에 사용하려 하면 프로그램이 거부한다.

### 6. 테스트와 기존 로그 plot

```bash
pytest -q
python3 plot_logs.py logs/heading_log_YYYYMMDD_HHMMSS_ffffff.csv
python3 plot_logs.py logs/heading_log_YYYYMMDD_HHMMSS_ffffff.csv --no-show
```

## 카메라 소프트웨어 선작업

- `FrameSource`: 향후 USB/CSI camera 또는 저장 video reader의 공통 경계
- `PoseProvider`: ArUco/SLAM/synthetic localization의 공통 출력 경계
- `Pose2D`: x, y, yaw, timestamp, source, confidence 표준 데이터
- `LocalizationStatus`: `TRACKING`, `LOST`, `STALE`
- `SyntheticPoseProvider`: 위치·yaw noise, latency, dropout simulation
- `PoseTracker`: 일시 dropout hold 및 오래된 pose 차단
- `CameraCalibration`, `MarkerMap`: 검증되는 JSON 설정 loader
- `ArucoDetector`: ID/corner와 marker-relative pose를 계산하는 offline detector

프로젝트의 world frame은 `+X` 오른쪽/동쪽, `+Y` 앞쪽/북쪽, yaw는 +X에서
반시계 방향으로 증가하는 것으로 정의한다. OpenCV `solvePnP`가 반환하는 camera
coordinate pose를 world `Pose2D`로 바꾸려면 실제 카메라 장착 방향(extrinsic)과
marker map을 적용해야 한다. 이 변환은 장착 위치가 결정된 뒤 구현할 adapter 영역이며,
현재 detector 결과를 임의로 world pose라고 가정하지 않는다.

## 센서 모델과 필터

`IMUSimulator`는 다음 값을 독립적으로 유지한다.

- `true_heading`: 가상 사용자의 실제 방향
- `measured_heading`: Gaussian noise + 시간 비례 yaw drift + 확률적 outlier
- `filtered_heading`: controller에 입력되는 filter 결과

`config.py`에서 각 오차 모델을 개별 활성화하고 크기를 조절한다. filter는
`none`, `moving_average`, `low_pass` 중 하나다. moving average는 sin/cos circular
mean을 사용하며 low-pass는 두 각도의 최단 차이를 필터링하므로 359°/1° 경계에서
잘못된 180° 평균이 생기지 않는다.

## 제어와 guidance 전략

heading error는 다음 식으로 `[-180, 180)` 범위에 wrap한다. 양수는 RIGHT,
음수는 LEFT이며 정확히 180°인 경우 일관되게 -180°(LEFT)를 선택한다.

```python
error = (target_heading - current_heading + 180) % 360 - 180
```

`|error| <= 5°`에서 진동을 끄고, 꺼진 후 `|error| >= 8°`일 때만 다시 켜서
chatter를 막는다.

- `continuous`: `min(|error| / 45, 1)`의 연속 세기
- `discrete`: 5~15°는 30%, 15~30°는 60%, 30° 초과는 100%
- `pulse`: 세기 75%, 오차 구간별 pulse 주기 1.0/0.5/0.2초

상태 머신은 `IDLE`, `GUIDING`, `ALIGNED`, `EMERGENCY_STOP`을 갖는다. `E`를 누르면
양쪽 PWM을 즉시 0으로 만들고 latch한다. `R` 전에는 heading이 변해도 출력되지 않는다.

## 성능 지표 정의

- **MAE**: 전체 sample의 `mean(|heading_error|)`
- **RMSE**: `sqrt(mean(heading_error²))`
- **Maximum Heading Error**: 전체 구간 최대 절대 오차
- **Time to Alignment**: 시작부터 처음으로 ±5° 안에 든 시각
- **Settling Time**: ±5° 안에 들어와 2초 연속 유지되기 시작한 시각
- **Overshoot**: 최초 오차와 반대 부호로 넘어간 뒤의 최대 절대 오차
- **Number of Motor Activations**: motor OFF→ON 전환 횟수
- **Total Vibration Time**: motor intensity가 0보다 큰 sample 구간의 누적 시간

최대 실험 시간 안에 alignment/settling하지 못하면 해당 값은 `NaN`이며 summary의
`valid_runs`가 성공한 run 수를 보여준다. Monte Carlo summary에는 각 지표의 mean,
population standard deviation, min, max가 기록된다.

## 출력 파일

- `logs/heading_log_*.csv`: true/measured/filtered/target heading, error, algorithm,
  state, 좌우 motor intensity/PWM, 현재 위치, target waypoint
- `logs/heading_log_*.png`: target 및 세 heading, error, 좌우 motor intensity
- `logs/*_route.png`: waypoint와 2D 이동 경로
- `results/algorithm_trials.csv`: 모든 알고리즘/run의 개별 metric
- `results/algorithm_comparison.csv`: 알고리즘별 mean/std/min/max
- `results/algorithm_comparison.png`: alignment time, MAE, vibration time 비교
- `results/camera_navigation_simulation.csv`: true/estimated position, localization
  status, target waypoint 및 target heading
- `results/camera_navigation_simulation.png`: true path, camera 추정 경로, 위치 오차
- `camera_config/generated_markers/*.png`: 생성된 인쇄용 ArUco marker

## 주요 파일

- `config.py`: 센서, filter, 제어, route, 실험 parameter
- `heading_controller.py`: angle wrap, hysteresis, 상태 머신, 전략 호출
- `heading_filters.py`: circular moving average와 low-pass
- `imu_simulator.py`: true/measured/filtered heading 및 키 입력
- `guidance_algorithms/`: continuous, discrete, pulse 전략
- `motor_interface/`: interface, console mock, lazy-import serial skeleton
- `route.py`, `route_simulator.py`: waypoint 계산과 2D 수동 simulator
- `metrics.py`, `experiment.py`: 자동 사용자 모델, 지표, Monte Carlo 비교
- `vision/`: camera/localization model, interface, simulator, tracker, ArUco detector
- `camera_navigation_simulator.py`: camera pose에서 target heading까지의 통합 simulation
- `calibrate_camera.py`, `generate_aruco_markers.py`, `aruco_offline.py`: offline 도구
- `camera_config/`: calibration 및 marker map JSON 형식 예시
- `logger.py`, `plot_logs.py`: 확장 CSV 및 시계열 graph
- `tests/`: angle, hysteresis, filter, guidance, route, safety 테스트

## 실제 하드웨어 연결

실제 IMU는 `HeadingSource`에 맞는 `imu_reader.py`를 추가하고 `main.py`에서
`IMUSimulator`만 교체한다. 축 방향 확인, hard/soft iron 보정, bias 추정, sampling
주기 관리, heading의 0~360° 정규화가 필요하다. 실제 sensor fusion을 쓴다면
`filtered_heading` 자리에 그 결과를 공급한다.

ESP32 연결은 `SerialMotorController`를 선택하고 port/baudrate를 설정한다. 현재
골격은 `LEFT_PWM=120,RIGHT_PWM=0` 형식의 ASCII line을 보낸다. ESP32 firmware에서
범위 검사, motor driver PWM, packet validation을 구현해야 한다. 안전을 위해 Pi와의
통신이 일정 시간 끊기면 ESP32가 양쪽 모터를 끄는 hardware-side watchdog을 반드시
추가해야 한다(TODO).

ArUco/SLAM은 추정 위치를 `RouteNavigator.position` 또는 향후 route planner에
공급하는 위치에 연결한다. route planner가 다음 waypoint와 target heading을 만들고,
그 아래 `HeadingController`와 motor 계층은 변경하지 않는 구조가 목표다.

실제 카메라를 연결할 때는 `FrameSource.read()`를 구현하고 frame을
`ArucoDetector.detect()`에 전달한다. 그 다음 실제 camera-to-body extrinsic과
`marker_map.example.json`의 world marker pose를 이용해 `Pose2D`를 계산하는 adapter가
필요하다. 해상도별 intrinsic calibration, 영상 timestamp, frame drop 처리도 실제
장치 연결 단계에서 검증해야 한다. 이 작업 전까지 어떤 코드도 `/dev/video*` 또는
CSI camera를 열지 않는다.
