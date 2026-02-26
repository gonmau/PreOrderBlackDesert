#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Steam 국가별 Top Seller 순위 추적기 (테스트용 - 5개국)
- Steam 공식 API: getappsincategory (최대 100개)
- 대상: 미국, 영국, 일본, 한국, 독일
"""

import json
import os
import time
from datetime import datetime, timezone, timedelta
import requests

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
STEAM_APP_IDS = {"3321460", "1418525"}  # 스탠다드 + 디럭스 에디션

# ======================
# Steam API 호출
# ======================
def get_top_sellers(cc):
    """Steam getappsincategory API로 국가별 top seller 가져오기 (최대 100개)"""
    url = f"https://store.steampowered.com/api/getappsincategory/?cc={cc}&category=topsellers&start=0&count=100&l=en"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            print(f"  ⚠️ {cc} 응답 실패: {r.status_code}")
            return None

        data = r.json()
        items = data.get("apps", [])
        if not items:
            print(f"  ⚠️ {cc} 데이터 없음, 키 목록: {list(data.keys())}")
            return None

        rank = None
        top20 = []
        seen = set()  # 중복 제거

        real_rank = 0
        for item in items:
            appid = str(item.get("id") or item.get("appid", ""))
            name = item.get("name", "")
            if appid in seen:
                continue
            seen.add(appid)
            real_rank += 1
            top20.append({"rank": real_rank, "appid": appid, "name": name})
            if appid in STEAM_APP_IDS:
                rank = real_rank
            if real_rank >= 20:
                break

        print(f"  ✅ {cc}: Crimson Desert {'#' + str(rank) if rank else '순위권 밖 (100위 이내)'}")
        return {"rank": rank, "top20": top20}

    except Exception as e:
        print(f"  ❌ {cc} 오류: {e}")
        return None
HISTORY_FILE = "steam_topseller_history.json"

KST = timezone(timedelta(hours=9))

# 테스트 대상 5개국 (국가코드: 한글명)
TARGET_COUNTRIES = {
    "us": "미국",
    "gb": "영국",
    "jp": "일본",
    "kr": "한국",
    "de": "독일",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}

# ======================
# Steam API 호출
# ======================


# ======================
# 히스토리 관리
# ======================
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

# ======================
# Discord 알림
# ======================
def send_discord(msg, embed=None):
    if not DISCORD_WEBHOOK:
        return
    payload = {"content": msg}
    if embed:
        payload["embeds"] = [embed]
    try:
        requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
    except Exception as e:
        print(f"  ❌ Discord 전송 실패: {e}")

# ======================
# 메인
# ======================
def main():
    print("=" * 60)
    print("🎮 Steam Top Seller 순위 추적기 (테스트 - 5개국)")
    print("=" * 60)

    now_kst = datetime.now(KST)
    timestamp = now_kst.isoformat()
    results = {}

    for cc, name in TARGET_COUNTRIES.items():
        print(f"\n🔍 {name} ({cc}) 수집 중...")
        result = get_top_sellers(cc)
        if result:
            results[name] = result
        time.sleep(1)  # API 과부하 방지

    if not results:
        print("❌ 수집 실패")
        return

    # 히스토리 저장
    history = load_history()
    history.append({
        "timestamp": timestamp,
        "results": results
    })
    save_history(history)
    print(f"\n✅ 히스토리 저장 완료 (총 {len(history)}개)")

    # Discord 알림
    lines = []
    for name, data in results.items():
        rank = data.get("rank")
        rank_str = f"**#{rank}**" if rank else "순위권 밖"
        lines.append(f"**{name}**: {rank_str}")

    embed = {
        "title": "🎮 Steam Top Seller — Crimson Desert",
        "description": (
            f"📅 {now_kst.strftime('%Y-%m-%d %H:%M KST')}\n\n"
            + "\n".join(lines)
        ),
        "color": 0x1B2838
    }
    send_discord("📢 Steam 순위 업데이트", embed)
    print("✅ 완료!")

if __name__ == "__main__":
    main()
