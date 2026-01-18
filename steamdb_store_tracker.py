import json
import os
import requests
from datetime import date
from urllib.parse import quote_plus

# =========================
# 기본 설정
# =========================

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

APP_NAME = "Crimson Desert"
STEAM_APP_ID = "3321460"

RELEASE_DATE = date(2026, 3, 19)

STATE_FILE = "store_state.json"

STEAMDB_URL = f"https://steamdb.info/app/{STEAM_APP_ID}/charts/"
STEAM_URL = f"https://store.steampowered.com/app/{STEAM_APP_ID}"
PS_US_URL = "https://store.playstation.com/en-us"
XBOX_SEARCH_URL = "https://www.xbox.com/en-US/search"
GAMESTOP_SEARCH_URL = "https://www.gamestop.com/search/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; GitHubActions/1.0)"
}

# =========================
# 유틸
# =========================

def load_state():
    default_state = {
        "gamestop_detected": False,
        "xbox_detected": False
    }

    if not os.path.exists(STATE_FILE):
        return default_state

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)

    # 🔧 누락 키 보정
    for key, value in default_state.items():
        if key not in state:
            state[key] = value

    return state


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def get_dday_label():
    today = date.today()
    delta = (RELEASE_DATE - today).days

    if delta > 0:
        return f"D-{delta}"
    elif delta == 0:
        return "🎉 TODAY"
    else:
        return "✅ 출시됨"

# =========================
# GameStop 검색 기반 감지
# =========================

def check_gamestop():
    query = quote_plus(APP_NAME)
    url = f"https://www.google.com/search?q=site:gamestop.com+{query}"

    r = requests.get(url, headers=HEADERS, timeout=10)
    if r.status_code != 200:
        return False

    return "gamestop.com" in r.text.lower()

# =========================
# Xbox 검색 기반 감지
# =========================

def check_xbox():
    query = quote_plus(APP_NAME)
    url = f"https://www.google.com/search?q=site:xbox.com+{query}"

    r = requests.get(url, headers=HEADERS, timeout=10)
    if r.status_code != 200:
        return False

    return "xbox.com" in r.text.lower()

# =========================
# Discord 전송
# =========================

def send_discord(message, embed):
    payload = {
        "content": message,
        "embeds": [embed]
    }
    requests.post(DISCORD_WEBHOOK, json=payload)

# =========================
# 메인
# =========================

def main():
    state = load_state()

    dday = get_dday_label()

    gamestop_open = check_gamestop()
    xbox_open = check_xbox()

    alerts = []

    if gamestop_open and not state["gamestop_detected"]:
        alerts.append("🛒 **GameStop 예구 페이지 감지됨**")
        state["gamestop_detected"] = True

    if xbox_open and not state["xbox_detected"]:
        alerts.append("🟢 **Xbox 스토어 페이지 감지됨**")
        state["xbox_detected"] = True

    embed = {
        "title": f"📊 {APP_NAME} 스토어 추적",
        "url": STEAMDB_URL,
        "color": 0xE74C3C,
        "fields": [
            {
                "name": "📅 출시일",
                "value": f"2026-03-19 ({dday})",
                "inline": True
            },
            {
                "name": "🔗 플랫폼 링크",
                "value": (
                    f"[SteamDB]({STEAMDB_URL}) | "
                    f"[PlayStation US]({PS_US_URL}) | "
                    f"[Xbox]({XBOX_SEARCH_URL}) | "
                    f"[Steam]({STEAM_URL}) | "
                    f"[GameStop]({GAMESTOP_SEARCH_URL})"
                ),
                "inline": False
            }
        ],
        "footer": {
            "text": "차단 회피: 검색 기반 감지 / GitHub Actions Safe"
        }
    }

    content = "\n".join(alerts) if alerts else None

    send_discord(content, embed)
    save_state(state)

if __name__ == "__main__":
    main()
