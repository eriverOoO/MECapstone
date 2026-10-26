# 카드 검증 이미지 출처 및 라이선스

아래 원본은 Wikimedia Commons에서 내려받은 공개 이미지입니다. 2026-10-25에 Commons API의 저작자·라이선스 메타데이터를 확인했으며, [확인 기록](data/test/topdown_kit/license_metadata.json)과 [출처 목록](data/test/topdown_kit/sources.csv)을 보존했습니다.

검증 결과의 파일 이름은 원본 ID를 유지합니다. 예를 들어 `aircash_front.jpg.png`, `aircash_front__left_12.jpg.png`는 모두 아래 `aircash_front`의 파생 이미지입니다. 가공은 리사이즈, 평면 회전·이동, 밝기·블러·저해상도 변형, 검사창·검출 박스·문구 표시, 비교판 합성입니다. 표시 영역은 알고리즘의 예측이며 원저작자의 주석이 아닙니다.

| 원본 ID | 저작자 | 원본 파일/출처 | 원본 및 해당 파생 이미지의 라이선스 |
|---|---|---|---|
| nh_front | Chapaguri | [NH체크카드 (앞면)](https://commons.wikimedia.org/wiki/File:NH체크카드_(앞면).jpg) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| nh_back | Chapaguri | [NH체크카드 (뒷면)](https://commons.wikimedia.org/wiki/File:NH체크카드_(뒷면).jpg) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| jago_front | VulcanSphere | [Front of Bank Jago Visa Debit card](https://commons.wikimedia.org/wiki/File:Front_of_Bank_Jago_Visa_Debit_card.jpg) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| jago_back | VulcanSphere | [Back of Bank Jago Visa Debit card](https://commons.wikimedia.org/wiki/File:Back_of_Bank_Jago_Visa_Debit_card.jpg) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| piraeus_master_front | Filippos Fragkogiannis | [Piraeus Mastercard Front](https://commons.wikimedia.org/wiki/File:Piraeus_Bank_Mastercard_Debit_Card_(Front).png) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| piraeus_master_back | Filippos Fragkogiannis | [Piraeus Mastercard Back](https://commons.wikimedia.org/wiki/File:Piraeus_Bank_Mastercard_Debit_Card_(Back).png) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| piraeus_visa_front | Filippos Fragkogiannis | [Piraeus Visa Front](https://commons.wikimedia.org/wiki/File:Piraeus_Bank_Visa_Debit_Card_(Front).png) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| piraeus_visa_back | Filippos Fragkogiannis | [Piraeus Visa Back](https://commons.wikimedia.org/wiki/File:Piraeus_Bank_Visa_Debit_Card_(Back).png) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| aircash_front | Filippos Fragkogiannis | [Aircash Front](https://commons.wikimedia.org/wiki/File:Aircash_Mastercard_Prepaid_Card_(Front).png) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| aircash_back | Filippos Fragkogiannis | [Aircash Back](https://commons.wikimedia.org/wiki/File:Aircash_Mastercard_Prepaid_Card_(Back).png) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| sbi_front | Rory trains | [SBI Debit Card Front](https://commons.wikimedia.org/wiki/File:Sumishin_SBI_Net_bank_New_Debit_Card_(Master).jpg) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| sbi_back | Rory trains | [SBI Debit Card Back](https://commons.wikimedia.org/wiki/File:Sumishin_SBI_Net_bank_New_Debit_Card_(Master)_Back_side.png) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| plain_back | Santeri Viinamäki | [Blank back of payment card](https://commons.wikimedia.org/wiki/File:Blank_back_of_payment_card.jpg) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |

적용 범위:

- `outputs/topdown_kit_baseline/`의 실물 이미지 PNG와 `outputs/topdown_roi_retest/annotated/`의 PNG는 파일명에 대응하는 위 원저작자의 이미지에 주석을 추가한 것입니다.
- `outputs/chip_position_retest/annotated/` 및 `classification_preview.png`도 동일한 원본에 위치 허용 영역·제외 후보·상태 문구를 추가한 파생 결과로 같은 출처와 라이선스가 적용됩니다.
- `outputs/chip_size_retest/annotated/` 및 해당 `classification_preview.png`는 같은 원본의 크기·비율 필터 재검사 결과이며 같은 출처와 라이선스를 적용합니다.
- 여러 원본이 들어간 `originals_*.png`, `detection_regions_preview.png`, `before_after.png`, `roi_results_preview.png`도 위 출처에 기반합니다. 이 비교 이미지에 추가한 부분은 CC BY-SA 4.0으로 제공합니다.
- `outputs/stage_roi_validation/`과 `outputs/synthetic_validation/`의 도형 카드는 이 프로젝트에서 생성한 합성 데이터이며 위 실물 이미지 출처와 별개입니다.

위 적용 범위의 실물 카드 파생 이미지와 비교판은 원본 저작자 표시를 유지하며, CC BY-SA 원본의 파생 결과와 비교판 추가 부분은 CC BY-SA 4.0으로 제공합니다. 이 문서는 프로젝트 코드 전체에 별도 라이선스를 부여하지 않습니다.
