#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Steam 동접 추적기 — 멀티 게임
- 붉은사막 출시(2026-03-20 07:00 KST) 전: 카운트다운 전송 + 비교군 게임 추적
- 붉은사막 출시 후: 붉은사막만 추적 (비교군 게임 자동 종료)
- cron 5분 주기 권장: */5 * * * * python3 /path/to/steam_concurrent_tracker.py

[히스토리 GitHub 자동 커밋]
- 환경변수 GH_TOKEN, GH_OWNER, GH_REPO 설정 필요
- 수집마다 steam_history_crimsondesert.json을 레포에 자동 커밋
- GitHub Pages가 활성화된 경우 best.html에서 직접 fetch 가능
  URL: https://{GH_OWNER}.github.io/{GH_REPO}/steam_history_crimsondesert.json
"""

import os
import json
import base64
import requests
from datetime import datetime, timezone, timedelta

# =============================================================================
# 설정
# =============================================================================

KST = timezone(timedelta(hours=9))
CRIMSON_DESERT_RELEASE = datetime(2026, 3, 20, 7, 0, 0, tzinfo=KST)

GAMES = [
    {
        "name": "붉은사막",
        "app_id": 3321460,
        "emoji": "🏜️",
        "history_file": "steam_history_crimsondesert.json",
        "track_after": CRIMSON_DESERT_RELEASE,
        "track_until": None,
        "milestones": [5_000, 10_000, 30_000, 50_000, 70_000, 100_000,
                       150_000, 200_000, 250_000, 300_000],
    },
]

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# GitHub 자동 커밋 설정
GH_TOKEN = os.getenv("GH_TOKEN")        # GitHub Personal Access Token (repo scope)
GH_OWNER = os.getenv("GH_OWNER", "gonmau")
GH_REPO  = os.getenv("GH_REPO",  "PreOrderBlackDesert")
GH_BRANCH = os.getenv("GH_BRANCH", "main")

# =============================================================================
# 유틸
# =============================================================================

def now_kst() -> datetime:
    return datetime.now(KST)

def is_active(game: dict, now: datetime) -> bool:
    if game["track_after"] and now < game["track_after"]:
        return False
    if game["track_until"] and now >= game["track_until"]:
        return False
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
    return f"D-{d} {h:02d}:{m:02d}:{s:02d}" if d > 0 else f"{h:02d}:{m:02d}:{s:02d}"

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
# 히스토리 로컬 관리
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
# GitHub 자동 커밋
# =============================================================================

def commit_to_github(local_path: str, repo_path: str, commit_message: str) -> bool:
    """
    로컬 파일을 GitHub API를 통해 레포에 커밋합니다.

    Args:
        local_path:     로컬 파일 경로 (예: 'steam_history_crimsondesert.json')
        repo_path:      레포 내 경로 (예: 'steam_history_crimsondesert.json')
        commit_message: 커밋 메시지
    Returns:
        True if success, False otherwise
    """
    if not GH_TOKEN:
        print("  ⚠️ GH_TOKEN 미설정 → GitHub 커밋 스킵")
        return False

    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    api_base = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}"

    # 1) 현재 파일의 SHA 가져오기 (업데이트 시 필요)
    sha = None
    try:
        r = requests.get(
            f"{api_base}/contents/{repo_path}",
            headers=headers,
            params={"ref": GH_BRANCH},
            timeout=15,
        )
        if r.status_code == 200:
            sha = r.json().get("sha")
        elif r.status_code != 404:
            print(f"  ⚠️ SHA 조회 실패 ({r.status_code}): {r.text[:200]}")
    except Exception as e:
        print(f"  ⚠️ SHA 조회 오류: {e}")

    # 2) 파일 내용을 base64 인코딩
    try:
        with open(local_path, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"  ❌ 파일 읽기 실패 ({local_path}): {e}")
        return False

    # 3) PUT으로 생성/업데이트
    payload = {
        "message": commit_message,
        "content": content_b64,
        "branch": GH_BRANCH,
    }
    if sha:
        payload["sha"] = sha  # 기존 파일 업데이트 시 SHA 필수

    try:
        r = requests.put(
            f"{api_base}/contents/{repo_path}",
            headers=headers,
            json=payload,
            timeout=20,
        )
        if r.status_code in (200, 201):
            action = "업데이트" if r.status_code == 200 else "생성"
            print(f"  ✅ GitHub 커밋 {action} 완료: {repo_path}")
            return True
        else:
            print(f"  ❌ GitHub 커밋 실패 ({r.status_code}): {r.text[:300]}")
            return False
    except Exception as e:
        print(f"  ❌ GitHub 커밋 오류: {e}")
        return False

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
    if d > 0: return f" ▲{d:,}"
    if d < 0: return f" ▼{abs(d):,}"
    return " ━"

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
        f"**24h 피크**: `{p_24h:,}명`",
    ]

    steamdb_url = f"https://steamdb.info/app/{game['app_id']}/charts/"
    lines.append(f"\n📊 [SteamDB 동접 차트]({steamdb_url})")

    color = 0x00B0F4
    if milestone:
        lines.insert(0, f"🏆 **{milestone:,}명 돌파!\n")
        color = 0xFFD700

    payload = {
        "embeds": [{
            "title": f"{t_emoji} {game['emoji']} {game['name']} — Steam 동접",
            "description": "\n".join(lines),
            "color": color,
            "footer": {"text": f"appid: {game['app_id']} · Steam Web API"},
            "timestamp": now.isoformat(),
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK, json=payload, timeout=10).raise_for_status()
        print(f"  ✅ Discord 전송 완료 ({current:,}명)")
    except Exception as e:
        print(f"  ❌ Discord 전송 실패: {e}")


CRIMSON_DESERT_STEAMDB = "https://steamdb.info/app/3321460/charts/"

def send_countdown(countdown_str: str, now: datetime):
    if not DISCORD_WEBHOOK:
        return
    payload = {
        "embeds": [{
            "title": "⏳ 🏜️ 붉은사막 — 출시 카운트다운",
            "description": (
                f"**출시까지**: `{countdown_str}`\n"
                f"**출시 일시**: `2026-03-20 07:00 KST` (글로벌 3/19)\n\n"
                f"📊 [SteamDB 동접 차트]({CRIMSON_DESERT_STEAMDB})\n\n"
                f"_Steam 동접 추적은 출시 후 자동으로 시작됩니다._"
            ),
            "color": 0xC0392B,
            "footer": {"text": "appid: 3321460"},
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
    print(f"{game['emoji']} {game['name']} (appid: {game['app_id']})")

    if not is_active(game, now):
        if game["track_until"] and now >= game["track_until"]:
            print("  ⏹️ 추적 종료")
        else:
            print("  ⏳ 추적 대기 중 (출시 전)")
        return

    current = fetch_current_players(game["app_id"])
    if current is None:
        print("  ❌ 동접 수집 실패, 스킵")
        return

    history  = load_history(game["history_file"])
    prev     = history[-1]["players"] if history else None
    p_all    = max(peak_all_time(history), current)
    p_24     = max(peak_24h(history, now), current)
    milestone = check_milestone(current, history, game["milestones"])

    # 로컬 히스토리에 추가 & 저장
    history.append({"timestamp": now.isoformat(), "players": current})
    save_history(game["history_file"], history)

    diff_str = format_diff(current, prev).strip()
    print(f"  현재: {current:,}명 {diff_str}")
    print(f"  피크: {p_all:,}명 / 24h: {p_24:,}명")
    if milestone:
        print(f"  🏆 {milestone:,}명 마일스톤 돌파!")

    # ── GitHub 자동 커밋 ──────────────────────────────────────────
    commit_msg = (
        f"ccu: {game['name']} {current:,}명 "
        f"({now.strftime('%m/%d %H:%M')} KST)"
    )
    commit_to_github(
        local_path=game["history_file"],
        repo_path=game["history_file"],   # 레포 루트에 저장
        commit_message=commit_msg,
    )
    # ──────────────────────────────────────────────────────────────

    send_active(game, current, prev, p_all, p_24, milestone, now)

# =============================================================================
# 메인
# =============================================================================

def main():
    now = now_kst()
    print(f"{'=' * 40}")
    print(f"🎮 Steam 동접 추적기")
    print(f"  {now.strftime('%Y-%m-%d %H:%M:%S KST')}")
    if is_pre_release(now):
        print(f"  ⏳ 붉은사막 출시까지: {format_countdown(now)}")
    else:
        print(f"  🚀 붉은사막 출시 후 모드")
    print(f"{'=' * 40}")

    if is_pre_release(now):
        release_day_start = CRIMSON_DESERT_RELEASE.replace(
            hour=6, minute=55, second=0, microsecond=0
        )
        if now >= release_day_start:
            send_countdown(format_countdown(now), now)
        elif now.hour == 9 and now.minute < 5:
            send_countdown(format_countdown(now), now)
        else:
            print("  ⏳ 카운트다운 전송 시간 아님 → 스킵")

    for game in GAMES:
        process_game(game, now)

    print(f"\n{'=' * 40}")
    print("완료")


if __name__ == "__main__":
    main()
