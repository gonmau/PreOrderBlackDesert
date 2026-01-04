import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import matplotlib.pyplot as plt
import os
import requests
from datetime import datetime
import random

# 설정 정보
DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK')
DATA_FILE = 'rank_history.csv'
REGIONS = {
    "USA": "en-us", "Japan": "ja-jp", "HongKong": "en-hk", "UK": "en-gb", 
    "Germany": "de-de", "France": "fr-fr", "Mexico": "es-mx", "Canada": "en-ca", 
    "Korea": "ko-kr", "Australia": "en-au", "Brazil": "pt-br", "Spain": "es-es"
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

async def get_preorder_rank(browser, region_name, region_code):
    context = await browser.new_context(user_agent=USER_AGENT, viewport={'width': 1920, 'height': 1080})
    page = await context.new_page()
    url = f"https://store.playstation.com/{region_code}/category/601955f3-5290-449e-9907-f3160a2b918b/1"
    rank = 30
    
    try:
        # 페이지 접속
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000) 

        # 동적 로딩을 위한 스크롤
        for _ in range(5):
            await page.mouse.wheel(0, 3000)
            await page.wait_for_timeout(2000)

        # 상품명 추출
        product_selector = '[data-qa="product-name"], .psw-t-body.psw-c-t-1.psw-t-truncate-2'
        await page.wait_for_selector(product_selector, timeout=20000)
        products = await page.locator(product_selector).all_text_contents()
        
        print(f"[{region_name}] Found {len(products)} products")

        # 키워드 매칭
        keywords = ["crimson desert", "붉은사막", "紅の砂漠", "紅의 砂漠", "赤血沙漠", "crimson"]
        for i, name in enumerate(products):
            if any(kw.lower() in name.lower() for kw in keywords):
                rank = i + 1
                print(f"MATCH: {region_name} - {name} (Rank: {rank})")
                break
                
    except Exception as e:
        print(f"ERROR: {region_name} - {str(e)[:50]}")
    finally:
        await context.close()
    return rank

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        today = datetime.now().strftime('%Y-%m-%d')
        results = {'date': today}
        
        print(f"--- Start Tracking: {today} ---")

        for name, code in REGIONS.items():
            rank = await get_preorder_rank(browser, name, code)
            results[name] = rank
            await asyncio.sleep(random.uniform(2, 4))
            
        await browser.close()

        # 데이터 업데이트
        if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
            df = pd.read_csv(DATA_FILE)
        else:
            df = pd.DataFrame(columns=['date'] + list(REGIONS.keys()))
            
        df = df[df['date'] != today]
        df = pd.concat([df, pd.DataFrame([results])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)

        # 시각화
        plt.figure(figsize=(15, 8))
        plot_df = df.tail(30)
        for col in REGIONS.keys():
            if col in plot_df.columns:
                plt.plot(plot_df['date'], plot_df[col], marker='o', label=col)
        
        plt.gca().invert_yaxis()
        plt.grid(True, alpha=0.3)
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), prop={'size': 8})
        plt.title(f"Crimson Desert Global Rank ({today})")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('rank_trend.png')

        # 디스코드 전송
        if DISCORD_WEBHOOK:
            try:
                with open('rank_trend.png', 'rb') as f:
                    requests.post(DISCORD_WEBHOOK, data={'content': f"Ranking Update: {today}"}, files={'file': f})
            except Exception as e:
                print(f"Discord Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
