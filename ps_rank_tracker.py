#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PS Store 국가별 베스트셀러 순위 추적기 (간소화 버전)

- 가중치/스케줄/디스코드 알림 등 다 빼고, "돌릴 때마다 국가별 순위를 표로 저장" 기능만.
- concept ID로 찾기 때문에 언어별 타이틀 신경 쓸 필요 없음.
- 속도: 국가별로 Chrome 인스턴스를 여러 개 띄워 병렬로 크롤링 (ThreadPoolExecutor).

설치:
    pip install selenium webdriver-manager pandas tabulate

실행:
    python ps_rank_tracker.py                       # 기본 concept id로 전체 국가 추적
    python ps_rank_tracker.py --concept-id 10002363
    python ps_rank_tracker.py --workers 12 --out data/rank.csv
"""

import argparse
import concurrent.futures as cf
import os
import time
from datetime import datetime, timezone, timedelta

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

KST = timezone(timedelta(hours=9))

# =============================================================================
# 설정
# =============================================================================

DEFAULT_CONCEPT_ID = "10002363"  # 붉은사막 (Crimson Desert)
MAX_PAGES = 9        # 게임 못 찾았을 때 최대 탐색 페이지 (약 200위까지)
PAGE_LOAD_TIMEOUT = 10  # 초 단위, 요소 로딩 대기 상한 (기존 고정 sleep(3) 대신 대기 조건으로 단축)
DEFAULT_WORKERS = 4     # 동시에 띄울 Chrome 인스턴스 수. GitHub Actions 무료 러너(2코어)는
                         # 4~5가 안전, 로컬 PC면 코어 수 보고 올려도 됨

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

# URL 없거나 스토어 미지원 국가 (기존 코드 기준)
SKIP_COUNTRIES = {"중국", "베트남", "슬로베니아", "필리핀"}

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


# =============================================================================
# 드라이버 / 크롤링
# =============================================================================

def setup_driver(driver_path: str):
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1280,800')
    # 이미지 로딩 꺼서 속도 향상 (순위 링크만 필요하므로 렌더링 이미지는 불필요)
    options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver


def get_browse_url(locale, page=1):
    return f"https://store.playstation.com/{locale}/pages/browse/{page}"


def _crawl_country_once(driver, locale, concept_id, max_pages):
    target = f"/concept/{concept_id}"
    total_rank = 0
    for page in range(1, max_pages + 1):
        url = get_browse_url(locale, page)
        driver.get(url)
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/concept/']"))
        )
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/concept/']")
        if not links:
            return None, "not_found"

        for link in links:
            href = link.get_attribute("href") or ""
            if "/concept/" not in href:
                continue
            total_rank += 1
            if target in href:
                return total_rank, "found"

    return None, "not_found"


def crawl_country(country, locale, driver_path, concept_id, max_pages=MAX_PAGES, retries=1):
    """국가 하나를 처음부터 끝까지 크롤링. 스레드마다 자체 driver를 만들어 병렬 실행.
    1페이지에서 타임아웃 나면 (동시 실행 리소스 경합 등 일시적 문제일 수 있어) retries만큼 재시도."""
    last_status = "error"
    for attempt in range(retries + 1):
        driver = setup_driver(driver_path)
        try:
            rank, status = _crawl_country_once(driver, locale, concept_id, max_pages)
            return country, rank, status
        except Exception:
            last_status = "error"
            continue
        finally:
            driver.quit()
    return country, None, last_status


# =============================================================================
# 메인
# =============================================================================

def run(concept_id: str, workers: int, max_pages: int) -> pd.DataFrame:
    countries = [c for c in LOCALE_MAP if c not in SKIP_COUNTRIES]
    now = datetime.now(KST).isoformat(timespec="seconds")

    # 드라이버는 한 번만 받아서 경로를 재사용 (스레드마다 동시에 install() 호출하면
    # webdriver_manager 캐시 경합으로 대부분 실패하는 문제가 있었음)
    driver_path = ChromeDriverManager().install()

    rows = []
    start = time.time()

    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {
            ex.submit(crawl_country, c, LOCALE_MAP[c], driver_path, concept_id, max_pages): c
            for c in countries
        }
        for fut in cf.as_completed(futures):
            country, rank, status = fut.result()
            print(f"  {FLAGS.get(country,'')} {country}: {rank if rank else status}")
            rows.append({
                "country": country,
                "flag": FLAGS.get(country, ""),
                "locale": LOCALE_MAP[country],
                "rank": rank,
                "status": status,
                "checked_at": now,
            })

    for c in SKIP_COUNTRIES:
        rows.append({
            "country": c, "flag": FLAGS.get(c, ""), "locale": LOCALE_MAP.get(c, ""),
            "rank": None, "status": "skipped", "checked_at": now,
        })

    elapsed = time.time() - start
    print(f"\n⏱️  소요 시간: {elapsed/60:.1f}분 ({workers}개 동시 실행)")

    df = pd.DataFrame(rows).sort_values(by="rank", na_position="last")
    return df


def main():
    parser = argparse.ArgumentParser(description="PS Store 국가별 순위 추적 (간소화판)")
    parser.add_argument("--concept-id", default=DEFAULT_CONCEPT_ID, help="PS Store concept ID")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="동시 실행 Chrome 인스턴스 수")
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES, help="국가당 최대 탐색 페이지")
    parser.add_argument("--out", default="data/rank_history.csv", help="CSV 저장 경로 (실행할 때마다 이 파일에 누적됨)")
    args = parser.parse_args()

    df = run(args.concept_id, args.workers, args.max_pages)

    view = df[["flag", "country", "rank", "status"]]
    try:
        print("\n" + view.to_markdown(index=False))
    except ImportError:
        print("\n" + view.to_string(index=False))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    file_exists = os.path.exists(args.out)
    save_df = df[["country", "rank"]]
    save_df.to_csv(args.out, mode="a", header=not file_exists, index=False, encoding="utf-8-sig")
    with open(args.out, encoding="utf-8-sig") as f:
        total_rows = sum(1 for _ in f) - 1
    print(f"\n누적 저장됨: {args.out} (누적 {total_rows}행)")


if __name__ == "__main__":
    main()
