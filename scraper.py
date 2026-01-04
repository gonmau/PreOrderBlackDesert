import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import matplotlib.pyplot as plt
import os
import requests
from datetime import datetime

DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK')
DATA_FILE = 'rank_history.csv'

# 국가 설정
REGIONS = {
    "USA": "en-us", "JPN": "ja-jp", "HKG": "en-hk", "IND": "en-in",
    "GBR": "en-gb", "DEU": "de-de", "FRA": "fr-fr", "MEX": "es-mx",
    "CAN": "en-ca", "KOR": "ko-kr", "AUS": "en-au", "BRA": "pt-br", "ESP": "es-es"
}

async def get_search_rank(page, region, keyword):
    # 각국 스토어의 검색 결과 페이지로 직접 이동
    url = f"https://store.playstation.com/{region}/search/{keyword}"
    try:
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(5000) # 검색 결과 로딩 대기
        
        # 검색 결과 리스트의 상품명들 수집
        names = await page.locator('[data-qa="product-name"]').all_text_contents()
        
        for i, name in enumerate(names):
            # 붉은사막 키워드가 포함된 가장 높은 순위 반환
            if any(kw in name.lower() for kw in ["crimson desert", "붉은사막", "紅の砂漠"]):
                return i + 1
        return 100 # 검색 결과에도 없으면 100위
    except:
        return 100

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        today = datetime.now().strftime('%Y-%m-%d')
        results = {'date': today}
        
        for name, code in REGIONS.items():
            # 각국 언어에 맞는 키워드로 검색 시도
            search_kw = "Crimson Desert"
            if name == "KOR": search_kw = "붉은사막"
            elif name == "JPN": search_kw = "紅の砂漠"
            
            rank = await get_search_rank(page, code, search_kw)
            results[name] = rank
            print(f"{name}: {rank}위")
            
        await browser.close()
        
        # --- 데이터 저장 및 그래프 생성 로직 (이전과 동일) ---
        if os.path.exists(DATA_FILE):
            df = pd.read_csv(DATA_FILE)
        else:
            df = pd.DataFrame(columns=['date'] + list(REGIONS.keys()))
            
        df = pd.concat([df, pd.DataFrame([results])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        
        plt.figure(figsize=(12, 6))
        for col in REGIONS.keys():
            plt.plot(df['date'], df[col], marker='o', label=col)
        plt.gca().invert_yaxis()
        plt.title("Crimson Desert Global Search Ranking")
        plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
        plt.grid(True, alpha=0.3)
        plt.savefig('rank_trend.png', bbox_inches='tight')
        
        with open('rank_trend.png', 'rb') as f:
            requests.post(DISCORD_WEBHOOK, data={'content': f"📊 {today} Crimson Desert Report"}, files={'file': f})

if __name__ == "__main__":
    asyncio.run(main())
