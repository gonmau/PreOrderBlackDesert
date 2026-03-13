#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Steam 동접 추적기 — 멀티 게임
- 붉은사막 출시(2026-03-20 07:00 KST) 전: 카운트다운 전송 + 비교군 게임 추적
- 붉은사막 출시 후: 붉은사막만 추적 (비교군 게임 자동 종료)
- cron 5분 주기 권장: */5 * * * * python3 /path/to/steam_concurrent_tracker.py
"""

import os
import json
import requests
from datetime import datetime, timezone, timedelta

# =============================================================================
# 설정
# =============================================================================

KST = timezone(timedelta(hours=9))

CRIMSON_DESERT_RELEASE = datetime(2026, 3, 20, 7, 0, 0, tzinfo=KST)

GAMES = [
    # ── 붉은사막 출시 후 추적 ──────────────────────────────────────────
    {
        "name":           "붉은사막",
        "app_id":         3321460,
        "emoji":          "🏜️",
        "history_file":   "steam_history_crimsondesert.json",
        "track_after":    CRIMSON_DESERT_RELEASE,   # 출시 후 추적 시작
        "track_until":    None,                      # 종료 없음
        "milestones":     [10_000, 50_000, 100_000, 200_000, 500_000],
    },
    # ── 붉은사막 출시 전까지만 추적 (비교군) ──────────────────────────
    {
        "name":           "슬레이 더 스파이어 2",
        "app_id":         2868840,
        "emoji":          "🃏",
        "history_file":   "steam_history_sts2.json",
        "track_after":    None,
        "track_until":    CRIMSON_DESERT_RELEASE,
        "milestones":     [50_000, 100_000, 200_000, 500_000],
    },
    {
        "name":           "바이오하자드 레퀴엠",
        "app_id":         3764200,
        "emoji":          "🧟",
        "history_file":   "steam_history_re_requiem.json",
        "track_after":    None,
        "track_until":    CRIMSON_DESERT_RELEASE,
        "milestones":     [50_000, 100_000, 200_000, 500_000],
    },
]

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# =============================================================================
# 유틸
# =============================================================================

def now_kst() -> datetime:
    return datetime.now(KST)

def is_active(game: dict, now: datetime) -> bool:
    """현재 추적해야 하는 게임인지 확인"""
    if game["track_after"] and now < game["track_after"]:
        return False   # 아직 추적 시작 전
    if game["track_until"] and now >= game["track_until"]:
        return False   # 추적 종료
    return True

def is_pre_release(now: datetime) -> bool:
    return now < CRIMSON_DESERT_RELEASE

def format_countdown(now: datetime) -> str:
    delta = CRIMSON_DESERT_RELEASE - now
    if delta.total_seconds() <= 0:
        return "출시됨 ✅"
    s = int(delta.total_seconds())
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"D-{d}  {h:02d}:{m:02d}:{s:02d}" if d > 0 else f"{h:02d}:{m:02d}:{s:02d}"

# =============================================================================
# Steam API
# =============================================================================

def fetch_current_players(app_id: int) -> int | None:
    url = (
        "https://api.steampowered.com/ISteamUserStats/"
        f"GetNumberOfCurrentPlayers/v1/?appid={app_id}"
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        result = r.json().get("response", {})
        if result.get("result") == 1:
            return result["player_count"]
    except Exception as e:
        print(f"  ❌ Steam API 오류 (appid={app_id}): {e}")
    return None

# =============================================================================
# 히스토리
# =============================================================================

def load_history(path: str) -> list:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"  ⚠️ 히스토리 로드 실패 ({path}): {e}")
        return []

def save_history(path: str, history: list):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  ⚠️ 히스토리 저장 실패 ({path}): {e}")

def peak_all_time(history: list) -> int:
    return max((h["players"] for h in history), default=0)

def peak_24h(history: list, now: datetime) -> int:
    cutoff = (now - timedelta(hours=24)).isoformat()
    vals = [h["players"] for h in history if h["timestamp"] >= cutoff]
    return max(vals, default=0)

def check_milestone(current: int, history: list, thresholds: list) -> int | None:
    prev_max = max((h["players"] for h in history), default=0)
    for t in sorted(thresholds):
        if prev_max < t <= current:
            return t
    return None

# =============================================================================
# Discord
# =============================================================================

def trend_emoji(current: int, prev: int | None) -> str:
    if prev is None: return "🎮"
    d = current - prev
    if d > 5000:  return "🚀"
    if d > 0:     return "📈"
    if d < -5000: return "📉"
    if d < 0:     return "🔻"
    return "➡️"

def format_diff(current: int, prev: int | None) -> str:
    if prev is None: return ""
    d = current - prev
    if d > 0:  return f"  ▲{d:,}"
    if d < 0:  return f"  ▼{abs(d):,}"
    return "  ━"

def send_active(game: dict, current: int, prev: int | None,
                p_all: int, p_24h: int, milestone: int | None, now: datetime):
    if not DISCORD_WEBHOOK:
        return

    diff     = format_diff(current, prev)
    t_emoji  = trend_emoji(current, prev)
    pct      = f"{current / p_all * 100:.1f}%" if p_all > 0 else "-"

    lines = [
        f"**현재 동접**: `{current:,}명`{diff}",
        f"**역대 피크**: `{p_all:,}명` ({pct})",
        f"**24h 피크**:  `{p_24h:,}명`",
    ]

    color = 0x00B0F4
    if milestone:
        lines.insert(0, f"🏆 **{milestone:,}명 돌파!**\n")
        color = 0xFFD700

    payload = {
        "embeds": [{
            "title":       f"{t_emoji} {game['emoji']} {game['name']} — Steam 동접",
            "description": "\n".join(lines),
            "color":       color,
            "footer":      {"text": f"appid: {game['app_id']} · Steam Web API"},
            "timestamp":   now.isoformat(),
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK, json=payload, timeout=10).raise_for_status()
        print(f"  ✅ Discord 전송 완료 ({current:,}명)")
    except Exception as e:
        print(f"  ❌ Discord 전송 실패: {e}")


def send_countdown(countdown_str: str, now: datetime):
    """붉은사막 출시 전 카운트다운 + 비교군 게임 현황 요약"""
    if not DISCORD_WEBHOOK:
        return

    payload = {
        "embeds": [{
            "title":       "⏳ 🏜️ 붉은사막 — 출시 카운트다운",
            "description": (
                f"**출시까지**: `{countdown_str}`\n"
                f"**출시 일시**: `2026-03-20 07:00 KST` (글로벌 3/19)\n\n"
                f"_Steam 동접 추적은 출시 후 자동으로 시작됩니다._\n"
                f"_비교군 게임(몬헌·STS2·ARC·레퀴엠)은 출시 시 자동 종료됩니다._"
            ),
            "color":     0xC0392B,
            "footer":    {"text": "appid: 3321460"},
            "timestamp": now.isoformat(),
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK, json=payload, timeout=10).raise_for_status()
        print(f"  ✅ 카운트다운 전송 완료 ({countdown_str})")
    except Exception as e:
        print(f"  ❌ 카운트다운 전송 실패: {e}")

# =============================================================================
# 게임별 처리
# =============================================================================

def process_game(game: dict, now: datetime):
    print(f"\n{'─' * 40}")
    print(f"{game['emoji']}  {game['name']}  (appid: {game['app_id']})")

    if not is_active(game, now):
        if game["track_until"] and now >= game["track_until"]:
            print("  ⏹️  추적 종료 (붉은사막 출시)")
        else:
            print("  ⏳ 추적 대기 중 (출시 전)")
        return

    current = fetch_current_players(game["app_id"])
    if current is None:
        print("  ❌ 동접 수집 실패, 스킵")
        return

    history   = load_history(game["history_file"])
    prev      = history[-1]["players"] if history else None
    p_all     = max(peak_all_time(history), current)
    p_24      = max(peak_24h(history, now), current)
    milestone = check_milestone(current, history, game["milestones"])

    history.append({"timestamp": now.isoformat(), "players": current})
    save_history(game["history_file"], history)

    diff_str = format_diff(current, prev).strip()
    print(f"  현재: {current:,}명  {diff_str}")
    print(f"  피크: {p_all:,}명  /  24h: {p_24:,}명")
    if milestone:
        print(f"  🏆 {milestone:,}명 마일스톤 돌파!")

    send_active(game, current, prev, p_all, p_24, milestone, now)

# =============================================================================
# 메인
# =============================================================================

def main():
    now = now_kst()
    print(f"{'=' * 40}")
    print(f"🎮 Steam 동접 추적기")
    print(f"   {now.strftime('%Y-%m-%d %H:%M:%S KST')}")
    if is_pre_release(now):
        print(f"   ⏳ 붉은사막 출시까지: {format_countdown(now)}")
    else:
        print(f"   🚀 붉은사막 출시 후 모드")
    print(f"{'=' * 40}")

    # 붉은사막 출시 전이면 카운트다운 별도 전송
    if is_pre_release(now):
        send_countdown(format_countdown(now), now)

    # 각 게임 처리
    for game in GAMES:
        process_game(game, now)

    print(f"\n{'=' * 40}")
    print("완료")

if __name__ == "__main__":
    main()
