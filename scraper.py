import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import matplotlib.pyplot as plt
import os
import requests
from datetime import datetime

DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK')
DATA_FILE = 'rank_history.csv'
# 네이버 이미지에 있는 국가 순서와 명칭 동일화
REGIONS = {
    "미국": "en-us", "일본": "ja-jp", "홍콩": "en-hk", "영국": "en-gb", 
    "독일": "de-de", "프랑스": "fr-fr", "멕시코": "es-mx", "캐나다": "en-ca", 
    "대한민국": "ko-kr", "호주": "en-au", "브라질": "pt-br", "스페인": "es-es"
}

async def get_preorder_rank(page, region):
    # 프리오더(예약 주문) 카테고리 직속 URL
    url = f"https://store.playstation.com/{region}/category/601955f3-5290-449e-9907-f3160a2b918b/1"
    try:
        # 빠른 로딩을 위해 domcontentloaded 사용
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        # 상품명이 나타날 때까지만 잠시 대기
        await page.wait_for_selector('[data-qa="product-name"]', timeout=10000)
        
        # 첫 페이지의 모든 상품명 수집
        names = await page.locator('[data-qa="product-name"]').all_text_contents()
        
        for i, name in enumerate(names):
            if any(kw in name.lower() for kw in ["crimson desert", "붉은사막", "紅の砂漠"]):
                return i + 1
        return 30 # 첫 페이지(24위) 안에 없으면 30위로 표시
    except:
        return 30

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 일반 브라우저처럼 보이게 설정
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()
        # 리소스 절약을 위해 이미지 로딩 차단
        await page.route("**/*.{png,jpg,jpeg,svg}", lambda route: route.abort())

        today = datetime.now().strftime('%m/%d')
        results = {'date': today}
        
        for name, code in REGIONS.items():
            rank = await get_preorder_rank(page, code)
            results[name] = rank
            print(f"{name}: {rank}위")
            
        await browser.close()

        # 데이터 누적 및 그래프 (이미지 속 표와 같은 형태 유지)
        df = pd.read_csv(DATA_FILE) if os.path.exists(DATA_FILE) else pd.DataFrame()
        df = pd.concat([df, pd.DataFrame([results])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        
        # 그래프 생성 (네이버 스타일)
        plt.figure(figsize=(10, 5))
        for col in REGIONS.keys():
            plt.plot(df['date'], df[col], marker='o', label=col)
        plt.gca().invert_yaxis()
        plt.grid(True, axis='y', alpha=0.3)
        plt.savefig('rank_trend.png', bbox_inches='tight')
        
        if DISCORD_WEBHOOK:
            msg = f"🎮 **붉은사막 프리오더 순위 ({datetime.now().strftime('%Y-%m-%d')})**"
            with open('rank_trend.png', 'rb') as f:
                requests.post(DISCORD_WEBHOOK, data={'content': msg}, files={'file': f})

if __name__ == "__main__":
    asyncio.run(main())
