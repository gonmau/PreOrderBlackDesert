#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crimson Desert PlayStation Store 순위 추적기
GitHub Actions + Discord Webhook
"""

import time
import re
import os
import json
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# =============================================================================
# 설정
# =============================================================================

COUNTRIES = ["미국", "영국", "프랑스", "독일", "일본", "스페인", "캐나다", "호주", "이탈리아", "브라질", "사우디아라비아", "아랍에미리트", "멕시코", "중국", "네덜란드", "한국"]

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
# 함수들
# =============================================================================

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(20)
    return driver

def extract_price(text):
    if not text: return None
    patterns = [r'₩\s*[\d,]+', r'[\d,]+\s*원', r'¥\s*[\d,]+', r'[\$€£]\s*[\d,\.]+', r'[\d,\.]+\s*[\$€£¥₩]']
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            try:
                num_str = re.findall(r'[\d,\.]+', matches[0])[0]
                if '₩' in matches[0] or '원' in matches[0] or '¥' in matches[0]:
                    return float(num_str.replace(',', ''))
                if ',' in num_str and '.' in num_str:
                    return float(num_str.replace(',', ''))
                elif num_str.count(',') == 1 and '.' not in num_str:
                    return float(num_str.replace(',', '.'))
                return float(num_str.replace(',', ''))
            except: pass
    return None

def crawl_country(driver, country, url):
    """국가별 순위 크롤링"""
    search_terms = SEARCH_TERMS.get(country, ["crimson desert"])
    print(f"[{country}] 시작...")
    
    found_products = []
    total_rank = 0
    
    for page in range(1, MAX_PAGES + 1):
        try:
            driver.get(url.replace("/1", f"/{page}"))
            time.sleep(1.5)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.8)
            
            cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")
            if not cards:
                cards = driver.find_elements(By.CSS_SELECTOR, "li[data-qa*='grid']")
            
            for card in cards:
                try:
                    link = card if card.tag_name == 'a' else card.find_element(By.CSS_SELECTOR, "a[href*='/product/']")
                    href = link.get_attribute("href") or ""
                    if "/product/" not in href: continue
                    
                    total_rank += 1
                    
                    aria_label = link.get_attribute("aria-label") or ""
                    card_text = card.text or ""
                    combined = (aria_label + " " + card_text).lower()
                    
                    if any(term.lower() in combined for term in search_terms):
                        price = extract_price(card_text)
                        if not price:
                            try:
                                price_elem = card.find_element(By.CSS_SELECTOR, "[data-qa*='price'], [class*='price']")
                                price = extract_price(price_elem.text)
                            except: pass
                        
                        found_products.append({'rank': total_rank, 'price': price, 'name': aria_label[:50]})
                        print(f"  발견: {total_rank}위 '{aria_label[:30]}' (가격: {price if price else '없음'})")
                        
                        # 2개 찾으면 즉시 종료
                        if len(found_products) >= 2:
                            print(f"  ✅ 2개 발견 완료!")
                            break
                except: continue
            
            if len(found_products) >= 2: break
        except: continue
    
    # 가격 기준으로 에디션 구분
    standard_rank = None
    deluxe_rank = None
    
    if len(found_products) >= 2:
        # 가격이 있는 것만 필터
        with_price = [p for p in found_products if p['price']]
        if len(with_price) >= 2:
            # 가격 순 정렬 (높은 가격 = 디럭스, 낮은 가격 = 스탠다드)
            with_price.sort(key=lambda x: x['price'], reverse=True)
            deluxe_rank = with_price[0]['rank']      # 가장 높은 가격
            standard_rank = with_price[-1]['rank']   # 가장 낮은 가격
            print(f"  ✅ 가격기준: S={standard_rank}위(${with_price[-1]['price']:.1f}) D={deluxe_rank}위(${with_price[0]['price']:.1f})")
        else:
            # 가격 정보 없으면 제품명으로 구분
            for p in found_products:
                name_lower = p['name'].lower()
                # 디럭스 키워드 확인
                if any(kw in name_lower for kw in ['deluxe', 'デラックス', '디럭스', '豪华', '豪華']):
                    if not deluxe_rank:
                        deluxe_rank = p['rank']
                else:
                    if not standard_rank:
                        standard_rank = p['rank']
            
            # 그래도 구분 안되면 순위순
            if not standard_rank and found_products:
                standard_rank = found_products[0]['rank']
            if not deluxe_rank and len(found_products) > 1:
                deluxe_rank = found_products[1]['rank']
            
            print(f"  ⚠️  가격없음: 이름기준 S={standard_rank}위 D={deluxe_rank}위")
    elif len(found_products) == 1:
        # 1개만 발견 - 이름으로 구분
        p = found_products[0]
        if any(kw in p['name'].lower() for kw in ['deluxe', 'デラックス', '디럭스', '豪华', '豪華']):
            deluxe_rank = p['rank']
        else:
            standard_rank = p['rank']
        print(f"  ⚠️  1개만 발견: {p['rank']}위")
    else:
        print(f"  ❌ 못찾음")
    
    return {"standard": standard_rank, "deluxe": deluxe_rank}

def calculate_avg(results):
    """평균 순위 계산"""
    std_ranks = [r['standard'] for r in results.values() if r['standard']]
    dlx_ranks = [r['deluxe'] for r in results.values() if r['deluxe']]
    
    std_avg = sum(std_ranks) / len(std_ranks) if std_ranks else None
    dlx_avg = sum(dlx_ranks) / len(dlx_ranks) if dlx_ranks else None
    
    return std_avg, dlx_avg

def send_discord(results, std_avg, dlx_avg):
    """Discord로 결과 전송"""
    if not DISCORD_WEBHOOK:
        print("⚠️  DISCORD_WEBHOOK 환경변수 없음")
        return
    
    # 결과 정리
    lines = []
    for country in COUNTRIES:
        data = results.get(country, {})
        std = data.get('standard', '-')
        dlx = data.get('deluxe', '-')
        
        if std != '-' and dlx != '-':
            lines.append(f"**{country}**: S `{std}위` / D `{dlx}위`")
        elif std != '-':
            lines.append(f"**{country}**: S `{std}위` / D `없음`")
        elif dlx != '-':
            lines.append(f"**{country}**: S `없음` / D `{dlx}위`")
        else:
            lines.append(f"**{country}**: 발견 안됨")
    
    # 평균 추가
    avg_text = ""
    if std_avg:
        avg_text += f"\n\n📊 **평균 순위 (스탠다드)**: `{std_avg:.1f}위`"
    if dlx_avg:
        avg_text += f"\n📊 **평균 순위 (디럭스)**: `{dlx_avg:.1f}위`"
    
    # Discord embed
    embed = {
        "title": "🎮 Crimson Desert PlayStation 순위",
        "description": "\n".join(lines) + avg_text,
        "color": 0x00B0F4,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "PlayStation Store Tracker"}
    }
    
    payload = {"embeds": [embed]}
    
    try:
        response = requests.post(DISCORD_WEBHOOK, json=payload)
        if response.status_code == 204:
            print("✅ Discord 전송 성공!")
        else:
            print(f"⚠️  Discord 전송 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ Discord 오류: {e}")

def save_json(results, std_avg, dlx_avg):
    """결과를 JSON 파일로 저장 (GitHub Actions artifact용)"""
    data = {
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "averages": {
            "standard": std_avg,
            "deluxe": dlx_avg
        }
    }
    
    with open("rank_results.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("✅ rank_results.json 저장 완료")

# =============================================================================
# 메인
# =============================================================================

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
    
    # 평균 계산
    std_avg, dlx_avg = calculate_avg(results)
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("📊 결과 요약")
    print("=" * 60)
    for country in COUNTRIES:
        data = results[country]
        print(f"{country}: S {data.get('standard', '-')}위 / D {data.get('deluxe', '-')}위")
    
    if std_avg:
        print(f"\n평균 (스탠다드): {std_avg:.1f}위")
    if dlx_avg:
        print(f"평균 (디럭스): {dlx_avg:.1f}위")
    
    # Discord 전송
    send_discord(results, std_avg, dlx_avg)
    
    # JSON 저장
    save_json(results, std_avg, dlx_avg)

if __name__ == "__main__":
    main()
