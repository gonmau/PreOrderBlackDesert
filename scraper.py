import requests
import os
from datetime import datetime

DISCORD_WEBHOOK_URL = os.environ['DISCORD_WEBHOOK']

# 붉은사막 정보 (실제 출시/예약판매 시점에 할당되는 ID 확인 필요)
# 현재는 검색 키워드 기반으로 순위를 대조합니다.
TARGET_GAME_NAME = "Crimson Desert" 

REGION_CONFIG = {
    "미국": {"lang": "en", "country": "us"},
    "일본": {"lang": "ja", "country": "jp"},
    "홍콩": {"lang": "en", "country": "hk"}, # 또는 zh-hant
    "인도": {"lang": "en", "country": "in"},
    "영국": {"lang": "en", "country": "gb"},
    "독일": {"lang": "de", "country": "de"},
    "프랑스": {"lang": "fr", "country": "fr"},
    "멕시코": {"lang": "es", "country": "mx"},
    "캐나다": {"lang": "en", "country": "ca"},
    "한국": {"lang": "ko", "country": "kr"},
    "호주": {"lang": "en", "country": "au"},
    "브라질": {"lang": "pt", "country": "br"},
    "스페인": {"lang": "es", "country": "es"}
}

def get_ps_rank_api(lang, country):
    # PS 스토어 베스트셀러 카테고리 ID (변동될 수 있음)
    category_id = "05a79ebd-771a-40ad-87d0-14fb847b019a"
    url = f"https://web-api.global.sonyentertainmentnetwork.com/query/v1/productRetrieve?size=100&age=99&lang={lang}&country={country}&category={category_id}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Origin': 'https://store.playstation.com'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        # 상품 리스트 순회하여 이름 매칭
        products = data.get('data', {}).get('categoryRetrieve', {}).get('products', [])
        
        for index, product in enumerate(products):
            name = product.get('name', '')
            if "Crimson Desert" in name or "붉은사막" in name or "紅の砂漠" in name:
                return f"🔥 **{index + 1}위**"
        
        return "100위권 밖"
    except:
        return "⚠️ 데이터 접근 오류"

def run_tracker():
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    report = [f"🎮 **붉은사막 전 세계 PS5 예약판매 현황** ({now})\n"]
    
    for country_name, info in REGION_CONFIG.items():
        rank = get_ps_rank_api(info['lang'], info['country'])
        report.append(f"📍 {country_name.ljust(6)}: {rank}")
    
    # 디스크도 전송 (메시지가 너무 길면 잘릴 수 있으니 한 번에 전송)
    requests.post(DISCORD_WEBHOOK_URL, json={"content": "\n".join(report)})

if __name__ == "__main__":
    run_tracker()
