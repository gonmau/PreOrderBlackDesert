#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crimson Desert Store & SOP Tracker (Final Stable)
- Steam / PS / Xbox 예구 상태 기준 고정
- PlayStation US: 카테고리 기반 링크 사용
- Xbox: 검색 기반 예구 오픈
- SteamDB: 참고 링크만 사용
- SOP(State of Play): PlayStation Blog 감지
- 변경 감지 시 Discord 알림
"""

import json
import os
from datetime import datetime, date
import requests

# ======================
# 환경 설정
# ======================
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

RELEASE_DATE = date(2026, 3, 19)

STEAMDB_URL = "https://steamdb.info/app/3321460/charts/"
STEAM_URL = "https://store.steampowered.com/app/3321460"

# 🔴 변경된 PS US 링크 (카테고리 기준)
PS_US_CATEGORY_URL = (
    "https://store.playstation.com/en-us/category/"
    "3bf499d7-7acf-4931-97dd-2667494ee2c9/1"
)

XBOX_SEARCH_URL = "https://www.xbox.com/en-US/search?q=Crimson+Desert"
PS_BLOG_URL = "https://blog.playstation.com/"

STATE_FILE = "store_state.json"

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
# SOP 감지 (PlayStation Blog)
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
def send_discord(msg, embed=None):
    payload = {"content": msg}
    if embed:
        payload["embeds"] = [embed]
    requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)

# ======================
# 메인
# ======================
def main():
    state = load_state()
    ensure_key(state, "xbox_preorder_open", False)
    ensure_key(state, "sop_detected", False)

    alerts = []

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

    embed = {
        "title": "📊 Crimson Desert 스토어 / SOP 추적",
        "description": (
            f"📅 **출시일**: 2026-03-19 ({dday})\n\n"
            f"🔗 **플랫폼 바로가기**\n"
            f"[SteamDB]({STEAMDB_URL}) | "
            f"[PlayStation US]({PS_US_CATEGORY_URL}) | "
            f"[Xbox]({XBOX_SEARCH_URL}) | "
            f"[Steam]({STEAM_URL})\n\n"
            f"🟢 **Steam**: 예구 오픈\n"
            f"🟢 **PlayStation US**: 예구 오픈\n"
            f"🟢 **Xbox**: 예구 오픈 (검색 기반)\n"
            f"🎥 **SOP**: {'감지됨' if state['sop_detected'] else '미감지'}\n\n"
            f"자동 추적 · {now}"
        ),
        "color": 0x2ecc71
    }

    if alerts:
        send_discord("🚨 **변경 감지 발생**\n" + "\n".join(alerts), embed)
    else:
        send_discord("🔔 **Crimson Desert 상태 업데이트**", embed)

    save_state(state)

if __name__ == "__main__":
    main()
