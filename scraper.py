import requests
from bs4 import BeautifulSoup
import os
import time
from datetime import datetime

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK')

# 각국의 PS 스토어 베스트셀러 페이지 경로
REGION_CONFIG = {
    "미국": "en-us", "일본": "ja-jp", "홍콩": "en-hk", "인도": "en-in",
    "영국": "en-gb", "독일": "de-de", "프랑스": "fr-fr", "멕시코": "es-mx",
    "캐나다": "en-ca", "한국": "ko-kr", "호주": "en-au", "브라질": "pt-br", "스페인": "es-es"
}

def get_ps_rank(region):
    # 공식 스토어의 베스트셀러 카테고리 URL
    url = f"https://store.playstation.com/{region}/category/05a79ebd-771a-40ad-87d0-14fb847b019a/1"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9,ko;q=0.8',
        'Referer': 'https://www.google.com/'
    }

    try:
        # 1. 외부 트래커 사이트(PSPrices 등)를 통한 우회 시도 (더 안정적)
        # 여기서는 설명을 위해 공식 사이트 구조를 타겟하되, 세션을 유지합니다.
        session = requests.Session()
        res = session.get(url, headers=headers, timeout=15)
        
        if res.status_code != 200:
            return f"접근제한({res.status_code})"
            
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # PS 스토어 내 상품 이름 태그 탐색 (구조는 주기적으로 변동됨)
        # 'Crimson Desert'나 '붉은사막' 키워드를 찾습니다.
        grid_items = soup.find_all('span', {'data-qa': 'product-name'})
        
        if not grid_items:
            # 다른 방식: 스크립트 태그 내 JSON 데이터 파싱 (고급)
            return "목록 분석중"

        for idx, item in enumerate(grid_items):
            name = item.get_text().lower()
            if 'crimson' in name or 'desert' in name or '붉은사막' in name:
                return f"**{idx + 1}위**"
                
        return "25위권 밖"
    except Exception as e:
        return "연결 지연"

def run_tracker():
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    report = [f"📊 **붉은사막 글로벌 판매 순위 집계** ({now})", "-"*30]
    
    for country, region in REGION_CONFIG.items():
        rank = get_ps_rank(region)
        report.append(f"{country.ljust(6)} : {rank}")
        time.sleep(1.5) # 차단 방지를 위한 필수 지연
    
    final_msg = "\n".join(report)
    print(final_msg)
    
    if DISCORD_WEBHOOK_URL:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": final_msg})

if __name__ == "__main__":
    run_tracker()
