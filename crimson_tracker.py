#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import re
import os
import json
import requests
from datetime import datetime
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# =============================================================================
# 설정 (시장 가중치 및 URL)
# =============================================================================

MARKET_WEIGHTS = {
    "미국": 30.0, "영국": 8.5, "일본": 8.0, "독일": 6.5, "프랑스": 6.0,
    "캐나다": 4.5, "스페인": 4.0, "이탈리아": 3.5, "호주": 3.0, "한국": 2.8,
    "브라질": 2.5, "멕시코": 2.0, "네덜란드": 1.8, "사우디아라비아": 1.5,
    "아랍에미리트": 1.2, "중국": 0.2
}

COUNTRIES = sorted(MARKET_WEIGHTS.keys(), key=lambda x: MARKET_WEIGHTS[x], reverse=True)

URLS = {
    "미국": "https://store.playstation.com/en-us/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "영국": "https://store.playstation.com/en-gb/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "프랑스": "https://store.playstation.com/fr-fr/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "독일": "https://store.playstation.com/de-de/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "일본": "https://store.playstation.com/ja-jp/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "스페인": "https://store.playstation.com/es-es/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "캐나다": "https://store.playstation.com/en-ca/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "호주": "https://store.playstation.com/en-au/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "이탈리아": "https://store.playstation.com/it-it/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "브라질": "https://store.playstation.com/pt-br/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "사우디아라비아": "https://store.playstation.com/en-sa/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "아랍에미리트": "https://store.playstation.com/en-ae/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "멕시코": "https://store.playstation.com/es-mx/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "중국": "https://store.playstation.com/zh-cn/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "네덜란드": "https://store.playstation.com/nl-nl/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "한국": "https://store.playstation.com/ko-kr/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1"
}

SEARCH_TERMS = {
    "미국": ["crimson desert"], "영국": ["crimson desert"], "프랑스": ["crimson desert"], "독일": ["crimson desert"],
    "일본": ["crimson desert", "紅の砂漠"], "스페인": ["crimson desert"], "캐나다": ["crimson desert"], "호주": ["crimson desert"],
    "이탈리아": ["crimson desert"], "브라질": ["crimson desert"], "사우디아라비아": ["crimson desert"], "아랍에미리트": ["crimson desert"],
    "멕시코": ["crimson desert"], "중국": ["crimson desert", "红之沙漠"], "네덜란드": ["crimson desert"], "한국": ["crimson desert", "붉은사막"]
}

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# =============================================================================
# 유틸리티 함수
# =============================================================================

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def crawl_country(driver, country, url):
    search_terms = SEARCH_TERMS.get(country, ["crimson desert"])
    print(f"[{country}] 크롤링 중...")
    found_products = []
    total_rank = 0
    
    for page in range(1, 4):
        try:
            driver.get(url.replace("/1", f"/{page}"))
            time.sleep(2)
            # PS Store 상품 링크 추출
            cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")
            
            for card in cards:
                try:
                    href = card.get_attribute("href")
                    if not href or "/product/" not in href: continue
                    
                    total_rank += 1
                    # aria-label에 상품명이 들어있음
                    label = (card.get_attribute("aria-label") or "").lower()
                    
                    if any(term.lower() in label for term in search_terms):
                        found_products.append({'rank': total_rank})
                        if len(found_products) >= 2: break
                except: continue
            if len(found_products) >= 2: break
        except: continue

    # 판정 로직: PS Store는 고가 에디션(Deluxe)을 먼저 노출함
    res = {"standard": None, "deluxe": None}
    if len(found_products) >= 2:
        res["deluxe"] = found_products[0]['rank']   # 1순위 발견
        res["standard"] = found_products[1]['rank']  # 2순위 발견
    elif len(found_products) == 1:
        res["standard"] = found_products[0]['rank']
        
    return res

def calculate_avg(results):
    s_sum, s_w, d_sum, d_w = 0, 0, 0, 0
    for c, data in results.items():
        w = MARKET_WEIGHTS.get(c, 1.0)
        if data['standard'] is not None:
            s_sum += data['standard'] * w
            s_w += w
        if data['deluxe'] is not None:
            d_sum += data['deluxe'] * w
            d_w += w
    return (s_sum/s_w if s_w > 0 else 0, d_sum/d_w if d_w > 0 else 0)

# =============================================================================
# 데이터 저장 및 그래프 전송
# =============================================================================

def send_discord(results, std_avg, dlx_avg):
    if not DISCORD_WEBHOOK: return
    
    # 국가별 순위 텍스트 생성
    lines = [f"**{c}**: S `{results[c]['standard'] or '-'}` / D `{results[c]['deluxe'] or '-'}`" for c in COUNTRIES]
    desc = "\n".join(lines) + f"\n\n📊 **가중 평균**: S `{std_avg:.1f}위` / D `{dlx_avg:.1f}위`"
    
    # 히스토리 관리 (그래프용)
    history_file = "rank_history.json"
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except: history = []
    
    history.append({
        "timestamp": datetime.now().isoformat(),
        "averages": {"standard": std_avg, "deluxe": dlx_avg}
    })
    
    # 최근 50개만 유지 및 저장
    history = history[-50:]
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    # 그래프 이미지 생성
    img_buf = None
    if HAS_MATPLOTLIB and len(history) >= 2:
        plt.figure(figsize=(10, 5))
        dates = [datetime.fromisoformat(h['timestamp']) for h in history]
        stds = [h['averages']['standard'] for h in history]
        dlxs = [h['averages']['deluxe'] for h in history]
        
        plt.plot(dates, stds, label='Standard', color='#00B0F4', marker='o')
        plt.plot(dates, dlxs, label='Deluxe', color='#FF4500', marker='s')
        plt.gca().invert_yaxis()  # 순위이므로 뒤집기
        plt.title("Crimson Desert PS Store Rank Trend")
        plt.legend()
        plt.grid(True, alpha=0.2)
        
        img_buf = BytesIO()
        plt.savefig(img_buf, format='png')
        img_buf.seek(0)
        plt.close()

    # Discord 페이로드 구성
    payload = {
        "payload_json": json.dumps({
            "embeds": [{
                "title": "🎮 Crimson Desert PS Store 순위 리포트",
                "description": desc,
                "color": 0x00B0F4,
                "image": {"url": "attachment://graph.png"} if img_buf else None,
                "footer": {"text": f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}"}
            }]
        })
    }
    
    try:
        if img_buf:
            files = {"file": ("graph.png", img_buf, "image/png")}
            requests.post(DISCORD_WEBHOOK, data=payload, files=files)
        else:
            requests.post(DISCORD_WEBHOOK, json=json.loads(payload["payload_json"]))
    except Exception as e:
        print(f"Discord 전송 실패: {e}")

# =============================================================================
# 메인 함수
# =============================================================================

def main():
    driver = setup_driver()
    results = {}
    try:
        for country in COUNTRIES:
            results[country] = crawl_country(driver, country, URLS[country])
    finally:
        driver.quit()
        
    std_avg, dlx_avg = calculate_avg(results)
    send_discord(results, std_avg, dlx_avg)
    print("✅ 모든 국가 집계 및 전송 완료")

if __name__ == "__main__":
    main()
