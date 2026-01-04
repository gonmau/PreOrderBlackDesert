import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime

# 설정
DISCORD_WEBHOOK_URL = os.environ['DISCORD_WEBHOOK']
# 붉은사막 PS Store ID (지역마다 다를 수 있으나, 일반적으로 Title ID 기반으로 검색)
PS_STORE_QUERY = "Crimson Desert"

# 이미지에 제공된 국가 리스트 및 PS Store 지역 코드 설정
REGION_CONFIG = {
    "미국": {"code": "en-us", "kw": "Crimson Desert"},
    "일본": {"code": "ja-jp", "kw": "紅の砂漠"},
    "홍콩": {"code": "zh-hans-hk", "kw": "赤色沙漠"},
    "인도": {"code": "en-in", "kw": "Crimson Desert"},
    "영국": {"code": "en-gb", "kw": "Crimson Desert"},
    "독일": {"code": "de-de", "kw": "Crimson Desert"},
    "프랑스": {"code": "fr-fr", "kw": "Crimson Desert"},
    "멕시코": {"code": "es-mx", "kw": "Crimson Desert"},
    "캐나다": {"code": "en-ca", "kw": "Crimson Desert"},
    "한국": {"code": "ko-kr", "kw": "붉은사막"},
    "호주": {"code": "en-au", "kw": "Crimson Desert"},
    "브라질": {"code": "pt-br", "kw": "Crimson Desert"},
    "스페인": {"code": "es-es", "kw": "Crimson Desert"}
}

def get_ps_rank(region_code, keyword):
    """국가별 PS Store 예약 판매 순위(Best Sellers) 추출"""
    # PS Store의 판매량 순위 페이지 타겟 (예시 URL 구조)
    url = f"https://store.playstation.com/{region_code}/category/05a79ebd-771a-40ad-87d0-14fb847b019a/1"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 상품 리스트 내에서 키워드(붉은사막) 포함 여부 확인 및 순위 계산
        # PS 스토어의 HTML 구조는 동적 로딩이 많으므로 실제 운영 시에는 API 엔드포인트 분석이 필요할 수 있습니다.
        items = soup.find_all('span', {'data-qa': 'product-name'})
        for index, item in enumerate(items):
            if keyword.lower() in item.text.lower():
                return f"{index + 1}위"
        return "순위권 밖"
    except:
        return "조회 불가"

def run_ps_tracker():
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    report_lines = [f"🎮 **붉은사막 PS5 전 세계 예약판매 순위** ({now})\n"]
    
    for country, info in REGION_CONFIG.items():
        rank = get_ps_rank(info['code'], info['kw'])
        report_lines.append(f"📍 **{country}**: {rank}")

    final_report = "\n".join(report_lines)
    
    # 디스크도 전송
    requests.post(DISCORD_WEBHOOK_URL, json={"content": final_report})

if __name__ == "__main__":
    run_ps_tracker()
