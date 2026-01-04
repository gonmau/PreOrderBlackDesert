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

# 실제 사용자와 유사한 브라우저 환경 설정
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

async def get_preorder_rank(browser, region_name, region_code):
    """국가별 PS Store 페이지에서 붉은사막 순위를 검색합니다."""
    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport={'width': 1920, 'height': 1080}
    )
    page = await context.new_page()
    
    # 인기 예약 주문 카테고리 URL
    url = f"https://store.playstation.com/{region_code}/category/601955f3-5290-449e-9907-f3160a2b918b/1"
    rank = 30 # 찾지 못할 경우 기본값
    
    try:
        # 1. 페이지 접속 및 초기 대기
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000) 

        # 2. 동적 로딩을 위해 하단까지 스크롤 (순위권 밖 데이터까지 로드)
        for _ in range(4):
            await page.mouse.wheel(0, 3000)
            await page.wait_for_timeout(2000)

        # 3. 상품 목록 추출 (최신 PS Store 선택자 반영)
        product_selector = '[data-qa="product-name"], .psw-t-body.psw-c-t-1.psw-t-truncate-2'
        await page.wait_for_selector(product_selector, timeout=20000)
        products = await page.locator(product_selector).all_text_contents()
        
        print(f"🔎 {region_name}: {len(products)}개 상품 로드됨")

        # 4. 키워드 매칭 (다국어 지원)
        keywords = ["crimson desert", "붉은사막", "紅の砂漠", "紅의 砂漠", "赤血沙漠", "crimson"]
        for i, name in enumerate(products):
            if any(kw.lower() in name.lower() for kw in keywords):
                rank = i + 1
                print(f"🎯 {region_name} 매칭: {name} ({rank}위)")
                break
                
    except Exception as e:
        print(f"⚠️ {region_name} 에러: {str(e)[:50]}")
        # 실패 시 로그 분석용 스크린샷 저장
        await page.screenshot(path=f"fail_{region_code}.png")
    finally:
        await context.close()
    return rank

async def main():
    async with async_playwright() as p:
        # 봇 탐지 우회 옵션으로 브라우저 실행
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        today = datetime.now().strftime('%Y-%m-%d')
        results = {'date': today}
        
        print(f"🚀 {today} 글로벌 순위 집계 시작...")

        for name, code in REGIONS.items():
            rank = await get_preorder_rank(browser, name, code)
            results[name] = rank
            print(f"📍 {name}: {rank}위")
            # 서버 부하 방지를 위한 랜덤 휴식
            await asyncio.sleep(random.uniform(2, 4))
            
        await browser.close()

        # 데이터 저장 및 그래프 생성 로직
        if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
            df = pd.read_csv(DATA_FILE)
        else:
            df = pd.DataFrame(columns=['date'] + list(REGIONS.keys()))
            
        df = df[df['date'] != today] # 중복 제거
        df = pd.concat([df, pd.DataFrame([results])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)

        # 그래프 시각화
        plt.figure(figsize=(15, 8))
        plot_df = df.tail(30) # 최근 30일
        for col in REGIONS.keys():
            if col in plot_df.columns:
                plt.plot(plot_df['date'], plot_df[col], marker='o', label=col)
        
        plt.gca().invert_yaxis() # 1위가 상단으로
        plt.grid(True, alpha=0.3)
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), prop={'size': 8})
        plt.title(f"Crimson Desert PS5 Global Rank ({today})")
        plt.tight_layout()
        plt.savefig('rank_trend.png')

        # 디스코드 알림
        if DISCORD_WEBHOOK:
            try:
                with open('rank_trend.png', 'rb') as f:
                    msg = f"📊 **{today} 붉은사막 글로벌 순위 업데이트**"
                    requests.post(DISCORD_WEBHOOK, data={'content': msg}, files={'file': f})
                print("✅ 디스코드 전송 완료")
            except Exception as e:
                print(f"❌ 전송 오류: {e}")

if __name__ == "__main__":
    asyncio.run(main())
