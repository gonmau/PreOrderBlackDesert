import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import matplotlib.pyplot as plt
import os
import requests
from datetime import datetime
import random

# 환경변수 로드
DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK')
DATA_FILE = 'rank_history.csv'

# 추적 대상 지역 및 언어 코드
REGIONS = {
    "미국": "en-us", "일본": "ja-jp", "홍콩": "en-hk", "영국": "en-gb", 
    "독일": "de-de", "프랑스": "fr-fr", "멕시코": "es-mx", "캐나다": "en-ca", 
    "대한민국": "ko-kr", "호주": "en-au", "브라질": "pt-br", "스페인": "es-es"
}

# 브라우저 위장용 User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

async def get_preorder_rank(browser, region_name, region_code):
    """
    각 국가별 PS Store에 접속하여 순위를 추출합니다.
    """
    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport={'width': 1920, 'height': 1080}
    )
    page = await context.new_page()
    
    # 인기 예약 주문 카테고리 URL
    url = f"https://store.playstation.com/{region_code}/category/601955f3-5290-449e-9907-f3160a2b918b/1"
    rank = 30  # 기본값 (찾지 못할 경우)
    
    try:
        # 1. 페이지 접속 및 초기 로딩 대기
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000) 

        # 2. 하위 순위 로드를 위한 자동 스크롤 (중요: 종토방 데이터처럼 보려면 필수)
        for _ in range(5):
            await page.mouse.wheel(0, 2500)
            await page.wait_for_timeout(1500)

        # 3. 상품명 추출 (최신 선택자 대응)
        product_selector = '[data-qa="product-name"], .psw-t-body.psw-c-t-1.psw-t-truncate-2'
        await page.wait_for_selector(product_selector, timeout=20000)
        products = await page.locator(product_selector).all_text_contents()
        
        print(f"🔎 {region_name}: 상품 {len(products)}개 로드됨")

        # 4. 키워드 매칭 (대소문자 구분 없이)
        keywords = ["crimson desert", "붉은사막", "紅の砂漠", "紅의 砂漠", "赤血沙漠", "crimson"]
        for i, name in enumerate(products):
            if any(kw.lower() in name.lower() for kw in keywords):
                rank = i + 1
                print(f"🎯 {region_name} 매칭 성공: {name} ({rank}위)")
                break
                
    except Exception as e:
        print(f"⚠️ {region_name} 처리 중 오류: {str(e)[:100]}")
        # 실패 시 로그 분석을 위해 스크린샷 저장
        await page.screenshot(path=f"error_{region_code}.png")
    finally:
        await context.close()
    return rank

async def main():
    async with async_playwright() as p:
        # 브라우저 실행 (봇 탐지 회피 옵션)
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        today = datetime.now().strftime('%Y-%m-%d')
        results = {'date': today}
        
        print(f"🚀 {today} 붉
