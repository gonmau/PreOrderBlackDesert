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
    "USA": "en-us", "JPN": "ja-jp", "KOR": "ko-kr", "HKG": "en-hk",
    "GBR": "en-gb", "DEU": "de-de", "FRA": "fr-fr", "ESP": "es-es"
}

async def get_exact_rank(page, region):
    category_id = "601955f3-5290-449e-9907-f3160a2b918b"
    url = f"https://store.playstation.com/{region}/category/{category_id}/1"
    
    try:
        # 핵심 변경: 'commit' 즉시 대기 종료 (네트워크 끝까지 안 기다림)
        # 15초 안에 페이지 기본 구조만 뜨면 성공으로 간주
        await page.goto(url, wait_until="commit", timeout=15000)
        
        # 상품명이 담긴 태그가 나타날 때까지만 대기 (최대 10초)
        await page.wait_for_selector('[data-qa="product-name"]', timeout=10000)
        
        names = await page.locator('[data-qa="product-name"]').all_text_contents()
        
        for i, name in enumerate(names):
            if any(kw in name.lower() for kw in ["crimson desert", "붉은사막", "紅の砂漠"]):
                return i + 1
        return 50
    except Exception as e:
        print(f"⚠️ {region} 빠른 스캔 실패: {e}")
        return 50

async def main():
    async with async_playwright() as p:
        # 가상 브라우저임을 숨기는 스텔스 설정
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()
        
        # 불필요한 이미지/폰트 로딩 차단 (속도 대폭 향상)
        await page.route("**/*.{png,jpg,jpeg,svg,woff,ttf}", lambda route: route.abort())
        
        today = datetime.now().strftime('%Y-%m-%d')
        results = {'date': today}
        
        for name, code in REGIONS.items():
            print(f"🚀 {name} 데이터 찾는 중...")
            rank = await get_exact_rank(page, code)
            results[name] = rank
            print(f"📍 {name}: {rank}위")
            
        await browser.close()

        # 데이터 저장 및 그래프 생성 로직
        if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
            df = pd.read_csv(DATA_FILE)
        else:
            df = pd.DataFrame(columns=['date'] + list(REGIONS.keys()))
            
        df = pd.concat([df, pd.DataFrame([results])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        
        plt.figure(figsize=(10, 5))
        for col in REGIONS.keys():
            plt.plot(df['date'], df[col], marker='o', label=col)
        plt.gca().invert_yaxis()
        plt.savefig('rank_trend.png', bbox_inches='tight')
        
        if DISCORD_WEBHOOK:
            with open('rank_trend.png', 'rb') as f:
                requests.post(DISCORD_WEBHOOK, data={'content': f"📈 {today} 업데이트 완료"}, files={'file': f})

if __name__ == "__main__":
    asyncio.run(main())
