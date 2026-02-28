#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import re
import os
import json
import requests
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# =============================================================================
# 설정
# =============================================================================

# 지역별 분류
REGIONS = {
    "Europe & Middle East": [
        "영국", "독일", "프랑스", "스페인", "이탈리아", "네덜란드",
        "폴란드", "스위스", "스웨덴", "노르웨이", "덴마크", "핀란드",
        "포르투갈", "그리스", "체코", "헝가리", "루마니아", "슬로바키아",
        "슬로베니아", "우크라이나", "사우디아라비아", "아랍에미리트", "남아공", "터키", "벨기에", "오스트리아", "이스라엘"
    ],
    "Americas": [
        "미국", "캐나다", "브라질", "멕시코", "아르헨티나", "칠레",
        "콜롬비아", "페루", "우루과이", "볼리비아", "과테말라", "온두라스"
    ],
    "Asia & Oceania": [
        "일본", "한국", "중국", "호주", "인도", "태국", "싱가포르",
        "말레이시아", "인도네시아", "필리핀", "베트남", "홍콩", "대만",
        "뉴질랜드"
    ]
}

MARKET_WEIGHTS = {
    # Americas
    "미국": 30.0, "캐나다": 4.5, "브라질": 2.5, "멕시코": 2.0,
    "아르헨티나": 0.9, "칠레": 0.8, "콜롬비아": 0.7, "페루": 0.4,
    "우루과이": 0.3, "볼리비아": 0.2, "과테말라": 0.2, "온두라스": 0.2,
    
    # Europe & Middle East
    "영국": 8.5, "독일": 6.5, "프랑스": 6.0, "스페인": 4.0, "이탈리아": 3.5,
    "네덜란드": 1.8, "사우디아라비아": 1.5, "아랍에미리트": 1.2,
    "폴란드": 1.2, "스위스": 1.0, "스웨덴": 1.0, "덴마크": 0.9, "포르투갈": 0.8,
    "핀란드": 0.8, "노르웨이": 0.8, "남아공": 0.8, "체코": 0.7, "루마니아": 0.6,
    "그리스": 0.5, "헝가리": 0.5, "우크라이나": 0.5, "슬로바키아": 0.3,
    "슬로베니아": 0.3, "터키": 0.8, "벨기에": 1.2, "오스트리아": 1.0, "이스라엘": 0.8,
    
    # Asia & Oceania
    "일본": 8.0, "호주": 3.0, "한국": 2.8, "인도": 2.0, "대만": 1.0,
    "싱가포르": 0.8, "태국": 0.9, "홍콩": 0.9, "인도네시아": 0.8,
    "말레이시아": 0.7, "베트남": 0.7, "필리핀": 0.6, "뉴질랜드": 0.6,
    "중국": 0.2
}

URLS = {
    # Americas
    "미국": "https://store.playstation.com/en-us/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "캐나다": "https://store.playstation.com/en-ca/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "브라질": "https://store.playstation.com/pt-br/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "멕시코": "https://store.playstation.com/es-mx/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "아르헨티나": "https://store.playstation.com/es-ar/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "칠레": "https://store.playstation.com/es-cl/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "콜롬비아": "https://store.playstation.com/es-co/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "페루": "https://store.playstation.com/es-pe/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "우루과이": "https://store.playstation.com/es-uy/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "볼리비아": "https://store.playstation.com/es-bo/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "과테말라": "https://store.playstation.com/es-gt/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "온두라스": "https://store.playstation.com/es-hn/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    
    # Europe & Middle East
    "영국": "https://store.playstation.com/en-gb/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "독일": "https://store.playstation.com/de-de/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "프랑스": "https://store.playstation.com/fr-fr/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "스페인": "https://store.playstation.com/es-es/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "이탈리아": "https://store.playstation.com/it-it/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "네덜란드": "https://store.playstation.com/nl-nl/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "폴란드": "https://store.playstation.com/pl-pl/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "스위스": "https://store.playstation.com/de-ch/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "스웨덴": "https://store.playstation.com/sv-se/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "노르웨이": "https://store.playstation.com/no-no/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "덴마크": "https://store.playstation.com/da-dk/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "핀란드": "https://store.playstation.com/fi-fi/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "포르투갈": "https://store.playstation.com/pt-pt/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "그리스": "https://store.playstation.com/el-gr/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "체코": "https://store.playstation.com/cs-cz/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "헝가리": "https://store.playstation.com/hu-hu/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "루마니아": "https://store.playstation.com/ro-ro/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "슬로바키아": "https://store.playstation.com/sk-sk/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "슬로베니아": "https://store.playstation.com/sl-si/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "우크라이나": "https://store.playstation.com/uk-ua/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "사우디아라비아": "https://store.playstation.com/en-sa/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "아랍에미리트": "https://store.playstation.com/en-ae/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "남아공": "https://store.playstation.com/en-za/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "터키": "https://store.playstation.com/en-tr/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "벨기에": "https://store.playstation.com/nl-be/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "오스트리아": "https://store.playstation.com/de-at/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "이스라엘": "https://store.playstation.com/en-il/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    
    # Asia & Oceania
    "일본": "https://store.playstation.com/ja-jp/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "한국": "https://store.playstation.com/ko-kr/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "중국": "https://store.playstation.com/zh-cn/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "호주": "https://store.playstation.com/en-au/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "인도": "https://store.playstation.com/en-in/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "태국": "https://store.playstation.com/th-th/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "싱가포르": "https://store.playstation.com/en-sg/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "말레이시아": "https://store.playstation.com/en-my/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "인도네시아": "https://store.playstation.com/id-id/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "필리핀": "https://store.playstation.com/en-ph/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "베트남": "https://store.playstation.com/vi-vn/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "홍콩": "https://store.playstation.com/zh-hk/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "대만": "https://store.playstation.com/zh-tw/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "뉴질랜드": "https://store.playstation.com/en-nz/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
}

FLAGS = {
    # Americas
    "미국": "🇺🇸", "캐나다": "🇨🇦", "브라질": "🇧🇷", "멕시코": "🇲🇽",
    "아르헨티나": "🇦🇷", "칠레": "🇨🇱", "콜롬비아": "🇨🇴", "페루": "🇵🇪",
    "우루과이": "🇺🇾", "볼리비아": "🇧🇴", "과테말라": "🇬🇹", "온두라스": "🇭🇳",
    
    # Europe & Middle East
    "영국": "🇬🇧", "독일": "🇩🇪", "프랑스": "🇫🇷", "스페인": "🇪🇸", "이탈리아": "🇮🇹",
    "네덜란드": "🇳🇱", "폴란드": "🇵🇱", "스위스": "🇨🇭", "스웨덴": "🇸🇪", "노르웨이": "🇳🇴",
    "덴마크": "🇩🇰", "핀란드": "🇫🇮", "포르투갈": "🇵🇹", "그리스": "🇬🇷", "체코": "🇨🇿",
    "헝가리": "🇭🇺", "루마니아": "🇷🇴", "슬로바키아": "🇸🇰", "슬로베니아": "🇸🇮",
    "우크라이나": "🇺🇦", "사우디아라비아": "🇸🇦", "아랍에미리트": "🇦🇪", "남아공": "🇿🇦", "터키": "🇹🇷", "벨기에": "🇧🇪", "오스트리아": "🇦🇹", "이스라엘": "🇮🇱",
    
    # Asia & Oceania
    "일본": "🇯🇵", "한국": "🇰🇷", "중국": "🇨🇳", "호주": "🇦🇺", "인도": "🇮🇳",
    "태국": "🇹🇭", "싱가포르": "🇸🇬", "말레이시아": "🇲🇾", "인도네시아": "🇮🇩",
    "필리핀": "🇵🇭", "베트남": "🇻🇳", "홍콩": "🇭🇰", "대만": "🇹🇼", "뉴질랜드": "🇳🇿",
}

SEARCH_TERMS = {
    "일본": ["crimson desert", "紅の砂漠"],
    "중국": ["crimson desert", "红之沙漠"],
    "한국": ["crimson desert", "붉은사막"],
    "홍콩": ["crimson desert", "赤血沙漠"],
    "대만": ["crimson desert", "赤血沙漠"],
}

# 모든 국가에 대해 기본 검색어 추가
ALL_COUNTRIES = set()
for region_countries in REGIONS.values():
    ALL_COUNTRIES.update(region_countries)

for country in ALL_COUNTRIES:
    if country not in SEARCH_TERMS:
        SEARCH_TERMS[country] = ["crimson desert"]

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# =============================================================================
# 출시 후 자동 URL 전환 설정
# =============================================================================

# 출시일 (한국 3/20 기준, 글로벌은 3/19이지만 KST로 통일)
# 중국은 사전예약도 목록 없으므로 제외
RELEASE_DATE_KST = datetime(2026, 3, 20, tzinfo=KST)

SKIP_COUNTRIES = {"중국"}  # 추적 제외 국가

PREORDER_CATEGORY   = "3bf499d7-7acf-4931-97dd-2667494ee2c9"
BESTSELLER_CATEGORY = "e1699f77-77e1-43ca-a296-26d08abacb0f"  # PS Store 신작 베스트셀러 (미국/영국 확인)

LOCALE_MAP = {
    "미국": "en-us", "캐나다": "en-ca", "브라질": "pt-br", "멕시코": "es-mx",
    "아르헨티나": "es-ar", "칠레": "es-cl", "콜롬비아": "es-co", "페루": "es-pe",
    "우루과이": "es-uy", "볼리비아": "es-bo", "과테말라": "es-gt", "온두라스": "es-hn",
    "영국": "en-gb", "독일": "de-de", "프랑스": "fr-fr", "스페인": "es-es",
    "이탈리아": "it-it", "네덜란드": "nl-nl", "폴란드": "pl-pl", "스위스": "de-ch",
    "스웨덴": "sv-se", "노르웨이": "no-no", "덴마크": "da-dk", "핀란드": "fi-fi",
    "포르투갈": "pt-pt", "그리스": "el-gr", "체코": "cs-cz", "헝가리": "hu-hu",
    "루마니아": "ro-ro", "슬로바키아": "sk-sk", "슬로베니아": "sl-si", "우크라이나": "uk-ua",
    "사우디아라비아": "en-sa", "아랍에미리트": "en-ae", "남아공": "en-za", "터키": "en-tr", "벨기에": "nl-be", "오스트리아": "de-at", "이스라엘": "en-il",
    "일본": "ja-jp", "한국": "ko-kr", "호주": "en-au", "인도": "en-in",
    "태국": "th-th", "싱가포르": "en-sg", "말레이시아": "en-my", "인도네시아": "id-id",
    "필리핀": "en-ph", "베트남": "vi-vn", "홍콩": "zh-hk", "대만": "zh-tw",
    "뉴질랜드": "en-nz",
}

def is_post_release():
    return datetime.now(KST) >= RELEASE_DATE_KST

def get_active_url(country):
    """
    출시 전 → 사전예약 카테고리 URL
    출시 후 → 베스트셀러 카테고리 URL
    중국 등 제외 국가 → None 반환
    """
    if country in SKIP_COUNTRIES:
        return None
    locale = LOCALE_MAP.get(country)
    if not locale:
        return URLS.get(country)  # fallback: 기존 URL
    category = BESTSELLER_CATEGORY if is_post_release() else PREORDER_CATEGORY
    return f"https://store.playstation.com/{locale}/category/{category}/1"

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
                    if not href or "/product/" not in href:
                        continue
                    total_rank += 1
                    label = (link_el.get_attribute("aria-label") or "").lower()
                    text = (item.text or "").lower()
                    if any(t.lower() in label or t.lower() in text for t in terms):
                        found_products.append({'rank': total_rank})
                        if len(found_products) >= 2:
                            break
                except:
                    continue
            if len(found_products) >= 2:
                break
        except:
            continue

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
    """순위 숫자 증감 포맷팅"""
    if previous is None or current is None:
        return ""
    diff = previous - current  # 작아질수록 순위 상승
    if diff > 0:
        return f"▲{diff}"
    elif diff < 0:
        return f"▼{abs(diff)}"
    else:
        return "0"

def get_emoji(diff_text):
    """순위 변동에 따른 이모지 반환"""
    if not diff_text or diff_text == "0":
        return "⚪"  # 변동 없음
    elif "▲" in diff_text:
        return "🟢"  # 상승 (순위가 좋아짐)
    elif "▼" in diff_text:
        return "🔴"  # 하락 (순위가 나빠짐)
    return ""

def load_history_safe(history_file):
    """
    rank_history.json을 안전하게 읽어 반환한다.
    - 읽기/파싱 실패 시 .backup 파일로 자동 복구 시도
    - .backup도 실패하면 RuntimeError를 raise해 호출부에서 스크립트를 중단
    - 성공 시 (history 리스트, 복구 여부 bool) 튜플 반환
    """
    import shutil

    backup_file = history_file + ".backup"

    def _try_load(path):
        """파일을 읽어 list를 반환. 실패 시 None 반환."""
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                print(f"⚠️  {path} 형식 오류: list가 아닙니다.")
                return None
            return data
        except json.JSONDecodeError as e:
            print(f"⚠️  {path} JSON 파싱 실패: {e}")
            return None
        except Exception as e:
            print(f"⚠️  {path} 읽기 실패: {e}")
            return None

    # 1차: 메인 파일 시도
    history = _try_load(history_file)
    if history is not None:
        return history, False  # 정상 로드, 복구 없음

    # 2차: backup 파일로 복구 시도
    print(f"⚠️  메인 파일 로드 실패 → {backup_file} 으로 복구를 시도합니다...")
    history = _try_load(backup_file)
    if history is not None:
        # backup → 메인 파일로 복원
        shutil.copy2(backup_file, history_file)
        print(f"✅  {backup_file} 에서 복구 성공! ({len(history)}개 레코드)")
        return history, True  # 복구 성공

    # 둘 다 실패 → 호출부에서 중단 처리
    raise RuntimeError(
        f"❌  {history_file} 과 {backup_file} 모두 읽기 실패.\n"
        f"   데이터 손실 방지를 위해 스크립트를 중단합니다.\n"
        f"   파일을 수동으로 확인해 주세요."
    )


def generate_csv_buffer(results):
    """순위 결과를 CSV 형식의 BytesIO 버퍼로 반환"""
    import csv
    from io import StringIO
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=["region", "country", "flag", "standard", "deluxe", "combined"])
    writer.writeheader()
    for region_name, region_countries in REGIONS.items():
        for country in region_countries:
            if country not in results or country in SKIP_COUNTRIES:
                continue
            data = results[country]
            standard = data.get("standard")
            deluxe = data.get("deluxe")
            combined = calculate_combined_rank(standard, deluxe)
            writer.writerow({
                "region": region_name,
                "country": country,
                "flag": FLAGS.get(country, ""),
                "standard": standard if standard else "-",
                "deluxe": deluxe if deluxe else "-",
                "combined": combined if combined else "-",
            })
    from io import BytesIO
    return BytesIO(buf.getvalue().encode("utf-8-sig"))


def send_discord(results, combined_avg):
    if not DISCORD_WEBHOOK:
        return

    import shutil

    history_file = "rank_history.json"
    backup_file = history_file + ".backup"

    # 안전하게 히스토리 로드 (실패 시 backup 자동 복구, 둘 다 실패 시 중단)
    try:
        history, was_recovered = load_history_safe(history_file)
    except RuntimeError as e:
        print(str(e))
        raise SystemExit(1)  # 다른 코드들도 오염되지 않도록 즉시 종료

    # 이전 실행 데이터
    prev_run = history[-1] if history else None

    # 평균 변동폭
    prev_combined_avg = prev_run['averages'].get('combined') if prev_run else None
    combined_diff_text = format_diff(combined_avg, prev_combined_avg)

    # 히스토리 업데이트
    new_entry = {
        "timestamp": datetime.now(KST).isoformat(),
        "averages": {"combined": combined_avg},
        "raw_results": results
    }
    history.append(new_entry)

    # 저장 전에 현재 파일을 backup으로 먼저 복사 (다음 실패 시 복구용)
    if os.path.exists(history_file):
        shutil.copy2(history_file, backup_file)

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


    if was_recovered:
        print(f"✅  backup에서 복구된 데이터에 새 항목을 추가해 저장했습니다.")

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
            plt.legend()
            plt.grid(True, alpha=0.2)
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            plt.gcf().autofmt_xdate()
            plt.tight_layout()
            
            img_buf = BytesIO()
            plt.savefig(img_buf, format='png', dpi=150)
            img_buf.seek(0)
            plt.close()

    # 요약 메시지 (그래프 포함)
    mode_label = "🚀 베스트셀러 차트" if is_post_release() else "⏳ 사전예약 차트"
    summary_desc = f"📊 **전체 가중 평균**: `{combined_avg:.1f}위` {'(' + combined_diff_text + ')' if combined_diff_text else ''}\n"
    summary_desc += f"🌐 **추적 중인 국가**: {len(results)}개국 | {mode_label}\n\n"
    
    # 지역별 평균 계산
    for region_name in ["Americas", "Europe & Middle East", "Asia & Oceania"]:
        region_countries = REGIONS[region_name]
        region_results = {c: results[c] for c in region_countries if c in results}
        region_avg = calculate_avg(region_results)
        if region_avg:
            summary_desc += f"**{region_name}**: `{region_avg:.1f}위`\n"
    
    summary_payload = {
        "embeds": [{
            "title": "🎮 Crimson Desert PS Store 순위 리포트",
            "description": summary_desc,
            "color": 0x00B0F4,
            "image": {"url": "attachment://graph.png"} if img_buf else None,
            "timestamp": datetime.now(KST).isoformat()
        }]
    }
    
    # 그래프와 함께 요약 전송
    if img_buf:
        files = {"file": ("graph.png", img_buf, "image/png")}
        payload = {"payload_json": json.dumps(summary_payload)}
        requests.post(DISCORD_WEBHOOK, data=payload, files=files)
    else:
        requests.post(DISCORD_WEBHOOK, json=summary_payload)
    
    time.sleep(1)  # Discord API rate limit 방지
    
    # 각 지역별로 별도 메시지 전송
    for region_name, region_countries in REGIONS.items():
        lines = []
        
        # 가중치 순으로 정렬
        sorted_countries = sorted(
            [c for c in region_countries if c in results],
            key=lambda x: MARKET_WEIGHTS.get(x, 0),
            reverse=True
        )
        
        for c in sorted_countries:
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
            
            # 이모지 추가
            s_emoji = get_emoji(s_diff)
            d_emoji = get_emoji(d_diff)
            c_emoji = get_emoji(c_diff)
            
            s_part = f"{curr_s or '-'} {s_diff}" if s_diff else f"{curr_s or '-'}"
            d_part = f"{curr_d or '-'} {d_diff}" if d_diff else f"{curr_d or '-'}"
            c_part = f"{curr_combined or '-'} {c_diff}" if c_diff else f"{curr_combined or '-'}"
            
            store_url = get_active_url(c)
            flag = FLAGS.get(c, "")
            country_label = f"{flag} [{c}]({store_url})" if store_url else f"{flag} {c}"

            lines.append(
                f"**{country_label}**: {s_emoji}S `{s_part}` / {d_emoji}D `{d_part}` → {c_emoji}`{c_part}`"
            )
        
        if lines:
            region_desc = "\n".join(lines)
            region_payload = {
                "embeds": [{
                    "title": f"🌐 {region_name}",
                    "description": region_desc,
                    "color": 0x00B0F4,
                    "timestamp": datetime.now(KST).isoformat()
                }]
            }
            requests.post(DISCORD_WEBHOOK, json=region_payload)
            time.sleep(1)  # Discord API rate limit 방지

    # CSV 파일 생성 후 디스코드로 전송
    csv_buf = generate_csv_buffer(results)
    if csv_buf:
        timestamp_label = datetime.now(KST).strftime('%Y-%m-%d %H:%M')
        files = {"file": (f"ranking_{datetime.now(KST).strftime('%Y%m%d_%H%M')}.csv", csv_buf, "text/csv")}
        payload = {"payload_json": json.dumps({"content": f"📎 **순위 데이터** ({timestamp_label} KST)"})}
        requests.post(DISCORD_WEBHOOK, data=payload, files=files)

def main():
    print("=" * 60)
    print("🎮 Crimson Desert PS Store 순위 추적")
    print("=" * 60)

    if is_post_release():
        print("🚀 출시 후 모드: 베스트셀러 카테고리 추적 중")
    else:
        print("⏳ 출시 전 모드: 사전예약 카테고리 추적 중")
    print(f"   (출시일 기준: {RELEASE_DATE_KST.strftime('%Y-%m-%d')} KST)")
    print()

    start_time = time.time()
    driver = setup_driver()

    results = {}

    try:
        all_countries = []
        for region_countries in REGIONS.values():
            all_countries.extend(region_countries)

        for country in all_countries:
            if country in SKIP_COUNTRIES:
                print(f"⏭️  스킵: {country} (추적 제외 국가)")
                results[country] = {"standard": None, "deluxe": None}
                continue

            url = get_active_url(country)
            if url:
                print(f"크롤링 중: {country}...")
                results[country] = crawl_country(driver, country, url)
            else:
                print(f"URL 없음: {country}")
                results[country] = {"standard": None, "deluxe": None}
    finally:
        driver.quit()
    
    elapsed = (time.time() - start_time) / 60
    print(f"\n⏱️ 소요 시간: {elapsed:.1f}분")
    
    # Combined 평균 계산
    combined_avg = calculate_avg(results)
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("📊 결과 요약")
    print("=" * 60)
    
    for region_name, region_countries in REGIONS.items():
        print(f"\n{region_name}:")
        for country in region_countries:
            if country in results:
                data = results[country]
                combined = calculate_combined_rank(data.get('standard'), data.get('deluxe'))
                print(f"  {country}: S {data.get('standard', '-')}위 / D {data.get('deluxe', '-')}위 → {combined or '-'}위")
    
    if combined_avg:
        print(f"\n전체 가중 평균: {combined_avg:.1f}위")
    
    # Discord 전송
    send_discord(results, combined_avg)

if __name__ == "__main__":
    main()
