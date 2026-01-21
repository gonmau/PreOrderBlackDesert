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

# 알림 임계값 설정
RANK_CHANGE_THRESHOLD = 3  # 순위 변동이 이 값 이상일 때만 알림

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

def find_true_new_entries(current_games, current_rank, previous_games, previous_rank):
    """진짜 신규 진입 게임만 찾기"""
    if previous_rank is None:
        # 첫 실행: 모든 게임을 신규로 간주하지 않음
        return []
    
    # Crimson Desert 순위 변동
    rank_diff = current_rank - previous_rank
    
    if rank_diff <= 0:
        # 순위가 올라갔거나 동일 → 현재 리스트에서 이전에 없던 게임들이 진짜 신규
        new_entries = [game for game in current_games if game not in previous_games]
    else:
        # 순위가 밀렸을 때
        # 예: 5위→7위 (2칸 하락), 앞선 게임 4개→6개 (2개 증가)
        # → 증가한 2개 중 Crimson이 밀린 2칸은 기존 게임이 포함된 것
        # → 실제 신규 진입 = 0개
        
        game_count_increase = len(current_games) - len(previous_games)
        true_new_count = game_count_increase - rank_diff
        
        if true_new_count <= 0:
            # 모든 증가가 Crimson이 밀려서 포함된 것
            return []
        else:
            # 진짜 신규 진입 게임 찾기
            # 현재 게임 중 이전에 없던 것들
            potential_new = [game for game in current_games if game not in previous_games]
            
            # 상위부터 true_new_count개만 진짜 신규로 판단
            # (하위는 Crimson이 밀려서 포함된 것일 가능성 높음)
            new_entries = []
            for game in current_games:
                if game in potential_new and len(new_entries) < true_new_count:
                    new_entries.append(game)
            
            return new_entries
    
    return new_entries

def format_rank_change(current, previous):
    """순위 변동 포맷팅"""
    if previous is None:
        return ""
    diff = current - previous
    if diff > 0:
        return f"▼{diff}"
    elif diff < 0:
        return f"▲{abs(diff)}"
    else:
        return "="

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
    countries_with_changes = []  # 변화가 있는 국가들
    
    try:
        # 모든 국가 크롤링
        all_countries = []
        for region_countries in REGIONS.values():
            all_countries.extend(region_countries)
        
        for country in all_countries:
            url = URLS.get(country)
            if not url:
                print(f"  URL 없음: {country}")
                continue
            
            print(f"  크롤링 중: {country}...")
            
            games_above, crimson_rank = get_games_above_crimson(driver, country, url)
            
            if crimson_rank is None:
                print(f"    Crimson Desert를 찾을 수 없음")
                continue
            
            # 이전 데이터
            previous_data = history.get(country, {})
            previous_games = previous_data.get('games', [])
            previous_rank = previous_data.get('crimson_rank')
            
            # 진짜 신규 진입 게임 찾기
            true_new_entries = find_true_new_entries(
                games_above, crimson_rank, 
                previous_games, previous_rank
            )
            
            # 순위 변동
            rank_change = None
            if previous_rank is not None:
                rank_change = crimson_rank - previous_rank
            
            # 히스토리 업데이트
            new_history[country] = {
                'games': games_above,
                'crimson_rank': crimson_rank
            }
            
            # 변화 감지: 신규 진입이 있거나 순위가 크게 변동된 경우
            has_new_entries = len(true_new_entries) > 0
            has_big_rank_change = rank_change is not None and abs(rank_change) >= RANK_CHANGE_THRESHOLD
            
            if has_new_entries or has_big_rank_change:
                countries_with_changes.append({
                    'country': country,
                    'crimson_rank': crimson_rank,
                    'previous_rank': previous_rank,
                    'rank_change': rank_change,
                    'games_above': games_above,
                    'new_entries': true_new_entries
                })
                print(f"    ✓ 변화 감지: 신규 {len(true_new_entries)}개, 순위변동 {rank_change}")
    
    finally:
        driver.quit()
    
    # 히스토리 저장
    save_history(new_history)
    
    elapsed = (time.time() - start_time) / 60
    print(f"\n⏱️ 소요 시간: {elapsed:.1f}분")
    print(f"📊 변화 감지: {len(countries_with_changes)}개국")
    
    # 디스코드 알림 (변화가 있을 때만)
    if countries_with_changes:
        # 헤더 메시지
        header = f"# 🎮 Crimson Desert 경쟁 게임 변화 감지\n"
        header += f"⏰ {current_time}\n"
        header += f"🌐 변화 감지: **{len(countries_with_changes)}개국**\n"
        header += f"📊 전체 추적: {len(new_history)}개국\n\n"
        
        send_discord_message(header)
        time.sleep(1)
        
        # 지역별로 그룹화
        for region_name, region_countries in REGIONS.items():
            region_changes = [c for c in countries_with_changes if c['country'] in region_countries]
            
            if not region_changes:
                continue
            
            region_msg = f"## 🌍 {region_name}\n\n"
            
            for change_data in region_changes:
                country = change_data['country']
                crimson_rank = change_data['crimson_rank']
                previous_rank = change_data['previous_rank']
                rank_change = change_data['rank_change']
                new_entries = change_data['new_entries']
                games_above = change_data['games_above']
                
                flag = FLAGS.get(country, "")
                url = URLS.get(country)
                country_label = f"{flag} [{country}]({url})"
                
                # 순위 변동 표시
                rank_change_text = format_rank_change(crimson_rank, previous_rank)
                if previous_rank:
                    rank_info = f"{previous_rank}위→{crimson_rank}위 {rank_change_text}"
                else:
                    rank_info = f"{crimson_rank}위"
                
                region_msg += f"### {country_label} (Crimson: {rank_info})\n"
                
                # 신규 진입 게임 표시
                if new_entries:
                    region_msg += f"🆕 **신규 진입: {len(new_entries)}개**\n"
                    for game in new_entries:
                        # 게임의 현재 순위 찾기
                        game_rank = games_above.index(game) + 1 if game in games_above else "?"
                        region_msg += f"  • **{game_rank}위: {game}**\n"
                
                # 순위 변동만 있고 신규 진입이 없는 경우
                elif abs(rank_change) >= RANK_CHANGE_THRESHOLD:
                    region_msg += f"📉 순위 변동만 발생 (신규 진입 없음)\n"
                
                region_msg += "\n"
            
            # 메시지 전송 (2000자 제한 고려)
            if len(region_msg) > 1900:
                # 국가별로 분할
                for change_data in region_changes:
                    country = change_data['country']
                    crimson_rank = change_data['crimson_rank']
                    previous_rank = change_data['previous_rank']
                    new_entries = change_data['new_entries']
                    games_above = change_data['games_above']
                    
                    flag = FLAGS.get(country, "")
                    url = URLS.get(country)
                    country_label = f"{flag} [{country}]({url})"
                    
                    rank_change_text = format_rank_change(crimson_rank, previous_rank)
                    if previous_rank:
                        rank_info = f"{previous_rank}위→{crimson_rank}위 {rank_change_text}"
                    else:
                        rank_info = f"{crimson_rank}위"
                    
                    country_msg = f"### {country_label} (Crimson: {rank_info})\n"
                    
                    if new_entries:
                        country_msg += f"🆕 **신규 진입: {len(new_entries)}개**\n"
                        for game in new_entries:
                            game_rank = games_above.index(game) + 1 if game in games_above else "?"
                            country_msg += f"  • **{game_rank}위: {game}**\n"
                    
                    send_discord_message(country_msg)
                    time.sleep(1)
            else:
                send_discord_message(region_msg)
                time.sleep(1)
    else:
        # 변화가 없을 때
        no_change_msg = f"# ✅ Crimson Desert 순위 안정\n"
        no_change_msg += f"⏰ {current_time}\n"
        no_change_msg += f"📊 {len(new_history)}개국 추적 중\n"
        no_change_msg += f"🔹 신규 진입 게임 없음\n"
        no_change_msg += f"🔹 큰 순위 변동(±{RANK_CHANGE_THRESHOLD}) 없음\n"
        
        send_discord_message(no_change_msg)
    
    print("\n=== 추적 완료 ===")

if __name__ == '__main__':
    main()
