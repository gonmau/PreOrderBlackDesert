#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import requests
from datetime import datetime
from io import BytesIO

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

BDO_STEAM_ID = "582660"  # Black Desert Online Steam App ID
STEAM_API_URL = f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={BDO_STEAM_ID}"
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# =============================================================================
# 함수들
# =============================================================================

def crawl_mmo_rank(driver=None):
    """Steam API에서 검은사막 동접자 수 가져오기"""
    print("🎮 Steam 동접자 수 조회 시작...")
    
    try:
        # Steam API 호출 (크롤링 불필요)
        response = requests.get(STEAM_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('response', {}).get('result') == 1:
            players = data['response']['player_count']
            
            bdo_data = {
                "players": players,
                "game_name": "Black Desert Online"
            }
            
            print(f"  ✅ 현재 동접자: {players:,}명")
            return bdo_data
        else:
            print("  ❌ Steam API 응답 오류")
            return None
        
    except Exception as e:
        print(f"  ❌ API 호출 오류: {e}")
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
    """동접자 변화 그래프 생성"""
    if not HAS_MATPLOTLIB:
        print("⚠️  matplotlib 없음 - 그래프 생략")
        return None
    
    history = load_history()
    if len(history) < 2:
        print("⚠️  데이터 부족 (2개 이상 필요) - 그래프 생략")
        return None
    
    # 데이터 파싱
    timestamps = []
    players = []
    
    for entry in history:
        try:
            dt = datetime.fromisoformat(entry['timestamp'])
            player_count = entry.get('players')
            
            if player_count:
                timestamps.append(dt)
                players.append(player_count)
        except:
            continue
    
    if not timestamps:
        return None
    
    # 그래프 생성
    plt.figure(figsize=(12, 6))
    plt.style.use('seaborn-v0_8-darkgrid')
    
    plt.plot(timestamps, players, marker='o', linewidth=2, 
            markersize=8, color='#FF6B00', label='Concurrent Players')
    
    plt.xlabel('Date', fontsize=12, fontweight='bold')
    plt.ylabel('Players', fontsize=12, fontweight='bold')
    plt.title('Black Desert Online - Steam Concurrent Players Trend', 
             fontsize=14, fontweight='bold', pad=20)
    plt.legend(loc='best', fontsize=11)
    plt.grid(True, alpha=0.3)
    
    # Y축 숫자 포맷 (쉼표)
    ax = plt.gca()
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
    
    # 날짜 포맷
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
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
        players = data.get("players")
        
        # 이전 데이터와 비교
        prev_players = prev_data.get("players")
        
        players_display = f"`{format_number(players)}`"
        if prev_players:
            player_change = players - prev_players
            if player_change > 0:
                players_display += f" (+{format_number(player_change)})"
            elif player_change < 0:
                players_display += f" ({format_number(player_change)})"
        
        desc = f"**현재 동접자**: {players_display}"
    
    # 그래프 생성
    graph_buf = create_rank_graph()
    
    # Discord embed
    embed = {
        "title": "🎮 Black Desert Online - Steam 동접자",
        "description": desc,
        "color": 0xFF6B00,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "Steam API Tracker"}
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
    print("🎮 Black Desert Online Steam 동접자 추적")
    print("=" * 60)
    
    start_time = time.time()
    
    # Steam API는 크롤링 불필요
    data = crawl_mmo_rank()
    
    elapsed = (time.time() - start_time) / 60
    print(f"\n⏱️  소요 시간: {elapsed:.1f}분")
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("📊 결과 요약")
    print("=" * 60)
    
    if data:
        print(f"현재 동접자: {data['players']:,}명")
    else:
        print("데이터를 가져올 수 없습니다.")
    
    # 히스토리 저장
    save_history(data)
    
    # Discord 전송
    send_discord(data)

if __name__ == "__main__":
    main()
