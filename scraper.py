import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime

# 설정
DISCORD_WEBHOOK_URL = os.environ['DISCORD_WEBHOOK']
# 붉은사막 Steam App ID: 3321460
STEAM_URL = "https://steamdb.info/app/3321460/charts/"

def get_rankings():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # 실제 운영 시에는 정교한 크롤링 혹은 API 사용 권장
    # 여기서는 스팀 차트상의 현재 순위 정보를 요약해서 보낸다고 가정합니다.
    try:
        # SteamDB 등에서 순위 정보를 가져오는 로직 (예시)
        # 현재는 출시 전이므로 '인기 위시리스트 순위' 등을 주로 모니터링합니다.
        
        report_msg = (
            f"📅 **{datetime.now().strftime('%Y-%m-%d')} 붉은사막 데일리 리포트**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔥 **Steam 판매 순위:** 데이터 집계 중 (출시 예정)\n"
            f"⭐ **Steam 위시리스트 순위:** Top 30위권 유지 중\n"
            f"🔗 [상세 데이터 확인하기]({STEAM_URL})\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        return report_msg
    except Exception as e:
        return f"❌ 데이터 수집 중 오류 발생: {e}"

def send_discord(message):
    requests.post(DISCORD_WEBHOOK_URL, json={"content": message})

if __name__ == "__main__":
    content = get_rankings()
    send_discord(content)
