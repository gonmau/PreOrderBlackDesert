#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import os
import json
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

KST = timezone(timedelta(hours=9))

# =============================================================================
# 설정
# =============================================================================
CONCEPT_ID = "10002363"
HISTORY_FILE = "bestseller_history.json"
MAX_WORKERS = 3 # 깃허브 액션에서는 3개가 가장 안전합니다.

CHROME_DRIVER_PATH = None

REGIONS = {
    "Americas": ["미국", "캐나다", "브라질", "멕시코", "아르헨티나", "칠레", "콜롬비아", "페루", "우루과이", "볼리비아", "과테말라", "온두라스", "코스타리카", "에콰도르", "엘살바도르", "니카라과", "파나마", "파라과이"],
    "Europe & Middle East": ["영국", "독일", "프랑스", "스페인", "이탈리아", "네덜란드", "폴란드", "스위스", "스웨덴", "노르웨이", "덴마크", "핀란드", "포르투갈", "그리스", "체코", "헝가리", "루마니아", "슬로바키아", "슬로베니아", "우크라이나", "사우디아라비아", "아랍에미리트", "남아공", "터키", "벨기에", "오스트리아", "이스라엘", "크로아티아", "불가리아", "키프로스", "아이슬란드", "아일랜드", "쿠웨이트", "레바논", "룩셈부르크", "몰타", "오만", "카타르", "바레인"],
    "Asia & Oceania": ["일본", "한국", "중국", "호주", "인도", "태국", "싱가포르", "말레이시아", "인도네시아", "필리핀", "베트남", "홍콩", "대만", "뉴질랜드"]
}

COUNTRY_CODES = {
    "미국": ("en", "us"), "캐나다": ("en", "ca"), "브라질": ("pt", "br"), "멕시코": ("es", "mx"), "아르헨티나": ("es", "ar"), "칠레": ("es", "cl"), "콜롬비아": ("es", "co"), "페루": ("es", "pe"), "우루과이": ("es", "uy"), "볼리비아": ("es", "bo"), "과테말라": ("es", "gt"), "온두라스": ("es", "hn"), "코스타리카": ("es", "cr"), "에콰도르": ("es", "ec"), "엘살바도르": ("es", "sv"), "니카라과": ("es", "ni"), "파나마": ("es", "pa"), "파라과이": ("es", "py"), "영국": ("en", "gb"), "독일": ("de", "de"), "프랑스": ("fr", "fr"), "스페인": ("es", "es"), "이탈리아": ("it", "it"), "네덜란드": ("nl", "nl"), "폴란드": ("pl", "pl"), "스위스": ("de", "ch"), "스웨덴": ("en", "se"), "노르웨이": ("en", "no"), "덴마크": ("en", "dk"), "핀란드": ("en", "fi"), "포르투갈": ("pt", "pt"), "그리스": ("en", "gr"), "체코": ("en", "cz"), "헝가리": ("en", "hu"), "루마니아": ("en", "ro"), "슬로바키아": ("en", "sk"), "슬로베니아": ("en", "si"), "우크라이나": ("en", "ua"), "사우디아라비아": ("en", "sa"), "아랍에미리트": ("en", "ae"), "남아공": ("en", "za"), "터키": ("en", "tr"), "벨기에": ("nl", "be"), "오스트리아": ("de", "at"), "이스라엘": ("en", "il"), "크로아티아": ("en", "hr"), "불가리아": ("en", "bg"), "키프로스": ("en", "cy"), "아이슬란드": ("en", "is"), "아일랜드": ("en", "ie"), "쿠웨이트": ("en", "kw"), "레바논": ("en", "lb"), "룩셈부르크": ("en", "lu"), "몰타": ("en", "mt"), "오만": ("en", "om"), "카타르": ("en", "qa"), "바레인": ("en", "bh"), "일본": ("ja", "jp"), "한국": ("ko", "kr"), "중국": ("zh", "hans-cn"), "호주": ("en", "au"), "인도": ("en", "in"), "태국": ("en", "th"), "싱가포르": ("en", "sg"), "말레이시아": ("en", "my"), "인도네시아": ("en", "id"), "필리핀": ("en", "ph"), "베트남": ("en", "vn"), "홍콩": ("en", "hk"), "대만": ("zh", "hant-tw"), "뉴질랜드": ("en", "nz")
}

WEIGHTS = {"미국": 30.0, "영국": 8.5, "일본": 8.0, "독일": 6.5, "프랑스": 6.0, "캐나다": 4.5, "스페인": 4.0, "이탈리아": 3.5, "호주": 3.0, "한국": 2.8}

def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # ⚠️ 이미지 차단이 오히려 로딩 인식을 방해할 수 있어 이번엔 제거했습니다.
    service = Service(CHROME_DRIVER_PATH)
    return webdriver.Chrome(service=service, options=options)

def check_country_rank(country):
    if country not in COUNTRY_CODES: return country, None
    lang, code = COUNTRY_CODES[country]
    driver = None
    found_rank = None
    
    try:
        driver = get_driver()
        # ⚠️ 검색 범위를 5페이지(120위)까지 늘렸습니다.
        for page in range(1, 6):
            url = f"https://store.playstation.com/{lang}-{code}/pages/browse/{page}"
            driver.get(url)
            
            # ⚠️ 요소가 나타날 때까지 확실히 대기
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "li[data-test-label='product-grid-item-list']"))
                )
            except:
                break # 페이지에 상품이 없으면 종료

            items = driver.find_elements(By.CSS_SELECTOR, "li[data-test-label='product-grid-item-list']")
            for idx, item in enumerate(items):
                try:
                    # 링크 텍스트 전체에서 CONCEPT_ID 확인 (더 확실한 방법)
                    html = item.get_attribute('innerHTML')
                    if CONCEPT_ID in html:
                        found_rank = (page - 1) * 24 + (idx + 1)
                        break
                except: continue
            if found_rank: break
            time.sleep(1) # 차단 방지 및 로딩 여유
    except Exception as e:
        print(f"Error in {country}: {e}")
    finally:
        if driver: driver.quit()
    return country, found_rank

def calculate_avg(results):
    total_w = 0
    weighted_sum = 0
    for country, rank in results.items():
        if rank is None: continue
        w = WEIGHTS.get(country, 1.0)
        total_w += w
        weighted_sum += rank * w
    return weighted_sum / total_w if total_w > 0 else None

def load_history_safe():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f), False
        except: return [], True
    return [], False

if __name__ == "__main__":
    print("🔧 크롬 드라이버 준비 중...")
    CHROME_DRIVER_PATH = ChromeDriverManager().install()
    
    start_time = time.time()
    all_countries = [c for r in REGIONS.values() for c in r]
    results = {}

    print(f"🚀 병렬 트래킹 시작 (Workers: {MAX_WORKERS})...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check_country_rank, c): c for c in all_countries}
        for future in futures:
            try:
                country, rank = future.result()
                results[country] = rank
                print(f"  - [{country}] {'Rank: '+str(rank) if rank else 'Not Found'}")
            except Exception as e:
                print(f"Critical thread error: {e}")

    combined_avg = calculate_avg(results)
    history, _ = load_history_safe()
    
    # ⚠️ combined_avg가 None일 경우를 대비한 안전장치
    avg_display = round(combined_avg, 1) if combined_avg is not None else "N/A"
    
    new_entry = {
        "timestamp": datetime.now(KST).isoformat(),
        "averages": {"combined": combined_avg},
        "raw_results": results
    }
    history.append(new_entry)
    
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    print(f"\n⏱️ 소요 시간: {(time.time()-start_time)/60:.1f}분 | 전체 평균: {avg_display}위")
