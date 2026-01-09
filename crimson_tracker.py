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
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# =============================================================================
# 설정
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
MAX_PAGES = 5

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

def extract_price(text):
    """국가별 다양한 가격 표기법에서 숫자만 추출 (예: 79,99€ -> 79.99)"""
    if not text: return None
    # 통화기호 제거 및 숫자, 마침표, 쉼표만 남김
    clean = re.sub(r'[^\d,.]', '', text)
    if not clean: return None
    try:
        # 천단위 구분자와 소수점 구분자 처리 (유럽식 쉼표 대응)
        if ',' in clean and '.' in clean:
            clean = clean.replace(',', '') # 1,234.56 -> 1234.56
        elif ',' in clean:
            clean = clean.replace(',', '.') # 79,99 -> 79.99
        return float(clean)
    except: return None

def crawl_country(driver, country, url):
    search_terms = SEARCH_TERMS.get(country, ["crimson desert"])
    print(f"[{country}] 크롤링 중...")
    found_products = []
    total_rank = 0
    
    for page in range(1, MAX_PAGES + 1):
        try:
            driver.get(url.replace("/1", f"/{page}"))
            time.sleep(2)
            cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/'], li[data-qa*='grid']")
            
            for card in cards:
                try:
                    link = card if card.tag_name == 'a' else card.find_element(By.CSS_SELECTOR, "a[href*='/product/']")
                    href = link.get_attribute("href")
                    if not href or "/product/" not in href: continue
                    
                    total_rank += 1
                    card_text = card.text or ""
                    aria_label = (link.get_attribute("aria-label") or "").lower()
                    
                    if any(term.lower() in aria_label or term.lower() in card_text.lower() for term in search_terms):
                        price = extract_price(card_text)
                        found_products.append({'rank': total_rank, 'price': price, 'name': aria_label})
                        if len(found_products) >= 2: break
                except: continue
            if len(found_products) >= 2: break
        except: continue

    # 에디션 판정: 가격이 높으면 Deluxe, 낮으면 Standard
    std_rank, dlx_rank = None, None
    if len(found_products) >= 2:
        # 가격 정보가 둘 다 있는 경우
        if found_products[0]['price'] and found_products[1]['price']:
            if found_products[0]['price'] > found_products[1]['price']:
                dlx_rank, std_rank = found_products[0]['rank'], found_products[1]['rank']
            else:
                std_rank, dlx_rank = found_products[0]['rank'], found_products[1]['rank']
        else:
            # 가격 정보가 없으면 이름으로 판정
            is_p1_dlx = any(kw in found_products[0]['name'] for kw in ['deluxe', 'edition', '디럭스', '豪華', 'デラックス'])
            if is_p1_dlx:
                dlx_rank, std_rank = found_products[0]['rank'], found_products[1]['rank']
            else:
                std_rank, dlx_rank = found_products[0]['rank'], found_products[1]['rank']
    elif len(found_products) == 1:
        std_rank = found_products[0]['rank']
        
    return {"standard": std_rank, "deluxe": dlx_rank}

def calculate_avg(results):
    s_sum, s_weight, d_sum, d_weight = 0, 0, 0, 0
    for c, data in results.items():
        w = MARKET_WEIGHTS.get(c, 1.0)
        if data['standard']:
            s_sum += data['standard'] * w
            s_weight += w
        if data['deluxe']:
            d_sum += data['deluxe'] * w
            d_weight += w
    return (s_sum/s_weight if s_weight > 0 else None, d_sum/d_weight if d_weight > 0 else None)

# =============================================================================
# 히스토리 및 그래프
# =============================================================================

def load_history():
    if os.path.exists("rank_history.json"):
        with open("rank_history.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_data(results, std_avg, dlx_avg):
    history = load_history()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "averages": {"standard": std_avg, "deluxe": dlx_avg}
    }
    history.append(entry)
    with open("rank_history.json", "w", encoding="utf-8") as f:
        json.dump(history[-100:], f, indent=2) # 최근 100개 유지

def create_graph(history):
    if not HAS_MATPLOTLIB or len(history) < 2: return None
    plt.figure(figsize=(10, 5))
    dates = [datetime.fromisoformat(h['timestamp']) for h in history]
    std = [h['averages']['standard'] for h in history]
    dlx = [h['averages']['deluxe'] for h in history]
    
    plt.plot(dates, std, label='Standard', marker='o', color='#00B0F4')
    plt.plot(dates, dlx, label='Deluxe', marker='s', color='#FF4500')
    plt.gca().invert_yaxis()
    plt.title("Crimson Desert PS Store Avg Rank Trend")
    plt.legend(); plt.grid(True, alpha=0.3)
    
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0); plt.close()
    return buf

# =============================================================================
# 디스코드 전송
# =============================================================================

def send_discord(results, std_avg, dlx_avg):
    if not DISCORD_WEBHOOK: return
    
    lines = [f"**{c}**: S `{results[c]['standard'] or '-'}` / D `{results[c]['deluxe'] or '-'}`" for c in COUNTRIES]
    desc = "\n".join(lines) + f"\n\n📊 **평균**: S `{std_avg:.1f}위` / D `{dlx_avg:.1f}위`"
    
    history = load_history()
    img_buf = create_graph(history)
    
    payload = {
        "payload_json": json.dumps({
            "embeds": [{
                "title": "🎮 Crimson Desert PS Store 순위 리포트",
                "description": desc,
                "color": 0x00B0F4,
                "image": {"url": "attachment://graph.png"} if img_buf else None,
                "timestamp": datetime.utcnow().isoformat()
            }]
        })
    }
    
    try:
        files = {"file": ("graph.png", img_buf, "image/png")} if img_buf else None
        requests.post(DISCORD_WEBHOOK, data=payload, files=files)
    except Exception as e: print(f"Discord 오류: {e}")

# =============================================================================
# 메인 실행
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
    save_data(results, std_avg, dlx_avg) # 히스토리 저장
    send_discord(results, std_avg, dlx_avg) # 디스코드 전송 (그래프 포함)
    print("✅ 모든 작업 완료")

if __name__ == "__main__":
    main()
