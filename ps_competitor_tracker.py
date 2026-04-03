#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PS Store 경쟁작 추적기 - Crimson Desert (v3.0 고속화)
개선점:
  - browse 타일에서 할인 뱃지 직접 감지 → 할인 없는 게임 상세 방문 스킵
  - 상세 페이지 셀렉터 정확도 대폭 향상 (data-qa 기반)
  - page_source 파싱으로 DOM 쿼리 최소화
  - sleep 최적화
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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

# "Offer ends" 패턴 - 다국어 지원
OFFER_ENDS_PATTERNS = re.compile(
    r'(offer ends?|ends?|sale ends?|종료|까지|fin\s*le|endet am|termina el|scade il|終了|有効期限)',
    re.IGNORECASE
)

# =============================================================================
# 드라이버 설정
# =============================================================================

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--blink-settings=imagesEnabled=false')  # 이미지 로드 비활성화 → 빠름
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-gpu')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(20)
    return driver

def get_browse_url(country, page=1):
    locale = LOCALE_MAP.get(country)
    return f"https://store.playstation.com/{locale}/pages/browse/{page}" if locale else None

def wait_for_tiles(driver, timeout=8):
    """타일이 최소 1개 이상 로드될 때까지 대기 (최대 timeout초)"""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-qa*="productTile"]'))
        )
    except:
        pass

# =============================================================================
# browse 페이지 파싱 (BeautifulSoup, 빠름)
# =============================================================================

def parse_browse_page(driver):
    """
    browse 페이지에서 타일 정보 추출 (Selenium DOM 직접 사용).
    반환: list of {tile_idx, url, title, has_discount}
    """
    tile_map = {}
    elements = driver.find_elements(By.CSS_SELECTOR, '[data-qa*="productTile"]')

    for elem in elements:
        qa = elem.get_attribute('data-qa') or ''
        match = re.search(r'productTile(\d+)', qa)
        if not match:
            continue
        tile_idx = int(match.group(1))

        if tile_idx not in tile_map:
            tile_map[tile_idx] = {'url': None, 'title': None, 'has_discount': False}

        # 링크 + 타이틀
        if elem.tag_name.lower() == 'a':
            href = elem.get_attribute('href') or ''
            if '/concept/' in href and not tile_map[tile_idx]['url']:
                tile_map[tile_idx]['url'] = href
                text = elem.text.strip()
                if text:
                    tile_map[tile_idx]['title'] = text.split('\n')[0].strip()

        # 할인 뱃지 감지: 텍스트에 "-숫자%" 또는 data-qa에 discount
        elem_text = elem.text or ''
        if re.search(r'-\d+%', elem_text) or 'discount' in qa.lower():
            tile_map[tile_idx]['has_discount'] = True

    results = []
    for idx in sorted(tile_map.keys()):
        d = tile_map[idx]
        if d['url']:
            results.append({
                'tile_idx': idx,
                'url': d['url'],
                'title': d['title'] or 'Unknown',
                'has_discount': d['has_discount']
            })
    return results

# =============================================================================
# 상세 페이지 할인 종료일 추출 (정확한 셀렉터)
# =============================================================================

def get_discount_deadline(driver, url):
    """
    상세 페이지에서 "Offer ends ..." 텍스트 추출 (Selenium DOM).
    """
    try:
        driver.get(url)
        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-qa*="mfe-purchase"], [data-qa*="price"]'))
            )
        except:
            time.sleep(3)

        # 전략 1: data-qa에 purchase/price/offer/discount 포함 요소
        candidates = driver.find_elements(By.CSS_SELECTOR,
            '[data-qa*="mfe-purchase"], [data-qa*="price"], [data-qa*="offer"], [data-qa*="discount"]')

        for elem in candidates:
            text = elem.text.strip()
            if not text:
                continue
            for line in text.split('\n'):
                line = line.strip()
                if OFFER_ENDS_PATTERNS.search(line) and len(line) > 5:
                    return line
            # 패턴은 있지만 줄 분리 안 된 경우
            if OFFER_ENDS_PATTERNS.search(text) and len(text) < 150:
                return text

        # 전략 2: 페이지 전체 span/p 중 짧고 날짜 포함된 텍스트
        for elem in driver.find_elements(By.CSS_SELECTOR, 'span, p'):
            text = elem.text.strip()
            if len(text) < 150 and OFFER_ENDS_PATTERNS.search(text):
                if re.search(r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{4}년|\d+월', text):
                    return text

        # 전략 3: "Save X%" 텍스트 (종료일 없어도 할인 확인)
        for elem in driver.find_elements(By.CSS_SELECTOR, 'span, p'):
            text = elem.text.strip()
            if re.search(r'save\s+\d+%', text, re.IGNORECASE) and len(text) < 200:
                return text

        return "종료일 정보 없음"

    except Exception as e:
        return f"확인 불가({str(e)[:30]})"

# =============================================================================
# 경쟁작 크롤링 (v3.0 고속화)
# =============================================================================

def crawl_competitors(driver, country):
    """
    1단계: browse 페이지에서 Crimson Desert 앞 게임 + 할인 뱃지 여부 수집
    2단계: 할인 뱃지 있는 게임만 상세 페이지 방문 → Offer ends 추출
    """
    all_tiles = []   # Crimson Desert 도달 전 전체 타일
    page = 1
    found_target = False

    print(f"🔍 {country} 탐색 중...", end="", flush=True)

    while page <= MAX_PAGES and not found_target:
        url = get_browse_url(country, page)
        if not url:
            break

        try:
            driver.get(url)
            wait_for_tiles(driver, timeout=8)
        except Exception:
            break

        tiles = parse_browse_page(driver)

        if not tiles:
            # 타일 파싱 실패 → 짧게 재대기 후 재시도
            time.sleep(2)
            tiles = parse_browse_page(driver)
            if not tiles:
                break

        for tile in tiles:
            if f"/concept/{CONCEPT_ID}" in tile['url']:
                found_target = True
                print(f" → {len(all_tiles)+1}위에서 발견!", flush=True)
                break
            all_tiles.append(tile)

        if not found_target:
            page += 1
            time.sleep(1.5)  # 페이지 간 최소 대기

    if not found_target:
        print(f" → 미발견 (최대 {MAX_PAGES}페이지)", flush=True)

    if not all_tiles:
        return []

    # 할인 뱃지 있는 게임만 필터 (상세 방문 대상)
    discounted = [t for t in all_tiles if t['has_discount']]
    non_discounted = [t for t in all_tiles if not t['has_discount']]

    print(f"   전체 {len(all_tiles)}개 중 할인 뱃지 {len(discounted)}개 → 상세 확인")

    final_results = []

    # 할인 뱃지 있는 게임: 상세 페이지 방문
    for tile in discounted:
        rank = tile['tile_idx'] + 1  # tile_idx는 0-based
        print(f"   ↳ [{rank}위] {tile['title'][:40]} → Offer ends 확인...")
        deadline = get_discount_deadline(driver, tile['url'])
        final_results.append({
            "rank": rank,
            "title": tile['title'],
            "discount_info": deadline,
            "has_badge": True
        })

    # 할인 뱃지 없는 게임: 상세 방문 없이 기록 (선택: 보고서에서 제외 가능)
    for tile in non_discounted:
        rank = tile['tile_idx'] + 1
        final_results.append({
            "rank": rank,
            "title": tile['title'],
            "discount_info": "할인 없음",
            "has_badge": False
        })

    # rank 순 정렬
    final_results.sort(key=lambda x: x['rank'])
    return final_results


# =============================================================================
# 저장 / Discord 전송
# =============================================================================

def save_data(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def send_discord(country_results):
    if not DISCORD_WEBHOOK:
        print("⚠️ DISCORD_WEBHOOK이 설정되지 않았습니다.")
        return

    report_lines = []
    total_discounted = 0

    for country, comps in country_results.items():
        if not comps:
            continue

        # 할인 뱃지 있고, 종료일 정보가 있는 것만
        active = [g for g in comps if g.get('has_badge') and g['discount_info'] not in ("종료일 정보 없음", "확인 불가", "할인 없음") and not g['discount_info'].startswith("확인 불가")]
        # 뱃지는 있지만 종료일 파싱 못한 것 (할인 중이긴 함)
        badge_only = [g for g in comps if g.get('has_badge') and g['discount_info'] in ("종료일 정보 없음",)]

        if not active and not badge_only:
            continue

        flag = FLAGS.get(country, "")
        lines_for_country = []

        for game in active:
            total_discounted += 1
            lines_for_country.append(f"> `{game['rank']}위` {game['title']} — ⏰ {game['discount_info']}")

        for game in badge_only:
            total_discounted += 1
            lines_for_country.append(f"> `{game['rank']}위` {game['title']} — 💸 할인 중 (종료일 미확인)")

        if lines_for_country:
            report_lines.append(f"**{flag} {country}**")
            report_lines.extend(lines_for_country)
            report_lines.append("")

    if not report_lines:
        print("ℹ️ 현재 할인 중인 경쟁작이 없습니다.")
        # 빈 알림도 발송 (확인용)
        requests.post(DISCORD_WEBHOOK, json={"embeds": [{
            "title": "⚔️ Crimson Desert 경쟁작 할인 추적",
            "description": "현재 할인 중인 경쟁작이 없습니다.",
            "color": 0x808080,
            "timestamp": datetime.now(KST).isoformat()
        }]})
        return

    desc = f"📊 **{total_discounted}개 경쟁작 할인 중**\n\n" + "\n".join(report_lines)

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


# =============================================================================
# main
# =============================================================================

def main():
    print("=" * 70)
    print("⚔️ Crimson Desert 경쟁작 추적기 v3.0 (고속화)")
    print("=" * 70)
    print("예상 실행 시간: 3~7분 (할인작 수에 따라 변동)")

    t0 = time.time()
    driver = setup_driver()
    country_results = {}

    try:
        all_countries = [c for region in REGIONS.values() for c in region]
        for i, country in enumerate(all_countries):
            if country in SKIP_COUNTRIES:
                continue
            competitors = crawl_competitors(driver, country)
            if competitors:
                country_results[country] = competitors
            elapsed = time.time() - t0
            remaining = len(all_countries) - i - 1
            print(f"   ⏱ 경과 {elapsed:.0f}s | 남은 국가 {remaining}개")
    finally:
        driver.quit()

    save_data({
        "timestamp": datetime.now(KST).isoformat(),
        "results": country_results
    })

    send_discord(country_results)

    total = time.time() - t0
    print(f"🎉 완료! 총 소요: {total:.0f}초 ({total/60:.1f}분)")


if __name__ == "__main__":
    main()
