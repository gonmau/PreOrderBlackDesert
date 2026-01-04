import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import matplotlib.pyplot as plt
import os
import requests
from datetime import datetime
import random

DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK')
DATA_FILE = 'rank_history.csv'
REGIONS = {
    "USA": "en-us", "Japan": "ja-jp", "HongKong": "en-hk", "UK": "en-gb", 
    "Germany": "de-de", "France": "fr-fr", "Mexico": "es-mx", "Canada": "en-ca", 
    "Korea": "ko-kr", "Australia": "en-au", "Brazil": "pt-br", "Spain": "es-es"
}

async def get_preorder_rank(browser, region_name, region_code):
    # 실제 크롬 브라우저와 구분할 수 없도록 상세 설정
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={'width': 1920, 'height': 1080},
        extra_http_headers={
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Referer": "https://www.google.com/"
        }
    )
    
    page = await context.new_page()
    
    # [핵심] 봇 탐지 우회 스크립트 (navigator.webdriver 감추기 등)
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        window.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR', 'ko', 'en-US', 'en']});
    """)

    url = f"https://store.playstation.com/{region_code}/category/601955f3-5290-449e-9907-f3160a2b918b/1"
    rank = 30
    
    try:
        # 응답 대기 시간을 늘리고 네트워크 유휴 상태까지 대기
        response = await page.goto(url, wait_until="networkidle", timeout=90000)
        
        # 만약 페이지 로딩이 차단되었다면 (403 Forbidden 등)
        if response.status != 200:
            print(f"⚠️ {region_name} 차단됨 (Status: {response.status})")
            await page.screenshot(path=f"blocked_{region_code}.png")
            return 30

        # 자연스러운 스크롤 (사람처럼 보이게 함)
        for _ in range(3):
            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(1.5)

        # 상품명 추출 (다양한 선택자 시도)
        selectors = ['[data-qa="product-name"]', '.psw-product-tile__details span', '.psw-t-body']
        products = []
        for sel in selectors:
            products = await page.locator(sel).all_text_contents()
            if len(products) > 5: break

        print(f"[{region_name}] 로드된 상품 수: {len(products)}")

        # 차단 확인용 스크린샷 (0개일 경우 디코 전송용)
        if len(products) == 0:
            await page.screenshot(path=f"zero_{region_code}.png")

        keywords = ["crimson desert", "붉은사막", "紅の砂漠", "紅의 砂漠", "赤血沙漠", "crimson"]
        for i, name in enumerate(products):
            if any(kw.lower() in name.lower() for kw in keywords):
                rank = i + 1
                print(f"✅ {region_name} 찾음: {rank}위")
                break
                
    except Exception as e:
        print(f"❌ {region_name} 에러: {str(e)[:50]}")
    finally:
        await context.close()
    return rank

async def main():
    async with async_playwright() as p:
        # 브라우저 실행 시 '자동화Controlled' 플래그 제거
        browser = await p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        today = datetime.now().strftime('%Y-%m-%d')
        results = {'date': today}
        
        for name, code in REGIONS.items():
            rank = await get_preorder_rank(browser, name, code)
            results[name] = rank
            await asyncio.sleep(random.uniform(3, 7))
            
        await browser.close()

        # 데이터 저장
        df = pd.read_csv(DATA_FILE) if os.path.exists(DATA_FILE) else pd.DataFrame(columns=['date'] + list(REGIONS.keys()))
        df = df[df['date'] != today]
        df = pd.concat([df, pd.DataFrame([results])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)

        # 그래프 저장
        plt.figure(figsize=(15, 8))
        for col in REGIONS.keys():
            if col in df.columns: plt.plot(df['date'], df[col], marker='o', label=col)
        plt.gca().invert_yaxis()
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        plt.savefig('rank_trend.png')

        # [중요] 결과 및 차단 여부 디스코드 알림
        if DISCORD_WEBHOOK:
            files = {'file': open('rank_trend.png', 'rb')}
            # 만약 한국 순위가 0개(30위)라면 차단된 화면 사진도 보냄
            if results["Korea"] == 30 and os.path.exists("zero_Korea.png"):
                files['debug'] = open('zero_Korea.png', 'rb')
            requests.post(DISCORD_WEBHOOK, data={'content': f"📊 {today} 집계 완료"}, files=files)

if __name__ == "__main__":
    asyncio.run(main())
