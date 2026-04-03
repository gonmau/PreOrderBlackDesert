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

LOCALE_MAP = {
    "미국": "en-us", "캐나다": "en-ca", "브라질": "pt-br", "멕시코": "es-mx",
    "아르헨티나": "es-ar", "칠레": "es-cl", "콜롬비아": "es-co", "페루": "es-pe",
    "우루과이": "es-uy", "볼리비아": "es-bo", "과테말라": "es-gt", "온두라스": "es-hn",
    "코스타리카": "es-cr", "에콰도르": "es-ec", "엘살바도르": "es-sv",
    "니카라과": "es-ni", "파나마": "es-pa", "파라과이": "es-py",
    "영국": "en-gb", "독일": "de-de", "프랑스": "fr-fr", "스페인": "es-es",
    "이탈리아": "it-it", "네덜란드": "nl-nl", "폴란드": "pl-pl", "스위스": "de-ch",
    "스웨덴": "sv-se", "노르웨이": "no-no", "덴마크": "en-dk", "핀란드": "fi-fi",
    "포르투갈": "pt-pt", "그리스": "en-gr", "체코": "en-cz", "헝가리": "en-hu",
    "루마니아": "en-ro", "슬로바키아": "en-sk", "슬로베니아": "en-si",
    "우크라이나": "ru-ua", "사우디아라비아": "en-sa", "아랍에미리트": "en-ae",
    "남아공": "en-za", "터키": "en-tr", "벨기에": "nl-be", "오스트리아": "de-at",
    "이스라엘": "en-il", "크로아티아": "en-hr", "불가리아": "en-bg",
    "키프로스": "en-cy", "아이슬란드": "en-is", "아일랜드": "en-ie",
    "쿠웨이트": "en-kw", "레바논": "en-lb", "룩셈부르크": "de-lu",
    "몰타": "en-mt", "오만": "en-om", "카타르": "en-qa", "바레인": "en-bh",
    "일본": "ja-jp", "한국": "ko-kr", "중국": "zh-cn", "호주": "en-au",
    "인도": "en-in", "태국": "en-th", "싱가포르": "en-sg", "말레이시아": "en-my",
    "인도네시아": "en-id", "필리핀": "en-ph", "베트남": "en-vn",
    "홍콩": "en-hk", "대만": "zh-hant-tw", "뉴질랜드": "en-nz",
}

REGIONS = {
    "Americas": ["미국", "캐나다", "브라질", "멕시코", "아르헨티나", "칠레", "콜롬비아", "페루", "우루과이", "볼리비아", "과테말라", "온두라스", "코스타리카", "에콰도르", "엘살바도르", "니카라과", "파나마", "파라과이"],
    "Europe & Middle East": ["영국", "독일", "프랑스", "스페인", "이탈리아", "네덜란드", "폴란드", "스위스", "스웨덴", "노르웨이", "덴마크", "핀란드", "포르투갈", "그리스", "체코", "헝가리", "루마니아", "슬로바키아", "슬로베니아", "우크라이나", "벨기에", "오스트리아", "이스라엘", "크로아티아", "불가리아", "키프로스", "아이슬란드", "아일랜드", "룩셈부르크", "몰타", "사우디아라비아", "아랍에미리트", "남아공", "터키", "쿠웨이트", "레바논", "오만", "카타르", "바레인"],
    "Asia & Oceania": ["일본", "한국", "중국", "호주", "인도", "태국", "싱가포르", "말레이시아", "인도네시아", "필리핀", "베트남", "홍콩", "대만", "뉴질랜드"],
}

FLAGS = {
    "미국": "🇺🇸", "캐나다": "🇨🇦", "브라질": "🇧🇷", "멕시코": "🇲🇽", "아르헨티나": "🇦🇷", "칠레": "🇨🇱", "콜롬비아": "🇨🇴", "페루": "🇵🇪", "우루과이": "🇺🇾",
    "볼리비아": "🇧🇴", "과테말라": "🇬🇹", "온두라스": "🇭🇳", "코스타리카": "🇨🇷", "에콰도르": "🇪🇨", "엘살바도르": "🇸🇻", "니카라과": "🇳🇮", "파나마": "🇵🇦", "파라과이": "🇵🇾",
    "영국": "🇬🇧", "독일": "🇩🇪", "프랑스": "🇫🇷", "스페인": "🇪🇸", "이탈리아": "🇮🇹", "네덜란드": "🇳🇱", "폴란드": "🇵🇱", "스위스": "🇨🇭", "스웨덴": "🇸🇪", "노르웨이": "🇳🇴",
    "덴마크": "🇩🇰", "핀란드": "🇫🇮", "포르투갈": "🇵🇹", "그리스": "🇬🇷", "체코": "🇨🇿", "헝가리": "🇭🇺", "루마니아": "🇷🇴", "슬로바키아": "🇸🇰", "슬로베니아": "🇸🇮", "우크라이나": "🇺🇦",
    "벨기에": "🇧🇪", "오스트리아": "🇦🇹", "이스라엘": "🇮🇱", "크로아티아": "🇭🇷", "불가리아": "🇧🇬", "키프로스": "🇨🇾", "아이슬란드": "🇮🇸", "아일랜드": "🇮🇪", "룩셈부르크": "🇱🇺", "몰타": "🇲🇹",
    "사우디아라비아": "🇸🇦", "아랍에미리트": "🇦🇪", "남아공": "🇿🇦", "터키": "🇹🇷", "쿠웨이트": "🇰🇼", "레바논": "🇱🇧", "오만": "🇴🇲", "카타르": "🇶🇦", "바레인": "🇧🇭",
    "일본": "🇯🇵", "한국": "🇰🇷", "중국": "🇨🇳", "호주": "🇦🇺", "인도": "🇮🇳", "태국": "🇹🇭", "싱가포르": "🇸🇬", "말레이시아": "🇲🇾", "인도네시아": "🇮🇩", "필리핀": "🇵🇭",
    "베트남": "🇻🇳", "홍콩": "🇭🇰", "대만": "🇹🇼", "뉴질랜드": "🇳🇿",
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
    browse 페이지에서 타일 정보 추출.
    DOM 구조:
      - 타일 루트: data-qa="ems-sdk-grid#productTileN" (div)
      - 링크:      <a href="/concept/..."> (data-qa 없음, 타일 내부)
      - 타이틀:    data-qa="ems-sdk-grid#productTileN#product-name" (span)
      - 할인 뱃지: data-qa="ems-sdk-grid#productTileN#discount-badge"
    반환: list of {tile_idx, url, title, has_discount}
    """
    tile_map = {}

    # 타일 루트 div만 수집 (하위 요소 제외하기 위해 정확히 "#productTileN" 끝나는 것)
    root_elems = driver.find_elements(By.CSS_SELECTOR, '[data-qa*="productTile"]')
    for elem in root_elems:
        qa = elem.get_attribute('data-qa') or ''
        # "ems-sdk-grid#productTileN" 형태만 (하위 #product-name 등 제외)
        match = re.search(r'productTile(\d+)$', qa)
        if not match:
            continue
        tile_idx = int(match.group(1))
        if tile_idx not in tile_map:
            tile_map[tile_idx] = {'url': None, 'title': None, 'has_discount': False}

        # 타일 div 텍스트 첫 줄 = 게임명 (fallback)
        text = elem.text.strip()
        if text and not tile_map[tile_idx]['title']:
            tile_map[tile_idx]['title'] = text.split('\n')[0].strip()

    # 링크: /concept/ href를 가진 <a> 태그 → 타일과 매칭
    # <a>는 data-qa가 없으므로 텍스트(게임명)로 타일과 연결
    links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/concept/"]')
    for a in links:
        href = a.get_attribute('href') or ''
        title = a.text.strip()
        # 타일맵에서 같은 게임명 찾기
        for idx, d in tile_map.items():
            if d['url']:
                continue
            if d['title'] and title and d['title'].startswith(title[:20]):
                d['url'] = href
                break
        else:
            # 매칭 실패 시 순서대로 빈 슬롯에 채우기
            for idx in sorted(tile_map.keys()):
                if not tile_map[idx]['url']:
                    tile_map[idx]['url'] = href
                    if title:
                        tile_map[idx]['title'] = title
                    break

    # 할인 뱃지: data-qa*="discount-badge" 요소
    badge_elems = driver.find_elements(By.CSS_SELECTOR, '[data-qa*="discount-badge"]')
    for elem in badge_elems:
        qa = elem.get_attribute('data-qa') or ''
        match = re.search(r'productTile(\d+)', qa)
        if match:
            tile_idx = int(match.group(1))
            if tile_idx in tile_map:
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
    상세 페이지에서 "Offer ends ..." 텍스트 추출.
    data-qa 기반 타깃 셀렉터만 사용 (전체 span/p 순회 제거 → 빠름).
    """
    try:
        driver.get(url)
        try:
            WebDriverWait(driver, 7).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-qa*="mfe-purchase"], [data-qa*="price"]'))
            )
        except:
            time.sleep(2)

        # 구매/가격 블록 전체 텍스트에서 줄 단위 탐색
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
            if OFFER_ENDS_PATTERNS.search(text) and len(text) < 150:
                return text

        # fallback: Save X% (종료일 없어도 할인 확인)
        for elem in candidates:
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
    cd_rank = None

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
            time.sleep(2)
            tiles = parse_browse_page(driver)
            if not tiles:
                break

        for tile in tiles:
            if f"/concept/{CONCEPT_ID}" in tile['url']:
                found_target = True
                cd_rank = len(all_tiles) + 1
                print(f" → 붉사 {cd_rank}위!", flush=True)
                break
            all_tiles.append(tile)

        if not found_target:
            page += 1
            time.sleep(1.5)

    if not found_target:
        print(f" → 미발견 (최대 {MAX_PAGES}페이지)", flush=True)

    if not all_tiles:
        return {"cd_rank": cd_rank, "games": []}

    for i, tile in enumerate(all_tiles):
        tile['rank'] = i + 1

    discounted = [t for t in all_tiles if t['has_discount']]
    non_discounted = [t for t in all_tiles if not t['has_discount']]

    print(f"   전체 {len(all_tiles)}개 중 할인 뱃지 {len(discounted)}개 → 상세 확인")

    final_results = []

    for tile in discounted:
        rank = tile['rank']
        print(f"   ↳ [{rank}위] {tile['title'][:40]} → Offer ends 확인...")
        deadline = get_discount_deadline(driver, tile['url'])
        final_results.append({
            "rank": rank,
            "title": tile['title'],
            "discount_info": deadline,
            "has_badge": True
        })

    for tile in non_discounted:
        final_results.append({
            "rank": tile['rank'],
            "title": tile['title'],
            "discount_info": "할인 없음",
            "has_badge": False
        })

    final_results.sort(key=lambda x: x['rank'])
    return {"cd_rank": cd_rank, "games": final_results}


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

    # 국가별 embed 생성 (나라 하나 = embed 하나 → 잘림 없음)
    embeds = []
    total_countries = 0

    for country, data in country_results.items():
        cd_rank = data.get("cd_rank")
        comps = data.get("games", [])

        active = [g for g in comps if g.get('has_badge') and not g['discount_info'].startswith("할인 없음") and not g['discount_info'].startswith("확인 불가")]
        badge_only = [g for g in comps if g.get('has_badge') and g['discount_info'] == "종료일 정보 없음"]

        if not active and not badge_only:
            continue

        total_countries += 1
        flag = FLAGS.get(country, "")
        lines = []

        for game in sorted(active + badge_only, key=lambda x: x['rank']):
            if game['discount_info'] == "종료일 정보 없음":
                lines.append(f"`{game['rank']}위` {game['title']} — 💸 할인 중 (종료일 미확인)")
            else:
                lines.append(f"`{game['rank']}위` {game['title']} — ⏰ {game['discount_info']}")

        cd_str = f" | 붉사 **{cd_rank}위**" if cd_rank else " | 붉사 미진입(8p↓)"
        title_str = f"{flag} {country}{cd_str}"

        embeds.append({
            "title": title_str,
            "description": "\n".join(lines),
            "color": 0xFFD700,
        })

    if not embeds:
        print("ℹ️ 현재 할인 중인 경쟁작이 없습니다.")
        requests.post(DISCORD_WEBHOOK, json={"embeds": [{
            "title": "⚔️ Crimson Desert 경쟁작 할인 추적",
            "description": "현재 할인 중인 경쟁작이 없습니다.",
            "color": 0x808080,
            "timestamp": datetime.now(KST).isoformat()
        }]})
        return

    # 헤더 embed
    header = {
        "title": "⚔️ Crimson Desert 경쟁작 할인 추적 리포트",
        "description": f"📊 **{total_countries}개국**에서 할인 경쟁작 발견",
        "color": 0xFF4500,
        "timestamp": datetime.now(KST).isoformat()
    }

    # Discord: 한 번에 최대 10개 embed
    all_embeds = [header] + embeds
    for i in range(0, len(all_embeds), 10):
        chunk = all_embeds[i:i+10]
        requests.post(DISCORD_WEBHOOK, json={"embeds": chunk})
        time.sleep(0.5)


# =============================================================================
# main
# =============================================================================

def main():
    print("=" * 70)
    print("⚔️ Crimson Desert 경쟁작 추적기 v3.1")
    print("=" * 70)

    t0 = time.time()
    driver = setup_driver()
    country_results = {}

    try:
        all_countries = [c for region in REGIONS.values() for c in region]
        for i, country in enumerate(all_countries):
            if country in SKIP_COUNTRIES:
                continue
            result = crawl_competitors(driver, country)
            country_results[country] = result
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
