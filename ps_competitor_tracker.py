#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PS Store 경쟁작 추적기 - Crimson Desert
각 국가별 베스트셀러 순위에서 붉은사막보다 순위가 높은 게임들의 목록과 할인 종료 일자를 추적합니다.
"""

import time
import os
import json
import requests
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

CONCEPT_ID = "10002363" # Crimson Desert

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
MAX_PAGES = 10 # 붉은사막 도달 전까지만 탐색하므로 페이지를 얕게 잡습니다.

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
HISTORY_FILE = "competitor_history.json"

# 할인 종료 안내 텍스트 다국어 키워드
DISCOUNT_KEYWORDS = ["종료", "ends", "termina", "fin", "ende", "scade", "終了", "%"]

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
    """
    게임 상세 페이지에 접속하여 할인 종료 날짜를 정밀하게 추출합니다.
    """
    try:
        driver.get(url)
        time.sleep(3) # 상세 페이지 로딩 대기
        
        # 할인 종료일이 포함된 전형적인 태그/텍스트 탐색
        # 스크린샷의 "Angebot endet am..." 또는 "Offer ends..." 등을 찾습니다.
        deadline_elements = driver.find_elements(By.CSS_SELECTOR, "[data-qa*='discount-descriptor'], [class*='pdp-discount-availability']")
        
        if deadline_elements:
            return deadline_elements[0].text.strip()
            
        # 태그로 못 찾을 경우, 페이지 전체 텍스트에서 '종료' 관련 키워드 검색
        page_text = driver.find_element(By.TAG_NAME, "body").text
        for line in page_text.split('\n'):
            if any(kw in line.lower() for kw in ["ends", "endet am", "종료", "termina"]):
                return line.strip()
                
        return "종료일 정보 없음"
    except:
        return "확인 불가"

def crawl_competitors(driver, country):
    total_rank = 0
    target = f"/concept/{CONCEPT_ID}"
    competitors_links = []

    # 1. 먼저 목록에서 붉은사막 전까지의 링크를 모두 수집
    driver.get(get_browse_url(country))
    time.sleep(5)
    
    links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/concept/']")
    for link in links:
        href = link.get_attribute("href") or ""
        if target in href: break # 붉은사막 발견 시 중단
        if href not in [c['url'] for c in competitors_links]:
            competitors_links.append({"url": href, "title": link.text.split('\n')[0]})

    # 2. 수집된 각 링크에 접속하여 상세 정보 파싱
    final_results = []
    for idx, item in enumerate(competitors_links):
        rank = idx + 1
        print(f"    ↳ [{rank}위] {item['title']} 상세 분석 중...")
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

    # 할인 중인 게임이 하나라도 존재하는 국가만 필터링
    report_lines = []
    total_competitors = 0

    for country, comps in country_results.items():
        if not comps:
            continue
        
        # '할인 없음'이 아닌 게임들만 필터링
        discounted_games = [g for g in comps if g['discount_info'] != "할인 없음"]
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
    
    # 디스코드 메시지 글자 수 제한(4096자) 방어
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
    print("⚔️ Crimson Desert 경쟁작 추적기")
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
            
            if competitors is not None:
                country_results[country] = competitors

    finally:
        driver.quit()

    # 데이터 저장 및 자동 푸시 타겟 파일 생성
    save_data({
        "timestamp": datetime.now(KST).isoformat(),
        "results": country_results
    })

    send_discord(country_results)

if __name__ == "__main__":
    main()
