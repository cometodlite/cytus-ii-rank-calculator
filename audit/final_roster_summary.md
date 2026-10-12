# CYTUS II 통합 단위인정시험 — 최종 편성 후보

기준: 커밋 `22bc0db`의 `audit/roster_proposal_288.csv`. 별도 감사 차수 없이 기존 감사의 출처 확인 후보만 사용했습니다.

| 시험 | 등급 | 슬롯 | 상태 |
|---|---:|---:|---|
| B-DCT Standard | 15 | 60 | PROPOSED |
| B-DCT SV | 13 | 52 | PROPOSED |
| B-DCT STT | 14 | 56 | PROPOSED |
| DCT Standard | 15 | 60 | PROPOSED |
| DCT MSTT | 15 | 60 | PROPOSED |
| **합계** | **72** | **288** | **PROPOSED** |

기존 제안에서 출처 확인 대체 후보 10개를 적용했습니다. 전체 교차 유형 중복은 3개 키/8개 슬롯으로 감소했고, 시험 내부 반복은 34개 키/89개 슬롯에 남았습니다. 적용한 모든 대체안도 실전 적합성 확정이 아닌 `PROPOSED`입니다.

Standard 4~7단 16개 후보와 기존 목표 레벨은 그대로 유지했습니다. 각 해당 슬롯에는 실제 난이도 확인 필요 플래그를 넣었습니다. DCT Standard와 MSTT는 각각 기존 60개 후보를 유지했고, MSTT 산식·합격 기준은 정하지 않았습니다.

[최종 후보 288슬롯 CSV](final_roster_candidates_288.csv)에는 곡명, 채보, 레벨, 출처, 선정 사유, 변경 이력, 충돌과 난이도 검토 상태가 있습니다. [예외 CSV](final_roster_exceptions.csv)에는 남은 중복, 출처 불일치, 플레이 검증 필요 항목이 있습니다.

모든 슬롯의 `roster_status`는 `PROPOSED`, `playtest_status`와 `slot_verification_status`는 `PENDING`입니다. 계산기 코드, `main`, GitHub Pages는 변경하지 않았습니다.
