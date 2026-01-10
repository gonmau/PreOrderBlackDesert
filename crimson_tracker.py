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

FLAGS = {
    "미국": "🇺🇸",
    "영국": "🇬🇧",
    "일본": "🇯🇵",
    "독일": "🇩🇪",
    "프랑스": "🇫🇷",
    "캐나다": "🇨🇦",
    "스페인": "🇪🇸",
    "이탈리아": "🇮🇹",
    "호주": "🇦🇺",
    "한국": "🇰🇷",
    "브라질": "🇧🇷",
    "멕시코": "🇲🇽",
    "네덜란드": "🇳🇱",
    "사우디아라비아": "🇸🇦",
    "아랍에미리트": "🇦🇪",
    "중국": "🇨🇳",
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

def calculate_combined_rank(standard, deluxe):
    """두 에디션을 하나의 순위로 통합 (더 좋은 순위 선택)"""
    if standard and deluxe:
        return min(standard, deluxe)
    return standard or deluxe

def calculate_avg(results):
    """가중 평균 순위 계산 (Combined 방식)"""
    combined_sum, combined_w = 0, 0
    
    for c, data in results.items():
        w = MARKET_WEIGHTS.get(c, 1.0)
        combined = calculate_combined_rank(data['standard'], data['deluxe'])
        
        if combined:
            combined_sum += combined * w
            combined_w += w
    
    return combined_sum / combined_w if combined_w > 0 else None

def format_diff(current, previous):
    """순위 수치 증감 포맷팅"""
    if previous is None or current is None:
        return ""
    diff = previous - current # 작아질수록 순위 상승
    if diff > 0: return f"▲{diff}"
    elif diff < 0: return f"▼{abs(diff)}"
    else: return "0"

def send_discord(results, combined_avg):
    if not DISCORD_WEBHOOK: return
    
    history_file = "rank_history.json"
    history = []
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            try: history = json.load(f)
            except: history = []

    # 이전 실행 데이터
    prev_run = history[-1] if history else None
    
    # 국가별 라인 생성
    lines = []
    for c in COUNTRIES:
        curr_s = results[c]['standard']
        curr_d = results[c]['deluxe']
        curr_combined = calculate_combined_rank(curr_s, curr_d)
        
        # 이전 개별 국가 순위
        prev_s, prev_d = None, None
        if prev_run and "raw_results" in prev_run:
            prev_country_data = prev_run["raw_results"].get(c, {})
            prev_s = prev_country_data.get("standard")
            prev_d = prev_country_data.get("deluxe")
        
        prev_combined = calculate_combined_rank(prev_s, prev_d)

        s_diff = format_diff(curr_s, prev_s)
        d_diff = format_diff(curr_d, prev_d)
        c_diff = format_diff(curr_combined, prev_combined)
        
        s_part = f"{curr_s or '-'}{'(' + s_diff + ')' if s_diff else ''}"
        d_part = f"{curr_d or '-'}{'(' + d_diff + ')' if d_diff else ''}"
        c_part = f"{curr_combined or '-'}{'(' + c_diff + ')' if c_diff else ''}"
        
        store_url = URLS.get(c)
        flag = FLAGS.get(c, "")
        country_label = f"{flag} [{c}]({store_url})" if store_url else f"{flag} {c}"

        lines.append(
            f"**{country_label}**: S `{s_part}` / D `{d_part}` → `{c_part}`"
        )


    # 평균 변동폭
    prev_combined_avg = prev_run['averages'].get('combined') if prev_run else None
    combined_diff_text = format_diff(combined_avg, prev_combined_avg)

    desc = "\n".join(lines) + f"\n\n📊 **가중 평균**: `{combined_avg:.1f}위` {'(' + combined_diff_text + ')' if combined_diff_text else ''}"
    
    # 히스토리 업데이트
    history.append({
        "timestamp": datetime.now().isoformat(),
        "averages": {"combined": combined_avg},
        "raw_results": results
    })
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history[-100:], f, indent=2)

    # 그래프 생성
    img_buf = None
    if HAS_MATPLOTLIB and len(history) >= 2:
        plt.figure(figsize=(10, 5))
        dates = [datetime.fromisoformat(h['timestamp']) for h in history]
        combined_ranks = [h['averages'].get('combined') for h in history]
        
        # None 값 필터링
        filtered_dates = [d for d, r in zip(dates, combined_ranks) if r is not None]
        filtered_ranks = [r for r in combined_ranks if r is not None]
        
        if filtered_dates:
            plt.plot(filtered_dates, filtered_ranks, label='Combined Rank', 
                    color='#00B0F4', marker='o', linewidth=2, markersize=8)
            plt.gca().invert_yaxis()
            plt.title("Crimson Desert - PlayStation Store Ranking", fontsize=14, fontweight='bold')
            plt.xlabel('Date', fontsize=12)
            plt.ylabel('Rank (weighted avg)', fontsize=12)
            plt.legend(); plt.grid(True, alpha=0.2)
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            plt.gcf().autofmt_xdate()
            plt.tight_layout()
            
            img_buf = BytesIO()
            plt.savefig(img_buf, format='png', dpi=150); img_buf.seek(0); plt.close()

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
    print("=" * 60)
    print("🎮 Crimson Desert PS Store 순위 추적")
    print("=" * 60)
    
    start_time = time.time()
    driver = setup_driver()
    
    results = {}
    
    try:
        for country in COUNTRIES:
            url = URLS[country]
            results[country] = crawl_country(driver, country, url)
    finally:
        driver.quit()
    
    elapsed = (time.time() - start_time) / 60
    print(f"\n⏱️  소요 시간: {elapsed:.1f}분")
    
    # Combined 평균 계산
    combined_avg = calculate_avg(results)
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("📊 결과 요약")
    print("=" * 60)
    for country in COUNTRIES:
        data = results[country]
        combined = calculate_combined_rank(data.get('standard'), data.get('deluxe'))
        print(f"{country}: S {data.get('standard', '-')}위 / D {data.get('deluxe', '-')}위 → {combined or '-'}위")
    
    if combined_avg:
        print(f"\n가중 평균: {combined_avg:.1f}위")
    
    # Discord 전송
    send_discord(results, combined_avg)

if __name__ == "__main__":
    main()
