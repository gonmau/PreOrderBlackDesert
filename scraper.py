import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import matplotlib.pyplot as plt
import os
import requests
from datetime import datetime
import random

# 환경변수 로드
DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK')
DATA_FILE = 'rank_history.csv'

# 추적 대상 지역 (PS Store 기준)
REGIONS = {
    "미국": "en-us", "일본": "ja-jp", "홍콩": "en-hk", "영국": "en-gb", 
    "독일": "de-de", "프랑스": "fr-fr", "멕시코": "es-mx", "캐나다": "en-ca", 
    "대한민국": "ko-kr", "호주": "en-au", "브라질": "pt-br", "스페인": "es-es"
}

# 브라우저 위장용 유저 에이전트
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

async def get_preorder_rank(browser, region_name, region_code):
    """
    각 국가별 페이지에 접속하여 붉은사막의 순위를 찾습니다.
    """
    # 컨텍스트 생성 시 실제 브라우저처럼 보이도록 설정
    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport={'width': 1920, 'height': 1080}
    )
    page = await context.new_page()
    
    # PS Store 예약 주문 카테고리 (인기순 정렬 기본 적용)
    url = f"https://store.playstation.com/{region_code}/category/601955f3-5290-449e-9907-f3160a2b918b/1"
    rank = 30 # 기본값 (찾지 못할 경우)
    
    try:
        # 1. 페이지 접속 및 대기
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)
        
        # 2. [핵심] 네이버 종토방 데이터처럼 하위 순위까지 잡으려면 스크롤이 필수입니다.
        # 아래로 5번 스크롤하여 더 많은 상품을 로드합니다.
        for _ in range(5):
            await page.mouse.wheel(0, 2000)
            await page.wait_for_timeout(1000)

        # 3. 상품명 리스트 추출
        product_selector = '[data-qa="product-name"]'
        await page.wait_for_selector(product_selector, timeout=20000)
        names = await page.locator(product_selector).all_text_contents()
        
        # 4. 키워드 매칭 (다국어 및 에디션 명칭 고려)
        keywords = ["crimson desert", "붉은사막", "紅の砂漠", "紅의 砂漠", "赤血沙漠", "crimson"]
        for i, name in enumerate(names):
            if any(kw.lower() in name.lower() for kw in keywords):
                rank = i + 1
                break
                
    except Exception as e:
        print(f"⚠️ {region_name} 실패: {str(e)[:50]}")
        # 실패한 화면을 스크린샷으로 남겨 GitHub Artifacts 등에서 확인 가능하게 함
        await page.screenshot(path=f"fail_{region_code}.png")
    finally:
        await context.close()
    return rank

async def main():
    async with async_playwright() as p:
        # 브라우저 런칭 (봇 탐지 방지 인자 포함)
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        today = datetime.now().strftime('%Y-%m-%d')
        results = {'date': today}
        
        print(f"🚀 {today} 순위 추적 시작...")

        for name, code in REGIONS.items():
            rank = await get_preorder_rank(browser, name, code)
            results[name] = rank
            print(f"📍 {name}: {rank}위")
            # 차단 방지를 위한 랜덤 지연
            await asyncio.sleep(random.uniform(2, 4))
            
        await browser.close()

        # 데이터 업데이트 로직
        if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
            df = pd.read_csv(DATA_FILE)
        else:
            df = pd.DataFrame(columns=['date'] + list(REGIONS.keys()))
            
        # 당일 데이터가 이미 있으면 제거하고 업데이트
        df = df[df['date'] != today]
        df = pd.concat([df, pd.DataFrame([results])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)

        # 그래프 생성
        plt.figure(figsize=(14, 7))
        # 최신 30회분 데이터 시각화
        plot_df = df.tail(30)
        for col in REGIONS.keys():
            if col in plot_df.columns:
                plt.plot(plot_df['date'], plot_df[col], marker='o', label=col)
        
        plt.gca().invert_yaxis() # 1위가 상단에 오도록 y축 반전
        plt.grid(True, alpha=0.3, linestyle='--')
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), prop={'size': 8})
        plt.title(f"Crimson Desert PS5 Pre-Order Rank ({today})", fontsize=14)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('rank_trend.png')

        # 디스코드 웹훅 전송
        if DISCORD_WEBHOOK:
            try:
                with open('rank_trend.png', 'rb') as f:
                    requests.post(DISCORD_WEBHOOK, 
                        data={'content': f"📊 **{today} 글로벌 붉은사막 순위 집계 결과**"}, 
                        files={'file': f}
                    )
                print("✅ 디스코드 알림 전송 성공")
            except Exception as e:
                print(f"❌ 디스코드 전송 오류: {e}")

if __name__ == "__main__":
    asyncio.run(main())
