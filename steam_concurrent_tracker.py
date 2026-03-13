#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Steam 동접 추적기 — 멀티 게임
- 붉은사막 (AppID 3321460): 한국 출시(2026-03-20 07:00 KST) 이후에만 추적 시작
- 몬헌 와일즈 (AppID 2246340): 항상 추적 (테스트용)
- Discord 웹훅으로 알림 전송
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

GAMES = [
    {
        "name":         "몬스터헌터 와일즈",
        "app_id":       2246340,
        "emoji":        "🦕",
        "history_file": "steam_history_mhwilds.json",
        "active_after": None,                                        # 항상 추적
        "milestones":   [50_000, 100_000, 200_000, 500_000],
    },
    {
        "name":         "붉은사막",
        "app_id":       3321460,
        "emoji":        "🏜️",
        "history_file": "steam_history_crimsondesert.json",
        "active_after": datetime(2026, 3, 20, 7, 0, 0, tzinfo=KST), # 한국 출시 기준
        "milestones":   [10_000, 50_000, 100_000, 200_000, 500_000],
    },
]

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# =============================================================================
# 유틸
# =============================================================================

def now_kst() -> datetime:
    return datetime.now(KST)

def is_game_active(game: dict, now: datetime) -> bool:
    if game["active_after"] is None:
        return True
    return now >= game["active_after"]

def format_countdown(release_dt: datetime, now: datetime) -> str:
    """출시까지 남은 시간을 D-7 06:23:45 형식으로 반환"""
    delta = release_dt - now
    if delta.total_seconds() <= 0:
        return "출시됨 ✅"
    total_sec = int(delta.total_seconds())
    days    = total_sec // 86400
    hours   = (total_sec % 86400) // 3600
    minutes = (total_sec % 3600) // 60
    seconds = total_sec % 60
    if days > 0:
        return f"D-{days}  {hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

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

def send_discord_active(game: dict, current: int, prev: int | None,
                        p_all: int, p_24h: int, milestone: int | None,
                        now: datetime):
    if not DISCORD_WEBHOOK:
        return

    diff    = format_diff(current, prev)
    t_emoji = trend_emoji(current, prev)
    pct     = f"{current / p_all * 100:.1f}%" if p_all > 0 else "-"

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


def send_discord_countdown(game: dict, countdown_str: str, now: datetime):
    """출시 전: D-day 카운트다운 알림"""
    if not DISCORD_WEBHOOK:
        return

    payload = {
        "embeds": [{
            "title":       f"⏳ {game['emoji']} {game['name']} — 출시 카운트다운",
            "description": (
                f"**출시까지**: `{countdown_str}`\n"
                f"**출시 일시**: `2026-03-20 07:00 KST` (글로벌 3/19)\n\n"
                f"_Steam 동접 추적은 출시 후 자동으로 시작됩니다._"
            ),
            "color":     0xC0392B,
            "footer":    {"text": f"appid: {game['app_id']}"},
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

    # 출시 전 → 카운트다운만
    if not is_game_active(game, now):
        countdown = format_countdown(game["active_after"], now)
        print(f"  ⏳ 출시 전 — {countdown}")
        send_discord_countdown(game, countdown, now)
        return

    # 동접 수집
    current = fetch_current_players(game["app_id"])
    if current is None:
        print("  ❌ 동접 수집 실패, 스킵")
        return

    # 히스토리 로드 & 통계
    history   = load_history(game["history_file"])
    prev      = history[-1]["players"] if history else None
    p_all     = max(peak_all_time(history), current)
    p_24      = max(peak_24h(history, now), current)
    milestone = check_milestone(current, history, game["milestones"])

    # 히스토리 저장
    history.append({"timestamp": now.isoformat(), "players": current})
    save_history(game["history_file"], history)

    # 콘솔 출력
    diff_str = format_diff(current, prev).strip()
    print(f"  현재: {current:,}명  {diff_str}")
    print(f"  피크: {p_all:,}명  /  24h: {p_24:,}명")
    if milestone:
        print(f"  🏆 {milestone:,}명 마일스톤 돌파!")

    # Discord 전송
    send_discord_active(game, current, prev, p_all, p_24, milestone, now)

# =============================================================================
# 메인
# =============================================================================

def main():
    now = now_kst()
    print(f"{'=' * 40}")
    print(f"🎮 Steam 동접 추적기")
    print(f"   {now.strftime('%Y-%m-%d %H:%M:%S KST')}")
    print(f"{'=' * 40}")

    for game in GAMES:
        process_game(game, now)

    print(f"\n{'=' * 40}")
    print("완료")

if __name__ == "__main__":
    main()
