import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import matplotlib.pyplot as plt
import os
import requests
from datetime import datetime

# 디스코드 설정
DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK')
DATA_FILE = 'rank_history.csv'

# 이미지 기반 13개국 설정
REGIONS = {
    "미국": "en-us", "일본": "ja-jp", "홍콩": "en-hk", "인도": "en-in",
    "영국": "en-gb", "독일": "de-de", "프랑스": "fr-fr", "멕시코": "es-mx",
    "캐나다": "en-ca", "한국": "ko-kr", "호주": "en-au", "브라질": "pt-br", "스페인": "es-es"
}

async def get_rank(page, region):
    url = f"https://store.playstation.com/{region}/category/05a79ebd-771a-40ad-87d0-14fb847b019a/1"
    try:
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(5000) # 데이터 로딩 대기
        
        # 상품 이름들 가져오기
        content = await page.content()
        # 붉은사막(Crimson Desert) 찾기 (대소문자 구분 없이)
        names = await page.locator('[data-qa="product-name"]').all_text_contents()
        
        for i, name in enumerate(names):
            if "crimson" in name.lower() or "desert" in name.lower() or "붉은사막" in name:
                return i + 1
        return 100 # 순위권 밖
    except:
        return 100

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        today = datetime.now().strftime('%Y-%m-%d')
        results = {'date': today}
        
        for name, code in REGIONS.items():
            rank = await get_rank(page, code)
            results[name] = rank
            print(f"{name}: {rank}위")
            
        await browser.close()
        
        # 데이터 저장 및 그래프 생성
        df = pd.read_csv(DATA_FILE) if os.path.exists(DATA_FILE) else pd.DataFrame()
        df = pd.concat([df, pd.DataFrame([results])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        
        # 그래프 그리기 (네이버 토론장 스타일)
        plt.figure(figsize=(10, 5))
        for col in df.columns[1:]:
            plt.plot(df['date'], df[col], marker='o', label=col)
        plt.gca().invert_yaxis()
        plt.legend(ncol=3, loc='upper center', bbox_to_anchor=(0.5, -0.1))
        plt.savefig('rank_trend.png', bbox_inches='tight')
        
        # 디스코드 전송
        with open('rank_trend.png', 'rb') as f:
            requests.post(DISCORD_WEBHOOK, data={'content': f"📊 {today} 붉은사막 글로벌 순위"}, files={'file': f})

if __name__ == "__main__":
    asyncio.run(main())
