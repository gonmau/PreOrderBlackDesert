#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crimson Desert Wishlist Tracker
- SteamDB: Wishlist 순위
- PlayStation Blog: State of Play 감지
"""

import json
import os
import re
from datetime import datetime, date
import requests
from io import BytesIO

# Matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# ======================
# 환경 설정
# ======================
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
RELEASE_DATE = date(2026, 3, 19)
STEAM_APP_ID = "3321460"

# URLs
STEAMDB_MOSTWISHED_URL = "https://steamdb.info/stats/mostwished/"
STEAM_URL = f"https://store.steampowered.com/app/{STEAM_APP_ID}"
STEAMDB_URL = f"https://steamdb.info/app/{STEAM_APP_ID}/charts/"
PS_BLOG_URL = "https://blog.playstation.com/tag/state-of-play/"

STATE_FILE = "store_state.json"
HISTORY_FILE = "steam_history.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

# ======================
# Wishlist 순위 수집
# ======================
def get_wishlist_rank():
    """SteamDB Most Wished에서 Crimson Desert 순위 추출"""
    print("🔍 SteamDB Wishlist 순위 수집 중...")
    
    try:
        r = requests.get(STEAMDB_MOSTWISHED_URL, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            print(f"  ⚠️ SteamDB 응답 실패: {r.status_code}")
            return None
        
        # Crimson Desert 앱 ID로 검색
        # HTML 패턴: <tr>...<td>순위</td>...<a href="/app/3321460/">Crimson Desert</a>...</tr>
        
        # 방법 1: 앱 ID로 행 찾기
        app_pattern = rf'/app/{STEAM_APP_ID}/'
        if app_pattern in r.text:
            # 해당 앱이 포함된 tr 태그 찾기
            lines = r.text.split('\n')
            for i, line in enumerate(lines):
                if app_pattern in line:
                    # 위쪽 라인들에서 순위 찾기 (보통 같은 행이나 바로 위에 있음)
                    for j in range(max(0, i-10), i+5):
                        # 순위는 보통 <td> 태그 안에 숫자로만 있음
                        rank_match = re.search(r'<td[^>]*>\s*(\d+)\s*\.\s*</td>', lines[j])
                        if rank_match:
                            rank = int(rank_match.group(1))
                            print(f"  ✅ Wishlist 순위: #{rank}")
                            return rank
        
        # 방법 2: 게임 이름으로 직접 검색
        name_pattern = r'Crimson Desert.*?</a>'
        name_match = re.search(name_pattern, r.text, re.IGNORECASE)
        if name_match:
            start_pos = name_match.start()
            # 이전 텍스트에서 가장 가까운 순위 번호 찾기
            prev_text = r.text[:start_pos]
            rank_matches = list(re.finditer(r'>(\d+)\.<', prev_text))
            if rank_matches:
                rank = int(rank_matches[-1].group(1))
                print(f"  ✅ Wishlist 순위: #{rank}")
                return rank
        
        print(f"  ⚠️ Crimson Desert를 찾을 수 없음")
        return None
        
    except Exception as e:
        print(f"  ❌ SteamDB 오류: {e}")
        return None

# ======================
# 상태/히스토리 관리
# ======================
def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def add_history_entry(rank):
    history = load_history()
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "rank": rank
    }
    history.append(entry)
    save_history(history)
    return history

# ======================
# 그래프 생성
# ======================
def create_rank_graph(history):
    """Wishlist 순위 그래프"""
    if not HAS_MATPLOTLIB or len(history) < 2:
        return None
    
    valid_entries = [e for e in history if e.get("rank") is not None]
    if len(valid_entries) < 2:
        return None
    
    dates = [datetime.fromisoformat(e["timestamp"]) for e in valid_entries]
    ranks = [e["rank"] for e in valid_entries]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.plot(dates, ranks, marker='o', linewidth=2, color='#4ECDC4', markersize=6)
    ax.invert_yaxis()  # 순위는 낮을수록 좋으므로 Y축 반전
    ax.set_title('Crimson Desert - Wishlist Activity Rank', fontsize=16, fontweight='bold')
    ax.set_ylabel('Rank', fontsize=12)
    ax.set_xlabel('Date', fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf

# ======================
# 유틸
# ======================
def calc_dday():
    today = date.today()
    diff = (RELEASE_DATE - today).days
    return f"D-{diff}" if diff > 0 else "D-DAY" if diff == 0 else f"D+{abs(diff)}"

def detect_sop():
    """PlayStation Blog에서 2026년 State of Play 감지"""
    print("🎥 State of Play 감지 중...")
    try:
        r = requests.get(PS_BLOG_URL, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            print(f"  ⚠️ PS Blog 응답 실패: {r.status_code}")
            return False
        
        t = r.text.lower()
        if "state of play" not in t:
            print(f"  ℹ️ State of Play 포스트 없음")
            return False
        
        # 2026년 날짜 패턴
        year_patterns = [
            r'january\s+\d{1,2},\s*2026',
            r'february\s+\d{1,2},\s*2026',
            r'march\s+\d{1,2},\s*2026',
            r'april\s+\d{1,2},\s*2026',
            r'may\s+\d{1,2},\s*2026',
            r'june\s+\d{1,2},\s*2026',
            r'july\s+\d{1,2},\s*2026',
            r'august\s+\d{1,2},\s*2026',
            r'september\s+\d{1,2},\s*2026',
            r'october\s+\d{1,2},\s*2026',
            r'november\s+\d{1,2},\s*2026',
            r'december\s+\d{1,2},\s*2026',
            r'jan\s+\d{1,2},\s*2026',
            r'feb\s+\d{1,2},\s*2026',
            r'mar\s+\d{1,2},\s*2026',
            r'apr\s+\d{1,2},\s*2026',
            r'jun\s+\d{1,2},\s*2026',
            r'jul\s+\d{1,2},\s*2026',
            r'aug\s+\d{1,2},\s*2026',
            r'sep\s+\d{1,2},\s*2026',
            r'oct\s+\d{1,2},\s*2026',
            r'nov\s+\d{1,2},\s*2026',
            r'dec\s+\d{1,2},\s*2026',
        ]
        
        for pattern in year_patterns:
            if re.search(pattern, t):
                print(f"  ✅ 2026년 SOP 일정 감지!")
                return True
        
        print(f"  ℹ️ State of Play 있지만 2026년 일정은 없음")
        return False
        
    except Exception as e:
        print(f"  ❌ PS Blog 오류: {e}")
        return False

def send_discord(msg, embed=None, file_data=None, filename=None):
    if not DISCORD_WEBHOOK:
        return
    
    files = {"file": (filename, file_data, "image/png")} if file_data and filename else None
    payload = {"content": msg}
    if embed:
        payload["embeds"] = [embed]
    
    try:
        if files:
            requests.post(DISCORD_WEBHOOK, data={"payload_json": json.dumps(payload)}, files=files, timeout=10)
        else:
            requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
    except Exception as e:
        print(f"  ❌ Discord 전송 실패: {e}")

# ======================
# 메인
# ======================
def main():
    print("=" * 60)
    print("🎮 Crimson Desert Wishlist Tracker")
    print("=" * 60)
    
    state = load_state()
    if "sop_detected" not in state:
        state["sop_detected"] = False
    
    alerts = []
    
    # 데이터 수집
    rank = get_wishlist_rank()
    
    # 히스토리 저장
    if rank is not None:
        history = add_history_entry(rank)
        print(f"✅ 히스토리 저장 완료 (총 {len(history)}개)")
    else:
        history = load_history()
        print(f"⚠️ 순위 수집 실패, 기존 히스토리 사용 (총 {len(history)}개)")
    
    # SOP 감지
    sop_detected = detect_sop()
    if sop_detected and not state["sop_detected"]:
        alerts.append("🎥 **State of Play 2026 일정 발표!**")
        state["sop_detected"] = True
    
    # 현재 시간
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    dday = calc_dday()
    
    # 최신 순위 (히스토리에서 가져오기)
    latest_rank = None
    for entry in reversed(history):
        if entry.get("rank") is not None:
            latest_rank = entry["rank"]
            break
    
    display_rank = rank if rank is not None else latest_rank
    
    # 그래프 생성
    graph_buffer = create_rank_graph(history)
    
    # Discord Embed
    rank_text = f"⭐ **Wishlist Rank**: #{display_rank}" if display_rank else "데이터 수집 중..."
    
    print(f"\n📊 Discord 전송 데이터:")
    print(f"  - Display Rank: {display_rank}")
    print(f"  - SOP Detected: {sop_detected}")
    
    embed = {
        "title": "📊 Crimson Desert Wishlist Tracker",
        "description": (
            f"📅 **출시일**: 2026-03-19 ({dday})\n\n"
            f"{rank_text}\n\n"
            f"📈 총 {len(history)}개 히스토리 기록\n\n"
            f"🔗 **링크**\n"
            f"[Steam]({STEAM_URL}) | [SteamDB]({STEAMDB_URL})\n\n"
            f"🎥 [**State of Play**: {'감지됨 ✅' if sop_detected else '소식없음'}]({PS_BLOG_URL})\n\n"
            f"_SteamDB · {now}_"
        ),
        "color": 0x1B2838
    }
    
    # 알림 전송
    if alerts:
        send_discord("🚨 **변경 감지**\n" + "\n".join(alerts), embed)
    else:
        send_discord("📢 **상태 업데이트**", embed)
    
    # 그래프를 별도 메시지로 전송
    if graph_buffer:
        graph_embed = {
            "title": "📈 Crimson Desert - Wishlist Rank History",
            "color": 0x1B2838,
            "image": {"url": "attachment://rank_graph.png"}
        }
        send_discord("", graph_embed, graph_buffer, "rank_graph.png")
    
    save_state(state)
    print("✅ 완료!")

if __name__ == "__main__":
    main()
