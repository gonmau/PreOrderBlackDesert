import requests
import os
from datetime import datetime

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK')

# 이미지 기반 국가 리스트 설정
REGION_CONFIG = {
    "미국": {"lang": "en", "country": "us"},
    "일본": {"lang": "ja", "country": "jp"},
    "홍콩": {"lang": "en", "country": "hk"},
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
    # PS 스토어 베스트셀러 카테고리 ID (글로벌 공통)
    category_id = "05a79ebd-771a-40ad-87d0-14fb847b019a"
    
    # GraphQL을 사용하는 최신 API 엔드포인트 또는 통합 쿼리 주소
    url = f"https://web-api.global.sonyentertainmentnetwork.com/query/v1/productRetrieve?size=100&lang={lang}&country={country}&category={category_id}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Origin': 'https://store.playstation.com',
        'Referer': f'https://store.playstation.com/{lang}-{country}/category/{category_id}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        # 만약 403 에러가 나면 여기서 예외 발생
        response.raise_for_status()
        
        data = response.json()
        products = data.get('data', {}).get('categoryRetrieve', {}).get('products', [])
        
        if not products:
            return "조회 결과 없음"

        for index, product in enumerate(products):
            name = product.get('name', '')
            # 예약 판매량 집계는 보통 상품명에 포함됨
            if any(kw in name for kw in ["Crimson Desert", "붉은사막", "紅の砂漠", "赤色沙漠"]):
                return f"🔥 **{index + 1}위**"
        
        return "100위권 밖"
    
    except requests.exceptions.HTTPError as e:
        return f"🚫 접근 차단 (Status: {e.response.status_code})"
    except Exception as e:
        return f"⚠️ 오류: {str(e)[:20]}..."

def run_tracker():
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    report = [f"🎮 **붉은사막 PS5 전 세계 예약판매 현황** ({now})\n"]
    
    for country_name, info in REGION_CONFIG.items():
        rank = get_ps_rank_api(info['lang'], info['country'])
        report.append(f"📍 {country_name.ljust(6)}: {rank}")
        # API 과부하 방지를 위한 미세한 지연
        import time
        time.sleep(0.5)
    
    final_msg = "\n".join(report)
    print(final_msg) # 로그 확인용
    
    if DISCORD_WEBHOOK_URL:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": final_msg})

if __name__ == "__main__":
    run_tracker()
