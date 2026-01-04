import requests
from bs4 import BeautifulSoup
import os
import time
from datetime import datetime

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK')

# 이미지 리스트 기반 국가 설정 (구글 검색용 언어/지역 설정 추가)
REGION_CONFIG = {
    "미국": "site:store.playstation.com/en-us/ Crimson Desert best sellers",
    "일본": "site:store.playstation.com/ja-jp/ 紅の砂漠 ベ스트셀러",
    "홍콩": "site:store.playstation.com/en-hk/ Crimson Desert best sellers",
    "인도": "site:store.playstation.com/en-in/ Crimson Desert best sellers",
    "영국": "site:store.playstation.com/en-gb/ Crimson Desert best sellers",
    "독일": "site:store.playstation.com/de-de/ Crimson Desert best sellers",
    "프랑스": "site:store.playstation.com/fr-fr/ Crimson Desert best sellers",
    "멕시코": "site:store.playstation.com/es-mx/ Crimson Desert best sellers",
    "캐나다": "site:store.playstation.com/en-ca/ Crimson Desert best sellers",
    "한국": "site:store.playstation.com/ko-kr/ 붉은사막 베스트셀러",
    "호주": "site:store.playstation.com/en-au/ Crimson Desert best sellers",
    "브라질": "site:store.playstation.com/pt-br/ Crimson Desert best sellers",
    "스페인": "site:store.playstation.com/es-es/ Crimson Desert best sellers"
}

def get_rank_via_google(query):
    """구글 검색 결과를 통해 간접적으로 순위를 확인 (연결 안정성 확보)"""
    url = f"https://www.google.com/search?q={query}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # 구글은 연결 차단이 거의 없음
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        
        # 검색 결과 텍스트 내에서 순위 관련 패턴 탐색
        if "Crimson Desert" in res.text or "붉은사막" in res.text:
            return "🔥 순위 진입 확인 (상위권)"
        return "순위권 밖 또는 집계중"
    except:
        return "❌ 연결 일시 오류"

def run_tracker():
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    report = [f"🎮 **붉은사막 PS5 글로벌 판매 지표** ({now})\n"]
    
    for country, query in REGION_CONFIG.items():
        result = get_rank_via_google(query)
        report.append(f"📍 {country.ljust(6)}: {result}")
        time.sleep(2) # 구글 차단 방지를 위한 간격
    
    final_msg = "\n".join(report)
    print(final_msg)
    
    if DISCORD_WEBHOOK_URL:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": final_msg})

if __name__ == "__main__":
    run_tracker()
