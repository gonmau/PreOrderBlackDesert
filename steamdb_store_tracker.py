#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crimson Desert Store & SOP Tracker + Wishlist History Graph
- Steam 위시리스트 수집 및 히스토리 저장
- matplotlib으로 그래프 생성
- Discord에 그래프 이미지 전송
"""

import json
import os
from datetime import datetime, date
import requests
import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO

# ======================
# 환경 설정
# ======================
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

RELEASE_DATE = date(2026, 3, 19)

STEAMDB_URL = "https://steamdb.info/app/3321460/charts/"
STEAM_URL = "https://store.steampowered.com/app/3321460"

PS_US_CATEGORY_URL = (
    "https://store.playstation.com/en-us/category/"
    "3bf499d7-7acf-4931-97dd-2667494ee2c9/1"
)

XBOX_SEARCH_URL = "https://www.xbox.com/en-US/search?q=Crimson+Desert"
PS_BLOG_URL = "https://blog.playstation.com/tag/state-of-play/"

STATE_FILE = "store_state.json"
HISTORY_FILE = "steam_history.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

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

def add_history_entry(wishlist_count):
    history = load_history()
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "wishlist": wishlist_count
    }
    history.append(entry)
    save_history(history)
    return history

# ======================
# Steam 위시리스트 수집
# ======================
def get_steam_wishlist():
    try:
        r = requests.get(STEAMDB_URL, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        
        # SteamDB에서 위시리스트 수 추출 (여러 패턴 시도)
        patterns = [
            r'([\d,]+)\s+wishlists?',  # "123,456 wishlists"
            r'wishlists?[:\s]+([\d,]+)',  # "wishlists: 123,456"
            r'data-cc-wishlists?="([\d,]+)"',  # 속성값
            r'"wishlists?":\s*"?([\d,]+)"?',  # JSON 형식
            r'Wishlists?[:\s]+([\d,]+)',  # 대문자 버전
        ]
        
        for pattern in patterns:
            match = re.search(pattern, r.text, re.IGNORECASE)
            if match:
                count_str = match.group(1).replace(',', '')
                try:
                    count = int(count_str)
                    if count > 0:  # 유효한 숫자인지 확인
                        return count
                except ValueError:
                    continue
        
        # 디버깅: 실패 시 HTML 일부 출력 (선택적)
        print(f"Steam wishlist parsing failed. Page length: {len(r.text)}")
        
        return None
    except Exception as e:
        print(f"Steam wishlist error: {e}")
        return None

# ======================
# 그래프 생성
# ======================
def create_wishlist_graph(history):
    if len(history) < 2:
        return None
    
    # 데이터 준비 - wishlist 키가 있는 항목만 필터링
    valid_entries = [entry for entry in history if "wishlist" in entry and "timestamp" in entry]
    
    if len(valid_entries) < 2:
        return None
    
    dates = [datetime.fromisoformat(entry["timestamp"]) for entry in valid_entries]
    wishlists = [entry["wishlist"] for entry in valid_entries]
    
    # 그래프 생성
    plt.figure(figsize=(12, 6))
    plt.plot(dates, wishlists, marker='o', linewidth=2, markersize=6, color='#1b2838')
    
    plt.title('Crimson Desert - Steam Wishlist History', fontsize=16, fontweight='bold')
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Wishlist Count', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # 날짜 포맷
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.gcf().autofmt_xdate()
    
    # y축 포맷 (천 단위 콤마)
    ax = plt.gca()
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
    
    plt.tight_layout()
    
    # 이미지를 메모리에 저장
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
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
    files = None
    if file_data and filename:
        files = {"file": (filename, file_data, "image/png")}
    
    payload = {"content": msg}
    if embed:
        payload["embeds"] = [embed]
    
    if files:
        # multipart/form-data로 전송
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
    state = load_state()
    ensure_key(state, "xbox_preorder_open", False)
    ensure_key(state, "sop_detected", False)

    alerts = []

    # Steam 위시리스트 수집
    wishlist_count = get_steam_wishlist()
    if wishlist_count is not None:
        history = add_history_entry(wishlist_count)
        alerts.append(f"📊 **Steam 위시리스트**: {wishlist_count:,}개")

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
    valid_history = [entry for entry in history if "wishlist" in entry and "timestamp" in entry]
    graph_buffer = create_wishlist_graph(valid_history) if len(valid_history) >= 2 else None

    wishlist_text = f"📊 **Steam 위시리스트**: {wishlist_count:,}개" if wishlist_count else "📊 **Steam 위시리스트**: 수집 실패"

    embed = {
        "title": "📊 Crimson Desert 스토어 / SOP 추적",
        "description": (
            f"📅 **출시일**: 2026-03-19 ({dday})\n\n"
            f"{wishlist_text}\n"
            f"📈 **총 {len(valid_history)}개 히스토리 기록**\n\n"
            f"🔗 **플랫폼 바로가기**\n"
            f"[SteamDB]({STEAMDB_URL}) | "
            f"[PlayStation US]({PS_US_CATEGORY_URL}) | "
            f"[Xbox]({XBOX_SEARCH_URL}) | "
            f"[Steam]({STEAM_URL})\n\n"
            f"🟢 **Steam**: 예구 오픈\n"
            f"🟢 **PlayStation US**: 예구 오픈\n"
            f"🟢 **Xbox**: 예구 오픈 (검색 기반)\n"
            f"🎥 [**SOP: {'감지됨' if state['sop_detected'] else '미감지'}**]({PS_BLOG_URL})\n"
            f"([PlayStation Blog]({PS_BLOG_URL}))\n\n"
            f"자동 추적 · {now}"
        ),
        "color": 0x2ecc71
    }

    if graph_buffer:
        embed["image"] = {"url": "attachment://wishlist_graph.png"}

    if alerts:
        send_discord(
            "🚨 **변경 감지 발생**\n" + "\n".join(alerts),
            embed,
            graph_buffer,
            "wishlist_graph.png" if graph_buffer else None
        )
    else:
        send_discord(
            "🔔 **Crimson Desert 상태 업데이트**",
            embed,
            graph_buffer,
            "wishlist_graph.png" if graph_buffer else None
        )

    save_state(state)

if __name__ == "__main__":
    main()
