# Top-down kit 기본 설정 테스트 결과

검증일: 2026-10-24. 기본 `config.yaml`, 이미지 모드, 입력 너비 960, 기구 투입구 오른쪽. 기존 알고리즘을 그대로 실행한 기준 결과입니다.

**프로그램은 169장을 오류 없이 처리했지만, 현재 검출기는 실물 이미지에서 오검출과 미검출이 많습니다. 기구 동작 판단에 바로 사용할 수준으로 검증되지 않았습니다.** 특히 뒷면의 홀로그램을 칩으로 잡거나 앞면의 비접촉 결제 아이콘을 칩으로 잡았습니다.

## 입력과 실행

제공된 Downloads 키트에는 이미지 없이 출처 CSV와 다운로드 스크립트만 있었습니다. 해당 스크립트를 읽어 확인한 뒤 작업 폴더 `data/test/topdown_kit/`로 복사하고 원본을 다운로드했습니다. 원본 13/13개를 다운로드했고, 키트의 생성 방식 그대로 원본당 12개 변형, 총 156개를 생성했습니다.

입력은 원본 13장 + 평면 회전/이동/어두움/블러/저해상도 변형 156장입니다. **169장은 독립적인 카드 169종이 아닙니다.** 13개 원본에 앞뒷면 짝이 포함되어 있습니다. 사진/스캔 모두 인터넷 출처이며, 사용자가 촬영한 폰카메라 데이터와 비교한 결과는 아닙니다.

데이터 출처·저작자·라이선스는 `data/test/topdown_kit/sources.csv`, 다운로드 성공 내역은 같은 폴더의 `download_results.json`, 변형 조건은 `variant_labels.csv`에 보존했습니다.

프로젝트 폴더에서 재현:

```powershell
.\python.ps1 main.py --batch data/test/topdown_kit/images --recursive --save-annotated --output outputs/topdown_kit_baseline
```

이 실행의 결과 디렉터리: [batch_20261024_153642_f36f4efa](batch_20261024_153642_f36f4efa/).

## 전체 수치

| 항목 | 전체 169장 | 원본 13장 | 변형 156장 |
|---|---:|---:|---:|
| 읽기·처리 성공 | 169 | 13 | 156 |
| 카드 검출 표시 | 119 (70.4%) | 7 (53.8%) | 112 (71.8%) |
| IC칩 검출 표시 | 64 (37.9%) | 4 (30.8%) | 60 (38.5%) |
| UNKNOWN | 111 (65.7%) | 9 (69.2%) | 102 (65.4%) |
| 평균 비전 처리 시간 | 7.35ms | 10.36ms | 7.09ms |

**위 검출 표시는 성공률/정확도가 아닙니다.** 잘못된 영역을 검출한 경우도 true로 집계됩니다. 실제로 일부 카드 박스는 카드가 아닌 원본 사진의 직사각형 배경에 맞았고, 칩 박스도 홀로그램/아이콘을 잡았습니다. 처리 시간은 해당 PC의 리사이즈·비전 처리만 포함하며 읽기·저장·UI와 Pi 속도를 포함하지 않습니다.

정답 방향/박스를 포함한 독립적인 169장 라벨은 없으므로 공식 분류 정확도는 계산하지 않았습니다. 키트도 CORRECT/REVERSED 정답을 제공하지 않습니다. 기본 오른쪽 투입구를 적용했으며, 이를 실물 기구의 실제 방향으로 검증한 것은 아닙니다.

원본 13장의 픽셀을 확인했을 때 앞면 6개에는 칩이 보이고 뒷면 7개에는 칩이 보이지 않았습니다. 이 구분을 변형에 전파하면 칩 없는 뒷면 91장 중 **19장에서 칩 검출 표시(20.9%)**가 나옵니다. 앞면 78장에서는 45장이 검출 표시지만, 앞면에서도 다른 무늬를 잡은 경우가 있으므로 이를 올바른 칩 위치 검출 재현율로 사용하면 안 됩니다.

## 결과 사유

| 판정 사유 | 건수 | 해석 |
|---|---:|---|
| no_card | 50 | 카드 외곽 후보 없음/필터 탈락 |
| unexpected_card_axis | 44 | 긴 변이 투입구 방향과 정렬되지 않음 |
| low_image_quality | 13 | 화질 조건 때문에 판정 유보 |
| weak_chip_candidate | 4 | 약한 후보 때문에 판정 유보 |
| no_chip_candidate | 22 | CHIP_NOT_VISIBLE로 판단, 실제 미검출 가능 |
| chip_away_from_inlet | 25 | REVERSED 표시, 오검출 포함 |
| chip_toward_inlet | 11 | CORRECT 표시, 오검출 포함 |

Jago와 Piraeus Mastercard 원본은 카드의 긴 변이 세로입니다. 0/180도와 ±12도 변형만 만들었으므로 여전히 세로입니다. 현재 기구 모델은 긴 변이 오른쪽 투입구와 나란해야 하므로 이 경우 UNKNOWN은 의도된 자세 제한입니다. 이를 칩 검출 실패와 구분해야 합니다.

## 눈으로 확인한 대표 사례

| 사례 | 확인 결과 | 저장 이미지 |
|---|---|---|
| Aircash 앞면 원본 | 실제 접점 칩을 검출, REVERSED | [보기](batch_20261024_153642_f36f4efa/annotated/originals/aircash_front.jpg.png) |
| Aircash 뒷면 원본 | debit 홀로그램을 칩으로 오검출, REVERSED | [보기](batch_20261024_153642_f36f4efa/annotated/originals/aircash_back.jpg.png) |
| SBI 뒷면 원본 | 홀로그램을 칩으로 오검출, REVERSED | [보기](batch_20261024_153642_f36f4efa/annotated/originals/sbi_back.jpg.png) |
| Piraeus Visa 앞면 원본 | 왼쪽 실제 칩 대신 오른쪽 비접촉 결제 아이콘 검출, CORRECT로 잘못 표시 | [보기](batch_20261024_153642_f36f4efa/annotated/originals/piraeus_visa_front.jpg.png) |
| Jago 앞면 center_0 | 칩 위치는 잡지만 사진 배경 외곽을 카드로 검출, 세로 자세로 UNKNOWN | [보기](batch_20261024_153642_f36f4efa/annotated/planar_variants/jago_front__center_0.jpg.png) |
| Piraeus Mastercard 앞면 center_0 | 실제 칩 검출, 세로 자세로 UNKNOWN | [보기](batch_20261024_153642_f36f4efa/annotated/planar_variants/piraeus_master_front__center_0.jpg.png) |
| Piraeus Mastercard 뒷면 center_0 | 홀로그램 오검출, 세로 자세로 UNKNOWN | [보기](batch_20261024_153642_f36f4efa/annotated/planar_variants/piraeus_master_back__center_0.jpg.png) |
| NH 앞·뒷면 | 원본과 모든 변형에서 카드 검출 표시 없음 | [앞면 원본](batch_20261024_153642_f36f4efa/annotated/originals/nh_front.jpg.png) |

위 이미지들을 포함해 원본 전체와 일부 대표 변형을 시각적으로 확인했습니다. 모든 169장의 박스 위치를 정밀 라벨링한 결과는 아닙니다. 높은 후보 점수(예: 0.92)로도 홀로그램 오검출이 발생하므로 점수를 보정된 확률처럼 해석할 수 없습니다.

뒷면에 칩이 있다고 오판한 이미지 중 Aircash 8장과 SBI 2장은 방향 상태도 CORRECT/REVERSED가 되어 잘못된 동작을 제안합니다. 현재 이미지 모드는 실제 명령을 생성하지 않지만, 같은 오검출이 영상에서 안정적으로 반복되면 연속 프레임 안정화만으로는 방지되지 않습니다.

## 원본별 요약

각 원본에 대해 원본+변형 13장씩 집계했습니다. 칩 검출 열은 올바른 위치 일치를 보장하지 않습니다.

| 원본 ID | 카드 검출 표시 | 칩 검출 표시 | UNKNOWN |
|---|---:|---:|---:|
| aircash_back | 13 | 8 | 4 |
| aircash_front | 13 | 10 | 3 |
| jago_back | 12 | 0 | 13 |
| jago_front | 12 | 9 | 13 |
| nh_back | 0 | 0 | 13 |
| nh_front | 0 | 0 | 13 |
| piraeus_master_back | 12 | 9 | 13 |
| piraeus_master_front | 13 | 9 | 13 |
| piraeus_visa_back | 5 | 0 | 8 |
| piraeus_visa_front | 12 | 8 | 2 |
| plain_back | 13 | 0 | 1 |
| sbi_back | 4 | 2 | 11 |
| sbi_front | 10 | 9 | 4 |

## 다음 개선의 우선순위

1. 홀로그램·비접촉 결제 아이콘·로고를 접점 칩과 구별하는 후보 검증을 강화합니다. 색상·사각형·내부 선 개수만으로는 부족합니다.
2. 카드 박스의 실제 위치를 검증합니다. 사진 배경을 카드로 정규화하면 칩의 면적/상대 위치 조건도 왜곡됩니다.
3. 최종 기구의 평면 자세 조건으로 평가할 데이터와, 세로 입력처럼 지원하지 않는 자세를 나눕니다. 현재 UNKNOWN은 실패와 정상적인 거부가 섞여 있습니다.
4. 원본 단위로 개발/평가를 나눕니다. 같은 원본에서 나온 12개 변형을 무작위로 나누면 범용 성능을 과대평가할 수 있습니다.

## 결과 파일

- [이미지별 CSV](batch_20261024_153642_f36f4efa/results.csv)
- [설정·좌표·이미지별 JSON](batch_20261024_153642_f36f4efa/results.json)
- [전체/원본/변형 요약 JSON](batch_20261024_153642_f36f4efa/summary.json)
- [박스가 표시된 이미지 폴더](batch_20261024_153642_f36f4efa/annotated/)
- 원본 연락판: [1](originals_1.png), [2](originals_2.png), [3](originals_3.png)
