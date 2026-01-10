#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import os
import json
import requests
from datetime import datetime
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

STEAM_WISHLIST_URL = "https://store.steampowered.com/search/?filter=popularwishlist"
SEARCH_TERM = "crimson desert"
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
MAX_PAGES = 3

# =============================================================================
# 함수들
# =============================================================================

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def crawl_steam_wishlist(driver):
    """Steam Wishlist 순위 크롤링"""
    print("🎮 Steam Wishlist 순위 크롤링 시작...")
    
    rank = 0
    found_rank = None
    
    for page in range(MAX_PAGES):
        try:
            url = f"{STEAM_WISHLIST_URL}&page={page + 1}"
            driver.get(url)
            time.sleep(3)
            
            # 게임 아이템들 찾기
            items = driver.find_elements(By.CSS_SELECTOR, "a.search_result_row")
            
            for item in items:
                rank += 1
                try:
                    # 게임 제목 추출
                    title_elem = item.find_element(By.CSS_SELECTOR, ".title")
                    title = title_elem.text.lower()
                    
                    if SEARCH_TERM.lower() in title:
                        found_rank = rank
                        print(f"  ✅ 발견: {rank}위 - '{title_elem.text}'")
                        return found_rank
                        
                except Exception as e:
                    continue
            
            print(f"  페이지 {page + 1} 완료 (현재까지 {rank}개 확인)")
            
        except Exception as e:
            print(f"  ⚠️  페이지 {page + 1} 오류: {e}")
            continue
    
    if not found_rank:
        print(f"  ❌ {MAX_PAGES}페이지 내에서 못찾음")
    
    return found_rank

def load_history():
    """기존 히스토리 데이터 로드"""
    history_file = "steam_history.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(rank):
    """히스토리 저장"""
    history = load_history()
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "rank": rank
    }
    
    history.append(entry)
    
    # 최근 100개만 유지
    if len(history) > 100:
        history = history[-100:]
    
    with open("steam_history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    print("✅ steam_history.json 저장 완료")

def create_rank_graph():
    """순위 변화 그래프 생성"""
    if not HAS_MATPLOTLIB:
        print("⚠️  matplotlib 없음 - 그래프 생략")
        return None
    
    history = load_history()
    if len(history) < 2:
        print("⚠️  데이터 부족 (2개 이상 필요) - 그래프 생략")
        return None
    
    # 데이터 파싱
    timestamps = []
    ranks = []
    
    for entry in history:
        try:
            dt = datetime.fromisoformat(entry['timestamp'])
            rank = entry.get('rank')
            
            if rank:
                timestamps.append(dt)
                ranks.append(rank)
        except:
            continue
    
    if not timestamps:
        return None
    
    # 그래프 생성
    plt.figure(figsize=(12, 6))
    plt.style.use('seaborn-v0_8-darkgrid')
    
    plt.plot(timestamps, ranks, marker='o', linewidth=2, 
            markersize=8, color='#1B2838', label='Wishlist Rank')
    
    plt.gca().invert_yaxis()  # 순위는 낮을수록 좋음
    plt.xlabel('Date', fontsize=12, fontweight='bold')
    plt.ylabel('Wishlist Rank', fontsize=12, fontweight='bold')
    plt.title('Crimson Desert - Steam Wishlist Ranking Trend', 
             fontsize=14, fontweight='bold', pad=20)
    plt.legend(loc='best', fontsize=11)
    plt.grid(True, alpha=0.3)
    
    # 날짜 포맷
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    plt.gcf().autofmt_xdate()
    
    plt.tight_layout()
    
    # BytesIO로 저장
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    print("✅ 그래프 생성 완료")
    return buf

def format_diff(current, previous):
    """순위 수치 증감 포맷팅"""
    if previous is None or current is None:
        return ""
    diff = previous - current  # 작아질수록 순위 상승
    if diff > 0:
        return f"▲{diff}"
    elif diff < 0:
        return f"▼{abs(diff)}"
    else:
        return "="

def send_discord(rank):
    """Discord로 결과 전송 (그래프 포함)"""
    if not DISCORD_WEBHOOK:
        print("⚠️  DISCORD_WEBHOOK 환경변수 없음")
        return
    
    history = load_history()
    prev_rank = history[-1]['rank'] if history else None
    
    # 증감 표시
    diff_text = format_diff(rank, prev_rank)
    rank_display = f"`{rank}위`" if rank else "`찾을 수 없음`"
    if diff_text and rank:
        rank_display = f"`{rank}위` ({diff_text})"
    
    # 설명 텍스트
    desc = f"**Steam Wishlist 순위**: {rank_display}"
    
    if not rank:
        desc += "\n\n⚠️  상위 75개 게임 내에서 발견되지 않았습니다."
    
    # 그래프 생성
    graph_buf = create_rank_graph()
    
    # Discord embed
    embed = {
        "title": "🎮 Crimson Desert - Steam Wishlist",
        "description": desc,
        "color": 0x1B2838,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "Steam Store Tracker"}
    }
    
    try:
        if graph_buf:
            # 그래프를 파일로 첨부
            embed['image'] = {'url': 'attachment://steam_trend.png'}
            payload = {'payload_json': json.dumps({'embeds': [embed]})}
            files = {'file': ('steam_trend.png', graph_buf, 'image/png')}
            response = requests.post(DISCORD_WEBHOOK, data=payload, files=files)
        else:
            # 그래프 없이 텍스트만
            payload = {"embeds": [embed]}
            response = requests.post(DISCORD_WEBHOOK, json=payload)
        
        if response.status_code in [204, 200]:
            print("✅ Discord 전송 성공!")
        else:
            print(f"⚠️  Discord 전송 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ Discord 오류: {e}")

# =============================================================================
# 메인
# =============================================================================

def main():
    print("=" * 60)
    print("🎮 Crimson Desert Steam Wishlist 순위 추적")
    print("=" * 60)
    
    start_time = time.time()
    driver = setup_driver()
    
    try:
        rank = crawl_steam_wishlist(driver)
    finally:
        driver.quit()
    
    elapsed = (time.time() - start_time) / 60
    print(f"\n⏱️  소요 시간: {elapsed:.1f}분")
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("📊 결과 요약")
    print("=" * 60)
    print(f"Steam Wishlist 순위: {rank if rank else '찾을 수 없음'}위")
    
    # 히스토리 저장
    save_history(rank)
    
    # Discord 전송
    send_discord(rank)

if __name__ == "__main__":
    main()
