# CYTUS II 통합 단위인정시험 — 채보 데이터 2차 정밀 감사

## 범위와 감사 원칙

감사 기준은 `audit/288-slot-chart-validation`의 기준 커밋 `2420956`입니다. 시험 범위는 5개 시험 유형, 72개 등급, 288개 슬롯입니다.

| 시험 유형 | 등급 | 슬롯 | 후보 현황 |
|---|---:|---:|---|
| B-DCT Standard | 15 | 60 | 기존 곡 배정 60개 대조 |
| B-DCT SV | 13 | 52 | 기존 곡 배정 52개 대조 |
| B-DCT STT | 14 | 56 | 기존 곡 배정 56개 대조 |
| DCT Standard | 15 | 60 | 독립 신규 후보 60개 |
| DCT MSTT | 15 | 60 | 독립 신규 후보 60개 |
| **합계** | **72** | **288** | **168개 기존 B-DCT 슬롯 + 120개 DCT 제안 슬롯** |

`VERIFIED`는 곡·채보가 그 시험 슬롯에 배정된 근거까지 확인된 경우에만 허용합니다. 이 감사에서 개별 커뮤니티 페이지를 통해 확인한 것은 주로 곡 페이지와 해당 곡의 차트 난이도·레벨·해금 표기입니다. 이 자료만으로는 기존 시험의 특정 슬롯에 그 차트가 실제 배정됐는지 증명할 수 없으므로 **288개 슬롯 모두 `PENDING`**입니다.

CSV 상태 용어는 다음처럼 구분합니다.

- `SONG_CONFIRMED`: 출처에 곡 페이지/곡명이 있습니다. 게임 고유 ID가 확인됐다는 뜻은 아닙니다.
- `CHART_CONFIRMED`: 해당 출처의 개별 곡 페이지에 채보 종류와 표기 레벨이 함께 있습니다. 시험 슬롯 배정이나 공식 게임 데이터 검증을 뜻하지 않습니다.
- `PENDING`: 슬롯 배정, 공식/게임 내 교차 확인, 패턴 적합성 등 남은 검토가 있습니다.
- `POTENTIAL_FROM_APP_DIFFICULTY_HEURISTIC`: 현행 앱의 채보 추정 규칙을 데이터에 적용했을 때 생기는 잠정 중복입니다.

공식 곡 ID를 확인할 수 없어 `official_song_id`/`song_id`는 비워 두었습니다. `fandom:<페이지 경로>`와 `fandom:<페이지 경로>#<난이도>`는 출처 내에서만 쓰는 작업 키이며 게임의 공식 ID가 아닙니다. 레벨은 `15+`, `16`, `α`, `β`, `γ` 등 원문 표기를 숫자화하거나 평탄화하지 않았습니다.

## 출처와 신뢰 한계

개별 곡 페이지와 All Cytus II Songs 색인을 교차 대조했습니다. 색인은 게임 버전 5.2.18을 표시하고 있으며, 조사 날짜는 2026-10-12입니다. 현재 참조 페이지는 팬 커뮤니티 위키라서 출처 신뢰도는 `MEDIUM`으로 기록했습니다. 공식 게임 내 화면/공식 배포 자료가 아니며, 해금 조건의 최신성이나 표기 변경도 공식적으로 보증하지 않습니다.

- [All Cytus II Songs (Cytus II Wiki)](https://cytus.fandom.com/wiki/All_Cytus_II_Songs): 곡 색인과 버전 맥락
- [Cytus II Wiki](https://cytus.fandom.com/wiki/Cytus_II_Wiki): 개별 곡 페이지 형식 및 차트 정보
- [Cytus II song list (Japanese community wiki)](https://wikiwiki.jp/cytus-2/楽曲一覧): 특수 레벨 표기 교차 참고. 이 출처의 표기는 곡/차트 슬롯 배정 증명이 아닙니다.

`audit/bdct_song_chart_facts.csv`에는 35개 고유 곡 페이지에서 찾은 125개 차트 사실을 기록했습니다. `audit/chart_fact_records.csv`는 기존 B-DCT 후보 차트와 DCT 제안 차트의 출처 사실을 모아둔 목록입니다. 출처 키가 있다는 것과 감사 대상 편성표에서 그 차트를 쓰기로 확정했다는 것은 별개입니다.

## 산출물

- `chart_slots.csv`: 288개 감사 슬롯. 기존 B-DCT 168개는 현재 앱이 가정하는 채보와 출처 페이지의 차트 사실을 나란히 기록했습니다. 실제 슬롯의 `song_id`, `chart_difficulty`, `actual_level`, `unlock_condition`, `source_url`, `verified_on`은 증거가 확보되기 전까지 비워 두고 `verification_status=PENDING`으로 둡니다.
- `bdct_song_chart_facts.csv`: 기존 B-DCT 곡명에서 매칭된 개별 곡 페이지의 채보 종류, 실제 표기 레벨, 해금 조건, 노트 수, BPM, 길이, 출처와 확인일. 125행.
- `bdct_standard_4_7_comparison.csv`: Standard 4~7단에서 현행 앱의 채보 추정에 따른 레벨과 v1.3 목표, 같은 곡의 더 가까운 레벨 채보 후보를 비교. 16행.
- `bdct_duplicate_replacement_candidates.csv`: 중복 가능성이 있는 기존 슬롯에 대해 같은 곡의 대체 채보 후보를 기록. 135개 후보 행. 앱의 현재 잠정 매핑에서 이미 사용 중인 후보인지도 표시합니다.
- `bdct_overlap_report.csv`: 앱의 HARD/CHAOS 추정 규칙을 적용했을 때 나타나는 유형 간 동일 차트 후보 37개.
- `dct_candidate_rosters.csv`: DCT Standard와 MSTT를 분리한 60개씩의 신규 후보. 120행 모두 슬롯 배정은 `PENDING`입니다.
- `chart_fact_records.csv`: 출처에서 수집한 후보 차트 사실의 정규화 목록.
- `findings.md`: 이번 감사의 결과, 난이도 검토, 중복 및 미해결 사항 요약.
- `source_samples.csv`: 이전 1차 감사의 공개 자료 샘플.

## DCT 신규 후보 해석

`dct_candidate_rosters.csv`의 두 목록은 서로 다른 곡과 후보 채보를 써서 구성한 **조사 후보**입니다. 각 목록은 15등급 × 4슬롯이며, 같은 제목이나 후보 차트 키는 두 목록 간 재사용하지 않았습니다. 각 후보의 출처 페이지에 해당 레벨의 채보와 해금 표기가 있다는 의미로 `candidate_status=CHART_CONFIRMED`를 기록했습니다. 시험 목적에 대한 기술 적합성 검토와 실제 슬롯 배정은 완료되지 않아 `slot_assignment_status=PENDING`입니다.

두 시험의 목표 레벨은 v1.3에 있던 임시 목표를 감사용으로 사용했으며, 공식 편성안이나 공식 난이도 체계가 아닙니다. 후보 난이도 분포가 두 유형에서 같게 보이는 것은 동일한 임시 목표를 사용했기 때문입니다. MSTT 공식 산식·합격 판정은 확정하지 않았고 이 후보로 점수를 판정하지 않습니다.

## 감사기와 상태 보존

프로젝트 루트에서 실행합니다.

```sh
python3 tools/validate_audit.py
```

검사기는 288개 슬롯과 시험별 등급 수, 슬롯 ID, 상태값, `VERIFIED` 필수 근거를 검사합니다. DCT 후보는 60+60개 구성, 목표 레벨 일치, 출처/확인일, 두 시험 사이의 후보 중복 방지를 별도로 검사합니다. `CHART_CONFIRMED`인 후보도 슬롯 배정 상태가 `PENDING`이면 공개 편성표로 승인되지 않습니다.

## 변경/배포 경계

이 브랜치는 감사용 CSV, 문서, 검사기만 다룹니다. 계산기 UI·계산 로직, `main`, GitHub Pages, 배포 설정은 수정하지 않았습니다. 이 결과는 검토 보고이며 편성 확정, 사용자 공개 또는 배포 승인으로 간주하지 않습니다.
