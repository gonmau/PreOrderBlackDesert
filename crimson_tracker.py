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

# [설정 부분은 이전과 동일하므로 생략 - MARKET_WEIGHTS, URLS, SEARCH_TERMS 유지]

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def crawl_country(driver, country, url):
    search_terms = SEARCH_TERMS.get(country, ["crimson desert"])
    found_products = []
    total_rank = 0
    
    for page in range(1, 4): # 페이지 범위를 약간 줄여 속도 향상
        try:
            driver.get(url.replace("/1", f"/{page}"))
            time.sleep(2)
            cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")
            for card in cards:
                try:
                    href = card.get_attribute("href")
                    if not href or "/product/" not in href: continue
                    total_rank += 1
                    label = (card.get_attribute("aria-label") or "").lower()
                    if any(term.lower() in label for term in search_terms):
                        found_products.append({'rank': total_rank})
                        if len(found_products) >= 2: break
                except: continue
            if len(found_products) >= 2: break
        except: continue

    # 발견 순서 기반: 첫 번째=디럭스, 두 번째=스탠다드
    res = {"standard": None, "deluxe": None}
    if len(found_products) >= 2:
        res["deluxe"] = found_products[0]['rank']
        res["standard"] = found_products[1]['rank']
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

def send_discord(results, std_avg, dlx_avg):
    if not DISCORD_WEBHOOK: return
    
    lines = [f"**{c}**: S `{results[c]['standard'] or '-'}` / D `{results[c]['deluxe'] or '-'}`" for c in COUNTRIES]
    desc = "\n".join(lines) + f"\n\n📊 **가중 평균**: S `{std_avg:.1f}위` / D `{dlx_avg:.1f}위`"
    
    # 히스토리 저장 및 그래프 생성
    history = []
    if os.path.exists("rank_history.json"):
        with open("rank_history.json", "r") as f: history = json.load(f)
    
    history.append({"timestamp": datetime.now().isoformat(), "averages": {"standard": std_avg, "deluxe": dlx_avg}})
    with open("rank_history.json", "w") as f: json.dump(history[-50:], f)

    img_buf = None
    if len(history) >= 2 and HAS_MATPLOTLIB:
        plt.figure(figsize=(10, 5))
        dates = [datetime.fromisoformat(h['timestamp']) for h in history]
        plt.plot(dates, [h['averages']['standard'] for h in history], label='Standard', color='#00B0F4', marker='o')
        plt.plot(dates, [h['averages']['deluxe'] for h in history], label='Deluxe', color='#FF4500', marker='s')
        plt.gca().invert_yaxis()
        plt.legend(); plt.grid(True, alpha=0.2); plt.title("Rank Trend")
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
