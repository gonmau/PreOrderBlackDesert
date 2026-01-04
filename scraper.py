import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import matplotlib.pyplot as plt
import os
import requests
from datetime import datetime
import random

# 환경변수 및 설정
DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK')
DATA_FILE = 'rank_history.csv'
REGIONS = {
    "USA": "en-us", "Japan": "ja-jp", "HongKong": "en-hk", "UK": "en-gb", 
    "Germany": "de-de", "France": "fr-fr", "Mexico": "es-mx", "Canada": "en-ca", 
    "Korea": "ko-kr", "Australia": "en-au", "Brazil": "pt-br", "Spain": "es-es"
}

async def get_preorder_rank(browser, region_name, region_code):
    # 실제 크롬 브라우저와 동일한 설정 주입
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={'width': 1920, 'height': 1080},
        extra_http_headers={"Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"}
    )
    
    page = await context.new_page()
    
    # 봇 감지 우회용 스크립트 실행
    await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    url = f"https://store.playstation.com/{region_code}/category/601955f3-5290-449e-9907-f3160a2b918b/1"
    rank = 30
    
    try:
        # 페이지 접속 및 최대 90초 대기
        await page.goto(url, wait_until="networkidle", timeout=90000)
        await page.wait_for_timeout(5000)

        # 상품 목록 로드를 위한 스크롤
        for _ in range(4):
            await page.mouse.wheel(0, 2000)
            await page.wait_for_timeout(2000)

        # 여러 선택자를 통해 상품명 추출
        selectors = ['[data-qa="product-name"]', '.psw-t-body.psw-c-t-1.psw-t-truncate-2']
        products = []
        for selector in selectors:
            elements = await page.locator(selector).all_text_contents()
            if elements:
                products = elements
                break

        print(f"[{region_name}] Found {len(products)} products")

        # 상품이 0개인 경우 디버그용 스크린샷 저장
        if len(products) == 0:
            await page.screenshot(path=f"zero_{region_code}.png")

        keywords = ["crimson desert", "붉은사막", "紅の砂漠", "紅의 砂漠", "赤血沙漠", "crimson"]
        for i, name in enumerate(products):
            if any(kw.lower() in name.lower() for kw in keywords):
                rank = i + 1
                print(f"MATCH: {region_name} - {name} (Rank: {rank})")
                break
                
    except Exception as e:
        print(f"ERROR: {region_name} - {str(e)[:50]}")
        await page.screenshot(path=f"error_{region_code}.png")
    finally:
        await context.close()
    return rank

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        today = datetime.now().strftime('%Y-%m-%d')
        results = {'date': today}
        
        print(f"--- Tracking Started: {today} ---")

        for name, code in REGIONS.items():
            rank = await get_preorder_rank(browser, name, code)
            results[name] = rank
            await asyncio.sleep(random.uniform(5, 10)) # 차단 방지를 위한 긴 대기
            
        await browser.close()

        # 데이터 저장
        df = pd.read_csv(DATA_FILE) if os.path.exists(DATA_FILE) else pd.DataFrame(columns=['date'] + list(REGIONS.keys()))
        df = df[df['date'] != today]
        df = pd.concat([df, pd.DataFrame([results])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)

        # 그래프 생성
        plt.figure(figsize=(15, 8))
        for col in REGIONS.keys():
            if col in df.columns:
                plt.plot(df['date'], df[col], marker='o', label=col)
        plt.gca().invert_yaxis()
        plt.grid(True, alpha=0.3)
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        plt.title(f"Crimson Desert Global Rank ({today})")
        plt.tight_layout()
        plt.savefig('rank_trend.png')

        # 디스코드 전송 (차단 시 스크린샷 포함)
        if DISCORD_WEBHOOK:
            files = {'file': open('rank_trend.png', 'rb')}
            if results["Korea"] == 30 and os.path.exists("zero_ko-kr.png"):
                files['debug'] = open('zero_ko-kr.png', 'rb')
            requests.post(DISCORD_WEBHOOK, data={'content': f"📊 Update: {today}"}, files=files)

if __name__ == "__main__":
    asyncio.run(main())
