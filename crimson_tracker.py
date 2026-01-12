#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time, os, json, requests
from datetime import datetime
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# =============================================================================
# 🌍 국가 설정 (이미지 기준 확장)
# =============================================================================

MARKET_WEIGHTS = {
    # Asia & Oceania
    "태국": 3.0, "뉴질랜드": 2.5, "인도": 3.5, "한국": 2.8, "베트남": 2.2,
    "마카오": 1.2, "브루나이": 1.0, "라오스": 1.0, "필리핀": 2.0,
    "호주": 3.0, "싱가포르": 2.5, "말레이시아": 2.0, "홍콩": 2.0,
    "일본": 8.0, "대만": 2.3,

    # Americas
    "우루과이": 1.5, "칠레": 2.0, "브라질": 2.5, "콜롬비아": 1.8,
    "아르헨티나": 2.0, "멕시코": 2.0, "도미니카": 1.0,
    "미국": 30.0, "니카라과": 1.0, "캐나다": 4.5,
    "볼리비아": 1.0, "온두라스": 1.0, "과테말라": 1.0, "페루": 1.5,

    # Europe & Middle East
    "슬로바키아": 1.0, "남아공": 2.0, "슬로베니아": 1.0,
    "몰타": 0.8, "포르투갈": 2.0, "우크라이나": 1.5,
    "핀란드": 1.8, "네덜란드": 1.8, "프랑스": 6.0,
    "튀르키예": 2.5, "덴마크": 1.8, "사우디아라비아": 1.5,
    "영국": 8.5, "UAE": 1.2, "헝가리": 1.5,
    "스위스": 1.8, "폴란드": 2.0, "스페인": 4.0,
    "독일": 6.5, "그리스": 1.5, "체코": 1.5,
    "노르웨이": 1.7, "이탈리아": 3.5, "스웨덴": 1.8,
}

COUNTRIES = sorted(MARKET_WEIGHTS, key=lambda x: MARKET_WEIGHTS[x], reverse=True)

# =============================================================================
# 🔗 PlayStation Store URL
# =============================================================================

def ps_url(code):
    return f"https://store.playstation.com/{code}/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1"

URLS = {
    "미국": ps_url("en-us"),
    "영국": ps_url("en-gb"),
    "일본": ps_url("ja-jp"),
    "한국": ps_url("ko-kr"),
    "프랑스": ps_url("fr-fr"),
    "독일": ps_url("de-de"),
    "스페인": ps_url("es-es"),
    "이탈리아": ps_url("it-it"),
    "호주": ps_url("en-au"),
    "캐나다": ps_url("en-ca"),
    "브라질": ps_url("pt-br"),
    "멕시코": ps_url("es-mx"),
    "네덜란드": ps_url("nl-nl"),
    "폴란드": ps_url("pl-pl"),
    "스웨덴": ps_url("sv-se"),
    "핀란드": ps_url("fi-fi"),
    "노르웨이": ps_url("nb-no"),
    "포르투갈": ps_url("pt-pt"),
    "그리스": ps_url("el-gr"),
    "체코": ps_url("cs-cz"),
    "튀르키예": ps_url("tr-tr"),
    "사우디아라비아": ps_url("en-sa"),
    "UAE": ps_url("en-ae"),
}

# =============================================================================
# 🚩 국기
# =============================================================================

FLAGS = {
    "미국": "🇺🇸", "영국": "🇬🇧", "일본": "🇯🇵", "한국": "🇰🇷",
    "프랑스": "🇫🇷", "독일": "🇩🇪", "스페인": "🇪🇸", "이탈리아": "🇮🇹",
    "호주": "🇦🇺", "캐나다": "🇨🇦", "브라질": "🇧🇷", "멕시코": "🇲🇽",
    "네덜란드": "🇳🇱", "폴란드": "🇵🇱", "스웨덴": "🇸🇪",
    "핀란드": "🇫🇮", "노르웨이": "🇳🇴", "포르투갈": "🇵🇹",
    "그리스": "🇬🇷", "체코": "🇨🇿", "튀르키예": "🇹🇷",
    "사우디아라비아": "🇸🇦", "UAE": "🇦🇪",
}

# =============================================================================
# 🔎 검색어
# =============================================================================

SEARCH_TERMS = {
    c: ["crimson desert"] for c in COUNTRIES
}
SEARCH_TERMS["한국"].append("붉은사막")
SEARCH_TERMS["일본"].append("紅の砂漠")

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# =============================================================================
# 이하 크롤링 / 계산 / 디스코드 전송 로직은
# 👉 당신이 올린 기존 코드 그대로 사용하면 됩니다
# =============================================================================
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
            url = URLS.get(country)
        if not url:
            print(f"⚠️ PS Store 미지원 국가 스킵: {country}")
            results[country] = {"standard": None, "deluxe": None}
            continue

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
