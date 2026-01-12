# 📈 주식 모니터링 봇

펄어비스, 신성델타테크, 메지온의 주가 및 공시를 자동으로 모니터링하여 디스코드로 알림을 보내는 봇입니다.

## 🚀 기능

### 1. 오전 8시 5분 모닝 리포트
- 각 종목의 현재가 및 등락률
- USD/KRW 환율 정보
- 최근 뉴스 1건 (종목별)
- 최근 공시 1건 (종목별)

### 2. 오전 9시 ~ 오후 4시 모니터링 (1시간 간격)
- 주가 변동 ±5% 이상 시 알림
- 신규 공시 발생 시 알림
- 조건 미충족 시 알림 없음

## 📋 준비물

### 1. Discord Webhook URL
1. Discord 서버에서 알림을 받을 채널 선택
2. 채널 설정 → 연동 → 웹후크 → 새 웹후크
3. 웹후크 URL 복사

### 2. 한국투자증권 API 키
1. [한국투자증권 오픈API](https://apiportal.koreainvestment.com/) 접속
2. 회원가입 및 로그인
3. API 신청 (모의투자 또는 실전투자)
4. APP KEY, APP SECRET 발급받기

### 3. OpenDart API 키
1. [OpenDart](https://opendart.fss.or.kr/) 접속
2. 회원가입 및 로그인
3. 인증키 신청/관리 → 인증키 발급

## 🔧 GitHub 설정

### 1. Repository Secrets 설정

GitHub Repository → Settings → Secrets and variables → Actions → New repository secret

다음 4개의 시크릿을 추가하세요:

| Name | Description | Example |
|------|-------------|---------|
| `DISCORD_WEBHOOK_URL` | Discord 웹후크 URL | `https://discord.com/api/webhooks/...` |
| `KIS_APP_KEY` | 한국투자증권 APP KEY | `PS1a2b3c4d5e...` |
| `KIS_APP_SECRET` | 한국투자증권 APP SECRET | `abcd1234efgh...` |
| `DART_API_KEY` | OpenDart 인증키 | `1234567890abcdef...` |

### 2. 파일 구조
```
your-repo/
├── .github/
│   └── workflows/
│       └── stock_monitor.yml
├── stock_monitor.py
├── requirements.txt
└── README.md
```

### 3. 실행 시간표 (KST 기준)

| 시간 | 작업 | 설명 |
|------|------|------|
| 08:05 | 모닝 리포트 | 전종목 요약 + 환율 + 뉴스 + 공시 |
| 09:00 | 모니터링 | ±5% 변동 또는 신규 공시 시 알림 |
| 10:00 | 모니터링 | ±5% 변동 또는 신규 공시 시 알림 |
| 11:00 | 모니터링 | ±5% 변동 또는 신규 공시 시 알림 |
| 12:00 | 모니터링 | ±5% 변동 또는 신규 공시 시 알림 |
| 13:00 | 모니터링 | ±5% 변동 또는 신규 공시 시 알림 |
| 14:00 | 모니터링 | ±5% 변동 또는 신규 공시 시 알림 |
| 15:00 | 모니터링 | ±5% 변동 또는 신규 공시 시 알림 |
| 16:00 | 모니터링 | ±5% 변동 또는 신규 공시 시 알림 |

## 🧪 테스트 방법

### 로컬 테스트
```bash
# 환경 변수 설정
export DISCORD_WEBHOOK_URL="your_webhook_url"
export KIS_APP_KEY="your_app_key"
export KIS_APP_SECRET="your_app_secret"
export DART_API_KEY="your_dart_key"

# 의존성 설치
pip install requests pytz

# 모닝 리포트 테스트
python stock_monitor.py morning

# 모니터링 테스트
python stock_monitor.py monitor
```

### GitHub Actions 수동 실행

1. Repository → Actions → Stock Monitor
2. Run workflow → Run workflow

## 📝 종목 추가/변경

`stock_monitor.py` 파일의 `STOCKS`와 `DART_CORP_CODES` 딕셔너리를 수정하세요:
```python
STOCKS = {
    '종목코드': {'name': '종목명', 'last_price': 0},
    # 예: '005930': {'name': '삼성전자', 'last_price': 0}
}

DART_CORP_CODES = {
    '종목코드': '고유번호',
    # OpenDart에서 기업 고유번호 확인 필요
}
```

## ⚠️ 주의사항

1. **GitHub Actions 무료 티어**: 월 2,000분 제한 (Public repo는 무제한)
2. **API 호출 제한**: 각 API의 일일 호출 제한 확인 필요
3. **주말/공휴일**: 장이 열리지 않는 날에도 스케줄은 실행됨
4. **시간대**: GitHub Actions는 UTC 기준이므로 cron 시간 주의

## 🔍 문제 해결

### Actions 탭에서 실행 로그 확인
- Repository → Actions → 실행된 workflow 클릭
- 각 step의 로그 확인

### 일반적인 오류
- **401 Unauthorized**: API 키 확인
- **Webhook 전송 실패**: Discord Webhook URL 확인
- **토큰 발급 실패**: 한국투자증권 API 상태 확인

## 📜 라이센스

MIT License

## 🤝 기여

이슈 및 풀 리퀘스트 환영합니다!
