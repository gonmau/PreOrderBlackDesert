# Ranking History Visualization

일별 국가별 Standard/Deluxe 순위 변화를 시각화하고 디스코드로 알림을 받는 프로젝트입니다.

## 📊 기능

- **개별 국가 그래프**: 각 국가별로 Standard와 Deluxe 순위를 한 그래프에 표시
- **통합 Standard 그래프**: 모든 국가의 Standard 순위를 한눈에 비교
- **통합 Deluxe 그래프**: 모든 국가의 Deluxe 순위를 한눈에 비교
- **🔔 디스코드 알림**: 그래프 생성 완료 시 자동으로 디스코드 채널에 알림

## 🚀 로컬 실행 방법

### 1. 저장소 클론
```bash
git clone <your-repo-url>
cd <repo-name>
```

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. 스크립트 실행
```bash
python plot_rankings.py
```

생성된 그래프는 `output/` 디렉토리에 저장됩니다.

## 🤖 GitHub Actions 사용

이 프로젝트는 GitHub Actions를 통해 자동으로 그래프를 생성합니다.

### 자동 실행 조건
- `rank_history__2_.json` 파일 업데이트 시
- `plot_rankings.py` 스크립트 수정 시
- 6시간마다 자동 실행 (스케줄)
- 수동 실행 (Actions 탭에서 "Run workflow")

### 결과 확인
1. GitHub 저장소의 **Actions** 탭 방문
2. 최신 워크플로우 실행 클릭
3. **Artifacts** 섹션에서 `ranking-plots` 다운로드

또는 자동으로 커밋된 `output/` 폴더 확인

### 🔔 디스코드 알림 설정
그래프 생성 완료 시 디스코드로 자동 알림을 받으려면:
1. 디스코드 웹훅 URL 생성
2. GitHub Secrets에 `DISCORD_WEBHOOK_URL` 등록

자세한 방법은 **[DISCORD_SETUP.md](DISCORD_SETUP.md)** 참고

## 📁 프로젝트 구조

```
.
├── .github/
│   └── workflows/
│       └── generate_plots.yml    # GitHub Actions 워크플로우
├── output/                        # 생성된 그래프 (자동 생성)
│   ├── 영국_ranking.png
│   ├── 독일_ranking.png
│   ├── ...
│   ├── all_countries_standard.png
│   └── all_countries_deluxe.png
├── rank_history__2_.json         # 순위 데이터
├── plot_rankings.py               # 그래프 생성 스크립트
├── requirements.txt               # Python 의존성
└── README.md                      # 이 파일
```

## 📈 출력 그래프 종류

### 1. 개별 국가 그래프
- 파일명: `{국가명}_ranking.png`
- 내용: 해당 국가의 Standard와 Deluxe 순위 추이

### 2. 통합 Standard 그래프
- 파일명: `all_countries_standard.png`
- 내용: 모든 국가의 Standard 순위 비교

### 3. 통합 Deluxe 그래프
- 파일명: `all_countries_deluxe.png`
- 내용: 모든 국가의 Deluxe 순위 비교

## 🔧 커스터마이징

### 그래프 스타일 수정
`plot_rankings.py`에서 다음 항목들을 수정할 수 있습니다:
- 그래프 크기: `figsize` 파라미터
- 색상 및 마커: `plot()` 함수의 스타일 옵션
- 해상도: `dpi` 파라미터

### 실행 스케줄 변경
`.github/workflows/generate_plots.yml`의 cron 표현식 수정:
```yaml
schedule:
  - cron: '0 */6 * * *'  # 6시간마다 → 원하는 시간으로 변경
```

## 📋 요구사항

- Python 3.11+
- matplotlib
- numpy
- requests (디스코드 알림용)

## 📝 라이선스

MIT License
