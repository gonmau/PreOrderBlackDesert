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
    # 예약 판매/출시 예정 카테고리 ID
    category_id = "601955f3-5290-449e-9907-f3160a2b918b"
    url = f"https://store.playstation.com/{region}/category/{category_id}/1"
    
    try:
        # 타임아웃을 늘리고 페이지 로드 완료를 명확히 대기
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)
        
        names = await page.locator('[data-qa="product-name"]').all_text_contents()
        
        for i, name in enumerate(names):
            if any(kw in name.lower() for kw in ["crimson desert", "붉은사막", "紅의 砂漠"]):
                return i + 1
        return 50
    except Exception as e:
        print(f"Error in {region}: {e}")
        return 50

async def main():
    print("🚀 크롤러 시작...")
    async with async_playwright() as p:
        # headless 모드로 브라우저 실행
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        today = datetime.now().strftime('%Y-%m-%d')
        results = {'date': today}
        
        for name, code in REGIONS.items():
            print(f"🔍 {name} 데이터 수집 중...")
            rank = await get_exact_rank(page, code)
            results[name] = rank
            print(f"✅ {name}: {rank}위")
            
        await browser.close()
        print("📊 데이터 수집 완료. 그래프 생성 중...")

        # 데이터 저장 로직
        df = pd.read_csv(DATA_FILE) if os.path.exists(DATA_FILE) else pd.DataFrame(columns=['date'] + list(REGIONS.keys()))
        df = pd.concat([df, pd.DataFrame([results])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        
        # 그래프 생성
        plt.figure(figsize=(10, 5))
        for col in REGIONS.keys():
            plt.plot(df['date'], df[col], marker='o', label=col)
        plt.gca().invert_yaxis()
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        plt.savefig('rank_trend.png', bbox_inches='tight')
        
        # 디스코드 전송
        if DISCORD_WEBHOOK:
            with open('rank_trend.png', 'rb') as f:
                requests.post(DISCORD_WEBHOOK, data={'content': f"📈 {today} 붉은사막 글로벌 순위 업데이트 완료"}, files={'file': f})
            print("🔔 디스코드 전송 완료!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        # 메인 루프에서 에러 발생 시 디코로 즉시 알림
        if DISCORD_WEBHOOK:
            requests.post(DISCORD_WEBHOOK, json={"content": f"🚨 크롤러 중명 오류 발생: {e}"})
        print(f"Fatal Error: {e}")
