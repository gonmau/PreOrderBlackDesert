import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import matplotlib.pyplot as plt
import os
import requests
from datetime import datetime

DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK')
DATA_FILE = 'rank_history.csv'
REGIONS = {
    "미국": "en-us", "일본": "ja-jp", "홍콩": "en-hk", "영국": "en-gb", 
    "독일": "de-de", "프랑스": "fr-fr", "멕시코": "es-mx", "캐나다": "en-ca", 
    "대한민국": "ko-kr", "호주": "en-au", "브라질": "pt-br", "스페인": "es-es"
}

async def get_preorder_rank(page, region):
    url = f"https://store.playstation.com/{region}/category/601955f3-5290-449e-9907-f3160a2b918b/1"
    try:
        # 페이지 이동 후 핵심 요소가 로드될 때까지 대기
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        # 상품명이 담긴 그리드가 보일 때까지 대기 (네이버 유저 수치 재현의 핵심)
        await page.wait_for_selector('[data-qa^="product-grid"]', timeout=15000)
        await page.wait_for_timeout(2000) # 안정적인 로딩을 위한 추가 2초
        
        names = await page.locator('[data-qa="product-name"]').all_text_contents()
        
        for i, name in enumerate(names):
            if any(kw in name.lower() for kw in ["crimson desert", "붉은사막", "紅の砂漠", "赤血沙漠"]):
                return i + 1
        return 30
    except Exception as e:
        print(f"⚠️ {region} 로딩 지연: {e}")
        return 30

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()
        # 이미지 로딩은 여전히 차단하여 속도 유지
        await page.route("**/*.{png,jpg,jpeg,svg}", lambda route: route.abort())

        today = datetime.now().strftime('%Y-%m-%d')
        results = {'date': today}
        
        for name, code in REGIONS.items():
            rank = await get_exact_rank(page, code) # 위에서 정의한 함수 호출
            results[name] = rank
            print(f"📍 {name}: {rank}위")
            
        await browser.close()

        # --- 파일 에러 방지 로직 (EmptyDataError 해결) ---
        if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
            try:
                df = pd.read_csv(DATA_FILE)
            except Exception:
                df = pd.DataFrame(columns=['date'] + list(REGIONS.keys()))
        else:
            df = pd.DataFrame(columns=['date'] + list(REGIONS.keys()))
            
        df = pd.concat([df, pd.DataFrame([results])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        
        # 그래프 생성
        plt.figure(figsize=(12, 6))
        for col in REGIONS.keys():
            plt.plot(df['date'], df[col], marker='o', label=col)
        plt.gca().invert_yaxis()
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), ncol=1)
        plt.grid(True, alpha=0.2)
        plt.savefig('rank_trend.png', bbox_inches='tight')
        
        if DISCORD_WEBHOOK:
            with open('rank_trend.png', 'rb') as f:
                requests.post(DISCORD_WEBHOOK, data={'content': f"📈 {today} 붉은사막 순위 리포트"}, files={'file': f})

if __name__ == "__main__":
    asyncio.run(main())
