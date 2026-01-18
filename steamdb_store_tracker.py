#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crimson Desert 스토어 오픈 감지 & 링크 알림 봇
- SteamDB: 링크만 제공 (차단 회피)
- PlayStation: US 스토어 링크
- Xbox: 예구 페이지 오픈 감지
- GameStop: Google 검색 기반 감지 (차단 회피)
"""

import os
import json
import requests
from datetime import datetime

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

APP_NAME = "Crimson Desert"

STEAMDB_URL = "https://steamdb.info/app/3321460/charts/"
STEAM_URL = "https://store.steampowered.com/app/3321460"
PS_US_URL = "https://store.playstation.com/en-us/concept/10005050"
XBOX_SEARCH_URL = "https://www.xbox.com/en-us/search?q=Crimson+Desert"
GAMESTOP_SEARCH_URL = "https://www.gamestop.com/search/?q=Crimson+Desert"

STATE_FILE = "store_state.json"


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "xbox_open": False,
        "gamestop_open": False,
    }


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def google_search_contains(keyword: str) -> bool:
    """
    Google HTML 검색 결과에 키워드 존재 여부만 확인
    (페이지 접근 X, 검색 결과만 사용)
    """
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    query = f"site:gamestop.com \"{keyword}\""
    url = f"https://www.google.com/search?q={query}"

    r = requests.get(url, headers=headers, timeout=15)
    return keyword.lower() in r.text.lower()


def xbox_search_open() -> bool:
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    r = requests.get(XBOX_SEARCH_URL, headers=headers, timeout=15)
    return "Crimson Desert" in r.text


def send_discord(embed):
    payload = {
        "embeds": [embed]
    }
    requests.post(DISCORD_WEBHOOK, json=payload)


def main():
    state = load_state()
    notifications = []

    # Xbox 감지
    xbox_now_open = xbox_search_open()
    if xbox_now_open and not state["xbox_open"]:
        notifications.append("🟢 Xbox 예구/스토어 페이지 감지")
        state["xbox_open"] = True

    # GameStop 감지 (검색 기반)
    gamestop_now_open = google_search_contains(APP_NAME)
    if gamestop_now_open and not state["gamestop_open"]:
        notifications.append("🟢 GameStop 예구 페이지 검색 감지")
        state["gamestop_open"] = True

    save_state(state)

    # 매일 기본 카드 (오픈 여부 포함)
    description_lines = [
        "🔔 **스토어 상태 자동 추적**",
        "",
        "🔗 **플랫폼 바로가기**",
        f"[SteamDB]({STEAMDB_URL})",
        f"[PlayStation US]({PS_US_URL})",
        f"[Xbox]({XBOX_SEARCH_URL})",
        f"[Steam]({STEAM_URL})",
        f"[GameStop 검색]({GAMESTOP_SEARCH_URL})",
        "",
        "🟢 Xbox: " + ("오픈" if state["xbox_open"] else "미오픈"),
        "🟢 GameStop: " + ("검색 감지됨" if state["gamestop_open"] else "미감지"),
    ]

    if notifications:
        description_lines.insert(0, "🚨 **변경 감지 발생**")
        description_lines.insert(1, "\n".join(notifications))

    embed = {
        "title": "Crimson Desert 스토어 추적",
        "description": "\n".join(description_lines),
        "color": 0x2ecc71,
        "footer": {
            "text": f"자동 추적 · {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        }
    }

    send_discord(embed)


if __name__ == "__main__":
    main()
