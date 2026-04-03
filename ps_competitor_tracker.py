#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PS Store 경쟁작 추적기 - Crimson Desert (수정판)
"""

import time
import os
import json
import requests
import re  # ← 추가
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

REGIONS = { ... }  # 기존 그대로

FLAGS = { ... }  # 기존 그대로

LOCALE_MAP = { ... }  # 기존 그대로

SKIP_COUNTRIES = {"중국"}
MAX_PAGES = 10

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
HISTORY_FILE = "competitor_history.json"

# =============================================================================
# 유틸리티 & 드라이버
# =============================================================================

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def get_browse_url(country, page=1):
    locale = LOCALE_MAP.get(country)
    return f"https://store.playstation.com/{locale}/pages/browse/{page}" if locale else None

# =============================================================================
# 크롤링
# =============================================================================

def get_discount_deadline(driver, url):
    try:
        driver.get(url)
        time.sleep(4)  # 상세 페이지 로딩 안정화
        
        # 기존 CSS + 전체 텍스트 검색 (현재 UI에서도 잘 잡힘)
        deadline_elements = driver.find_elements(By.CSS_SELECTOR, 
            "[data-qa*='discount-descriptor'], [class*='pdp-discount'], [class*='price'], [data-qa*='offer']")
        
        if deadline_elements:
            text = deadline_elements[0].text.strip()
            if any(kw in text.lower() for kw in ["ends", "종료", "offer ends", "save"]):
                return text
        
        # 전체 페이지 텍스트에서 가장 적합한 라인 찾기
        page_text = driver.find_element(By.TAG_NAME, "body").text
        for line in page_text.split('\n'):
            line = line.strip()
            if any(kw in line.lower() for kw in ["ends", "endet am", "종료", "termina", "fin", "scade", "終了"]):
                return line
                
        return "종료일 정보 없음"
    except:
        return "확인 불가"


def crawl_competitors(driver, country):
    total_rank = 0
    target = f"/concept/{CONCEPT_ID}"
    competitors_links = []
    page = 1
    found_target = False

    print(f"    🔎 {country} Best Selling 목록 탐색 (최대 {MAX_PAGES}페이지)")

    while page <= MAX_PAGES and not found_target:
        driver.get(get_browse_url(country, page))
        time.sleep(7 if page == 1 else 5)  # 첫 페이지 로딩 여유

        # productTile 번호로 타일 그룹핑 → 정확한 순서 보장
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
            
            # 게임 링크 발견
            if elem.tag_name == 'a' and '/concept/' in (elem.get_attribute('href') or ''):
                href = elem.get_attribute('href')
                tile_map[tile_idx]['link'] = href
                # title은 링크 텍스트에서 첫 번째 줄 (기존 방식 그대로)
                if elem.text:
                    tile_map[tile_idx]['title'] = elem.text.split('\n')[0].strip()
        
        # 타일 번호 순서대로 처리 (Best Selling 순위 순)
        for idx in sorted(tile_map.keys()):
            data = tile_map[idx]
            if not data['link']:
                continue
            href = data['link']
            title = data['title'] or "Unknown Title"
            
            if target in href:
                found_target = True
                break
            
            if href not in [c['url'] for c in competitors_links]:
                competitors_links.append({"url": href, "title": title})
                total_rank += 1
                print(f"      ↳ [{total_rank}위] {title}")
        
        page += 1

    if not competitors_links:
        print(f"    ⚠️ {country}에서 Crimson Desert보다 높은 순위 경쟁작을 찾지 못했습니다.")
        return [], "not_found"
    
    print(f"    ✅ {country} 경쟁작 {len(competitors_links)}개 수집 완료")
    
    # 상세 페이지에서 할인 종료일 추출
    final_results = []
    for idx, item in enumerate(competitors_links):
        rank = idx + 1
        print(f"    ↳ [{rank}위] {item['title']} → 할인 정보 확인 중...")
        deadline = get_discount_deadline(driver, item['url'])
        final_results.append({
            "rank": rank,
            "title": item['title'],
            "discount_info": deadline
        })
    
    return final_results, "found"


# =============================================================================
# 메인 & 알림 발송
# =============================================================================

def save_data(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def send_discord(country_results):
    if not DISCORD_WEBHOOK:
        return

    report_lines = []
    total_competitors = 0

    for country, comps in country_results.items():
        if not comps:
            continue
        
        # 🔥 수정: 실제 할인 정보가 있는 게임만 필터링
        discounted_games = [g for g in comps 
                           if g['discount_info'] not in ("종료일 정보 없음", "확인 불가")]
        
        if not discounted_games:
            continue

        flag = FLAGS.get(country, "")
        report_lines.append(f"**{flag} {country}** (붉은사막 도달 전)")
        
        for game in discounted_games:
            total_competitors += 1
            report_lines.append(f"> `{game['rank']}위` {game['title']} - ⏰ {game['discount_info']}")
        report_lines.append("")

    if not report_lines:
        print("ℹ️ 알림을 보낼 할인 중인 경쟁작이 없습니다.")
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
    print("=" * 60)
    print("⚔️ Crimson Desert 경쟁작 추적기 (수정판)")
    print("=" * 60)

    driver = setup_driver()
    country_results = {}

    try:
        all_countries = [c for region in REGIONS.values() for c in region]
        for country in all_countries:
            if country in SKIP_COUNTRIES:
                continue
            print(f"🔍 {country} 탐색 중...")
            competitors, status = crawl_competitors(driver, country)
            if competitors:
                country_results[country] = competitors

    finally:
        driver.quit()

    save_data({
        "timestamp": datetime.now(KST).isoformat(),
        "results": country_results
    })

    send_discord(country_results)


if __name__ == "__main__":
    main()
