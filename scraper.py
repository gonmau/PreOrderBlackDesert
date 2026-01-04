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
    "미국": "en-us", "일본": "ja-jp", "홍콩": "en-hk", "영국": "en-gb", 
    "독일": "de-de", "프랑스": "fr-fr", "멕시코": "es-mx", "캐나다": "en-ca", 
    "대한민국": "ko-kr", "호주": "en-au", "브라질": "pt-br", "스페인": "es-es"
}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

async def get_preorder_rank(browser, region_name, region_code):
    context = await browser.new_context(user_agent=USER_AGENT, viewport={'width': 1920, 'height': 1080})
    page = await context.new_page()
    
    # 1. 예약 주문 페이지 접속 (인기순 정렬 기본 적용된 URL)
    url = f"https://store.playstation.com/{region_code}/category/601955f3-5290-449e-9907-f3160a2b918b/1"
    rank = 30 # 기본값
    
    try:
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000) # 추가 렌더링 대기
        
        # 2. 모든 상품 로드를 위해 아래로 스크롤 (중요!)
        for _ in range(3):
            await page.mouse.wheel(0, 2000)
            await page.wait_for_timeout(1000)

        # 3. 상품 목록 추출
        product_selector = '[data-qa="product-name"]'
        await page.wait_for_selector(product_selector, timeout=15000)
        products = await page.locator(product_selector).all_text_contents()
        
        # 4. 순위 검색
        keywords = ["crimson desert", "붉은사막", "紅の砂漠", "赤血沙漠", "デザート"]
        for i, name in enumerate(products):
            if any(kw.lower() in name.lower() for kw in keywords):
                rank = i + 1
                print(f"✅ {region_name} 매칭 성공: {name} ({rank}위)")
                break
                
    except Exception as e:
        print(f"⚠️ {region_name} 에러: {str(e)[:50]}")
        await page.screenshot(path=f"debug_{region_code}.png") # 실패 시 화면 확인용
    finally:
        await context.close()
    return rank

async def main():
    async with async_playwright() as p:
        # 봇 탐지 우회를 위한 인자 추가
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        
        today = datetime.now().strftime('%Y-%m-%d')
        results = {'date': today}
        
        for name, code in REGIONS.items():
            rank = await get_preorder_rank(browser, name, code)
            results[name] = rank
            print(f"📍 {name}: {rank}위")
            # 서버 과부하 및 차단 방지를 위한 짧은 휴식
            await asyncio.sleep(random.uniform(1, 3))
            
        await browser.close()

        # 데이터 저장 로직
        df = pd.read_csv(DATA_FILE) if os.path.exists(DATA_FILE) else pd.DataFrame(columns=['date'] + list(REGIONS.keys()))
        df = df[df['date'] != today] # 당일 중복 데이터 제거
        df = pd.concat([df, pd.DataFrame([results])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)

        # 그래프 생성
        plt.figure(figsize=(15, 8))
        for col in REGIONS.keys():
            plt.plot(df['date'], df[col], marker='o', label=col)
        
        plt.gca().invert_yaxis() # 1위가 상단에 오도록
        plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=6)
        plt.title(f"Crimson Desert Global Pre-Order Rank ({today})")
        plt.grid(True, axis='y', alpha=0.3)
        plt.tight_layout()
        plt.savefig('rank_trend.png')

        # 디스코드 알림
        if DISCORD_WEBHOOK:
            with open('rank_trend.png', 'rb') as f:
                requests.post(DISCORD_WEBHOOK, data={'content': f"📊 **{today} 붉은사막 예구 현황**"}, files={'file': f})

if __name__ == "__main__":
    asyncio.run(main())
