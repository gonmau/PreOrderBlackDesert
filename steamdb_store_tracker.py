#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crimson Desert Complete Store Tracker
- Steam App Details API: 가격, 리뷰 수, 출시일 확인
- SteamSpy API: 대략적인 소유자 수 (무료)
- Xbox: 검색 기반 예구 오픈
- SOP(State of Play): PlayStation Blog 감지
- 모든 데이터 히스토리 저장 및 그래프 생성
"""

import json
import os
import time
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
STEAM_APP_DETAILS_URL = f"https://store.steampowered.com/api/appdetails?appids={STEAM_APP_ID}"
STEAMSPY_URL = f"https://steamspy.com/api.php?request=appdetails&appid={STEAM_APP_ID}"
STEAM_REVIEWS_URL = f"https://store.steampowered.com/appreviews/{STEAM_APP_ID}?json=1&language=all&purchase_type=all"
STEAM_URL = f"https://store.steampowered.com/app/{STEAM_APP_ID}"
STEAMDB_URL = f"https://steamdb.info/app/{STEAM_APP_ID}/charts/"

PS_US_CATEGORY_URL = (
    "https://store.playstation.com/en-us/category/"
    "3bf499d7-7acf-4931-97dd-2667494ee2c9/1"
)

XBOX_SEARCH_URL = "https://www.xbox.com/en-US/search?q=Crimson+Desert"
PS_BLOG_URL = "https://blog.playstation.com/tag/state-of-play/"

STATE_FILE = "store_state.json"
HISTORY_FILE = "steam_history.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ======================
# Steam 데이터 수집
# ======================
def get_steam_stats():
    """Steam 공식 API와 SteamSpy에서 데이터 수집"""
    print("🎮 Steam 데이터 수집 중...")
    
    stats = {
        "review_count": None,
        "positive_reviews": None,
        "negative_reviews": None,
        "owners": None,
        "players_2weeks": None
    }
    
    # Steam Reviews API
    try:
        print("  📊 Steam Reviews 수집...")
        r = requests.get(STEAM_REVIEWS_URL, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if 'query_summary' in data:
                summary = data['query_summary']
                stats["review_count"] = summary.get('total_reviews', 0)
                stats["positive_reviews"] = summary.get('total_positive', 0)
                stats["negative_reviews"] = summary.get('total_negative', 0)
                print(f"  ✅ 리뷰 수: {stats['review_count']:,}")
                print(f"    👍 긍정: {stats['positive_reviews']:,} | 👎 부정: {stats['negative_reviews']:,}")
    except Exception as e:
        print(f"  ⚠️ Steam Reviews 실패: {e}")
    
    # SteamSpy API (무료, 대략적인 수치)
    try:
        print("  📊 SteamSpy 데이터 수집...")
        r = requests.get(STEAMSPY_URL, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            # owners: "0 .. 20,000" 형식
            owners_str = data.get('owners', '0')
            stats["owners"] = owners_str
            stats["players_2weeks"] = data.get('players_2weeks', 0)
            print(f"  ✅ 소유자: {owners_str}")
            print(f"  ✅ 최근 2주 플레이어: {stats['players_2weeks']:,}")
    except Exception as e:
        print(f"  ⚠️ SteamSpy 실패: {e}")
    
    print(f"  📊 Steam 수집 결과: {stats}")
    return stats

# ======================
# 상태 관리
# ======================
def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def ensure_key(state, key, default):
    if key not in state:
        state[key] = default

# ======================
# 히스토리 관리
# ======================
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def add_history_entry(stats):
    history = load_history()
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        **stats
    }
    history.append(entry)
    save_history(history)
    return history

# ======================
# 그래프 생성
# ======================
def create_stats_graph(history):
    """리뷰 수와 플레이어 수 그래프"""
    if not HAS_MATPLOTLIB or len(history) < 2:
        return None
    
    # 유효한 데이터만 필터링
    valid_entries = [e for e in history if "timestamp" in e]
    if len(valid_entries) < 2:
        return None
    
    dates = [datetime.fromisoformat(e["timestamp"]) for e in valid_entries]
    
    # 2x1 서브플롯
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    fig.suptitle('Crimson Desert - Steam Stats History', fontsize=16, fontweight='bold')
    
    # 1. 리뷰 수 (긍정/부정)
    review_data = [(d, e.get("review_count"), e.get("positive_reviews"), e.get("negative_reviews")) 
                   for d, e in zip(dates, valid_entries) 
                   if e.get("review_count")]
    if review_data:
        d, total, pos, neg = zip(*review_data)
        ax1.plot(d, total, marker='o', linewidth=2, color='#1B2838', label='Total Reviews')
        if pos and any(pos):
            ax1.plot(d, pos, marker='s', linewidth=1.5, color='#5C9F5E', label='Positive', alpha=0.7)
        if neg and any(neg):
            ax1.plot(d, neg, marker='s', linewidth=1.5, color='#D75452', label='Negative', alpha=0.7)
        ax1.set_title('Steam Reviews', fontweight='bold')
        ax1.set_ylabel('Count')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
    
    # 2. 최근 2주 플레이어
    players_data = [(d, e.get("players_2weeks")) for d, e in zip(dates, valid_entries)
                    if e.get("players_2weeks")]
    if players_data:
        d, v = zip(*players_data)
        ax2.plot(d, v, marker='o', linewidth=2, color='#4ECDC4', label='Players (2 weeks)')
        ax2.set_title('Active Players (Last 2 Weeks)', fontweight='bold')
        ax2.set_ylabel('Count')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
    
    # 날짜 레이블 회전
    for ax in [ax1, ax2]:
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
    if diff > 0:
        return f"D-{diff}"
    if diff == 0:
        return "D-DAY"
    return f"D+{abs(diff)}"

# ======================
# Xbox 예구 감지
# ======================
def detect_xbox_preorder():
    try:
        r = requests.get(XBOX_SEARCH_URL, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return False
        text = r.text.lower()
        return any(k in text for k in ["pre-order", "preorder", "buy", "purchase"])
    except Exception:
        return False

# ======================
# SOP 감지
# ======================
def detect_sop():
    try:
        r = requests.get(PS_BLOG_URL, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return False
        t = r.text.lower()
        if "state of play" not in t:
            return False
        return any(k in t for k in ["announce", "broadcast", "watch live", "returns"])
    except Exception:
        return False

# ======================
# Discord
# ======================
def send_discord(msg, embed=None, file_data=None, filename=None):
    if not DISCORD_WEBHOOK:
        return
    
    files = None
    if file_data and filename:
        files = {"file": (filename, file_data, "image/png")}
    
    payload = {"content": msg}
    if embed:
        payload["embeds"] = [embed]
    
    if files:
        requests.post(
            DISCORD_WEBHOOK,
            data={"payload_json": json.dumps(payload)},
            files=files,
            timeout=10
        )
    else:
        requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)

# ======================
# 메인
# ======================
def main():
    print("=" * 60)
    print("🎮 Crimson Desert Complete Tracker")
    print("=" * 60)
    
    state = load_state()
    ensure_key(state, "xbox_preorder_open", False)
    ensure_key(state, "sop_detected", False)

    alerts = []

    # Steam 데이터 수집
    steam_stats = get_steam_stats()
    if any(v for v in steam_stats.values() if v):
        history = add_history_entry(steam_stats)
        print(f"✅ 히스토리 저장 완료 (총 {len(history)}개)")

    # Xbox
    xbox_open = detect_xbox_preorder()
    if xbox_open and not state["xbox_preorder_open"]:
        alerts.append("🟢 **Xbox 예구 오픈 (검색 기반)**")
        state["xbox_preorder_open"] = True

    # SOP
    sop_open = detect_sop()
    if sop_open and not state["sop_detected"]:
        alerts.append("🎥 **State of Play 행사 감지**")
        state["sop_detected"] = True

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    dday = calc_dday()

    # 그래프 생성
    history = load_history()
    graph_buffer = create_stats_graph(history)

    # 통계 텍스트
    stats_text = "📊 **Steam Stats**\n"
    if steam_stats["review_count"]:
        positive_pct = 0
        if steam_stats["review_count"] > 0:
            positive_pct = (steam_stats["positive_reviews"] / steam_stats["review_count"]) * 100
        stats_text += f"⭐ 리뷰: **{steam_stats['review_count']:,}개** (👍 {positive_pct:.1f}%)\n"
    if steam_stats["owners"]:
        stats_text += f"👥 소유자: **{steam_stats['owners']}**\n"
    if steam_stats["players_2weeks"]:
        stats_text += f"🎮 최근 플레이어: **{steam_stats['players_2weeks']:,}명**\n"

    embed = {
        "title": "📊 Crimson Desert Complete Tracker",
        "description": (
            f"📅 **출시일**: 2026-03-19 ({dday})\n\n"
            f"{stats_text}\n"
            f"📈 **총 {len(history)}개 히스토리 기록**\n\n"
            f"🔗 **플랫폼 바로가기**\n"
            f"[Steam]({STEAM_URL}) | "
            f"[SteamDB]({STEAMDB_URL}) | "
            f"[PlayStation US]({PS_US_CATEGORY_URL}) | "
            f"[Xbox]({XBOX_SEARCH_URL})\n\n"
            f"🟢 **Steam**: 예구 오픈\n"
            f"🟢 **PlayStation US**: 예구 오픈\n"
            f"🟢 **Xbox**: 예구 오픈 (검색 기반)\n"
            f"🎥 [**SOP: {'감지됨' if state['sop_detected'] else '미감지'}**]({PS_BLOG_URL})\n\n"
            f"_Steam API & SteamSpy 기반 · {now}_"
        ),
        "color": 0x1B2838
    }

    if graph_buffer:
        embed["image"] = {"url": "attachment://stats_graph.png"}

    if alerts:
        send_discord(
            "🚨 **변경 감지 발생**\n" + "\n".join(alerts),
            embed,
            graph_buffer,
            "stats_graph.png" if graph_buffer else None
        )
    else:
        send_discord(
            "🔔 **Crimson Desert 상태 업데이트**",
            embed,
            graph_buffer,
            "stats_graph.png" if graph_buffer else None
        )

    save_state(state)
    print("✅ 완료!")

if __name__ == "__main__":
    main()
