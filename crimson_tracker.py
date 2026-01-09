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
    "일본": ["crimson desert", "紅の砂漠"],
    "스페인": ["crimson desert"], "캐나다": ["crimson desert"], "호주": ["crimson desert"],
    "이탈리아": ["crimson desert"], "브라질": ["crimson desert"], "사우디아라비아": ["crimson desert"], "아랍에미리트": ["crimson desert"],
    "멕시코": ["crimson desert"], "중국": ["crimson desert", "红之沙漠"], "네덜란드": ["crimson desert"], "한국": ["crimson desert", "붉은사막"]
}

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# =============================================================================
# 유틸리티
# =============================================================================

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def crawl_country(driver, country, url):
    terms = SEARCH_TERMS.get(country, ["crimson desert"])
    found_products = []
    total_rank = 0
    
    for page in range(1, 4):
        try:
            driver.get(url.replace("/1", f"/{page}"))
            time.sleep(3)
            items = driver.find_elements(By.CSS_SELECTOR, "li[data-qa*='grid-item'], a[href*='/product/']")
            for item in items:
                try:
                    link_el = item if item.tag_name == 'a' else item.find_element(By.CSS_SELECTOR, "a")
                    href = link_el.get_attribute("href")
                    if not href or "/product/" not in href: continue
                    total_rank += 1
                    label = (link_el.get_attribute("aria-label") or "").lower()
                    text = (item.text or "").lower()
                    if any(t.lower() in label or t.lower() in text for t in terms):
                        found_products.append({'rank': total_rank})
                        if len(found_products) >= 2: break
                except: continue
            if len(found_products) >= 2: break
        except: continue

    res = {"standard": None, "deluxe": None}
    if len(found_products) >= 2:
        if country in ["한국", "스페인"]:
            res["standard"], res["deluxe"] = found_products[0]['rank'], found_products[1]['rank']
        else:
            res["deluxe"], res["standard"] = found_products[0]['rank'], found_products[1]['rank']
    elif len(found_products) == 1:
        res["standard"] = found_products[0]['rank']
    return res

def calculate_avg(results):
    s_sum, s_w, d_sum, d_w = 0, 0, 0, 0
    for c, data in results.items():
        w = MARKET_WEIGHTS.get(c, 1.0)
        if data['standard']:
            s_sum += data['standard'] * w
            s_w += w
        if data['deluxe']:
            d_sum += data['deluxe'] * w
            d_w += w
    return (s_sum/s_w if s_w > 0 else 0, d_sum/d_w if d_w > 0 else 0)

def format_diff(current, previous):
    """순위 수치 증감 포맷팅"""
    if previous is None or current is None:
        return ""
    diff = previous - current # 작아질수록 순위 상승
    if diff > 0: return f"▲{diff}"
    elif diff < 0: return f"▼{abs(diff)}"
    else: return "0"

def send_discord(results, std_avg, dlx_avg):
    if not DISCORD_WEBHOOK: return
    
    history_file = "rank_history.json"
    history = []
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            try: history = json.load(f)
            except: history = []

    # 이전 실행 데이터 (최신 1건)
    prev_run = history[-1] if history else None
    
    # 국가별 라인 생성
    lines = []
    for c in COUNTRIES:
        curr_s = results[c]['standard']
        curr_d = results[c]['deluxe']
        
        # 이전 개별 국가 순위 가져오기
        prev_s, prev_d = None, None
        if prev_run and "raw_results" in prev_run:
            prev_country_data = prev_run["raw_results"].get(c, {})
            prev_s = prev_country_data.get("standard")
            prev_d = prev_country_data.get("deluxe")

        s_diff = format_diff(curr_s, prev_s)
        d_diff = format_diff(curr_d, prev_d)
        
        s_part = f"{curr_s or '-'}{'(' + s_diff + ')' if s_diff else ''}"
        d_part = f"{curr_d or '-'}{'(' + d_diff + ')' if d_diff else ''}"
        
        lines.append(f"**{c}**: S `{s_part}` / D `{d_part}`")

    # 평균 변동폭
    prev_std_avg = prev_run['averages']['standard'] if prev_run else None
    prev_dlx_avg = prev_run['averages']['deluxe'] if prev_run else None
    std_diff_text = format_diff(std_avg, prev_std_avg)
    dlx_diff_text = format_diff(dlx_avg, prev_dlx_avg)

    desc = "\n".join(lines) + f"\n\n📊 **가중 평균**\nStandard: `{std_avg:.1f}위` {'(' + std_diff_text + ')' if std_diff_text else ''}\nDeluxe: `{dlx_avg:.1f}위` {'(' + dlx_diff_text + ')' if dlx_diff_text else ''}"
    
    # 히스토리 업데이트 (raw_results 포함하여 저장해야 다음 실행 때 비교 가능)
    history.append({
        "timestamp": datetime.now().isoformat(),
        "averages": {"standard": std_avg, "deluxe": dlx_avg},
        "raw_results": results # 개별 국가 순위 보관
    })
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history[-100:], f, indent=2)

    # 그래프 생성
    img_buf = None
    if HAS_MATPLOTLIB and len(history) >= 2:
        plt.figure(figsize=(10, 5))
        dates = [datetime.fromisoformat(h['timestamp']) for h in history]
        plt.plot(dates, [h['averages']['standard'] for h in history], label='Standard', color='#00B0F4', marker='o')
        plt.plot(dates, [h['averages']['deluxe'] for h in history], label='Deluxe', color='#FF4500', marker='s')
        plt.gca().invert_yaxis()
        plt.title("Crimson Desert Rank Trend"); plt.legend(); plt.grid(True, alpha=0.2)
        img_buf = BytesIO()
        plt.savefig(img_buf, format='png'); img_buf.seek(0); plt.close()

    payload = {"payload_json": json.dumps({
        "embeds": [{
            "title": "🎮 Crimson Desert PS Store 순위 리포트",
            "description": desc,
            "color": 0x00B0F4,
            "image": {"url": "attachment://graph.png"} if img_buf else None,
            "timestamp": datetime.utcnow().isoformat()
        }]
    })}
    
    files = {"file": ("graph.png", img_buf, "image/png")} if img_buf else None
    requests.post(DISCORD_WEBHOOK, data=payload, files=files)

def main():
    driver = setup_driver()
    results = {c: crawl_country(driver, c, URLS[c]) for c in COUNTRIES}
    driver.quit()
    std_avg, dlx_avg = calculate_avg(results)
    send_discord(results, std_avg, dlx_avg)

if __name__ == "__main__":
    main()
