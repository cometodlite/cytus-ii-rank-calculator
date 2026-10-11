# CYTUS II 통합 단위인정시험 감사 자료

## 현행 감사 단계

최신 결과는 [3차 정밀 감사 보고서](findings_3rd.md)입니다. 기준 브랜치는 `audit/288-slot-chart-validation`, 기준 커밋은 `1464737`입니다. 기존 2차 조사 기록은 [findings.md](findings.md)에 남아 있습니다.

시험 범위는 5개 유형, 72개 등급, 288개 슬롯입니다.

| 시험 | 등급 | 슬롯 |
|---|---:|---:|
| B-DCT Standard | 15 | 60 |
| B-DCT SV | 13 | 52 |
| B-DCT STT | 14 | 56 |
| DCT Standard | 15 | 60 |
| DCT MSTT | 15 | 60 |

## 상태 정의

- `PENDING`: 슬롯 또는 목적 적합성을 판단할 증거가 부족함.
- `SOURCE_CONFIRMED`: 출처에 곡·채보가 존재하고 표기 레벨 등 출처 사실이 확인됨. 슬롯 배정과 패턴 적합성은 확인된 것이 아님.
- `CANDIDATE_REVIEWED`: 목표 레벨과 시험 목적에 대한 충분한 자료 기반 검토가 완료됨.
- `PLAYTESTED`: 실제 플레이 결과를 기록해 검토함.
- `VERIFIED`: 시험 편성에서 해당 곡·채보를 사용한다는 근거와 필수 메타데이터가 확인됨.

현재 출처 사실은 `SOURCE_CONFIRMED`로 기록했습니다. 패턴 원자료와 플레이 기록은 없어 `CANDIDATE_REVIEWED`, `PLAYTESTED`, `VERIFIED`로 올린 후보는 없습니다. 슬롯 배정은 모두 `PENDING`입니다. 출처만 확인한 사실을 실전 검증이나 슬롯 확정으로 취급하지 않습니다.

공식 게임 곡 ID는 출처에서 확인되지 않아 ID 칸을 비워 두었습니다. `fandom:<페이지>#<채보>`는 출처 작업용 키이며 게임 공식 ID가 아닙니다. `15+`, `16`, `α`, `β`, `γ` 등 특수 표기는 그대로 보존합니다. 출처는 팬 커뮤니티 위키를 포함하므로 공식 데이터로 인증하지 않았습니다. [Cytus II 곡 색인](https://cytus.fandom.com/wiki/All_Cytus_II_Songs), [레벨별 곡 목록](https://wikiwiki.jp/cytus-2/%E6%A5%BD%E6%9B%B2%E4%B8%80%E8%A6%A7%28%E3%83%AC%E3%83%99%E3%83%AB%E5%88%A52%29)

## 결과 파일

- `chart_slots.csv`: 288개 슬롯과 출처 확인된 후보 사실을 구분해 기록합니다. 실제 시험 슬롯의 곡·채보 배정은 미확정입니다.
- `bdct_song_chart_facts.csv`: 35개 고유 곡 페이지에서 수집한 125개 차트 사실.
- `bdct_standard_4_7_recomposition_candidates.csv`: Standard 4~7단의 같은 곡 내 목표 레벨 근접 후보와 새 슬롯 순서 제안. 플레이 전 후보입니다.
- `bdct_sv_stt_overlap_resolution.csv`: 앱의 채보 추정 규칙에 따라 식별된 37개 잠정 중복 및 레벨 차이만 고려한 보류용 소유 유형 참고.
- `bdct_cross_type_replacement_options.csv`: 중복 영향을 받는 슬롯별 같은 곡 대체 채보 후보 291행. 후보 간 전역 배정은 아직 풀지 않았습니다.
- `dct_candidate_review.csv`: DCT Standard/MSTT 후보 120개의 목표 레벨, 차트 종류, 노트 수, BPM, 길이, 노트/분 참고값. 목적 적합성 검토는 보류입니다.
- `grade_level_progression.csv`: 5개 시험의 72등급을 등급별로 비교한 레벨 흐름 요약. B-DCT는 앱 추정값이며, DCT는 제안 후보 기준입니다.
- `chart_playtest_queue.csv`: 현재 후보·대체 후보에서 중복을 제거한 237개 채보의 플레이 검토 대기열.
- `bdct_overlap_report.csv`: 유형 간 잠정 중복 원본 37행.
- `bdct_duplicate_replacement_candidates.csv`: 2차 감사의 대체 후보 원본.
- `bdct_standard_4_7_comparison.csv`: 2차 감사의 기존/후보 레벨 비교.
- `dct_candidate_rosters.csv`: DCT Standard/MSTT 각각 60개 독립 제안.
- `chart_fact_records.csv`: 수집 차트 사실 정규화 목록.
- `findings.md`: 2차 감사 기록.

노트/분은 `노트 수 ÷ 곡 길이(분)`의 계산 참고값입니다. 이는 패턴 난이도, 리듬 복잡도, 양손 이동, 점수 안정성, TP 성능, 지속력을 직접 측정하지 않습니다.

## 검사

프로젝트 루트에서 실행합니다.

```sh
python3 tools/build_audit_3.py
python3 tools/validate_audit.py
```

검사기는 288개 슬롯 구성, 독립 편성 수, 후보 상태, 레벨 순서 및 미승격 상태를 확인합니다. 생성 스크립트는 감사 CSV만 갱신합니다.

## 변경 경계

이번 감사는 자료와 후보 검토 파일만 다룹니다. `main`, 계산기 UI/계산 로직, GitHub Pages와 원격 배포는 수정하지 않았습니다. 최종 편성 확정과 공개는 별도 승인 전까지 보류합니다.
