# 카드 IC칩 비전 · 동작 시뮬레이터

녹화 영상과 JPG/JPEG/PNG 등의 이미지에서 카드와 IC칩 후보를 찾고, 검출 위치·카드 상태·다음 동작을 표시하는 CPU용 Python/OpenCV 프로토타입입니다. 폴더 단위 이미지 Batch Test도 지원합니다. 영상 입력, 비전 처리, 동작 판단을 분리했습니다. **모터 명령은 전부 시뮬레이션이며 하드웨어 출력 코드는 없습니다.**

실제 카드 영상은 아직 제공되지 않았습니다. 합성 데이터로 코드 실행과 상태 전이를 검증했으며, 실제 카드·반사·가림·카메라 변경에 대한 정확도는 측정하지 않았습니다. `CHIP_NOT_VISIBLE`은 뒷면의 확정 판정이 아닙니다. 규칙 기반 검출기의 한계로 칩을 놓칠 수 있습니다.

## 지금 이 PC에서 실행

현재 작업 폴더의 `.deps`에 실행에 필요한 패키지를 설치해 두었습니다. 시스템 기본 `python`은 OpenCV가 없는 MSYS Python이므로 이 PC에서는 아래 래퍼가 준비된 Python을 선택합니다. PowerShell에서:

```powershell
cd 'C:\Users\shang\OneDrive\바탕 화면\MECapstone\card_vision'
.\python.ps1 tools/generate_demo.py
.\python.ps1 main.py --source data/test/demo_correct.avi
```

촬영한 `.MOV` 또는 `.MP4`를 **`card_vision/data/videos/`**에 넣은 뒤:

```powershell
.\python.ps1 main.py --source 'data/videos/my_card.MOV'
# 또는 파일 선택창
.\python.ps1 main.py
# 화면 없이 JSONL 로그 생성
.\python.ps1 main.py --source 'data/videos/my_card.MOV' --headless
```

PowerShell이 스크립트 실행을 막으면 실행 정책을 전역으로 변경할 필요 없이 해당 프로세스만 다음처럼 실행할 수 있습니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\python.ps1 main.py --source data/test/demo_correct.avi
```

## 다른 PC / Linux 설치

CPython 3.10 이상(이 구현은 CPython 3.12에서 검증), OpenCV, NumPy, PyYAML을 사용합니다. GPU와 신경망은 필요하지 않습니다.

```powershell
cd card_vision
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py --source data/videos/my_card.MOV
```

Windows에서 Python Launcher가 없으면 설치한 CPython의 `python -m venv .venv`를 사용합니다. Linux:

```bash
cd card_vision
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py --source data/videos/my_card.mp4
.venv/bin/python main.py --source data/videos/my_card.mp4 --headless
```

GUI는 데스크톱 세션이 필요합니다. Linux의 파일 선택창은 `python3-tk`가 필요하며 `--source`를 쓰면 생략할 수 있습니다. GUI가 전혀 없는 Pi에서는 `opencv-python` 대신 `opencv-python-headless` 하나만 설치할 수 있습니다. 두 OpenCV 패키지를 동시에 설치하지 마세요. 데이터·출력·가상환경은 Git에서 제외했습니다.

## 화면과 키

원본 처리 영상의 카드 외곽은 파란색, 칩 후보는 노란색, 중심점은 빨간색, 투입구 방향은 보라색으로 표시합니다. 점수는 후보 품질을 비교하는 **휴리스틱 점수**이며 확률이 아닙니다. 처리 FPS는 계산 시간의 역수이고, 실제 재생 FPS/하드웨어 처리량과 다릅니다.

| 키 | 기능 |
|---|---|
| Space | 재생 / 일시정지 |
| `n` / → | 일시정지하고 다음 프레임 한 장 처리 |
| `b` / ← | 이전 프레임 한 장 (파일만 가능, 시뮬레이션 사이클 초기화) |
| `+` / `-` | 재생 속도 0.125~8배 |
| `[` / `]` | 처리 간격 조절 (사이클 초기화) |
| `d` | 그레이·엣지·윤곽·정규화 카드·색상 마스크·칩 후보 창 |
| `a` | 대기 중인 모의 동작의 성공 완료 신호 |
| `x` | 대기 중인 모의 동작의 실패 신호 |
| `r` | 새 카드 사이클 시작 |
| `o` | 다른 파일 열기 |
| `s` | 현재 원본 처리 프레임 PNG와 판정 JSON 저장 |
| `q` / Esc | 종료 |

일시정지 화면을 다시 그리는 것만으로 안정화 횟수가 쌓이지 않습니다. 사진은 아래의 단일 이미지 검토 모드로 즉시 방향을 판단하며, 동작 명령은 생성하지 않습니다. 뒤로 이동·파일 변경·간격 변경 시 이전 판단을 초기화합니다. 파일 끝에서는 화면이 멈추며 이전 프레임 이동이 가능합니다. 라이브 카메라는 일시정지 시 읽기를 중단하므로 재개 시 드라이버의 버퍼 지연이 있을 수 있습니다.

## 단일 이미지 입력

지원 형식은 **JPG, JPEG, PNG, BMP, WebP**이며 확장자 대소문자를 구분하지 않습니다. 이미지를 `data/images/`에 넣고 실행합니다.

```powershell
.\python.ps1 main.py --source 'data/images/card.JPG'
# 화면 없이 결과 기록 + 박스가 표시된 이미지 저장
.\python.ps1 main.py --source 'data/images/card.JPG' --headless --save-annotated
# 제공된 합성 이미지로 확인
.\python.ps1 main.py --source data/test/demo_correct.png
```

이미지 모드는 카드·칩 검출과 방향 판단을 한 번 수행하고 UI에 표시합니다. 영상의 첫 프레임 움직임 확인과 연속 프레임 안정화를 적용하지 않으며, 블러·밝기·복수 후보·90도 배치 등의 판단 조건은 그대로 사용합니다. 움직임과 시간 안정성은 사진으로 측정할 수 없어 `N/A`로 표시합니다. UI의 `Suggested action`은 검토용 제안이며, `--simulate-acks`가 있어도 이미지에서는 동작 명령을 생성하지 않습니다.

`d`는 중간 처리 창, `o`는 다른 이미지/영상 열기, `s`는 **박스와 정보 패널이 있는 이미지 + JSON** 저장입니다. 저장 위치는 `outputs/frames/<실행ID>/`이며 `--save-annotated`를 주면 자동 저장합니다. 나머지 영상 재생·동작 완료 키는 이미지 모드에서 사용하지 않습니다. 이미지 자체의 방향 판단은 JSONL 로그에도 남습니다.

## 폴더 단위 Batch Test

```powershell
# 폴더 바로 아래 이미지만 처리; CSV/JSON 기록, 이미지 저장 없음
.\python.ps1 main.py --batch data/images
# 하위 폴더 포함 + 검출 박스/상태가 표시된 PNG 저장
.\python.ps1 main.py --batch data/images --recursive --save-annotated
# 출력 경로와 선택적 정답 라벨 지정
.\python.ps1 main.py --batch data/images --recursive --save-annotated --labels data/image_labels.json --output outputs/comparison
```

Batch는 GUI 없이 각 이미지를 독립적으로 한 번 처리합니다. 다른 이미지의 움직임·안정화 상태를 공유하지 않습니다. 읽을 수 없는 파일도 오류 행으로 기록한 뒤 다음 이미지를 처리합니다. 폴더가 없거나 지원 이미지가 하나도 없으면 오류를 출력합니다. 비이미지 파일은 건너뜁니다. 실행마다 새 디렉터리를 생성하므로 이전 결과를 덮어쓰지 않습니다.

```text
outputs/batch_<실행ID>/
  results.csv            Excel에서 열 수 있는 UTF-8 BOM CSV
  results.json           이미지별 결과 + 설정 + 좌표계 + 전체/그룹별 요약
  summary.json           전체/그룹별 요약만
  annotated/             --save-annotated 지정 시 생성
    internet/card.jpg.png
    phone/card.png.png
```

파일명, 카드 검출 여부, 칩 검출 여부, 카드 외곽/박스, 칩 박스/다각형/중심/상대 좌표, 방향 상태, 판단 사유, 품질 점수, 처리 시간, 오류, 저장된 이미지 경로를 기록합니다. 같은 이름의 JPG와 PNG 및 다른 하위 폴더의 같은 이름도 각각 저장합니다. Batch 출력 폴더가 입력 아래에 있으면 재귀 검색에서 그 폴더를 제외합니다. 입력과 출력 폴더를 똑같이 지정할 수는 없습니다.

`card_box`와 `chip_image_box`는 `[x,y,width,height]` 형식의 **처리 영상 픽셀**입니다. `card_quad`/`chip_polygon`/`chip_center`도 리사이즈·설정 회전 이후, 정보 패널을 붙이기 전 좌표입니다. `chip_box`는 원근 보정된 카드 좌표이고 `chip_relative`는 그 안의 0~1 좌표입니다. 약한 후보는 칩 검출이 false여도 후보 위치가 남을 수 있으므로 `chip_detected`와 `reason`을 함께 확인하세요. 읽기 오류에서는 검출 여부를 false로 단정하지 않고 null로 기록합니다.

`processing_ms`는 리사이즈·검출·판단 시간으로 파일 읽기/이미지 저장을 제외합니다. `total_ms`는 읽기부터 선택적 결과 이미지 저장까지의 이미지별 경과 시간입니다.

### 인터넷 이미지와 직접 촬영 이미지 비교

아래처럼 나눈 뒤 `--recursive`로 처리하면 `summary.json`의 `by_group.internet`, `by_group.phone`에서 각각 검출 비율·UNKNOWN 비율·평균 시간을 확인할 수 있습니다. 그룹은 입력 폴더의 첫 번째 하위 폴더명입니다. 입력 폴더에 바로 있는 파일은 `(root)` 그룹입니다.

```text
data/images/
  internet/     인터넷에서 수집한 이미지
  phone/        직접 촬영한 이미지
```

**검출 비율은 정확도가 아닙니다.** 실제 카드/칩 유무와 방향의 정답을 지정해야 오검출·미검출·오분류를 측정할 수 있습니다. Batch용 정답 JSON은 다음과 같습니다. `file`은 Batch 입력 폴더에 대한 상대 경로이며 영상 구간 라벨과 별도입니다. 템플릿은 `data/image_labels.example.json`에 있습니다.

```json
[
  {"file":"internet/card01.jpg", "card_present":true, "chip_visible":true, "status":"CORRECT"},
  {"file":"phone/card02.png", "card_present":true, "chip_visible":false, "status":"CHIP_NOT_VISIBLE"}
]
```

라벨이 있는 이미지에 대해 전체/그룹별 방향 분류 정확도, 카드/칩 검출 재현율, 오검출 건수, 혼동 결과를 추가합니다. 라벨이 없으면 정확도·재현율은 null입니다. 디코딩/처리 오류는 정확도 분모에서 제외하고 `labelled_input_errors`로 따로 집계합니다. 라벨과 매칭되지 않은 경로는 `unmatched_labels`로 표시합니다. 다른 구도나 임의 방향의 인터넷 이미지는 현재 투입구 설정을 기준으로 판정하므로 같은 기준으로 라벨링해야 합니다. 이미지 수집·다운로드는 이 기능에 포함하지 않습니다.

## 세 가지 업무 상태와 예외

| 안정화 상태 | 모의 동작 | 완료 신호 이후 |
|---|---|---|
| `CHIP_NOT_VISIBLE` | `FLIP` | 새 프레임으로 재확인 |
| `REVERSED` | `ROTATE_180` | 새 프레임에서 `CORRECT` 확인 후 `INSERT` |
| `CORRECT` | `INSERT` | 완료 신호를 받아 `COMPLETED` |
| `UNKNOWN` | `RECHECK` (모터 명령 없음) | 관측 유지, 제한 초과 시 `ERROR` |

기본값은 연속 5개 **처리된** 프레임의 일치입니다. 카드 없음, 낮은 화질, 움직임, 약한 칩 후보, 비슷한 점수의 복수 후보, 중앙에 있는 칩, 예상하지 않은 90도 배치는 동작 근거로 사용하지 않습니다. 카드 뒷면처럼 보이는 영상도 카드 외곽과 화질 조건을 만족한 뒤에만 한 번 뒤집기를 요청합니다. 정지한 손이나 정교한 금색 무늬까지 확실히 구별하는 알고리즘은 아닙니다.

`a`를 눌러도 녹화 영상이 실제로 뒤집히거나 회전하지는 않습니다. 이후 영상에 해당 동작 결과가 있어야 검증을 통과합니다. 반대 방향 영상이 계속 보이면 회전 재확인 오류로 멈춥니다. 기본 제한은 뒤집기 1회·회전 1회, 관측 120프레임 또는 20초, 동작 완료 대기 15초입니다. 타임아웃은 실제 경과 시간이며 UI 일시정지 중에도 유지됩니다. `r`로 다음 모의 사이클을 시작합니다.

Headless에서도 기본값은 완료 신호를 자동 생성하지 않습니다. 자동 모의 완료가 필요한 경우에만:

```powershell
.\python.ps1 main.py --source data/test/demo_correct.avi --headless --simulate-acks
```

완료 신호를 받기 전에는 다음 명령을 보내지 않습니다. 명령마다 증가하는 `command_id`로 잘못된/중복 완료 신호를 거부합니다. 뒤집기·회전 후 안정화 기록을 비우며, 대기 중에 들어온 프레임과 과거 프레임도 재사용하지 않습니다. 예:

```json
{"command_id": 1, "card_status": "REVERSED", "action": "ROTATE_180", "requires_recheck": true}
```

## 설정과 좌표계

`config.yaml`을 수정하거나 `--config 다른설정.yaml`로 지정합니다.

- `input.width`: 종횡비를 유지해 리사이즈하는 너비. 그 뒤 `rotation`(시계방향)과 `mirror`를 적용합니다.
- `input.stride`: 처리할 프레임 간격. 안정화 5프레임은 stride=3이면 원본 15프레임 정도가 필요합니다.
- `card.fixed_roi`: null이면 전체 화면에서 카드 검출, `[x,y,w,h]`면 그 주변의 고정 **검색창** 안에서 실제 카드 경계를 찾습니다. 카드 경계와 일치시킬 필요가 없습니다. 검색창 자체를 카드라고 간주하거나 검색창 전체를 카드 크기로 변환하지 않습니다.
- `card.roi_padding_fraction`: 설정 검색창의 각 변 바깥에 추가하는 여백 비율입니다. 기본 0.10은 가로/세로 각각의 10%를 양쪽에 추가합니다(총 크기는 약 1.2배). 실제 카드가 조금 이동·회전해도 포함되도록 잡고, 영상 밖으로 넘어간 여백은 잘라냅니다. UI의 녹색 `SEARCH ROI`와 로그의 `inspection_roi`는 추가 여백을 적용한 실제 검사영역입니다. 카드 면적 필터의 분모는 검색창이 아닌 전체 처리 영상 크기입니다.
- `chip.hsv_lower/upper`, 면적·점수·복수 후보 차이: 금색 분할, 은색 후보와 내부 접점 선 패턴의 기준입니다. 금속 성질 자체를 측정하지는 않습니다.
- `quality`: 카드 ROI의 블러·밝기·극단 밝기 비율과 프레임 차이 기준. 실제 영상으로 조정해야 합니다. 움직임은 전체 영상의 평균 절대 차이를 사용하므로 작은 부분 가림을 모두 검출하지 못합니다.
- `orientation.inlet`: **기구 좌표계**의 `right/left/up/down`. y는 아래쪽이 양수입니다. 초기값 right입니다.
- `orientation.image_to_stage`: **처리 영상 픽셀 → 기구 평면 좌표**의 3×3 호모그래피. 기본 항등행렬이면 화면 방향이 기구 방향입니다. 실제 장착 후 대응점으로 보정할 수 있습니다. `input.rotation/mirror`는 이 행렬에 앞서 적용되므로 중복 보정하지 마세요.

카드 원근 보정은 긴 변이 가로가 되도록 640×약404 크기로 만듭니다. 외곽만으로 카드의 0°/180°를 결정하지 않습니다. 칩의 정규화 좌표를 역변환해 처리 영상으로 복원하고, 카드와 칩을 기구 좌표계로 옮겨 투입구 방향으로의 상대 위치를 비교합니다. 칩 박스는 정규화 카드 좌표, `chip_relative`는 그 안의 0~1 상대 좌표, `chip_center` 및 화면 다각형은 처리 영상 픽셀입니다. 원본 파일 해상도의 좌표와는 다릅니다.

기본 자동 외곽 검출은 큰 원근 왜곡·겹친 카드·배경 사각형에 취약합니다. 중심 정렬된 실제 기구에서는 고정 ROI와 일정한 조명을 먼저 검토하세요.

### 실제 기구의 검사영역 설계

기구가 카드 중심을 정렬하며, 바닥은 검정색 필라멘트 출력물일 가능성이 있다는 조건을 반영합니다. 고정 검색창은 카드보다 넉넉하게 잡아 작은 중심 오차와 평면 회전을 허용합니다. 실제 카드 경계를 검출한 뒤 그 카드만 원근 보정하므로, 검색창의 여백이 칩의 상대 좌표로 섞이지 않습니다. 영상의 움직임 판정도 검색창이 설정되어 있으면 그 안의 변화만 사용합니다.

예를 들어 **960×540 합성 영상용**으로 다음과 같이 설정할 수 있습니다. 실제 카메라 좌표로 확정한 설정은 아닙니다.

```yaml
card:
  fixed_roi: [170, 75, 620, 390]
  roi_padding_fraction: 0.10
```

위 항목은 기존 YAML의 `card` 섹션에 반영하고 나머지 카드 설정을 유지합니다. 검색창과 추가 여백은 실제 카메라를 장착한 뒤 카드가 놓일 수 있는 범위로 조정합니다. 기본 `config.yaml`의 `fixed_roi`는 아직 null이며, 카메라가 없는 상태에서 실제 기구의 픽셀 좌표를 임의로 고정하지 않았습니다.

우선순위는 정렬된 카드의 칩·홀로그램·아이콘 구분입니다. 카드와 배경의 경계가 불분명한 인터넷 이미지에 맞추기 위한 외곽 검출 튜닝은 후순위로 둡니다. 검정 출력물의 실제 표면 반사·적층무늬·어두운 카드와의 대비는 실물 촬영으로 확인해야 합니다. 검색창이 비어 있거나 카드가 검사창 밖으로 잘려 불확실하면 UNKNOWN으로 유지합니다.

## 로그 · 정답 라벨 · 평가

`outputs/logs/*.jsonl`에 파일명, 원본 프레임 번호(0부터), 영상 시간(초), 카드·칩 검출, 상대/영상 좌표, 점수, 단일 프레임 상태, 안정화 상태, 동작, 사유, 처리 시간, 명령·완료·초기화 이벤트를 기록합니다. 파일 경로 전체와 카드번호 OCR은 기록하지 않습니다.

이미지는 기본 저장하지 않습니다. `s`, `--save-annotated`, `--save-failures` 또는 `output.save_failures: true`를 명시했을 때만 저장합니다. 이미지에는 카드 정보가 포함될 수 있습니다. 실패 자동 저장은 `UNKNOWN` 프레임을 설정된 간격으로 저장합니다.

정답 라벨은 영상별 연속 구간 JSON입니다. 시작·끝 프레임 모두 포함하며 겹치는 구간은 금지합니다. `file`은 로그의 파일명과 일치해야 합니다. 같은 이름의 다른 영상은 이름을 구분해 주세요.

```json
[
  {"file": "card01.MOV", "start_frame": 30, "end_frame": 200,
   "card_type": "card_01", "card_present": true, "chip_visible": true, "status": "CORRECT"},
  {"file": "card01.MOV", "start_frame": 250, "end_frame": 400,
   "card_type": "card_01", "card_present": true, "chip_visible": false, "status": "CHIP_NOT_VISIBLE"}
]
```

카드를 움직이거나 손으로 가리는 구간은 `UNKNOWN`으로 라벨링하거나 평가 구간에서 제외하세요. 사진 추출은 UI `s`로 가능합니다. 예를 들어:

```powershell
$logs = (Get-ChildItem outputs/logs/*.jsonl).FullName
.\python.ps1 tools/evaluate.py --logs $logs --labels data/test/labels.json --output outputs/evaluation.json
```

카드 검출 재현율, 보이는 칩 검출 재현율, 카드/칩 오검출 건수, 상태 분류 정확도, 혼동 건수, UNKNOWN 비율, 평균 처리 시간, 카드 종류별 지표를 제공합니다. 정확도 분모에는 라벨이 있는 프레임만 포함하며 UNKNOWN도 분류 결과로 계산합니다. 라벨이 없으면 정확도는 `null`입니다. 같은 파일/프레임이 여러 로그에 있으면 마지막 기록만 사용합니다. **카메라별 비교는 서로 다른 로그 묶음으로 평가하세요.**

`seconds_to_stable_correct`는 라벨 구간 내 첫 관측부터 올바른 상태가 연속 5회 안정화될 때까지의 **영상 시간**입니다. `--stable-frames`로 바꿀 수 있습니다. 동작 완료와 기구 이동 시간을 포함하는 실제 장비의 종단간 지연은 아닙니다. 정답이 UNKNOWN이거나 판정을 얻지 못하면 `null`입니다.

## 테스트와 합성 데모

```powershell
.\python.ps1 -m unittest discover -s tests -v
.\python.ps1 tools/generate_demo.py
.\python.ps1 tools/verify_demo.py
.\python.ps1 main.py --source data/test/demo_reversed.avi
```

합성 카드에는 개인정보가 없습니다. 정방향·역방향·뒷면·90도·은색 칩·카드 없음 영상과 라벨을 생성합니다. 단위/통합 테스트는 방향과 좌표 변환, 불확실한 관측, 반복 프레임, 완료 신호, 타임아웃, 뒤집기/회전 제한, 새 프레임 재확인, 합성 검출, 영상 디코딩, 한글 이미지 경로, 평가 지표를 다룹니다. 실제 영상의 성능을 대변하지 않습니다. 구체적인 실행 결과는 `VALIDATION.md`에 기록합니다.

## MOV/HEVC/HDR 입력 문제

아이폰 MOV는 HEVC, HDR 또는 회전 메타데이터 때문에 OpenCV 빌드에 따라 읽히지 않거나 색상이 달라질 수 있습니다. 시작 시 입력 실패 오류를 출력합니다. 재생 중 조기 디코딩 실패는 파일 끝처럼 보일 수 있으므로 정상 프레임 수와 로그를 확인하세요. 호환성을 높이려면 촬영 설정에서 H.264/SDR을 쓰거나 FFmpeg가 설치된 환경에서 변환합니다.

```bash
ffmpeg -i input.MOV -an -c:v libx264 -pix_fmt yuv420p -crf 18 -movflags +faststart output.mp4
```

이 명령은 일반적인 코덱 변환입니다. HDR을 SDR로 올바르게 톤매핑하는 것까지 보장하지 않으므로 과노출·색상 문제가 있으면 SDR 원본을 먼저 사용하세요. OpenCV의 자동 회전 메타데이터 처리 이후에 설정의 회전을 적용합니다. 올바른 실제 방향을 UI로 확인하세요. FFmpeg 자체는 이 프로젝트에 포함하지 않습니다.

## 구조와 하드웨어 이식

```text
main.py                       CLI / 영상 처리 루프
cardvision/
  sources.py                  파일·사진·웹캠·선택적 Picamera2 어댑터
  models.py                   Observation / Command 계약
  batch.py                    독립 이미지 일괄 검사 / CSV·JSON·그룹별 평가
  vision/card_detector.py     외곽·원근 보정·고정 ROI
  vision/chip_detector.py     교체 가능한 OpenCV 후보 검출기
  vision/geometry.py          좌표 변환·방향 판정
  vision/pipeline.py          화질·움직임·관측·연속 안정화
  vision/temporal.py          카메라/OpenCV와 독립적인 연속 관측 필터
  control.py                  상태 머신 / Actuator Protocol / MockActuator
  ui.py                       오버레이·중간 처리 창
  config.py                   YAML 검증
  logging_utils.py            메타데이터·명시적 이미지 저장
tools/                        합성 데이터 생성 / 평가
tests/                        하드웨어 없이 실행하는 테스트
```

웹캠: `python main.py --camera 0`. Raspberry Pi OS에서 Picamera2를 별도로 설치한 뒤 `python main.py --picamera --headless`를 사용할 수 있도록 어댑터를 준비했습니다. 이 경로는 실제 Pi에서 검증하지 않았습니다. 카메라 드라이버가 BGR 프레임과 인덱스·시간을 반환하면 동일한 비전 코드를 사용합니다. 해상도·조명·노출·화각이 바뀌면 다시 튜닝하고 측정해야 합니다. Pi의 실시간 속도는 아직 측정하지 않았습니다.

미래 MCU 연동은 `Actuator.submit(command)`와 `poll()`의 `(command_id, success)` 이벤트를 구현하고 `Controller.acknowledge()`에 전달하는 구조입니다. 비전이 모터를 직접 제어하지 않습니다. 실제 연동 시 비동기 완료, 긴급 정지, 명령 중복 방지, 하드웨어 실패 처리와 reset/abort 절차를 구현해야 합니다. 지금의 `r` 초기화는 모의 장치 전용입니다. 처리 중 상태는 ANALYZING, FLIPPING, ROTATING, VERIFYING, INSERTING, COMPLETED, ERROR로 구분하며 캡처는 입력 루프에서 수행합니다.

처음에는 카메라를 고정하고 3~5종 카드의 정방향·역방향·뒷면을 촬영하세요. 카드번호를 가린 위치가 칩·외곽을 가리지 않도록 하고, 일반 조명과 반사를 포함하세요. 튜닝 영상과 평가 영상은 카드 종류/촬영 세션 단위로 분리해야 범용성을 확인할 수 있습니다.
