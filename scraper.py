import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import time

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK')

# 이미지에 있는 13개 국가 설정
COUNTRIES = {
    "미국": "us", "일본": "jp", "홍콩": "hk", "인도": "in", "영국": "gb", 
    "독일": "de", "프랑스": "fr", "멕시코": "mx", "캐나다": "ca", 
    "한국": "kr", "호주": "au", "브라질": "br", "스페인": "es"
}

def get_rank_from_tracker(country_code):
    # 각 국가별 베스트셀러 순위를 제공하는 외부 트래커 혹은 공식 API 서브 경로
    # 예시: PS 스토어의 공개된 JSON API 엔드포인트 활용
    url = f"https://api.psnprofiles.com/sales/rankings?region={country_code}" 
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        # 세션을 사용하여 연결 안정성 확보
        with requests.Session() as s:
            res = s.get(url, headers=headers, timeout=20)
            if res.status_code == 200:
                # 데이터 파싱 로직 (해당 사이트 구조에 맞춤)
                # 실제 데이터에서 'Crimson Desert' 또는 '붉은사막' 인덱스 찾기
                data = res.json() 
                for item in data['rankings']:
                    if "Crimson Desert" in item['title'] or "붉은사막" in item['title']:
                        return f"**{item['rank']}위**"
                return "25위권 밖"
            else:
                return f"연결실패({res.status_code})"
    except Exception as e:
        return "데이터 점검중"

def run_tracker():
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    report = [f"📊 **붉은사막 글로벌 판매 순위 집계** ({now})"]
    report.append("-" * 30)
    
    for name, code in COUNTRIES.items():
        rank = get_rank_from_tracker(code)
        report.append(f"{name.ljust(6)} : {rank}")
        time.sleep(1) # IP 차단 방지

    final_msg = "\n".join(report)
    if DISCORD_WEBHOOK_URL:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": final_msg})

if __name__ == "__main__":
    run_tracker()
