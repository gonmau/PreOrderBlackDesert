#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PS Store 전체 베스트셀러 순위 추적기 - Crimson Desert
전체 베스트셀러 카테고리에서 게임이 발견될 때까지 페이지를 넘기며 순위를 추적합니다.
"""

import time
import os
import json
import shutil
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

REGIONS = {
    "Europe & Middle East": [
        "영국", "독일", "프랑스", "스페인", "이탈리아", "네덜란드",
        "폴란드", "스위스", "스웨덴", "노르웨이", "덴마크", "핀란드",
        "포르투갈", "그리스", "체코", "헝가리", "루마니아", "슬로바키아",
        "슬로베니아", "우크라이나", "사우디아라비아", "아랍에미리트", "남아공",
        "터키", "벨기에", "오스트리아", "이스라엘", "크로아티아", "불가리아",
        "키프로스", "아이슬란드", "아일랜드", "쿠웨이트", "레바논",
        "룩셈부르크", "몰타", "오만", "카타르", "바레인"
    ],
    "Americas": [
        "미국", "캐나다", "브라질", "멕시코", "아르헨티나", "칠레",
        "콜롬비아", "페루", "우루과이", "볼리비아", "과테말라", "온두라스",
        "코스타리카", "에콰도르", "엘살바도르", "니카라과", "파나마", "파라과이"
    ],
    "Asia & Oceania": [
        "일본", "한국", "중국", "호주", "인도", "태국", "싱가포르",
        "말레이시아", "인도네시아", "필리핀", "베트남", "홍콩", "대만",
        "뉴질랜드"
    ]
}

MARKET_WEIGHTS = {
    "미국": 30.0, "캐나다": 4.5, "브라질": 2.5, "멕시코": 2.0,
    "아르헨티나": 0.9, "칠레": 0.8, "콜롬비아": 0.7, "페루": 0.4,
    "우루과이": 0.3, "볼리비아": 0.2, "과테말라": 0.2, "온두라스": 0.2,
    "코스타리카": 0.2, "에콰도르": 0.3, "엘살바도르": 0.1, "니카라과": 0.1,
    "파나마": 0.2, "파라과이": 0.2,
    "영국": 8.5, "독일": 6.5, "프랑스": 6.0, "스페인": 4.0, "이탈리아": 3.5,
    "네덜란드": 1.8, "사우디아라비아": 1.5, "아랍에미리트": 1.2,
    "폴란드": 1.2, "스위스": 1.0, "스웨덴": 1.0, "덴마크": 0.9, "포르투갈": 0.8,
    "핀란드": 0.8, "노르웨이": 0.8, "남아공": 0.8, "체코": 0.7, "루마니아": 0.6,
    "그리스": 0.5, "헝가리": 0.5, "우크라이나": 0.5, "슬로바키아": 0.3,
    "슬로베니아": 0.3, "터키": 0.8, "벨기에": 1.2, "오스트리아": 1.0,
    "이스라엘": 0.8, "크로아티아": 0.2, "불가리아": 0.3, "키프로스": 0.1,
    "아이슬란드": 0.1, "아일랜드": 0.8, "쿠웨이트": 0.3, "레바논": 0.1,
    "룩셈부르크": 0.1, "몰타": 0.1, "오만": 0.2, "카타르": 0.3, "바레인": 0.2,
    "일본": 8.0, "호주": 3.0, "한국": 2.8, "인도": 2.0, "대만": 1.0,
    "싱가포르": 0.8, "태국": 0.9, "홍콩": 0.9, "인도네시아": 0.8,
    "말레이시아": 0.7, "베트남": 0.7, "필리핀": 0.6, "뉴질랜드": 0.6,
    "중국": 0.2
}

FLAGS = {
    "미국": "🇺🇸", "캐나다": "🇨🇦", "브라질": "🇧🇷", "멕시코": "🇲🇽",
    "아르헨티나": "🇦🇷", "칠레": "🇨🇱", "콜롬비아": "🇨🇴", "페루": "🇵🇪",
    "우루과이": "🇺🇾", "볼리비아": "🇧🇴", "과테말라": "🇬🇹", "온두라스": "🇭🇳",
    "코스타리카": "🇨🇷", "에콰도르": "🇪🇨", "엘살바도르": "🇸🇻",
    "니카라과": "🇳🇮", "파나마": "🇵🇦", "파라과이": "🇵🇾",
    "영국": "🇬🇧", "독일": "🇩🇪", "프랑스": "🇫🇷", "스페인": "🇪🇸",
    "이탈리아": "🇮🇹", "네덜란드": "🇳🇱", "폴란드": "🇵🇱", "스위스": "🇨🇭",
    "스웨덴": "🇸🇪", "노르웨이": "🇳🇴", "덴마크": "🇩🇰", "핀란드": "🇫🇮",
    "포르투갈": "🇵🇹", "그리스": "🇬🇷", "체코": "🇨🇿", "헝가리": "🇭🇺",
    "루마니아": "🇷🇴", "슬로바키아": "🇸🇰", "슬로베니아": "🇸🇮",
    "우크라이나": "🇺🇦", "사우디아라비아": "🇸🇦", "아랍에미리트": "🇦🇪",
    "남아공": "🇿🇦", "터키": "🇹🇷", "벨기에": "🇧🇪", "오스트리아": "🇦🇹",
    "이스라엘": "🇮🇱", "크로아티아": "🇭🇷", "불가리아": "🇧🇬",
    "키프로스": "🇨🇾", "아이슬란드": "🇮🇸", "아일랜드": "🇮🇪",
    "쿠웨이트": "🇰🇼", "레바논": "🇱🇧", "룩셈부르크": "🇱🇺",
    "몰타": "🇲🇹", "오만": "🇴🇲", "카타르": "🇶🇦", "바레인": "🇧🇭",
    "일본": "🇯🇵", "한국": "🇰🇷", "중국": "🇨🇳", "호주": "🇦🇺",
    "인도": "🇮🇳", "태국": "🇹🇭", "싱가포르": "🇸🇬", "말레이시아": "🇲🇾",
    "인도네시아": "🇮🇩", "필리핀": "🇵🇭", "베트남": "🇻🇳",
    "홍콩": "🇭🇰", "대만": "🇹🇼", "뉴질랜드": "🇳🇿",
}

# 각국 언어별 게임 검색어
SEARCH_TERMS = {
    "일본": ["crimson desert", "クリムゾンデザート", "紅の砂漠"],
    "중국": ["crimson desert", "红之沙漠"],
    "한국": ["crimson desert", "붉은사막"],
    "홍콩": ["crimson desert", "赤血沙漠"],
    "대만": ["crimson desert", "赤血沙漠"],
}
# 나머지 국가는 영어 검색어
ALL_COUNTRIES = set()
for region_countries in REGIONS.values():
    ALL_COUNTRIES.update(region_countries)
for country in ALL_COUNTRIES:
    if country not in SEARCH_TERMS:
        SEARCH_TERMS[country] = ["crimson desert"]

# Product ID로 에디션 구분
DELUXE_IDS   = {"0655875232157653", "0347209645474317"}
STANDARD_IDS = {"0470822165475407", "0469040252458022"}

# 전체 베스트셀러 카테고리 (출시 후 판매 순위)
BESTSELLER_CATEGORY = "e1699f77-77e1-43ca-a296-26d08abacb0f"

LOCALE_MAP = {
    "미국": "en-us", "캐나다": "en-ca", "브라질": "pt-br", "멕시코": "es-mx",
    "아르헨티나": "es-ar", "칠레": "es-cl", "콜롬비아": "es-co", "페루": "es-pe",
    "우루과이": "es-uy", "볼리비아": "es-bo", "과테말라": "es-gt", "온두라스": "es-hn",
    "코스타리카": "es-cr", "에콰도르": "es-ec", "엘살바도르": "es-sv",
    "니카라과": "es-ni", "파나마": "es-pa", "파라과이": "es-py",
    "영국": "en-gb", "독일": "de-de", "프랑스": "fr-fr", "스페인": "es-es",
    "이탈리아": "it-it", "네덜란드": "nl-nl", "폴란드": "pl-pl", "스위스": "de-ch",
    "스웨덴": "sv-se", "노르웨이": "no-no", "덴마크": "da-dk", "핀란드": "fi-fi",
    "포르투갈": "pt-pt", "그리스": "en-gr", "체코": "en-cz", "헝가리": "en-hu",
    "루마니아": "en-ro", "슬로바키아": "en-sk", "슬로베니아": "en-si",
    "우크라이나": "uk-ua", "사우디아라비아": "en-sa", "아랍에미리트": "en-ae",
    "남아공": "en-za", "터키": "en-tr", "벨기에": "nl-be", "오스트리아": "de-at",
    "이스라엘": "en-il", "크로아티아": "en-hr", "불가리아": "en-bg",
    "키프로스": "en-cy", "아이슬란드": "en-is", "아일랜드": "en-ie",
    "쿠웨이트": "en-kw", "레바논": "en-lb", "룩셈부르크": "fr-lu",
    "몰타": "en-mt", "오만": "en-om", "카타르": "en-qa", "바레인": "en-bh",
    "일본": "ja-jp", "한국": "ko-kr", "중국": "zh-cn", "호주": "en-au",
    "인도": "en-in", "태국": "en-th", "싱가포르": "en-sg", "말레이시아": "en-my",
    "인도네시아": "en-id", "필리핀": "en-ph", "베트남": "en-vn",
    "홍콩": "zh-hant-hk", "대만": "zh-hant-tw", "뉴질랜드": "en-nz",
}

# URL 조회 안 되거나 PS Store 미지원 국가 제외
# 실행 중 자동으로 감지되어 추가될 수도 있음
SKIP_COUNTRIES = {"중국", "베트남", "슬로베니아", "필리핀"}

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
HISTORY_FILE    = "bestseller_history.json"
BACKUP_FILE     = HISTORY_FILE + ".backup"

# 최대 탐색 페이지 수 (게임 미발견 시 여기까지만)
MAX_PAGES = 30

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
    return webdriver.Chrome(service=service, options=options)

# =============================================================================
# 크롤링
# =============================================================================

def get_bestseller_url(country, page=1):
    locale = LOCALE_MAP.get(country)
    if not locale:
        return None
    return f"https://store.playstation.com/{locale}/category/{BESTSELLER_CATEGORY}/{page}"

def crawl_country(driver, country):
    """
    전체 베스트셀러 카테고리에서 Crimson Desert를 발견할 때까지 페이지를 순회.
    - 게임 발견 시 → 순위 반환
    - MAX_PAGES까지 없으면 → None 반환 (차트권 밖)
    - 페이지 자체 로드 실패(URL 없음/스토어 미지원) → skip 처리
    """
    terms = SEARCH_TERMS.get(country, ["crimson desert"])
    total_rank = 0

    for page in range(1, MAX_PAGES + 1):
        url = get_bestseller_url(country, page)
        if not url:
            return None, "no_url"

        try:
            driver.get(url)
            time.sleep(3)

            items = driver.find_elements(
                By.CSS_SELECTOR,
                "li[data-qa*='grid-item'], a[href*='/product/']"
            )

            # 페이지에 아이템이 없으면 마지막 페이지 도달
            if not items:
                print(f"    ↳ {country}: {page}페이지 아이템 없음 → 탐색 종료 (차트권 밖)")
                return {"standard": None, "deluxe": None}, "not_found"

            page_has_items = False
            for item in items:
                try:
                    link_el = item if item.tag_name == 'a' else item.find_element(By.CSS_SELECTOR, "a")
                    href = link_el.get_attribute("href")
                    if not href or "/product/" not in href:
                        continue
                    page_has_items = True
                    total_rank += 1
                    label = (link_el.get_attribute("aria-label") or "").lower()
                    text  = (item.text or "").lower()

                    if any(t.lower() in label or t.lower() in text for t in terms):
                        pid = href.split("-")[-1]
                        edition = "deluxe" if pid in DELUXE_IDS else "standard"
                        print(f"    ✅ {country}: {edition} {total_rank}위 발견 (page {page})")
                        # 같은 페이지에서 다른 에디션도 확인
                        result = {"standard": None, "deluxe": None}
                        result[edition] = total_rank

                        # 나머지 아이템에서 두 번째 에디션 탐색
                        remaining_items = items[items.index(item)+1:]
                        for item2 in remaining_items:
                            try:
                                link2 = item2 if item2.tag_name == 'a' else item2.find_element(By.CSS_SELECTOR, "a")
                                href2 = link2.get_attribute("href")
                                if not href2 or "/product/" not in href2:
                                    continue
                                total_rank += 1
                                label2 = (link2.get_attribute("aria-label") or "").lower()
                                text2  = (item2.text or "").lower()
                                if any(t.lower() in label2 or t.lower() in text2 for t in terms):
                                    pid2 = href2.split("-")[-1]
                                    edition2 = "deluxe" if pid2 in DELUXE_IDS else "standard"
                                    if result[edition2] is None:
                                        result[edition2] = total_rank
                                    break
                            except:
                                continue
                        return result, "found"

                except:
                    continue

            if not page_has_items:
                print(f"    ↳ {country}: {page}페이지 유효 아이템 없음 → 탐색 종료")
                return {"standard": None, "deluxe": None}, "not_found"

            print(f"    {country}: page {page} 완료 ({total_rank}위까지 확인), 다음 페이지...")

        except Exception as e:
            print(f"    ⚠️ {country} page {page} 오류: {e}")
            # 첫 페이지부터 오류면 URL 자체 문제 → skip
            if page == 1:
                return None, "error"
            break

    print(f"    ↳ {country}: {MAX_PAGES}페이지({total_rank}위)까지 미발견")
    return {"standard": None, "deluxe": None}, "not_found"

# =============================================================================
# 계산 유틸
# =============================================================================

def calculate_combined_rank(standard, deluxe):
    if standard and deluxe:
        return min(standard, deluxe)
    return standard or deluxe

def calculate_avg(results):
    combined_sum, combined_w = 0, 0
    for c, data in results.items():
        if not data:
            continue
        w = MARKET_WEIGHTS.get(c, 1.0)
        combined = calculate_combined_rank(data.get('standard'), data.get('deluxe'))
        if combined:
            combined_sum += combined * w
            combined_w += w
    return combined_sum / combined_w if combined_w > 0 else None

def format_diff(current, previous):
    if previous is None or current is None:
        return ""
    diff = previous - current
    if diff > 0:   return f"▲{diff}"
    elif diff < 0: return f"▼{abs(diff)}"
    else:          return "0"

def get_emoji(diff_text):
    if not diff_text or diff_text == "0": return "⚪"
    elif "▲" in diff_text: return "🟢"
    elif "▼" in diff_text: return "🔴"
    return ""

# =============================================================================
# 히스토리 관리
# =============================================================================

def load_history_safe():
    def _try_load(path):
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else None
        except Exception as e:
            print(f"⚠️  {path} 로드 실패: {e}")
            return None

    history = _try_load(HISTORY_FILE)
    if history is not None:
        return history, False

    print(f"⚠️  메인 파일 로드 실패 → backup 복구 시도...")
    history = _try_load(BACKUP_FILE)
    if history is not None:
        shutil.copy2(BACKUP_FILE, HISTORY_FILE)
        print(f"✅  backup에서 복구 성공 ({len(history)}개 레코드)")
        return history, True

    # 둘 다 없으면 빈 히스토리로 시작
    print("ℹ️  히스토리 없음 → 새로 시작")
    return [], False

def save_history(history):
    if os.path.exists(HISTORY_FILE):
        shutil.copy2(HISTORY_FILE, BACKUP_FILE)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

# =============================================================================
# Discord 알림
# =============================================================================

def send_discord(results, combined_avg, skipped_countries, history):
    if not DISCORD_WEBHOOK:
        print("ℹ️  DISCORD_WEBHOOK 미설정, 알림 스킵")
        return

    prev_run = history[-2] if len(history) >= 2 else None
    prev_combined_avg = prev_run['averages'].get('combined') if prev_run else None
    combined_diff_text = format_diff(combined_avg, prev_combined_avg)

    tracked = len(results) - len(skipped_countries)
    found_count = sum(
        1 for v in results.values()
        if v and (v.get("standard") or v.get("deluxe"))
    )

    # 요약 메시지
    summary_desc = ""
    if combined_avg:
        summary_desc += f"📊 **전체 가중 평균**: `{combined_avg:.1f}위`"
        if combined_diff_text:
            summary_desc += f" ({combined_diff_text})"
        summary_desc += "\n"
    summary_desc += f"🌐 **추적 국가**: {tracked}개국 | **순위권 발견**: {found_count}개국\n\n"

    for region_name in ["Americas", "Europe & Middle East", "Asia & Oceania"]:
        region_countries = REGIONS[region_name]
        region_results = {c: results[c] for c in region_countries if c in results and results[c]}
        region_avg = calculate_avg(region_results)
        if region_avg:
            summary_desc += f"**{region_name}**: `{region_avg:.1f}위`\n"

    summary_payload = {
        "embeds": [{
            "title": "🎮 Crimson Desert 전체 베스트셀러 순위 리포트",
            "description": summary_desc,
            "color": 0xFF4500,
            "timestamp": datetime.now(KST).isoformat()
        }]
    }
    requests.post(DISCORD_WEBHOOK, json=summary_payload)
    time.sleep(1)

    # 지역별 상세
    for region_name, region_countries in REGIONS.items():
        lines = []
        sorted_countries = sorted(
            [c for c in region_countries if c in results],
            key=lambda x: MARKET_WEIGHTS.get(x, 0),
            reverse=True
        )

        for c in sorted_countries:
            if c in skipped_countries:
                continue
            curr_data = results.get(c) or {}
            curr_s = curr_data.get('standard')
            curr_d = curr_data.get('deluxe')
            curr_combined = calculate_combined_rank(curr_s, curr_d)

            prev_s, prev_d = None, None
            if prev_run and "raw_results" in prev_run:
                prev_data = prev_run["raw_results"].get(c, {}) or {}
                prev_s = prev_data.get("standard")
                prev_d = prev_data.get("deluxe")

            prev_combined = calculate_combined_rank(prev_s, prev_d)
            s_diff = format_diff(curr_s, prev_s)
            d_diff = format_diff(curr_d, prev_d)
            c_diff = format_diff(curr_combined, prev_combined)

            s_emoji = get_emoji(s_diff)
            d_emoji = get_emoji(d_diff)
            c_emoji = get_emoji(c_diff)

            s_part = f"{curr_s or '-'} {s_diff}".strip()
            d_part = f"{curr_d or '-'} {d_diff}".strip()
            c_part = f"{curr_combined or '-'} {c_diff}".strip()

            store_url = get_bestseller_url(c)
            flag = FLAGS.get(c, "")
            country_label = f"{flag} [{c}]({store_url})" if store_url else f"{flag} {c}"

            lines.append(
                f"**{country_label}**: {s_emoji}S `{s_part}` / {d_emoji}D `{d_part}` → {c_emoji}`{c_part}`"
            )

        if not lines:
            continue

        CHUNK_LIMIT = 3800
        chunks, current_chunk, current_len = [], [], 0
        for line in lines:
            if current_len + len(line) + 1 > CHUNK_LIMIT and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [line]
                current_len = len(line)
            else:
                current_chunk.append(line)
                current_len += len(line) + 1
        if current_chunk:
            chunks.append(current_chunk)

        for i, chunk in enumerate(chunks):
            part_label = f" ({i+1}/{len(chunks)})" if len(chunks) > 1 else ""
            payload = {
                "embeds": [{
                    "title": f"🌐 {region_name}{part_label}",
                    "description": "\n".join(chunk),
                    "color": 0xFF4500,
                    "timestamp": datetime.now(KST).isoformat()
                }]
            }
            requests.post(DISCORD_WEBHOOK, json=payload)
            time.sleep(1)

# =============================================================================
# 메인
# =============================================================================

def main():
    print("=" * 60)
    print("🎮 Crimson Desert PS Store 전체 베스트셀러 순위 추적")
    print(f"   최대 탐색: {MAX_PAGES}페이지까지")
    print("=" * 60)

    start_time = time.time()
    driver = setup_driver()

    results = {}
    skipped_countries = set(SKIP_COUNTRIES)

    try:
        all_countries = []
        for region_countries in REGIONS.values():
            all_countries.extend(region_countries)

        for country in all_countries:
            if country in SKIP_COUNTRIES:
                print(f"⏭️  스킵: {country}")
                results[country] = None
                continue

            print(f"🔍 크롤링: {country}...")
            result, status = crawl_country(driver, country)

            if status == "error" or status == "no_url":
                print(f"    ⚠️  {country}: 접근 불가 → 자동 스킵")
                skipped_countries.add(country)
                results[country] = None
            else:
                results[country] = result

    finally:
        driver.quit()

    elapsed = (time.time() - start_time) / 60
    print(f"\n⏱️  소요 시간: {elapsed:.1f}분")

    combined_avg = calculate_avg(results)

    print("\n" + "=" * 60)
    print("📊 결과 요약")
    print("=" * 60)
    for region_name, region_countries in REGIONS.items():
        print(f"\n{region_name}:")
        for country in region_countries:
            if country in skipped_countries:
                print(f"  {FLAGS.get(country,'')} {country}: 스킵")
                continue
            data = results.get(country) or {}
            combined = calculate_combined_rank(data.get('standard'), data.get('deluxe'))
            print(f"  {FLAGS.get(country,'')} {country}: S {data.get('standard','-')}위 / D {data.get('deluxe','-')}위 → {combined or '-'}위")

    if combined_avg:
        print(f"\n전체 가중 평균: {combined_avg:.1f}위")

    # 히스토리 저장
    history, was_recovered = load_history_safe()
    new_entry = {
        "timestamp": datetime.now(KST).isoformat(),
        "averages": {"combined": combined_avg},
        "skipped": list(skipped_countries),
        "raw_results": results
    }
    history.append(new_entry)
    save_history(history)
    print(f"\n✅  bestseller_history.json 저장 완료 (총 {len(history)}개 레코드)")

    # Discord 전송
    send_discord(results, combined_avg, skipped_countries, history)

if __name__ == "__main__":
    main()
