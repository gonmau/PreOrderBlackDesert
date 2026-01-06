# Black Desert - 실시간 플랫폼별 판매량 순위 스크래핑 시스템 🎮

Black Desert를 포함한 게임들의 실시간 플랫폼별 판매 순위를 웹 스크래핑으로 수집하고 분석하는 Python 프로젝트입니다.

## 주요 기능

- 🌐 **실시간 데이터 수집**: 웹사이트에서 실제 베스트셀러 차트 스크래핑
- 📊 **다중 플랫폼 지원**: Steam, PlayStation Store, VGChartz 등
- 🔍 **게임 순위 검색**: 특정 게임의 플랫폼별 순위 자동 조회
- 💾 **데이터 저장**: JSON 형식으로 수집 이력 저장
- 📈 **순위 추적**: 시간대별 순위 변화 추적
- 📄 **리포트 생성**: 수집된 데이터를 텍스트 리포트로 출력

## 지원 데이터 소스

### 1. Steam (PC)
- Steam 글로벌 베스트셀러 차트
- TOP 20 실시간 수집
- 출처: `store.steampowered.com/charts/topselling`

### 2. PlayStation Store
- PlayStation 인기 게임 차트
- GraphQL API 활용
- 지역별 데이터 수집 가능

### 3. VGChartz
- 게임 예약 판매 순위
- 멀티플랫폼 종합 차트
- 출처: `vgchartz.com/preorders`

## 설치 방법

### 1. 저장소 클론
```bash
git clone https://github.com/yourusername/black-desert-sales-scraper.git
cd black-desert-sales-scraper
```

### 2. 필수 패키지 설치
```bash
pip install -r requirements.txt
```

필요한 패키지:
- `requests` - HTTP 요청
- `beautifulsoup4` - HTML 파싱
- `lxml` - 고속 파서 (선택)

### 3. Python 버전
- Python 3.7 이상 필요

## 사용 방법

### 기본 실행 (대화형 메뉴)

```bash
python preorder_tracker.py
```

메뉴에서 선택:
1. **Black Desert 게임 순위 검색** - 특정 게임의 플랫폼별 순위 조회
2. **전체 플랫폼 베스트셀러 수집** - 모든 플랫폼의 TOP 20 수집
3. **저장된 데이터 보기** - 이전에 수집한 데이터 조회
4. **리포트 생성** - 텍스트 파일로 리포트 생성

### 코드로 직접 사용

```python
from preorder_tracker import GameSalesScraper

# 스크래퍼 초기화
scraper = GameSalesScraper()

# 특정 게임 검색
results = scraper.search_game_ranking("Black Desert")
scraper.display_rankings(results)

# 전체 플랫폼 베스트셀러 수집
all_data = scraper.get_all_platform_rankings()
scraper.display_all_rankings(all_data)

# 리포트 생성
scraper.generate_report("my_report.txt")
```

### Steam만 수집

```python
scraper = GameSalesScraper()
steam_games = scraper.scrape_steam_bestsellers()

for game in steam_games[:10]:
    print(f"{game['rank']}. {game['title']}")
```

### PlayStation Store 수집

```python
scraper = GameSalesScraper()
ps_games = scraper.scrape_playstation_store(region="US")

for game in ps_games[:10]:
    print(f"{game['rank']}. {game['title']}")
```

## 출력 예시

### 게임 검색 결과
```
======================================================================
게임: Black Desert
검색 시간: 2026-01-06T14:30:45.123456
======================================================================

📊 Steam:
  ✓ 순위: 15위
  제목: Black Desert Online

📊 PlayStation:
  ✗ Top 20 차트에 없음

======================================================================
```

### 전체 플랫폼 베스트셀러
```
======================================================================
전세계 플랫폼별 베스트셀러 TOP 10
수집 시간: 2026-01-06T14:30:45.123456
======================================================================

🎮 Steam:
----------------------------------------------------------------------
   1위. Counter-Strike 2
   2위. Dota 2
   3위. Baldur's Gate 3
   4위. Cyberpunk 2077
   5위. Red Dead Redemption 2
   ...

🎮 PlayStation Store:
----------------------------------------------------------------------
   1위. Spider-Man 2
   2위. God of War Ragnarök
   3위. The Last of Us Part II
   ...

======================================================================
총 3개 플랫폼에서 데이터 수집 완료
======================================================================
```

## 데이터 구조

### sales_data.json
```json
{
  "game_name": "Black Desert",
  "platforms": {
    "Steam": {
      "rank": 15,
      "found": true,
      "details": {
        "title": "Black Desert Online",
        "platform": "Steam (PC)",
        "url": "https://store.steampowered.com/..."
      }
    }
  },
  "last_updated": "2026-01-06T14:30:45.123456",
  "history": [...]
}
```

## API 레퍼런스

### GameSalesScraper 클래스

#### 주요 메서드

**데이터 수집**
- `scrape_steam_bestsellers()` - Steam 베스트셀러 TOP 20 수집
- `scrape_playstation_store(region="US")` - PlayStation Store 인기 차트 수집
- `scrape_vgchartz_preorders()` - VGChartz 예약 판매 차트 수집

**게임 검색**
- `search_game_ranking(game_name)` - 특정 게임의 플랫폼별 순위 검색
- `get_all_platform_rankings()` - 모든 플랫폼 데이터 한번에 수집

**결과 출력**
- `display_rankings(results)` - 게임 순위 결과 콘솔 출력
- `display_all_rankings(data)` - 전체 순위 콘솔 출력
- `generate_report(filename)` - 텍스트 파일로 리포트 생성

**데이터 관리**
- `load_data()` - 저장된 데이터 로드
- `save_data()` - 데이터를 JSON 파일로 저장

## 주의사항

### 웹 스크래핑 에티켓
1. **Rate Limiting**: 요청 간 2초 대기 (코드에 구현됨)
2. **User-Agent**: 적절한 User-Agent 헤더 사용
3. **로봇 제외 표준**: 각 사이트의 robots.txt 준수
4. **과도한 요청 금지**: 서버에 부담을 주지 않도록 주의

### 법적 고려사항
- 이 도구는 **교육 및 개인 연구 목적**으로만 사용하세요
- 수집한 데이터의 **상업적 사용**은 각 사이트의 이용약관을 확인하세요
- 웹사이트 구조 변경 시 코드 수정이 필요할 수 있습니다

### 데이터 정확성
- 실시간 데이터는 **순위만 표시**하며 정확한 판매량은 제공하지 않습니다
- 각 플랫폼마다 순위 계산 방식이 다를 수 있습니다
- 일부 게임은 지역별로 차트에 표시되지 않을 수 있습니다

## 문제 해결

### 오류: "Connection timeout"
```bash
# 네트워크 연결 확인 또는 timeout 증가
# preorder_tracker.py에서 timeout=10을 timeout=30으로 수정
```

### 오류: "No module named 'bs4'"
```bash
pip install beautifulsoup4
```

### 웹사이트 구조 변경
웹사이트가 업데이트되어 스크래핑이 실패하는 경우:
1. 해당 웹사이트의 HTML 구조 확인
2. BeautifulSoup selector 수정
3. Issue에 버그 리포트 남기기

## 개발 로드맵

- [ ] Xbox Store 지원 추가
- [ ] Nintendo eShop 지원 추가
- [ ] Epic Games Store 지원
- [ ] 데이터 시각화 (그래프)
- [ ] 순위 변화 알림 기능
- [ ] 웹 대시보드 개발
- [ ] 자동 스케줄링 (cron job)

## 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능합니다.

## 면책 조항

이 프로젝트는 교육 목적으로 만들어졌습니다. 웹 스크래핑은 각 웹사이트의 이용약관과 robots.txt를 준수해야 합니다. 사용자는 본 도구의 사용에 따른 모든 책임을 집니다.

Black Desert는 Pearl Abyss의 상표이며, 이 프로젝트는 Pearl Abyss와 공식적인 관계가 없습니다.

## 연락처

프로젝트 링크: [https://github.com/yourusername/black-desert-sales-scraper](https://github.com/yourusername/black-desert-sales-scraper)

## 감사의 말

- Steam Store API
- PlayStation Network API
- VGChartz
- BeautifulSoup 개발팀
