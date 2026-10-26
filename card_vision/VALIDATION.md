# 실행 검증 기록

검증일: 2026-10-24. Windows PC, CPython 3.12.14, OpenCV Python 패키지 5.0.0.93 (`cv2.__version__=5.0.0`), NumPy 2.5.4, PyYAML 6.0.3. 패키지는 작업 폴더 상위 `.deps`에 설치했으며 시스템 Python을 변경하지 않았습니다.

## 수행 결과

| 검증 | 결과 |
|---|---|
| `python.ps1 -m unittest discover -s tests -v` | **52개 통과** (2026-10-26 실행); 다운로드 이미지가 없으면 선택적 실제 이미지 회귀 테스트는 건너뜀 |
| `tools/verify_demo.py` | 6개 합성 AVI, 각 36프레임, 총 216프레임 디코딩·처리 |
| 정방향 / 역방향 / 뒷면 / 은색 칩 CLI | 각각 INSERTING / ROTATING / FLIPPING / INSERTING 상태에서 완료 신호 대기 |
| 90도 카드 / 빈 화면 CLI | 각각 UNKNOWN 관측 유지 / WAITING_FOR_CARD, 모터 명령 없음 |
| `--simulate-acks` 정방향 CLI | INSERT 요청 후 모의 ACK를 받아 COMPLETED |
| 합성 화면을 바꾸는 통합 테스트 | FLIP → 새 관측 → ROTATE_180 → 새 관측 → INSERT → COMPLETED |
| OpenCV GUI 실행 (`--max-frames 6`) | 창 생성·프레임 표시·6프레임 처리·정상 종료 |
| 오버레이 / 중간 처리 이미지 | 생성 후 직접 이미지로 확인, 검출 박스·좌표·투입구 화살표·상태 표시 |
| 평가 CLI | JSONL 여러 파일 입력과 정답 구간 JSON을 읽어 보고서 출력 |
| 실패 이미지 명시적 저장 | `--save-failures --max-frames 2`에서 UNKNOWN 프레임 PNG/JSON 생성 |
| 한글 경로 | 한글 작업 폴더의 AVI 디코딩과 `카드.png` 저장/읽기 통과 |
| 단일 JPG/JPEG/PNG | 대문자 확장자·한글 파일명 디코딩, 즉시 방향 판단, 품질 조건 유지 |
| 단일 이미지 CLI | CORRECT 판정과 IMAGE_REVIEW 로그; 자동 모의 ACK 옵션에도 명령 미생성 |
| Batch CLI | 합성 PNG 6개 처리; CSV/JSON/박스가 표시된 PNG 생성 |
| 하위 폴더 비교 | 합성 JPG/JPEG/PNG 4개, internet/phone 그룹별 결과와 라벨 평가 생성 |
| Batch 오류/격리 | 손상 파일 기록 후 계속 처리, 같은 이름/다른 확장자 보존, 중첩 출력 폴더 제외 |
| 이미지 저장 오류 | 검출 결과 보존과 별도 annotation_error 기록 |
| 단일 이미지 저장 | UNKNOWN에 자동 실패 저장을 함께 켜도 검출 표시·정보 패널 보존 |
| 고정 검색창 여백 | 실제 카드 경계와 일치하지 않는 검색창에서 카드 검출·좌표 복원 |
| 합성 검정 바닥 | 좌우 최대 35px·상하 최대 18px 이동 및 ±6도 조건의 카드/칩 판정 |
| 검색창의 빈 바닥·잘린 카드 | 카드로 가정하지 않고 UNKNOWN 유지 |
| 검색창 바깥 움직임 | 내부 영상이 동일하면 외부 변화가 움직임 판정을 흔들지 않음 |
| 칩 위치 필터 | 여유 영역·중심점 검사·180도 대응·외부 고득점 후보 제외·중복 후보 통합 |
| 같은 색상 카드/칩 | 금색 바탕의 칩을 경계 후보로 복원하는 합성 회귀 테스트 |
| 실제 이미지 회귀 | Aircash 뒷면 홀로그램 제외 및 Piraeus Visa 실제 칩 복원 |
| 크기·비율 결합 조건 | 두 SBI 홀로그램 제외, 큰 정사각형/작은 가로형 후보 보존, 필터 설정 검증 |

테스트는 잘못된 완료 ID, 중복 관측, 불안정한 분류, 카드 없음, 완료 실패, 동작/관측 타임아웃, 반복 뒤집기·회전 제한, 뒤집기 후 카드 소실, 중심/90도/거울/좌표 회전, 블러/이동/부분 카드, 고정 ROI의 빈 화면, 복수 칩 후보, 무늬 후보, 라벨 없는 평가를 포함합니다.

## 합성 영상 수치

아래 합성 영상 수치는 초기 버전 실행 기록입니다. 2026-10-26 칩 위치 필터 버전의 실제 이미지 재검사 수치는 [별도 보고서](outputs/chip_position_retest/REPORT.md)에 있습니다.

추가 크기·비율 조건을 적용한 [최신 재검사](outputs/chip_size_retest/REPORT.md)에서는 같은 169장 중 칩 없는 뒷면의 오검출 2건이 제외되었고, 이전 앞면 칩 검출 50건을 모두 유지했습니다. 같은 개발 이미지에 맞춰 조정한 결과이며 다른 카드에 대한 일반화 성능은 미검증입니다.

아래 결과는 이 구현의 간단한 도형 생성기로 만든 **좁은 범위의 합성 데이터 회귀 검사**입니다. 실제 카드 인식 성능 추정치가 아닙니다. 합성 테스트가 성공하도록 기준을 구현했으므로 실제 카드의 디자인·금속 반사·화질 분포를 대표하지 않습니다.

- 상태 분류 일치: 212/216 프레임, **98.15%**.
- 카드 검출: 카드가 있는 180/180 프레임. 카드가 없는 36프레임에서 카드 오검출 0건.
- 칩 검출: 칩이 보이는 143/144 프레임. 칩이 없는 72프레임에서 칩 오검출 0건.
- UNKNOWN: 76/216 프레임. 이 중 72프레임은 90도/빈 화면으로 정답도 UNKNOWN이며, 나머지 4프레임은 첫 프레임 안정성 조건 때문에 판정을 유보했습니다.
- 정상 세 업무 상태의 연속 5프레임 안정화까지 영상 시간 약 **0.333초** (15 FPS 합성 영상).
- 해당 PC 실행의 평균 비전 처리 시간 약 **9.30ms/프레임**. 입력 디코딩·UI·실제 기구 동작을 포함한 처리량이 아니며 Pi 속도를 의미하지 않습니다.

세부 보고서: `outputs/synthetic_validation/evaluation.json`, 별도 평가 CLI 결과: `outputs/synthetic_validation/cli_evaluation.json`.

화면 예시: `outputs/synthetic_validation/preview.png`, 중간 처리 예시: `outputs/synthetic_validation/intermediates.png`.

이미지 비교 예시는 `data/test/image_batch_demo/`와 `outputs/image_comparison_demo/`에 생성했습니다. internet/phone은 그룹 구분을 검증하기 위한 폴더 이름이며 **두 그룹 모두 합성 이미지**입니다. 실물/인터넷 이미지의 성능 비교 결과가 아닙니다. Batch의 라벨 없는 정확도 null, 그룹별 정확도, 손상 파일 및 출력 충돌 처리는 `tests/test_images.py`에서도 검증합니다.

## 아직 검증하지 않은 항목

실제 아이폰 MOV/MP4, HEVC/HDR 색상·코덱 호환성, 다양한 실물 카드, 반사광·가림·손, 심한 원근 왜곡, 웹캠, Raspberry Pi/Picamera2, Pi에서의 지연·CPU 점유율, 실제 모터/MCU 완료 신호, Linux GUI에서의 실행은 미검증입니다. GUI의 모든 키와 파일 선택창을 사람이 하나씩 조작하는 검증도 수행하지 않았습니다. 영상 재생·seek·판정/상태 로직은 코드 테스트로 확인했습니다.

실제 영상이 생기면 카드 종류/촬영 세션을 분리해 정답 구간을 만들고, `tools/evaluate.py`로 별도 측정해야 합니다. 실제 기구에 연결하기 전에는 불확실한 판정과 동작 실패에 대한 정지 동작도 장비에서 검증해야 합니다.

고정 검색창 검증의 어두운 줄무늬 배경은 합성 데이터이며 실제 검정 필라멘트 출력물을 촬영한 것이 아닙니다. 테스트의 픽셀 이동·회전 범위는 기구의 실제 허용오차를 보장하지 않습니다. 실제 카메라와 기구가 준비되면 검색창 좌표와 여유 폭을 맞춰야 합니다. 칩 오검출기 자체는 이번 검색창 변경으로 개선되었다고 평가하지 않았습니다.

## 재현

프로젝트 폴더에서:

```powershell
.\python.ps1 -m unittest discover -s tests -v
.\python.ps1 tools/verify_demo.py
.\python.ps1 main.py --source data/test/demo_correct.avi --max-frames 6
.\python.ps1 main.py --source data/test/demo_correct.png --headless --save-annotated
.\python.ps1 main.py --batch data/test/image_batch_demo --recursive --save-annotated --labels data/test/image_batch_demo/labels.json
```
