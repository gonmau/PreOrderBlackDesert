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
        # 봇 감지 회피를 위한 대기 및 실제 페이지 이동
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000)
        
        # 제품 이름 목록 추출
        names = await page.locator('[data-qa="product-name"]').all_text_contents()
        
        for i, name in enumerate(names):
            if any(kw in name.lower() for kw in ["crimson desert", "붉은사막", "紅の砂漠"]):
                return i + 1
        return 50
    except Exception as e:
        print(f"⚠️ {region} 수집 실패: {e}")
        return 50

async def main():
    async with async_playwright() as p:
        # 실제 브라우저와 유사한 환경 설정 (User-Agent 추가)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        today = datetime.now().strftime('%Y-%m-%d')
        results = {'date': today}
        
        for name, code in REGIONS.items():
            rank = await get_exact_rank(page, code)
            results[name] = rank
            print(f"📍 {name}: {rank}위")
            
        await browser.close()

        # --- 파일 읽기 및 데이터 누적 (오류 방지 로직) ---
        if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
            try:
                df = pd.read_csv(DATA_FILE)
            except pd.errors.EmptyDataError:
                df = pd.DataFrame(columns=['date'] + list(REGIONS.keys()))
        else:
            df = pd.DataFrame(columns=['date'] + list(REGIONS.keys()))
            
        df = pd.concat([df, pd.DataFrame([results])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        
        # --- 그래프 생성 및 전송 ---
        plt.figure(figsize=(12, 6))
        for col in REGIONS.keys():
            plt.plot(df['date'], df[col], marker='o', label=col)
        plt.gca().invert_yaxis()
        plt.title("Crimson Desert PS5 Global Ranking Trend")
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        plt.grid(True, alpha=0.2)
        plt.savefig('rank_trend.png', bbox_inches='tight')
        
        if DISCORD_WEBHOOK:
            with open('rank_trend.png', 'rb') as f:
                requests.post(DISCORD_WEBHOOK, data={'content': f"📈 {today} 데이터 업데이트 완료"}, files={'file': f})

if __name__ == "__main__":
    asyncio.run(main())
