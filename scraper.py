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
    # 예약 주문 카테고리 URL
    url = f"https://store.playstation.com/{region}/category/601955f3-5290-449e-9907-f3160a2b918b/1"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        # 상품 그리드가 로드될 때까지 충분히 대기
        await page.wait_for_selector('[data-qa^="product-grid"]', timeout=15000)
        await page.wait_for_timeout(3000) # 안정적인 렌더링을 위한 3초 추가 대기
        
        names = await page.locator('[data-qa="product-name"]').all_text_contents()
        
        for i, name in enumerate(names):
            # 네이버 유저가 사용한 다국어 키워드 모두 포함
            if any(kw in name.lower() for kw in ["crimson desert", "붉은사막", "紅の砂漠", "赤血沙漠"]):
                return i + 1
        return 30
    except Exception as e:
        print(f"⚠️ {region} 로딩 실패: {e}")
        return 30

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()
        # 속도를 위해 이미지 차단
        await page.route("**/*.{png,jpg,jpeg,svg}", lambda route: route.abort())

        today = datetime.now().strftime('%Y-%m-%d')
        results = {'date': today}
        
        for name, code in REGIONS.items():
            # 함수명을 get_preorder_rank로 통일 (오류 해결 지점)
            rank = await get_preorder_rank(page, code) 
            results[name] = rank
            print(f"📍 {name}: {rank}위")
            
        await browser.close()

        # 데이터 누적 및 파일 에러 방지
        if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
            try:
                df = pd.read_csv(DATA_FILE)
            except:
                df = pd.DataFrame(columns=['date'] + list(REGIONS.keys()))
        else:
            df = pd.DataFrame(columns=['date'] + list(REGIONS.keys()))
            
        df = pd.concat([df, pd.DataFrame([results])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        
        # 그래프 생성 및 범례 최적화
        plt.figure(figsize=(12, 6))
        for col in REGIONS.keys():
            plt.plot(df['date'], df[col], marker='o', label=col)
        plt.gca().invert_yaxis()
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), ncol=1, prop={'size': 8})
        plt.title("Crimson Desert PS5 Pre-Order Rank")
        plt.grid(True, alpha=0.2)
        plt.savefig('rank_trend.png', bbox_inches='tight')
        
        if DISCORD_WEBHOOK:
            with open('rank_trend.png', 'rb') as f:
                requests.post(DISCORD_WEBHOOK, data={'content': f"📊 {today} 붉은사막 순위 집계 결과"}, files={'file': f})

if __name__ == "__main__":
    asyncio.run(main())
