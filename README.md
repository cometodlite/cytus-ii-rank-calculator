# CYTUS II 통합 단위인정 계산기

GitHub Pages에서 실행하는 단일 파일 계산기입니다. `index.html`에 B-DCT 편성 데이터와 CSV 330곡이 포함되어 있어 별도 서버나 라이브러리 없이 사용할 수 있습니다.

## 포함 기능

- B-DCT Standard 15등급, SV 13등급, STT 14등급
- DCT 15등급의 Standard 및 MSTT 모드
- 4곡 배점: 20% / 20% / 25% / 35%
- Standard: 게임 점수 75% + TP 25%, 통합점수만 합격 판정에 사용
- SV: 게임 점수 90% + TP 10%
- STT: 게임 점수 50% + TP 50%
- SV/STT의 통합점수, 곡별 최저점 및 FINAL 별도 판정
- CSV 330곡 검색과 DCT 시험곡 선택
- 시험·등급별 입력 및 사용자 설정을 브라우저 로컬 저장소에 보관
- 작은 화면용 입력 배치, 입력 진행도, 성적표 복사

## DCT에 관한 안내

CSV는 개인 플레이 기록을 모은 수록곡 목록이지 DCT 시험곡 편성표가 아닙니다. 정확한 기존 DCT 60곡 등급별 편성 자료는 이 프로젝트에 포함되어 있지 않아 자동 편성하지 않습니다. DCT의 합격선은 사용자가 설정하는 값으로 처리하며 공식 기준으로 표시하지 않습니다. MSTT 계산 역시 임시 시뮬레이션입니다. 공식 산식이 확인되기 전까지 확정 공식으로 간주하지 마세요.

## GitHub Pages 배포

저장소의 **Settings → Pages**에서 **Deploy from a branch**, `main`, `/(root)`를 선택하면 됩니다. 사이트는 다음 주소에서 확인할 수 있습니다.

<https://cometodlite.github.io/cytus-ii-rank-calculator/>

성적과 DCT 사용자 설정은 입력한 기기의 브라우저 안에만 저장됩니다. iPhone에서는 GitHub Pages 주소를 Safari에서 열어 사용하세요.
