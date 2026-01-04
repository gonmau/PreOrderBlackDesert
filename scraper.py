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
    "미국": "en-us", "일본": "ja-jp", "홍콩": "en-hk", "영국": "en-gb", 
    "독일": "de-de", "프랑스": "fr-fr", "멕시코": "es-mx", "캐나다": "en-ca", 
    "대한민국": "ko-kr", "호주": "en-au", "브라질": "pt-br", "스페인": "es-es"
}

async def get_preorder_rank(browser, region_name, region_code):
    # 실제 사람처럼 보이게 하는 컨텍스트 설정
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={'width': 1920, 'height': 1080}
    )
    page = await context.new_page()
    
    # PS Store 예약구매 카테고리 (인기순 정렬 적용)
    url = f"https://store.playstation.com/{region_code}/category/601955f3-5290-449e-9907-f3160a2b918b/1"
    rank = 30
    
    try:
        # 페이지 접속
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)
        
        # [중요] 네이버 종토방 자료처럼 하위 순위까지 찾으려면 스크롤을 내려야 합니다.
        # 하단까지 총 5번 스크롤하여 상품을 더 로드합니다.
        for _ in range(5):
            await page.mouse.wheel(0, 2500)
            await page.wait_for_timeout(1500)

        # 상품명 리스트 추출
        product_selector = '[data-qa="product-name"]'
        await page.wait_for_selector(product_selector, timeout=20000)
        names = await page.locator(product_selector).all_text_contents()
        
        # 키워드 매칭
        keywords = ["crimson desert", "붉은사막", "紅의 砂漠", "紅の砂漠", "赤血沙漠"]
        for i, name in enumerate(names):
            if any(kw.lower() in name.lower() for kw in keywords):
                rank = i + 1
                break
                
    except Exception as e:
        print(f"⚠️ {region_name} 실패: {str(e)[:50]}")
        # 실패 시 스크린샷 저장하여 로그에서 확인 가능하게 함
        await page.screenshot(path=f"fail_{region_code}.png")
    finally:
        await context.close()
    return rank

async def main():
    async with async_playwright() as p:
        # 봇 탐지 회피 옵션 적용
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        today = datetime.now().strftime('%Y-%m-%d')
        results = {'date': today}
        
        for name, code in REGIONS.items():
            rank = await get_preorder_rank(browser, name, code)
            results[name] = rank
            print(f"📍 {name}: {rank}위")
            # 연속 접속으로 인한 차단 방지 (랜덤 휴식)
            await asyncio.sleep(random.uniform(2, 5))
            
        await browser.close()

        # 데이터 업데이트 및 파일 저장
        if os.path.exists(DATA_FILE):
            df = pd.read_csv(DATA_FILE)
        else:
            df = pd.DataFrame(columns=['date'] + list(REGIONS.keys()))
            
        df = df[df['date'] != today] # 중복 제거
        df = pd.concat([df, pd.DataFrame([results])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)

        # --- 그래프 생성 부분 ---
        plt.figure(figsize=(12, 6))
        # 최신 30일 데이터만 시각화 (너무 많으면 가독성 저하)
        plot_df = df.tail(30)
        for col in REGIONS.keys():
            plt.plot(plot_df['date'], plot_df[col], marker='o', label=col)
        
        plt.gca().invert_yaxis() # 1위가 위로 오게
        plt.grid(True, alpha=0.3)
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), prop={'size': 7})
        plt.title(f"Crimson Desert Global Ranking ({today})")
        plt.tight_layout()
        plt.savefig('rank_trend.png')

        # 디스코드 전송
        if DISCORD_WEBHOOK:
            with open('rank_trend.png', 'rb') as f:
                requests.post(DISCORD_WEBHOOK, data={'content': f"📊 **{today} 순위 업데이트 완료**"}, files={'file': f})

if __name__ == "__main__":
    asyncio.run(main())
