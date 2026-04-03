#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PS Store 경쟁작 추적기 - Crimson Desert (최종 최적화판 v2.3)
"""

import time
import os
import json
import requests
import re
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# =============================================================================
# 설정
# =============================================================================

CONCEPT_ID = "10002363"  # Crimson Desert

REGIONS = {
    "Americas": ["미국", "캐나다", "브라질", "멕시코", "아르헨티나", "칠레", "콜롬비아", "페루", "우루과이"],
    "Europe & Middle East": ["영국", "독일", "프랑스", "스페인", "이탈리아", "네덜란드", "폴란드", "사우디아라비아", "아랍에미리트", "남아공", "터키"],
    "Asia & Oceania": ["일본", "한국", "중국", "호주", "인도", "대만", "싱가포르", "태국", "홍콩", "말레이시아"]
}

FLAGS = {
    "미국": "🇺🇸", "캐나다": "🇨🇦", "브라질": "🇧🇷", "멕시코": "🇲🇽", "아르헨티나": "🇦🇷", "칠레": "🇨🇱", "콜롬비아": "🇨🇴", "페루": "🇵🇪", "우루과이": "🇺🇾",
    "영국": "🇬🇧", "독일": "🇩🇪", "프랑스": "🇫🇷", "스페인": "🇪🇸", "이탈리아": "🇮🇹", "네덜란드": "🇳🇱", "폴란드": "🇵🇱", "사우디아라비아": "🇸🇦", "아랍에미리트": "🇦🇪", "남아공": "🇿🇦", "터키": "🇹🇷",
    "일본": "🇯🇵", "한국": "🇰🇷", "중국": "🇨🇳", "호주": "🇦🇺", "인도": "🇮🇳", "대만": "🇹🇼", "싱가포르": "🇸🇬", "태국": "🇹🇭", "홍콩": "🇭🇰", "말레이시아": "🇲🇾"
}

LOCALE_MAP = {
    "미국": "en-us", "캐나다": "en-ca", "브라질": "pt-br", "멕시코": "es-mx", "아르헨티나": "es-ar", "칠레": "es-cl", "콜롬비아": "es-co", "페루": "es-pe", "우루과이": "es-uy",
    "영국": "en-gb", "독일": "de-de", "프랑스": "fr-fr", "스페인": "es-es", "이탈리아": "it-it", "네덜란드": "nl-nl", "폴란드": "pl-pl", "사우디아라비아": "en-sa", "아랍에미리트": "en-ae", "남아공": "en-za", "터키": "en-tr",
    "일본": "ja-jp", "한국": "ko-kr", "중국": "zh-cn", "호주": "en-au", "인도": "en-in", "대만": "zh-hant-tw", "싱가포르": "en-sg", "태국": "en-th", "홍콩": "en-hk", "말레이시아": "en-my"
}

SKIP_COUNTRIES = {"중국"}
MAX_PAGES = 8

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
HISTORY_FILE = "competitor_history.json"

# =============================================================================
# 드라이버 설정
# =============================================================================

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(25)
    return driver

def get_browse_url(country, page=1):
    locale = LOCALE_MAP.get(country)
    return f"https://store.playstation.com/{locale}/pages/browse/{page}" if locale else None

# =============================================================================
# 할인 종료일 추출
# =============================================================================

def get_discount_deadline(driver, url):
    try:
        driver.get(url)
        time.sleep(3)
        
        elements = driver.find_elements(By.CSS_SELECTOR, 
            "[data-qa*='discount'], [class*='discount'], [class*='price'], [data-qa*='offer'], [data-qa*='availability']")
        
        for el in elements:
            text = el.text.strip()
            if any(kw in text.lower() for kw in ["ends", "종료", "offer ends", "save", "까지", "fin", "scade"]):
                return text
        return "종료일 정보 없음"
    except:
        return "확인 불가"

# =============================================================================
# 경쟁작 크롤링 (최적화)
# =============================================================================

def crawl_competitors(driver, country):
    competitors_links = []
    page = 1
    found_target = False

    print(f"🔍 {country} Best Selling 탐색 시작...")

    while page <= MAX_PAGES and not found_target:
        driver.get(get_browse_url(country, page))
        time.sleep(4 if page == 1 else 2.5)   # 대폭 줄임

        tile_map = {}
        elements = driver.find_elements(By.CSS_SELECTOR, '[data-qa*="productTile"]')
        
        for elem in elements:
            qa = elem.get_attribute('data-qa') or ''
            match = re.search(r'productTile(\d+)', qa)
            if not match:
                continue
            tile_idx = int(match.group(1))
            
            if tile_idx not in tile_map:
                tile_map[tile_idx] = {'link': None, 'title': None}
            
            if elem.tag_name.lower() == 'a':
                href = elem.get_attribute('href')
                if href and '/concept/' in href:
                    tile_map[tile_idx]['link'] = href
                    if elem.text:
                        tile_map[tile_idx]['title'] = elem.text.split('\n')[0].strip()

        for idx in sorted(tile_map.keys()):
            data = tile_map[idx]
            if not data.get('link'):
                continue
                
            href = data['link']
            title = data.get('title') or "Unknown Title"

            if f"/concept/{CONCEPT_ID}" in href:
                found_target = True
                print(f"   ✅ Crimson Desert를 {len(competitors_links) + 1}위에서 발견!")
                break

            if href not in [c.get('url') for c in competitors_links]:
                competitors_links.append({"url": href, "title": title})
                print(f"   ↳ [{len(competitors_links)}위] {title}")

        page += 1

    if not competitors_links:
        print(f"   ⚠️ {country} 경쟁작 없음")
        return []

    print(f"✅ {country} 경쟁작 {len(competitors_links)}개 수집 완료")

    # 할인 정보 확인
    final_results = []
    for idx, item in enumerate(competitors_links[:15]):   # 너무 많으면 상위 15개까지만 상세 확인
        rank = idx + 1
        print(f"   ↳ [{rank}위] {item['title']} → 할인 정보 확인...")
        deadline = get_discount_deadline(driver, item['url'])
        final_results.append({
            "rank": rank,
            "title": item['title'],
            "discount_info": deadline
        })
    
    return final_results


def save_data(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def send_discord(country_results):
    if not DISCORD_WEBHOOK:
        print("⚠️ DISCORD_WEBHOOK이 설정되지 않았습니다.")
        return

    report_lines = []
    total_competitors = 0

    for country, comps in country_results.items():
        if not comps:
            continue
        
        discounted_games = [g for g in comps if g['discount_info'] not in ("종료일 정보 없음", "확인 불가")]
        if not discounted_games:
            continue

        flag = FLAGS.get(country, "")
        report_lines.append(f"**{flag} {country}** (붉은사막 도달 전)")
        
        for game in discounted_games:
            total_competitors += 1
            report_lines.append(f"> `{game['rank']}위` {game['title']} - ⏰ {game['discount_info']}")
        report_lines.append("")

    if not report_lines:
        print("ℹ️ 현재 할인 중인 경쟁작이 없습니다.")
        return

    desc = f"📊 **총 {total_competitors}개의 경쟁작이 할인 진행 중입니다.**\n\n" + "\n".join(report_lines)
    
    CHUNK_LIMIT = 4000
    chunks = [desc[i:i+CHUNK_LIMIT] for i in range(0, len(desc), CHUNK_LIMIT)]

    for chunk in chunks:
        requests.post(DISCORD_WEBHOOK, json={"embeds": [{
            "title": "⚔️ Crimson Desert 경쟁작 할인 추적 리포트",
            "description": chunk,
            "color": 0xFFD700,
            "timestamp": datetime.now(KST).isoformat()
        }]})
        time.sleep(1)


def main():
    print("=" * 70)
    print("⚔️ Crimson Desert 경쟁작 추적기 (최종 최적화 v2.3)")
    print("=" * 70)
    print("예상 실행 시간: 8~15분 정도")

    driver = setup_driver()
    country_results = {}

    try:
        all_countries = [c for region in REGIONS.values() for c in region]
        for country in all_countries:
            if country in SKIP_COUNTRIES:
                continue
            competitors = crawl_competitors(driver, country)
            if competitors:
                country_results[country] = competitors
    finally:
        driver.quit()

    save_data({
        "timestamp": datetime.now(KST).isoformat(),
        "results": country_results
    })

    send_discord(country_results)
    print("🎉 작업 완료!")


if __name__ == "__main__":
    main()
