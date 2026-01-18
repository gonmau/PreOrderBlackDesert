#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crimson Desert Store & SOP Tracker
- Steam / PS / Xbox 예구 상태 고정
- Xbox: 검색 기반 예구 오픈 감지
- GameStop: 검색 감지
- SOP(State of Play): PlayStation Blog 기반 감지
- 변경 감지 시 Discord 알림
- GitHub Actions Safe
"""

import json
import os
from datetime import datetime, date, timedelta
import requests

# ======================
# 환경 설정
# ======================
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

APP_NAME = "Crimson Desert"
RELEASE_DATE = date(2026, 3, 19)

STEAMDB_URL = "https://steamdb.info/app/3321460/charts/"
STEAM_URL = "https://store.steampowered.com/app/3321460"
PS_US_URL = "https://store.playstation.com/en-us/concept/10010482"
XBOX_SEARCH_URL = "https://www.xbox.com/en-US/search?q=Crimson+Desert"
GAMESTOP_SEARCH_URL = "https://www.gamestop.com/search/?q=Crimson+Desert"
PS_BLOG_URL = "https://blog.playstation.com/"

STATE_FILE = "store_state.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ======================
# 상태 로드 / 저장
# ======================
def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def safe_state(state, key, default):
    if key not in state:
        state[key] = default

# ======================
# 유틸
# ======================
def calc_dday():
    today = date.today()
    delta = (RELEASE_DATE - today).days
    if delta > 0:
        return f"D-{delta}"
    elif delta == 0:
        return "D-DAY"
    else:
        return f"D+{abs(delta)}"

# ======================
# Xbox 예구 감지 (검색 기반)
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
# GameStop 검색 감지
# ======================
def detect_gamestop():
    try:
        r = requests.get(GAMESTOP_SEARCH_URL, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return False
        return "crimson desert" in r.text.lower()
    except Exception:
        return False

# ======================
# SOP 감지 (PlayStation Blog)
# ======================
def detect_sop():
    try:
        r = requests.get(PS_BLOG_URL, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None

        text = r.text.lower()
        if "state of play" not in text:
            return None

        # 행사 발표에 쓰이는 키워드
        if not any(k in text for k in ["announce", "broadcast", "watch live", "returns"]):
            return None

        return PS_BLOG_URL
    except Exception:
        return None

# ======================
# Discord 전송
# ======================
def send_discord(content, embed=None):
    payload = {"content": content}
    if embed:
        payload["embeds"] = [embed]
    requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)

# ======================
# 메인
# ======================
def main():
    state = load_state()

    # 기존 state.json 호환
    safe_state(state, "xbox_preorder_open", False)
    safe_state(state, "gamestop_detected", False)
    safe_state(state, "sop_detected", False)

    alerts = []

    # Xbox
    xbox_open = detect_xbox_preorder()
    if xbox_open and not state["xbox_preorder_open"]:
        alerts.append("🟢 **Xbox 예구 오픈 (검색 기반)**")
        state["xbox_preorder_open"] = True

    # GameStop
    gamestop_open = detect_gamestop()
    if gamestop_open and not state["gamestop_detected"]:
        alerts.append("🛒 **GameStop 검색 감지**")
        state["gamestop_detected"] = True

    # SOP
    sop_url = detect_sop()
    if sop_url and not state["sop_detected"]:
        alerts.append("🎥 **State of Play 행사 감지**")
        state["sop_detected"] = True

    # 공통 카드
    dday = calc_dday()
    now_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    embed = {
        "title": "📊 Crimson Desert 스토어 / SOP 추적",
        "description": (
            f"📅 **출시일**: 2026-03-19 ({dday})\n\n"
            f"🔗 **플랫폼 바로가기**\n"
            f"[SteamDB]({STEAMDB_URL}) | "
            f"[PlayStation US]({PS_US_URL}) | "
            f"[Xbox]({XBOX_SEARCH_URL}) | "
            f"[Steam]({STEAM_URL}) | "
            f"[GameStop 검색]({GAMESTOP_SEARCH_URL})\n\n"
            f"🟢 **Steam**: 예구 오픈\n"
            f"🟢 **PlayStation US**: 예구 오픈\n"
            f"🟢 **Xbox**: 예구 오픈 (검색 기반)\n"
            f"🟡 **GameStop**: {'감지됨' if gamestop_open else '미감지'}\n"
            f"🎥 **SOP**: {'감지됨' if state['sop_detected'] else '미감지'}\n\n"
            f"자동 추적 · {now_utc}"
        ),
        "color": 0x5865F2
    }

    if alerts:
        send_discord("🚨 **변경 감지 발생**\n" + "\n".join(alerts), embed)
    else:
        send_discord("🔔 **Crimson Desert 상태 업데이트**", embed)

    save_state(state)

if __name__ == "__main__":
    main()
