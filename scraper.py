import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import matplotlib.pyplot as plt
import os
import requests
from datetime import datetime

DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK')
DATA_FILE = 'rank_history.csv'

# 국가 설정 (영문 레이블로 변경하여 그래프 깨짐 방지)
REGIONS = {
    "USA": "en-us", "JPN": "ja-jp", "HKG": "en-hk", "IND": "en-in",
    "GBR": "en-gb", "DEU": "de-de", "FRA": "fr-fr", "MEX": "es-mx",
    "CAN": "en-ca", "KOR": "ko-kr", "AUS": "en-au", "BRA": "pt-br", "ESP": "es-es"
}

async def get_preorder_rank(page, region):
    # 'Coming Soon' 및 'Pre-Order'가 포함된 카테고리 URL로 접근
    url = f"https://store.playstation.com/{region}/category/601955f3-5290-449e-9907-f3160a2b918b/1"
    try:
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(5000)
        
        # 상품 명칭 리스트 추출
        names = await page.locator('[data-qa="product-name"]').all_text_contents()
        
        for i, name in enumerate(names):
            if any(kw in name.lower() for kw in ["crimson desert", "붉은사막", "紅の砂漠"]):
                return i + 1
        return 50 # 예약 목록에도 없으면 50위로 표시
    except:
        return 50

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        today = datetime.now().strftime('%Y-%m-%d')
        results = {'date': today}
        
        for name, code in REGIONS.items():
            rank = await get_preorder_rank(page, code)
            results[name] = rank
            print(f"{name}: {rank}위")
            
        await browser.close()
        
        # 데이터 누적 로직
        if os.path.exists(DATA_FILE):
            df = pd.read_csv(DATA_FILE)
        else:
            df = pd.DataFrame(columns=['date'] + list(REGIONS.keys()))
            
        df = pd.concat([df, pd.DataFrame([results])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        
        # 그래프 생성 (한글 깨짐 방지를 위해 영문 레이블 사용)
        plt.figure(figsize=(12, 6))
        for col in REGIONS.keys():
            plt.plot(df['date'], df[col], marker='o', label=col)
        plt.gca().invert_yaxis() # 1위가 위로 가도록
        plt.title("Crimson Desert PS5 Pre-Order Global Ranking Trend")
        plt.legend(loc='upper left', bbox_to_anchor=(1, 1), ncol=1)
        plt.grid(True, alpha=0.3)
        plt.savefig('rank_trend.png', bbox_inches='tight')
        
        # 디스코드 전송
        with open('rank_trend.png', 'rb') as f:
            requests.post(DISCORD_WEBHOOK, data={'content': f"📊 {today} Crimson Desert Ranking Report"}, files={'file': f})

if __name__ == "__main__":
    asyncio.run(main())
