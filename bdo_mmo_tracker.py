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

STEAM_CHARTS_URL = "https://steamcharts.com/top"
BDO_STEAM_ID = "582660"  # Black Desert Online Steam App ID
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

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

def crawl_mmo_rank(driver):
    """Steam Charts에서 검은사막 순위 크롤링"""
    print("🎮 Steam 동접자 순위 크롤링 시작...")
    
    try:
        driver.get(STEAM_CHARTS_URL)
        time.sleep(4)
        
        # 순위 테이블 찾기
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        
        for idx, row in enumerate(rows, 1):
            try:
                # 게임 이름 찾기
                game_link = row.find_element(By.CSS_SELECTOR, "td.game-name a")
                game_name = game_link.text.strip()
                
                # Black Desert 찾기
                if "Black Desert" in game_name:
                    # 현재 플레이어 수 추출
                    try:
                        current_players_elem = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)")
                        players_text = current_players_elem.text.strip().replace(",", "")
                        players = int(players_text) if players_text.isdigit() else None
                    except:
                        players = None
                    
                    bdo_data = {
                        "rank": idx,
                        "players": players,
                        "game_name": game_name
                    }
                    
                    print(f"  ✅ 발견: {idx}위 - {players:,}명 동접" if players else f"  ✅ 발견: {idx}위")
                    return bdo_data
                    
            except Exception as e:
                continue
        
        print("  ❌ Black Desert를 찾을 수 없음")
        return None
        
    except Exception as e:
        print(f"  ❌ 크롤링 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

def load_history():
    """기존 히스토리 데이터 로드"""
    history_file = "bdo_history.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(data):
    """히스토리 저장"""
    history = load_history()
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "rank": data.get("rank") if data else None,
        "players": data.get("players") if data else None
    }
    
    history.append(entry)
    
    # 최근 200개만 유지
    if len(history) > 200:
        history = history[-200:]
    
    with open("bdo_history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    print("✅ bdo_history.json 저장 완료")

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
            markersize=8, color='#FF6B00', label='MMO Rank')
    
    plt.gca().invert_yaxis()  # 순위는 낮을수록 좋음
    plt.xlabel('Date', fontsize=12, fontweight='bold')
    plt.ylabel('Steam Ranking', fontsize=12, fontweight='bold')
    plt.title('Black Desert Online - Steam Ranking Trend', 
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

def format_number(num):
    """숫자를 K, M 단위로 포맷"""
    if num is None:
        return "N/A"
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    else:
        return str(num)

def format_diff(current, previous):
    """증감 포맷팅"""
    if previous is None or current is None:
        return ""
    diff = previous - current  # 순위는 작아질수록 상승
    if diff > 0:
        return f"▲{diff}"
    elif diff < 0:
        return f"▼{abs(diff)}"
    else:
        return "="

def send_discord(data):
    """Discord로 결과 전송 (그래프 포함)"""
    if not DISCORD_WEBHOOK:
        print("⚠️  DISCORD_WEBHOOK 환경변수 없음")
        return
    
    history = load_history()
    prev_data = history[-1] if history else {}
    
    if not data:
        desc = "⚠️  데이터를 가져올 수 없습니다."
    else:
        rank = data.get("rank")
        players = data.get("players")
        
        # 이전 데이터와 비교
        prev_rank = prev_data.get("rank")
        prev_players = prev_data.get("players")
        
        rank_diff = format_diff(rank, prev_rank)
        
        rank_display = f"`{rank}위`"
        if rank_diff:
            rank_display += f" ({rank_diff})"
        
        players_display = f"`{format_number(players)}`"
        if prev_players:
            player_change = players - prev_players
            if player_change > 0:
                players_display += f" (+{format_number(player_change)})"
            elif player_change < 0:
                players_display += f" ({format_number(player_change)})"
        
        desc = f"**Steam 게임 순위**: {rank_display}\n"
        desc += f"**현재 동접자**: {players_display}"
    
    # 그래프 생성
    graph_buf = create_rank_graph()
    
    # Discord embed
    embed = {
        "title": "🎮 Black Desert Online - Steam 순위",
        "description": desc,
        "color": 0xFF6B00,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "Steam Charts Tracker"}
    }
    
    try:
        if graph_buf:
            embed['image'] = {'url': 'attachment://bdo_trend.png'}
            payload = {'payload_json': json.dumps({'embeds': [embed]})}
            files = {'file': ('bdo_trend.png', graph_buf, 'image/png')}
            response = requests.post(DISCORD_WEBHOOK, data=payload, files=files)
        else:
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
    print("🎮 Black Desert Online Steam 순위 추적")
    print("=" * 60)
    
    start_time = time.time()
    driver = setup_driver()
    
    try:
        data = crawl_mmo_rank(driver)
    finally:
        driver.quit()
    
    elapsed = (time.time() - start_time) / 60
    print(f"\n⏱️  소요 시간: {elapsed:.1f}분")
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("📊 결과 요약")
    print("=" * 60)
    
    if data:
        print(f"Steam 순위: {data['rank']}위")
        print(f"현재 동접자: {data['players']:,}명")
    else:
        print("데이터를 가져올 수 없습니다.")
    
    # 히스토리 저장
    save_history(data)
    
    # Discord 전송
    send_discord(data)

if __name__ == "__main__":
    main()
