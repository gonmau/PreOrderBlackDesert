#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Steam 국가별 Top Seller 순위 추적기 (10개국)
- Steam 공식 API: search/results (Crimson Desert 발견 시 즉시 중단)
- 디스코드: 텍스트 embed + 꺾은선 그래프 + 막대 그래프
"""

import io
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates
import matplotlib.ticker as ticker
import requests

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
STEAM_APP_IDS = {"3321460"}  # Crimson Desert

HISTORY_FILE = "steam_topseller_history.json"
KST = timezone(timedelta(hours=9))

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

COUNTRY_COLORS = {
    "US": "#4A90D9",
    "GB": "#C0392B",
    "DE": "#2ECC71",
    "FR": "#9B59B6",
    "CA": "#E67E22",
    "BR": "#27AE60",
    "JP": "#E74C3C",
    "KR": "#3498DB",
    "CN": "#F39C12",
    "RU": "#1ABC9C",
}

# Steam 시장 가중치 (index.html의 STEAM_MARKET_WEIGHTS 기준, 미국=10 베이스)
STEAM_WEIGHTS = {
    "us": 10.0,
    "gb":  1.9,
    "de":  1.9,
    "fr":  1.7,
    "ca":  1.8,
    "br":  1.4,
    "jp":  1.2,
    "kr":  0.9,
    "cn": 12.3,
    "ru":  3.2,
}

def calc_weighted_avg(results):
    """10개국 단순평균 순위 계산 (순위 없으면 해당 국가 제외)"""
    ranks = [data.get("rank") for data in results.values() if data.get("rank") is not None]
    return round(sum(ranks) / len(ranks), 1) if ranks else None


RETRY_DELAYS = {
    "cn": [10, 30, 60],
    "ru": [10, 30, 60],
}
DEFAULT_RETRY_DELAYS = [5, 15, 30]

COUNTRY_SLEEP = {
    "cn": 5,
    "ru": 5,
}
DEFAULT_COUNTRY_SLEEP = 1.5

STORE_LINKS = {
    cc: f"https://store.steampowered.com/charts/topselling/{cc.upper()}"
    for cc in TARGET_COUNTRIES
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}

# ======================
# Steam API 호출
# ======================
def fetch_page(cc, page, retry_delays):
    url = "https://store.steampowered.com/search/results/"
    params = {"filter": "topsellers", "cc": cc, "l": "en", "json": 1, "page": page}

    for attempt, delay in enumerate([0] + retry_delays):
        if delay > 0:
            print(f"  ⏳ {cc} p{page} {delay}초 후 재시도 ({attempt}/{len(retry_delays)})...")
            time.sleep(delay)
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                print(f"  ⚠️ {cc} p{page} 429 Rate Limited")
                if attempt == len(retry_delays):
                    print(f"  ❌ {cc} p{page} 재시도 초과, 포기")
                    return None
                continue
            else:
                print(f"  ⚠️ {cc} p{page} 응답 실패: {r.status_code}")
                return None
        except Exception as e:
            print(f"  ❌ {cc} p{page} 오류: {e}")
            return None
    return None

def get_top_sellers(cc):
    retry_delays = RETRY_DELAYS.get(cc, DEFAULT_RETRY_DELAYS)
    rank = None
    all_items = []
    seen = set()
    real_rank = 0
    found = False

    for page in range(1, 11):
        data = fetch_page(cc, page, retry_delays)
        if data is None:
            break
        items = data.get("items", [])
        if not items:
            break

        for item in items:
            logo = item.get("logo", "")
            name = item.get("name", "")
            m = re.search(r'/steam/apps/(\d+)/', logo)
            appid = m.group(1) if m else ""
            if not appid or appid in seen:
                continue
            seen.add(appid)
            real_rank += 1
            all_items.append({"rank": real_rank, "appid": appid, "name": name})
            if appid in STEAM_APP_IDS:
                rank = real_rank
                found = True

        if found:
            break
        time.sleep(1.0)

    if not all_items:
        print(f"  ⚠️ {cc} 데이터 없음")
        return None

    print(f"  ✅ {cc}: 총 {real_rank}개 파싱, Crimson Desert {'#' + str(rank) if rank else '순위권 밖'}")
    return {"rank": rank, "top20": all_items}

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
# 그래프 생성
# ======================
def make_graphs(history):
    # cc(영문) 기준으로 처리 — 한글 폰트 불필요
    cc_list = list(TARGET_COUNTRIES.keys())           # ["us","gb", ...]
    name_by_cc = {cc: name for cc, name in TARGET_COUNTRIES.items()}  # 한글명은 JSON 키 조회용
    BG = "#1B2838"
    GRID = "#4A5568"
    TEXT = "#C7D5E0"

    # 데이터 파싱 (10개국 완전한 레코드만)
    timestamps = []
    cc_ranks = {cc: [] for cc in cc_list}
    wavg_list = []

    for entry in history:
        try:
            ts = datetime.fromisoformat(entry["timestamp"])
        except:
            continue
        results = entry.get("results", {})
        # JSON 키는 한글 국가명 — 모두 있는지 확인
        if not all(name_by_cc[cc] in results for cc in cc_list):
            continue
        timestamps.append(ts)
        for cc in cc_list:
            cc_ranks[cc].append(results[name_by_cc[cc]].get("rank"))
        wavg_list.append(calc_weighted_avg(results))

    plt.rcParams["font.family"] = ["DejaVu Sans", "sans-serif"]

    # ── 0. 가중평균 순위 추이 그래프 ──────────────────────────
    fig0, ax0 = plt.subplots(figsize=(11, 4))
    fig0.patch.set_facecolor(BG)
    ax0.set_facecolor(BG)

    valid_ts0 = [t for t, w in zip(timestamps, wavg_list) if w is not None]
    valid_w0  = [w for w in wavg_list if w is not None]

    if valid_ts0:
        ax0.plot(valid_ts0, valid_w0, color="#FFD700", linewidth=2.5,
                 marker="o", markersize=5, label="Weighted Avg")
        # 각 포인트에 값 라벨
        for t, w in zip(valid_ts0, valid_w0):
            ax0.annotate(f"{w:.1f}",
                         xy=(t, w), xytext=(0, 8), textcoords="offset points",
                         fontsize=8, color="#FFD700", ha="center")
        # 최신값 강조
        ax0.axhline(y=valid_w0[-1], color="#FFD700", linestyle="--", alpha=0.3, linewidth=1)

    ax0.invert_yaxis()
    ax0.yaxis.set_major_locator(ticker.MaxNLocator(integer=False, nbins=6))
    ax0.set_xlabel("Date (KST)", color=TEXT, fontsize=10)
    ax0.set_ylabel("Weighted Rank", color=TEXT, fontsize=10)
    ax0.set_title("Crimson Desert — Avg Rank (Steam)", color="white", fontsize=13, pad=12)
    ax0.tick_params(colors=TEXT)
    ax0.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m/%d %H:%M"))
    plt.setp(ax0.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=8)
    for spine in ax0.spines.values():
        spine.set_edgecolor(GRID)
    ax0.grid(axis="y", color=GRID, linestyle="--", alpha=0.5)
    fig0.tight_layout()

    buf0 = io.BytesIO()
    fig0.savefig(buf0, format="png", dpi=130, bbox_inches="tight", facecolor=BG)
    buf0.seek(0)
    plt.close(fig0)

    # ── 1. 꺾은선 그래프 ─────────────────────────────────────
    fig1, ax1 = plt.subplots(figsize=(13, 6))
    fig1.patch.set_facecolor(BG)
    ax1.set_facecolor(BG)

    for cc in cc_list:
        ranks = cc_ranks[cc]
        valid_ts = [t for t, r in zip(timestamps, ranks) if r is not None]
        valid_r  = [r for r in ranks if r is not None]
        if not valid_r:
            continue
        color = COUNTRY_COLORS.get(cc.upper(), "#FFFFFF")
        ax1.plot(valid_ts, valid_r, marker="o", markersize=4,
                 linewidth=1.8, label=cc.upper(), color=color)
        ax1.annotate(f"#{valid_r[-1]}",
                     xy=(valid_ts[-1], valid_r[-1]),
                     xytext=(5, 0), textcoords="offset points",
                     fontsize=8, color=color, va="center")

    ax1.invert_yaxis()
    ax1.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax1.set_xlabel("Date (KST)", color=TEXT, fontsize=10)
    ax1.set_ylabel("Rank", color=TEXT, fontsize=10)
    ax1.set_title("Crimson Desert — Steam Top Seller Trend", color="white", fontsize=13, pad=12)
    ax1.tick_params(colors=TEXT)
    ax1.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m/%d %H:%M"))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=8)
    for spine in ax1.spines.values():
        spine.set_edgecolor(GRID)
    ax1.legend(loc="upper right", fontsize=8, framealpha=0.3,
               labelcolor="white", facecolor="#2A3F5F")
    ax1.grid(axis="y", color=GRID, linestyle="--", alpha=0.5)
    fig1.tight_layout()

    buf1 = io.BytesIO()
    fig1.savefig(buf1, format="png", dpi=130, bbox_inches="tight", facecolor=BG)
    buf1.seek(0)
    plt.close(fig1)

    # ── 2. 막대 그래프 (최신 스냅샷) ─────────────────────────
    latest_ranks = {}
    for entry in reversed(history):
        results = entry.get("results", {})
        if all(name_by_cc[cc] in results for cc in cc_list):
            for cc in cc_list:
                r = results[name_by_cc[cc]].get("rank")
                if r is not None:
                    latest_ranks[cc.upper()] = r
            break

    if not latest_ranks:
        return buf1, None

    sorted_items = sorted(latest_ranks.items(), key=lambda x: x[1])
    labels = [c for c, _ in sorted_items]   # "US", "GB", ...
    values = [r for _, r in sorted_items]
    colors = [COUNTRY_COLORS.get(c, "#888") for c in labels]

    fig2, ax2 = plt.subplots(figsize=(10, 5))
    fig2.patch.set_facecolor(BG)
    ax2.set_facecolor(BG)

    bars = ax2.barh(labels, values, color=colors, edgecolor="#2A3F5F", height=0.6)
    ax2.invert_yaxis()

    for bar, val in zip(bars, values):
        ax2.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                 f"#{val}", va="center", ha="left", color="white", fontsize=10, fontweight="bold")

    ax2.set_xlabel("Rank", color=TEXT, fontsize=10)
    ax2.set_title("Crimson Desert — Latest Snapshot", color="white", fontsize=13, pad=12)
    ax2.tick_params(colors=TEXT)
    for spine in ax2.spines.values():
        spine.set_edgecolor(GRID)
    ax2.grid(axis="x", color=GRID, linestyle="--", alpha=0.5)
    fig2.tight_layout()

    buf2 = io.BytesIO()
    fig2.savefig(buf2, format="png", dpi=130, bbox_inches="tight", facecolor=BG)
    buf2.seek(0)
    plt.close(fig2)

    return buf0, buf1, buf2

# ======================
# Discord 전송
# ======================
def send_discord_text(embed):
    if not DISCORD_WEBHOOK:
        return
    try:
        requests.post(DISCORD_WEBHOOK, json={"embeds": [embed]}, timeout=10)
    except Exception as e:
        print(f"  ❌ Discord 텍스트 전송 실패: {e}")

def send_discord_image(buf, filename, caption):
    if not DISCORD_WEBHOOK:
        return
    try:
        requests.post(
            DISCORD_WEBHOOK,
            data={"content": caption},
            files={"file": (filename, buf, "image/png")},
            timeout=30,
        )
    except Exception as e:
        print(f"  ❌ Discord 이미지 전송 실패: {e}")

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

        sleep_sec = COUNTRY_SLEEP.get(cc, DEFAULT_COUNTRY_SLEEP)
        print(f"  💤 다음 국가까지 {sleep_sec}초 대기...")
        time.sleep(sleep_sec)

    if not results:
        print("❌ 수집 실패")
        return

    # 히스토리 저장
    history = load_history()
    history.append({"timestamp": timestamp, "results": results})
    save_history(history)
    print(f"\n✅ 히스토리 저장 완료 (총 {len(history)}개)")

    # 가중평균 계산
    wavg = calc_weighted_avg(results)
    wavg_str = f"{wavg:.2f}" if wavg else "N/A"

    # Discord 텍스트 embed
    cc_by_name = {v: k for k, v in TARGET_COUNTRIES.items()}
    lines = []
    for name, data in results.items():
        rank = data.get("rank")
        rank_str = f"**#{rank}**" if rank else "순위권 밖"
        cc = cc_by_name.get(name, "")
        link = STORE_LINKS.get(cc, "")
        lines.append(f"[**{name}**]({link}): {rank_str}")

    embed = {
        "title": "🎮 Steam Top Seller — Crimson Desert",
        "description": (
            f"📅 {now_kst.strftime('%Y-%m-%d %H:%M KST')}\n"
            f"⚖️ 평균 순위: **#{wavg_str}**\n\n"
            + "\n".join(lines)
        ),
        "color": 0x1B2838,
    }
    send_discord_text(embed)

    # Discord 그래프
    print("\n📊 그래프 생성 중...")
    buf_wavg, buf_line, buf_bar = make_graphs(history)

    if buf_wavg:
        send_discord_image(buf_wavg, "weighted.png", "⚖️ 평균 순위 추이")
        print("  ✅ 가중평균 그래프 전송")
    if buf_line:
        send_discord_image(buf_line, "trend.png", "📈 전체 기간 순위 추이")
        print("  ✅ 꺾은선 그래프 전송")
    if buf_bar:
        send_discord_image(buf_bar, "snapshot.png", "📊 최신 스냅샷")
        print("  ✅ 막대 그래프 전송")

    print("✅ 완료!")

if __name__ == "__main__":
    main()
