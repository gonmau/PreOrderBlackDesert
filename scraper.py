import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime

# 설정
DISCORD_WEBHOOK_URL = os.environ['DISCORD_WEBHOOK']
APP_ID = "3321460" # 붉은사막 스팀 ID

# 국가별 정보 설정 (현지어 키워드 포함)
REGION_CONFIG = {
    "Global": {"cc": "us", "kw": "Crimson Desert"},
    "South Korea": {"cc": "kr", "kw": "붉은사막"},
    "Japan": {"cc": "jp", "kw": "紅の砂漠"},
    "Taiwan": {"cc": "tw", "kw": "赤色沙漠"},
    "Germany": {"cc": "de", "kw": "Crimson Desert"},
    "France": {"cc": "fr", "kw": "Crimson Desert"}
}

def get_steam_rank(country_code):
    """스팀 국가별 판매 순위 추출"""
    url = f"https://store.steampowered.com/search/?filter=topsellers&cc={country_code}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.find_all('a', {'data-ds-appid': True})
        for index, item in enumerate(items):
            if item['data-ds-appid'] == APP_ID:
                return f"{index + 1}위"
        return "100위권 밖"
    except:
        return "조회 실패"

def get_local_news(keyword):
    """구글 뉴스 RSS를 이용한 국가별 최신 뉴스 1건 추출"""
    url = f"https://news.google.com/rss/search?q={keyword}&hl=en&gl=US&ceid=US:en"
    # 실제로는 hl, gl 값을 키워드에 맞춰 변경하면 더 정확합니다.
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.content, 'xml')
        top_news = soup.find('item')
        if top_news:
            return f"[{top_news.title.text}]({top_news.link.text})"
        return "관련 뉴스 없음"
    except:
        return "뉴스 조회 실패"

def run_tracker():
    report_lines = [f"🛡️ **붉은사막 전 세계 지표 보고서** ({datetime.now().strftime('%Y-%m-%d')})\n"]
    
    for region, info in REGION_CONFIG.items():
        rank = get_steam_rank(info['cc'])
        news = get_local_news(info['kw'])
        report_lines.append(f"📍 **{region}**")
        report_lines.append(f"  - 순위: {rank}")
        report_lines.append(f"  - 최신소식: {news}\n")

    final_report = "\n".join(report_lines)
    requests.post(DISCORD_WEBHOOK_URL, json={"content": final_report})

if __name__ == "__main__":
    run_tracker()
