#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import os
import json
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# =============================================================================
# 설정
# =============================================================================

# 지역별 분류
REGIONS = {
    "Europe & Middle East": [
        "영국", "독일", "프랑스", "스페인", "이탈리아", "네덜란드",
        "폴란드", "스위스", "스웨덴", "노르웨이", "덴마크", "핀란드",
        "포르투갈", "그리스", "체코", "헝가리", "루마니아", "슬로바키아",
        "슬로베니아", "우크라이나", "사우디아라비아", "아랍에미리트", "남아공"
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
    "우크라이나": "🇺🇦", "사우디아라비아": "🇸🇦", "아랍에미리트": "🇦🇪", "남아공": "🇿🇦",
    
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
HISTORY_FILE = 'crimson_competitors_history.json'

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

def get_games_above_crimson(driver, country, url):
    """Crimson Desert보다 앞선 게임 목록 가져오기"""
    terms = SEARCH_TERMS.get(country, ["crimson desert"])
    all_games = []
    crimson_rank = None
    
    # 최대 3페이지 크롤링
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
                    
                    label = (link_el.get_attribute("aria-label") or "").lower()
                    text = (item.text or "").lower()
                    
                    # 게임 제목 추출
                    game_name = link_el.get_attribute("aria-label") or item.text or "Unknown"
                    game_name = game_name.strip().split('\n')[0]  # 첫 줄만 사용
                    
                    all_games.append(game_name)
                    
                    # Crimson Desert 찾기
                    if crimson_rank is None and any(t.lower() in label or t.lower() in text for t in terms):
                        crimson_rank = len(all_games)
                        break  # Crimson Desert를 찾으면 중단
                        
                except:
                    continue
            
            if crimson_rank is not None:
                break  # Crimson Desert를 찾으면 페이지 크롤링 중단
                
        except Exception as e:
            print(f"  Error on page {page}: {e}")
            continue
    
    # Crimson Desert보다 앞선 게임만 반환
    if crimson_rank:
        games_above = all_games[:crimson_rank - 1]
        return games_above, crimson_rank
    else:
        return [], None

def load_history():
    """과거 히스토리 로드"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_history(history):
    """히스토리 저장"""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def send_discord_message(content):
    """디스코드로 메시지 전송"""
    if not DISCORD_WEBHOOK:
        print("DISCORD_WEBHOOK not set")
        return
    
    try:
        response = requests.post(
            DISCORD_WEBHOOK,
            json={'content': content},
            timeout=10
        )
        response.raise_for_status()
        print(f"Message sent successfully")
    except Exception as e:
        print(f"Error sending Discord message: {e}")

def main():
    print("=" * 60)
    print("🎮 Crimson Desert 경쟁 게임 추적")
    print("=" * 60)
    
    start_time = time.time()
    driver = setup_driver()
    
    history = load_history()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S KST')
    
    new_history = {}
    has_new_entries = False
    
    try:
        # 각 지역별로 처리
        for region_name, region_countries in REGIONS.items():
            print(f"\n=== {region_name} ===")
            
            region_report = f"\n{'='*50}\n"
            region_report += f"## 🌍 {region_name}\n\n"
            
            for country in region_countries:
                url = URLS.get(country)
                if not url:
                    print(f"  URL 없음: {country}")
                    continue
                
                print(f"  크롤링 중: {country}...")
                
                games_above, crimson_rank = get_games_above_crimson(driver, country, url)
                
                if crimson_rank is None:
                    print(f"    Crimson Desert를 찾을 수 없음")
                    continue
                
                # 게임 이름 목록 (비교용)
                current_games = games_above
                previous_games = history.get(country, [])
                
                # 신규 진입 게임 찾기
                new_entries = [game for game in current_games if game not in previous_games]
                
                if new_entries:
                    has_new_entries = True
                
                # 히스토리 업데이트
                new_history[country] = current_games
                
                # 국가별 리포트 생성
                flag = FLAGS.get(country, "")
                store_url = url
                country_label = f"{flag} [{country}]({store_url})"
                
                region_report += f"### {country_label}\n"
                region_report += f"📍 **Crimson Desert 현재 순위: {crimson_rank}위**\n\n"
                
                if not games_above:
                    region_report += f"✨ Crimson Desert가 1위입니다!\n\n"
                else:
                    region_report += f"**Crimson Desert보다 앞선 게임 ({len(games_above)}개):**\n"
                    for i, game in enumerate(games_above, 1):
                        # 신규 진입 게임 강조
                        if game in new_entries:
                            region_report += f"🆕 **{i}위: {game}** ⬅️ 신규 진입!\n"
                        else:
                            region_report += f"{i}위: {game}\n"
                    region_report += "\n"
            
            # 지역별 메시지 전송 (2000자 제한 고려)
            if len(region_report) > 1900:
                # 메시지가 너무 길면 국가별로 분할
                country_messages = []
                current_msg = f"\n{'='*50}\n## 🌍 {region_name}\n\n"
                
                for country in region_countries:
                    url = URLS.get(country)
                    if not url or country not in new_history:
                        continue
                    
                    games_above = new_history[country]
                    previous_games = history.get(country, [])
                    new_entries = [game for game in games_above if game not in previous_games]
                    
                    # Crimson rank 재계산 필요 (저장하지 않았으므로)
                    # 간단하게 게임 수 + 1로 근사
                    crimson_rank = len(games_above) + 1
                    
                    flag = FLAGS.get(country, "")
                    country_label = f"{flag} [{country}]({url})"
                    
                    country_block = f"### {country_label}\n"
                    country_block += f"📍 **Crimson Desert: {crimson_rank}위**\n\n"
                    
                    if not games_above:
                        country_block += f"✨ 1위입니다!\n\n"
                    else:
                        country_block += f"**앞선 게임 ({len(games_above)}개):**\n"
                        for i, game in enumerate(games_above, 1):
                            if game in new_entries:
                                country_block += f"🆕 **{i}위: {game}**\n"
                            else:
                                country_block += f"{i}위: {game}\n"
                        country_block += "\n"
                    
                    # 메시지 길이 체크
                    if len(current_msg) + len(country_block) > 1900:
                        country_messages.append(current_msg)
                        current_msg = country_block
                    else:
                        current_msg += country_block
                
                if current_msg:
                    country_messages.append(current_msg)
                
                for msg in country_messages:
                    send_discord_message(msg)
                    time.sleep(1)
            else:
                send_discord_message(region_report)
                time.sleep(1)
    
    finally:
        driver.quit()
    
    # 히스토리 저장
    save_history(new_history)
    
    elapsed = (time.time() - start_time) / 60
    print(f"\n⏱️ 소요 시간: {elapsed:.1f}분")
    
    # 헤더 메시지
    header = f"# 🎮 Crimson Desert 경쟁 게임 현황\n"
    header += f"⏰ {current_time}\n"
    header += f"🌐 추적 중인 국가: {len(new_history)}개국\n"
    
    if has_new_entries:
        header += f"🆕 **신규 진입 게임 감지!**\n"
    
    send_discord_message(header)
    time.sleep(1)
    
    print("\n=== 추적 완료 ===")

if __name__ == '__main__':
    main()
