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
    "일본": ["crimson desert", "紅의砂漠"], "스페인": ["crimson desert"], "캐나다": ["crimson desert"], "호주": ["crimson desert"],
    "이탈리아": ["crimson desert"], "브라질": ["crimson desert"], "사우디아라비아": ["crimson desert"], "아랍에미리트": ["crimson desert"],
    "멕시코": ["crimson desert"], "중국": ["crimson desert", "红之沙漠"], "네덜란드": ["crimson desert"], "한국": ["crimson desert", "붉은사막"]
}

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# =============================================================================
# 함수 정의
# =============================================================================

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def crawl_country(driver, country, url):
    search_terms = SEARCH_TERMS.get(country, ["crimson desert"])
    print(f"[{country}] 탐색 시작...")
    found_products = []
    total_rank = 0
    
    for page in range(1, 4):
        try:
            driver.get(url.replace("/1", f"/{page}"))
            time.sleep(3) # 로딩 대기
            
            # 더 넓은 범위의 요소를 탐색
            items = driver.find_elements(By.CSS_SELECTOR, "li[data-qa*='grid-item'], a[href*='/product/']")
            
            for item in items:
                # 중복 카운팅 방지 (링크가 포함된 li만 처리)
                if item.tag_name == 'li':
                    try:
                        link_el = item.find_element(By.CSS_SELECTOR, "a")
                    except: continue
                else:
                    link_el = item
                
                href = link_el.get_attribute("href")
                if not href or "/product/" not in href: continue
                
                total_rank += 1
                card_text = item.text or ""
                aria_label = (link_el.get_attribute("aria-label") or "").lower()
                combined_text = (aria_label + " " + card_text).lower()
                
                if any(term.lower() in combined_text for term in search_terms):
                    print(f"   > 발견! {total_rank}위")
                    found_products.append({'rank': total_rank})
                    if len(found_products) >= 2: break
            if len(found_products) >= 2: break
        except Exception as e:
            print(f"   ! 에러 발생 ({country}): {e}")
            continue

# --- 에디션 구분 로직 (국가별 맞춤형) ---
    res = {"standard": None, "deluxe": None}
    
    if len(found_products) >= 2:
        # 한국과 스페인은 발견 순서가 [스탠다드, 디럭스]인 경우
        if country in ["한국", "스페인"]:
            res["standard"] = found_products[0]['rank'] # 먼저 발견된 게 스탠다드
            res["deluxe"] = found_products[1]['rank']   # 나중에 발견된 게 디럭스
        # 그 외 국가(미국 등)는 발견 순서가 [디럭스, 스탠다드]인 경우
        else:
            res["deluxe"] = found_products[0]['rank']   # 먼저 발견된 게 디럭스
            res["standard"] = found_products[1]['rank'] # 나중에 발견된 게 스탠다드
            
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

def send_discord(results, std_avg, dlx_avg):
    if not DISCORD_WEBHOOK: return
    
    lines = [f"**{c}**: S `{results[c]['standard'] or '-'}` / D `{results[c]['deluxe'] or '-'}`" for c in COUNTRIES]
    desc = "\n".join(lines) + f"\n\n📊 **가중 평균**: S `{std_avg:.1f}위` / D `{dlx_avg:.1f}위`"
    
    # 히스토리 업데이트
    history_file = "rank_history.json"
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f: history = json.load(f)
        except: pass
    
    history.append({"timestamp": datetime.now().isoformat(), "averages": {"standard": std_avg, "deluxe": dlx_avg}})
    history = history[-50:]
    with open(history_file, "w", encoding="utf-8") as f: json.dump(history, f, indent=2)

    # 그래프 생성
    img_buf = None
    if HAS_MATPLOTLIB and len(history) >= 2:
        plt.figure(figsize=(10, 5))
        dates = [datetime.fromisoformat(h['timestamp']) for h in history]
        plt.plot(dates, [h['averages']['standard'] for h in history], label='Standard', color='#00B0F4', marker='o')
        plt.plot(dates, [h['averages']['deluxe'] for h in history], label='Deluxe', color='#FF4500', marker='s')
        plt.gca().invert_yaxis()
        plt.title("Rank Trend"); plt.legend(); plt.grid(True, alpha=0.2)
        img_buf = BytesIO()
        plt.savefig(img_buf, format='png'); img_buf.seek(0); plt.close()

    payload = {"payload_json": json.dumps({
        "embeds": [{
            "title": "🎮 Crimson Desert PS Store Rank",
            "description": desc,
            "color": 0x00B0F4,
            "image": {"url": "attachment://graph.png"} if img_buf else None
        }]
    })}
    
    try:
        if img_buf:
            requests.post(DISCORD_WEBHOOK, data=payload, files={"file": ("graph.png", img_buf, "image/png")})
        else:
            requests.post(DISCORD_WEBHOOK, json=json.loads(payload["payload_json"]))
    except: pass

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

if __name__ == "__main__":
    main()
