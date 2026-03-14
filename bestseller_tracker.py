#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PS Store 전체 베스트셀러 순위 추적기 - Crimson Desert
pages/browse/{page} 에서 concept ID로 게임을 찾을 때까지 페이지를 순회합니다.
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

# Crimson Desert concept ID (전 세계 공통)
CONCEPT_ID = "10002363"

REGIONS = {
    "Americas": [
        "미국", "캐나다", "브라질", "멕시코", "아르헨티나", "칠레",
        "콜롬비아", "페루", "우루과이", "볼리비아", "과테말라", "온두라스",
        "코스타리카", "에콰도르", "엘살바도르", "니카라과", "파나마", "파라과이"
    ],
    "Europe & Middle East": [
        "영국", "독일", "프랑스", "스페인", "이탈리아", "네덜란드",
        "폴란드", "스위스", "스웨덴", "노르웨이", "덴마크", "핀란드",
        "포르투갈", "그리스", "체코", "헝가리", "루마니아", "슬로바키아",
        "슬로베니아", "우크라이나", "사우디아라비아", "아랍에미리트", "남아공",
        "터키", "벨기에", "오스트리아", "이스라엘", "크로아티아", "불가리아",
        "키프로스", "아이슬란드", "아일랜드", "쿠웨이트", "레바논",
        "룩셈부르크", "몰타", "오만", "카타르", "바레인"
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

# URL 없거나 스토어 미지원 국가
SKIP_COUNTRIES = {"중국", "베트남", "슬로베니아", "필리핀"}

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
HISTORY_FILE = "bestseller_history.json"
BACKUP_FILE  = HISTORY_FILE + ".backup"
BASELINE_FILE = "discord_baseline.json"  # 마지막 알림 발송 시점 기준값

# 게임 미발견 시 최대 탐색 페이지
MAX_PAGES = 30

# =============================================================================
# 드라이버
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

def get_browse_url(country, page=1):
    locale = LOCALE_MAP.get(country)
    if not locale:
        return None
    return f"https://store.playstation.com/{locale}/pages/browse/{page}"

def crawl_country(driver, country):
    """
    pages/browse/{page} 에서 /concept/CONCEPT_ID 링크를 찾을 때까지 순회.
    반환: (rank or None, status)
      status: "found" | "not_found" | "error" | "no_url"
    """
    total_rank = 0
    target = f"/concept/{CONCEPT_ID}"

    for page in range(1, MAX_PAGES + 1):
        url = get_browse_url(country, page)
        if not url:
            return None, "no_url"

        try:
            driver.get(url)
            time.sleep(3)

            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/concept/']")

            if not links:
                print(f"    ↳ {country}: {page}p 아이템 없음 → 탐색 종료")
                return None, "not_found"

            for link in links:
                href = link.get_attribute("href") or ""
                if "/concept/" not in href:
                    continue
                total_rank += 1

                if target in href:
                    print(f"    ✅ {country}: {total_rank}위 발견 (page {page})")
                    return total_rank, "found"

            print(f"    {country}: page {page} 완료 ({total_rank}위까지 확인)...")

        except Exception as e:
            print(f"    ⚠️ {country} page {page} 오류: {e}")
            if page == 1:
                return None, "error"
            break

    print(f"    ↳ {country}: {MAX_PAGES}p({total_rank}위)까지 미발견")
    return None, "not_found"

# =============================================================================
# 계산 유틸
# =============================================================================

def calculate_avg(results):
    total_w, total_sum = 0, 0
    for c, rank in results.items():
        if rank is None:
            continue
        w = MARKET_WEIGHTS.get(c, 1.0)
        total_sum += rank * w
        total_w += w
    return total_sum / total_w if total_w > 0 else None

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

    print("⚠️  메인 파일 로드 실패 → backup 복구 시도...")
    history = _try_load(BACKUP_FILE)
    if history is not None:
        shutil.copy2(BACKUP_FILE, HISTORY_FILE)
        print(f"✅  backup 복구 성공 ({len(history)}개 레코드)")
        return history, True

    print("ℹ️  히스토리 없음 → 새로 시작")
    return [], False

def save_history(history):
    if os.path.exists(HISTORY_FILE):
        shutil.copy2(HISTORY_FILE, BACKUP_FILE)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def load_baseline():
    """마지막 Discord 알림 발송 시점의 combined_avg 로드"""
    if not os.path.exists(BASELINE_FILE):
        return None
    try:
        with open(BASELINE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("combined_avg")
    except:
        return None

def save_baseline(combined_avg):
    """Discord 알림 발송 시점의 combined_avg 저장"""
    with open(BASELINE_FILE, "w", encoding="utf-8") as f:
        json.dump({"combined_avg": combined_avg, "timestamp": datetime.now(KST).isoformat()}, f)

# =============================================================================
# Discord 알림
# =============================================================================

def send_discord(results, combined_avg, skipped_countries, history):
    if not DISCORD_WEBHOOK:
        print("ℹ️  DISCORD_WEBHOOK 미설정, 알림 스킵")
        return

    prev_run = history[-2] if len(history) >= 2 else None
    prev_avg = prev_run['averages'].get('combined') if prev_run else None
    if isinstance(prev_avg, dict):
        prev_avg = None  # 구버전 데이터 방어
    avg_diff = format_diff(combined_avg, prev_avg)

    # 마지막 알림 발송 기준점과 비교해서 ±1.0 이상 변화 시에만 알림 발송
    baseline_avg = load_baseline()
    if combined_avg is not None and baseline_avg is not None:
        diff = abs(combined_avg - baseline_avg)
        if diff < 1.0:
            print(f"ℹ️  기준점 대비 변화 미미 (기준: {baseline_avg:.1f} → 현재: {combined_avg:.1f}, 차이: {diff:.2f}) - 알림 스킵")
            return
        print(f"🔔 기준점 대비 변화 감지 (기준: {baseline_avg:.1f} → 현재: {combined_avg:.1f}, 차이: {diff:.2f}) - 알림 발송")

    tracked = sum(1 for c in results if c not in skipped_countries)
    found   = sum(1 for c, r in results.items() if c not in skipped_countries and r is not None)

    desc = ""
    if combined_avg:
        desc += f"📊 **전체 가중 평균**: `{combined_avg:.1f}위`"
        if avg_diff:
            desc += f" ({avg_diff})"
        desc += "\n"
    desc += f"🌐 **추적 국가**: {tracked}개국 | **순위권 발견**: {found}개국\n\n"

    for region_name in ["Americas", "Europe & Middle East", "Asia & Oceania"]:
        region_results = {c: results[c] for c in REGIONS[region_name]
                         if c in results and results[c] is not None and c not in skipped_countries}
        region_avg = calculate_avg(region_results)
        if region_avg:
            desc += f"**{region_name}**: `{region_avg:.1f}위`\n"

    requests.post(DISCORD_WEBHOOK, json={"embeds": [{
        "title": "🎮 Crimson Desert 전체 베스트셀러 순위 리포트",
        "description": desc,
        "color": 0xFF4500,
        "timestamp": datetime.now(KST).isoformat()
    }]})
    time.sleep(1)

    prev_results = prev_run.get("raw_results", {}) if prev_run else {}

    def extract_rank(val):
        """이전 형식(dict) 또는 현재 형식(int/None) 모두 처리"""
        if isinstance(val, dict):
            # 구버전: {"standard": N, "deluxe": N} → 더 좋은 순위 반환
            s = val.get("standard")
            d = val.get("deluxe")
            if s and d: return min(s, d)
            return s or d or None
        return val  # int or None

    for region_name, region_countries in REGIONS.items():
        lines = []
        sorted_countries = sorted(
            [c for c in region_countries if c in results and c not in skipped_countries],
            key=lambda x: MARKET_WEIGHTS.get(x, 0), reverse=True
        )

        for c in sorted_countries:
            curr = results.get(c)
            prev = extract_rank(prev_results.get(c))
            diff = format_diff(curr, prev)
            emoji = get_emoji(diff)
            rank_str = f"{curr}위 {diff}".strip() if curr else "미발견"

            store_url = get_browse_url(c)
            flag = FLAGS.get(c, "")
            label = f"{flag} [{c}]({store_url})" if store_url else f"{flag} {c}"
            lines.append(f"**{label}**: {emoji} `{rank_str}`")

        if not lines:
            continue

        CHUNK_LIMIT = 3800
        chunks, cur_chunk, cur_len = [], [], 0
        for line in lines:
            if cur_len + len(line) + 1 > CHUNK_LIMIT and cur_chunk:
                chunks.append(cur_chunk)
                cur_chunk = [line]
                cur_len = len(line)
            else:
                cur_chunk.append(line)
                cur_len += len(line) + 1
        if cur_chunk:
            chunks.append(cur_chunk)

        for i, chunk in enumerate(chunks):
            part = f" ({i+1}/{len(chunks)})" if len(chunks) > 1 else ""
            requests.post(DISCORD_WEBHOOK, json={"embeds": [{
                "title": f"🌐 {region_name}{part}",
                "description": "\n".join(chunk),
                "color": 0xFF4500,
                "timestamp": datetime.now(KST).isoformat()
            }]})
            time.sleep(1)

    # 알림 발송 완료 → 현재 avg를 기준점으로 저장
    if combined_avg is not None:
        save_baseline(combined_avg)
        print(f"✅ baseline 갱신: {combined_avg:.1f}")

# =============================================================================
# 메인
# =============================================================================

def main():
    print("=" * 60)
    print(f"🎮 Crimson Desert 전체 베스트셀러 순위 추적")
    print(f"   Concept ID: {CONCEPT_ID} | 최대 {MAX_PAGES}페이지")
    print("=" * 60)

    start_time = time.time()
    driver = setup_driver()

    results = {}
    skipped = set(SKIP_COUNTRIES)

    try:
        all_countries = [c for region in REGIONS.values() for c in region]

        for country in all_countries:
            if country in SKIP_COUNTRIES:
                print(f"⏭️  스킵: {country}")
                results[country] = None
                continue

            print(f"🔍 {country}...")
            rank, status = crawl_country(driver, country)

            if status in ("error", "no_url"):
                print(f"    ⚠️  접근 불가 → 자동 스킵")
                skipped.add(country)
                results[country] = None
            else:
                results[country] = rank

    finally:
        driver.quit()

    elapsed = (time.time() - start_time) / 60
    print(f"\n⏱️  소요 시간: {elapsed:.1f}분")

    combined_avg = calculate_avg({c: r for c, r in results.items() if c not in skipped})

    print("\n" + "=" * 60)
    print("📊 결과 요약")
    print("=" * 60)
    for region_name, region_countries in REGIONS.items():
        print(f"\n{region_name}:")
        for country in region_countries:
            flag = FLAGS.get(country, "")
            if country in skipped:
                print(f"  {flag} {country}: 스킵")
            else:
                rank = results.get(country)
                print(f"  {flag} {country}: {rank}위" if rank else f"  {flag} {country}: 미발견")

    if combined_avg:
        print(f"\n전체 가중 평균: {combined_avg:.1f}위")

    history, _ = load_history_safe()
    new_entry = {
        "timestamp": datetime.now(KST).isoformat(),
        "averages": {"combined": combined_avg},
        "skipped": list(skipped),
        "raw_results": results
    }

    if combined_avg is None:
        print("\n⚠️  전국 미발견 (combined_avg=None) → 히스토리 저장 스킵")
    else:
        history.append(new_entry)
        save_history(history)
        print(f"\n✅  {HISTORY_FILE} 저장 완료 (총 {len(history)}개 레코드)")

    send_discord(results, combined_avg, skipped, history)

if __name__ == "__main__":
    main()
