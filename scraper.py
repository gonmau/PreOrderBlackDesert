import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import matplotlib.pyplot as plt
import os
import requests
from datetime import datetime

# 환경변수 로드
DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK')
DATA_FILE = 'rank_history.csv'

# 지역 코드 및 타겟
REGIONS = {
    "미국": "en-us", "일본": "ja-jp", "홍콩": "en-hk", "영국": "en-gb", 
    "독일": "de-de", "프랑스": "fr-fr", "멕시코": "es-mx", "캐나다": "en-ca", 
    "대한민국": "ko-kr", "호주": "en-au", "브라질": "pt-br", "스페인": "es-es"
}

# PS Store는 봇 탐지가 심하므로 리얼한 헤더 사용
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

async def get_preorder_rank(browser, region_name, region_code):
    # 국가별 격리를 위해 매번 새로운 Context 생성
    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport={'width': 1920, 'height': 1080},
        locale=region_code
    )
    page = await context.new_page()
    
    # 예약 주문 카테고리 URL
    url = f"https://store.playstation.com/{region_code}/category/601955f3-5290-449e-9907-f3160a2b918b/1"
    
    rank = 30 # 기본값 (순위 밖)
    
    try:
        # 타임아웃을 30초로 넉넉하게 설정
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        # 봇 탐지 회피를 위한 임의 지연 (사람처럼 보이게)
        await page.wait_for_timeout(2000)

        # 상품 그리드가 로드될 때까지 대기
        try:
            await page.wait_for_selector('[data-qa^="product-grid"]', state="visible", timeout=20000)
        except Exception:
            # 선택자를 못 찾으면 캡차나 에러 페이지일 가능성이 높음 -> 스크린샷 저장
            print(f"⚠️ {region_name} ({region_code}) 그리드 로딩 실패 - 디버그 스크린샷 저장 중...")
            await page.screenshot(path=f"debug_error_{region_code}.png")
            raise Exception("Grid Selector Timeout")

        names = await page.locator('[data-qa="product-name"]').all_text_contents()
        
        found = False
        for i, name in enumerate(names):
            # 대소문자 무시하고 키워드 확인
            if any(kw in name.lower() for kw in ["crimson desert", "붉은사막", "紅の砂漠", "赤血沙漠"]):
                rank = i + 1
                found = True
                break
        
        if not found:
            rank = 30

    except Exception as e:
        print(f"⚠️ {region_name} 최종 실패: {e}")
        # 에러 발생 시에도 30위로 처리하거나, 필요시 None으로 처리
        rank = 30
    
    finally:
        await context.close()
        
    return rank

async def main():
    async with async_playwright() as p:
        # 브라우저 런칭 시 봇 탐지 회피 옵션 추가
        browser = await p.chromium.launch(
            headless=True, # 디버깅 시에는 False로 변경하여 화면 확인 권장
            args=["--disable-blink-features=AutomationControlled"]
        )

        today = datetime.now().strftime('%Y-%m-%d')
        results = {'date': today}
        
        print(f"🚀 {today} 붉은사막 순위 집계 시작...")

        for name, code in REGIONS.items():
            rank = await get_preorder_rank(browser, name, code)
            results[name] = rank
            print(f"📍 {name}: {rank}위")
        
        await browser.close()

        # --- 데이터 저장 및 그래프 로직 (기존 유지) ---
        if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
            try:
                df = pd.read_csv(DATA_FILE)
            except:
                df = pd.DataFrame(columns=['date'] + list(REGIONS.keys()))
        else:
            df = pd.DataFrame(columns=['date'] + list(REGIONS.keys()))
            
        # 오늘 날짜 중복 제거 (재실행 시 중복 방지)
        df = df[df['date'] != today]
        
        # 새로운 데이터 추가
        new_row = pd.DataFrame([results])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        
        # 그래프 생성
        plt.figure(figsize=(12, 6))
        
        # 한글 폰트 깨짐 방지 (시스템에 따라 다를 수 있음, 영문으로 표기 추천)
        for col in REGIONS.keys():
            if col in df.columns:
                # 데이터가 없는 경우(NaN) 처리
                valid_data = df[['date', col]].dropna()
                if not valid_data.empty:
                    plt.plot(valid_data['date'], valid_data[col], marker='o', label=col)
        
        plt.gca().invert_yaxis() # 1위가 위로 가도록 반전
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), ncol=1, prop={'size': 8})
        plt.title(f"Crimson Desert PS5 Pre-Order Rank ({today})")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('rank_trend.png')
        
        # 디스코드 알림
        if DISCORD_WEBHOOK:
            try:
                with open('rank_trend.png', 'rb') as f:
                    requests.post(DISCORD_WEBHOOK,
