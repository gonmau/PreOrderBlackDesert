import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import matplotlib.pyplot as plt
import os
import requests
from datetime import datetime
import random

# 환경변수 설정
DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK')
DATA_FILE = 'rank_history.csv'
REGIONS = {
    "미국": "en-us", "일본": "ja-jp", "홍콩": "en-hk", "영국": "en-gb", 
    "독일": "de-de", "프랑스": "fr-fr", "멕시코": "es-mx", "캐나다": "en-ca", 
    "대한민국": "ko-kr", "호주": "en-au", "브라질": "pt-br", "스페인": "es-es"
}

# 브라우저 핑거프린트 위장
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

async def get_preorder_rank(browser, region_name, region_code):
    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport={'width': 1920, 'height': 1080}
    )
    page = await context.new_page()
    url = f"https://store.playstation.com/{region_code}/category/601955f3-5290-449e-9907-f3160a2b918b/1"
    rank = 30 
    
    try:
        # 페이지 로딩 대기 시간 최적화
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000) 

        # 종토방 데이터처럼 하위 순위까지 불러오기 위한 강제 스크롤
        for _ in range(5):
            await page.mouse.wheel(0, 3000)
            await page.wait_for_timeout(2000)

        # 상품명 선택자 (PS Store 최신 버전 대응)
        product_selector = '[data-qa="product-name"], .psw-t-body.psw-c-t-1.psw-t-truncate-2'
        await page.wait_for_selector(product_selector, timeout=20000)
        products = await page.locator(product_selector).all_text_contents()
        
        print(f"[{region_name}] Total products loaded: {len(products)}")

        # 붉은사막 키워드 매칭
        keywords = ["crimson desert", "붉은사막", "紅의 砂漠", "紅의 砂漠", "赤血沙漠", "crimson"]
        for i, name in enumerate(products):
            if any(kw.lower() in name.lower() for kw in keywords):
                rank = i + 1
                print(f"FOUND: {region_name} - {name} (Rank: {rank})")
                break
                
    except Exception as e:
        print(f"ERROR: {region_name} failed - {str(e)[:50]}")
        await page.screenshot(path=f"debug_{region_code}.png")
    finally:
        await context.close()
    return rank

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        today = datetime.now().strftime('%Y-%m-%d')
        results = {'date': today}
        
        print(f"--- Tracker Started: {today} ---")

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

        # 시각화 (한글 깨짐 방지를 위해 타이틀은 영어 권장)
        plt.figure(figsize=(15, 8))
        plot_df = df.tail(30)
        for col in REGIONS.keys():
            if col in plot_df.columns:
                plt.plot(plot_df['date'], plot_df[col], marker='o', label=col)
        
        plt.gca().invert_yaxis()
        plt.grid(True, alpha=0.3)
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), prop={'size': 8})
        plt.title(f"Crimson Desert Global Rank Trend ({today})")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('rank_trend.png')

        # 디스코드 알림
        if DISCORD_WEBHOOK:
            try:
                with open('rank_trend.png', 'rb') as f:
                    requests.post(DISCORD_WEBHOOK, 
                        data={'content': f"📊 **{today} Crimson Desert Rank Update**"}, 
                        files={'file': f}
                    )
            except Exception as e:
                print(f"Discord Notify Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
