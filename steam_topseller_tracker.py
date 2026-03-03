#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Steam 국가별 Top Seller 순위 추적기 (10개국)
- Steam 공식 API: getappsincategory (최대 100개)
- 대상: 미국, 영국, 독일, 프랑스, 캐나다, 브라질, 일본, 한국, 중국, 러시아
"""

import json
import os
import time
from datetime import datetime, timezone, timedelta
import requests

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
STEAM_APP_IDS = {"3321460"}  # Crimson Desert (스탠다드/디럭스 동일 App ID, 1418525는 sub ID라 제거)

# ======================
# Steam API 호출
# ======================
def get_top_sellers(cc):
    """Steam charts/topselling 페이지에서 국가별 top seller 파싱 (최대 100개)"""
    url = f"https://store.steampowered.com/charts/topselling/{cc.upper()}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            print(f"  ⚠️ {cc} 응답 실패: {r.status_code}")
            return None

        html = r.text

        # charts 페이지는 JSON 데이터를 _popularityData 또는 script 태그에 포함
        # "appid":3321460 형태로 검색
        import re

        # 방법1: script 내 JSON 파싱 (Steam charts 페이지 구조)
        # data-ds-appid 또는 href="/app/{appid}" 패턴으로 순위 추출
        app_ids_in_order = []
        seen = set()

        # href="/app/숫자" 패턴으로 appid 순서대로 추출
        pattern = re.compile(r'href="https://store\.steampowered\.com/app/(\d+)/')
        matches = pattern.findall(html)

        for appid in matches:
            if appid not in seen:
                seen.add(appid)
                app_ids_in_order.append(appid)
            if len(app_ids_in_order) >= 100:
                break

        if not app_ids_in_order:
            print(f"  ⚠️ {cc} HTML 파싱 실패 (앱 목록 없음), HTML 길이: {len(html)}")
            return None

        rank = None
        top20 = []
        for i, appid in enumerate(app_ids_in_order, 1):
            top20.append({"rank": i, "appid": appid})
            if appid in STEAM_APP_IDS:
                rank = i

        print(f"  ✅ {cc}: 총 {len(app_ids_in_order)}개 파싱, Crimson Desert {'#' + str(rank) if rank else '순위권 밖'}")
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
    "de": "독일",
    "fr": "프랑스",
    "ca": "캐나다",
    "br": "브라질",
    "jp": "일본",
    "kr": "한국",
    "cn": "중국",
    "ru": "러시아",
}

STORE_LINKS = {
    cc: f"https://store.steampowered.com/charts/topselling/{cc.upper()}"
    for cc in ["us","gb","de","fr","ca","br","jp","kr","cn","ru"]
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
    print("🎮 Steam Top Seller 순위 추적기 (10개국)")
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
    cc_by_name = {v: k for k, v in TARGET_COUNTRIES.items()}
    for name, data in results.items():
        rank = data.get("rank")
        rank_str = f"**#{rank}**" if rank else "순위권 밖"
        cc = cc_by_name.get(name, "")
        link = STORE_LINKS.get(cc, "")
        lines.append(f"[**{name}**]({link}): {rank_str}")

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
