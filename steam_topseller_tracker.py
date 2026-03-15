#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Steam 국가별 Top Seller 순위 추적기 (44개국)
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

HISTORY_FILE  = "steam_topseller_history.json"
BASELINE_FILE = "steam_topseller_baseline.json"  # 마지막 알림 발송 시점 기준값
WORKFLOW_FILE = ".github/workflows/steam_topseller_tracker.yml"  # 스케줄 소스
KST = timezone(timedelta(hours=9))


# ======================
# 스케줄 파싱 (yml → JSON 메타 → 대시보드)
# ======================

def parse_cron_to_kst_slots(cron_expr: str) -> list:
    """
    'MIN HOUR ...' cron 표현식에서 UTC hour 목록을 추출 → KST(+9) 변환.
    분(MIN) 필드에 복수 값이 있으면(예: '0,30 * * * *') 슬롯을 분 단위로 반환.
    반환 형식: {"type": "interval", "interval_min": 30}
              또는 {"type": "fixed", "slots_kst": [6, 18]}
    """
    parts = cron_expr.strip().split()
    if len(parts) < 2:
        return {"type": "unknown"}

    min_field  = parts[0]
    hour_field = parts[1]

    # 매 N분 패턴: */N  or  0,30  or  * (모든 분)
    if hour_field == '*':
        if min_field == '*':
            return {"type": "interval", "interval_min": 1}
        if min_field.startswith('*/'):
            interval = int(min_field[2:])
            return {"type": "interval", "interval_min": interval}
        # 0,30  → 간격 계산
        mins = sorted(int(m) for m in min_field.split(',') if m.strip().isdigit())
        if len(mins) >= 2:
            interval = mins[1] - mins[0]
            return {"type": "interval", "interval_min": interval}
        return {"type": "interval", "interval_min": 60}

    # 고정 시각 패턴: '0 9,21 * * *'
    utc_hours = []
    for token in hour_field.split(','):
        token = token.strip()
        if token.isdigit():
            utc_hours.append(int(token))
    kst_hours = sorted(set((h + 9) % 24 for h in utc_hours))
    return {"type": "fixed", "slots_kst": kst_hours}


def read_schedule_meta() -> dict:
    """
    workflow yml에서 cron 표현식을 읽어 스케줄 메타 dict 반환.
    읽기 실패 시 None 반환 (기존 JSON의 schedule 값 유지).
    """
    import re as _re
    if not os.path.exists(WORKFLOW_FILE):
        print(f"ℹ️  {WORKFLOW_FILE} 없음 → 스케줄 메타 업데이트 스킵")
        return None
    try:
        with open(WORKFLOW_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        m = _re.search(r"cron:\s*['\"]([^'\"]+)['\"]", content)
        if not m:
            print("ℹ️  cron 표현식 파싱 실패 → 스케줄 메타 업데이트 스킵")
            return None
        cron_expr = m.group(1)
        parsed = parse_cron_to_kst_slots(cron_expr)
        meta = {"cron": cron_expr, **parsed}
        print(f"✅  스케줄 파싱: {cron_expr!r} → {parsed}")
        return meta
    except Exception as e:
        print(f"⚠️  스케줄 파싱 오류: {e}")
        return None

TARGET_COUNTRIES = {
    # 기존 (미주/유럽/아시아 핵심)
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
    "au": "호주",
    "es": "스페인",
    "it": "이탈리아",
    "pl": "폴란드",
    "tr": "터키",
    "mx": "멕시코",
    # 유럽 추가
    "nl": "네덜란드",
    "se": "스웨덴",
    "no": "노르웨이",
    "dk": "덴마크",
    "fi": "핀란드",
    "pt": "포르투갈",
    "at": "오스트리아",
    "ch": "스위스",
    "cz": "체코",
    "hu": "헝가리",
    "ro": "루마니아",
    "ar": "아르헨티나",
    "cl": "칠레",
    "co": "콜롬비아",
    "sg": "싱가포르",
    "za": "남아공",
    # 공식 차트 지원국 추가
    "be": "벨기에",
    "hk": "홍콩",
    "nz": "뉴질랜드",
    "tw": "대만",
    # 동남아 / 남아시아
    "th": "태국",
    "id": "인도네시아",
    "my": "말레이시아",
    "ph": "필리핀",
    "vn": "베트남",
    "in": "인도",
    # 동유럽
    "ua": "우크라이나",
    # 남미
    "pe": "페루",
}

COUNTRY_COLORS = {
    # 기존
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
    "AU": "#F0E68C",
    "ES": "#FF6B6B",
    "IT": "#4ECDC4",
    "PL": "#A8E6CF",
    "TR": "#FF8B94",
    "MX": "#88D8B0",
    # 신규
    "NL": "#FF9933",
    "SE": "#006AA7",
    "NO": "#EF2B2D",
    "DK": "#C60C30",
    "FI": "#003580",
    "PT": "#006600",
    "AT": "#ED2939",
    "CH": "#FF0000",
    "CZ": "#D7141A",
    "HU": "#CE2939",
    "RO": "#002B7F",
    "AR": "#74ACDF",
    "CL": "#D52B1E",
    "CO": "#FCD116",
    "SG": "#EF3340",
    "ZA": "#007A4D",
    "BE": "#FAE042",
    "HK": "#DE2910",
    "NZ": "#00247D",
    "TW": "#FE0000",
    "TH": "#A51931",
    "ID": "#CE1126",
    "MY": "#CC0001",
    "PH": "#0038A8",
    "VN": "#DA251D",
    "IN": "#FF9933",
    "UA": "#005BBB",
    "PE": "#D91023",
}

# Steam 시장 가중치 (index.html의 STS_W 와 동기화)
STEAM_WEIGHTS = {
    # 기존
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
    "au":  0.9,
    "es":  0.7,
    "it":  0.6,
    "pl":  0.7,
    "tr":  0.7,
    "mx":  0.5,
    # 신규
    "nl":  0.8,
    "se":  0.7,
    "no":  0.5,
    "dk":  0.5,
    "fi":  0.4,
    "pt":  0.5,
    "at":  0.6,
    "ch":  0.7,
    "cz":  0.4,
    "hu":  0.3,
    "ro":  0.3,
    "ar":  0.6,
    "cl":  0.4,
    "co":  0.3,
    "sg":  0.5,
    "za":  0.3,
    "be":  0.8,
    "hk":  0.7,
    "nz":  0.4,
    "tw":  0.8,
    "th":  0.8,
    "id":  0.7,
    "my":  0.5,
    "ph":  0.5,
    "vn":  0.5,
    "in":  0.6,
    "ua":  0.8,
    "pe":  0.4,
}

def calc_weighted_avg(results):
    """추적국 단순평균 순위 계산 (순위 없으면 해당 국가 제외)"""
    ranks = [data.get("rank") for data in results.values() if data.get("rank") is not None]
    return round(sum(ranks) / len(ranks), 1) if ranks else None


RETRY_DELAYS = {
    "cn": [10, 30, 60],
    "ru": [10, 30, 60],
    "ar": [5, 15, 30],
    "co": [5, 15, 30],
    "vn": [5, 15, 30],
    "ph": [5, 15, 30],
    "in": [5, 15, 30],
}
DEFAULT_RETRY_DELAYS = [5, 15, 30]

COUNTRY_SLEEP = {
    "cn": 5,
    "ru": 5,
    "ar": 3,
    "vn": 3,
    "ph": 3,
    "in": 3,
    "id": 3,
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
            m = re.search(r'/steam/apps/(\d+)/', logo)
            appid = m.group(1) if m else ""
            if not appid or appid in seen:
                continue
            seen.add(appid)
            real_rank += 1
            if appid in STEAM_APP_IDS:
                rank = real_rank
                found = True

        if found:
            break
        time.sleep(1.0)

    if real_rank == 0:
        print(f"  ⚠️ {cc} 데이터 없음")
        return None

    print(f"  ✅ {cc}: 총 {real_rank}개 파싱, Crimson Desert {'#' + str(rank) if rank else '순위권 밖'}")
    return {"rank": rank}

# ======================
# 히스토리 관리
# ======================
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 신규 포맷: {"schedule": ..., "history": [...]}
        if isinstance(data, dict) and "history" in data:
            return data["history"]
        # 구버전 포맷: 리스트 그대로
        if isinstance(data, list):
            return data
        return []
    except:
        return []

def save_history(history, schedule_meta=None):
    """
    history 리스트를 저장합니다.
    schedule_meta가 주어지면 {"schedule": ..., "history": [...]} 형식으로,
    없으면 기존 schedule 값을 유지합니다.
    대시보드(index.html)는 schedule 키를 읽어 스케줄 표시에 활용합니다.
    """
    # 기존 파일에서 schedule 값 유지
    existing_schedule = None
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if isinstance(existing, dict):
                existing_schedule = existing.get("schedule")
        except Exception:
            pass

    final_schedule = schedule_meta if schedule_meta is not None else existing_schedule

    payload = {"history": history}
    if final_schedule:
        payload["schedule"] = final_schedule

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

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

    # 데이터 파싱 (추적국 전체, 국가 수 변경에도 기존 데이터 보존)
    timestamps = []
    cc_ranks = {cc: [] for cc in cc_list}
    wavg_list = []

    for entry in history:
        try:
            ts = datetime.fromisoformat(entry["timestamp"])
        except:
            continue
        results = entry.get("results", {})
        # 최소 1개국 이상 있으면 포함 (국가 수 변경에도 기존 데이터 보존)
        if not results:
            continue
        timestamps.append(ts)
        for cc in cc_list:
            name = name_by_cc[cc]
            rank = results.get(name, {}).get("rank") if name in results else None
            cc_ranks[cc].append(rank)
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

        # 시작 / 최고(순위 숫자 가장 작음) / 최저(순위 숫자 가장 큼) / 최신 4개 포인트만 라벨
        best_idx  = valid_w0.index(min(valid_w0))   # 숫자 작을수록 높은 순위
        worst_idx = valid_w0.index(max(valid_w0))
        special = {0, best_idx, worst_idx, len(valid_w0) - 1}

        for idx in sorted(special):
            t, w = valid_ts0[idx], valid_w0[idx]
            ax0.annotate(f"{w:.1f}",
                         xy=(t, w), xytext=(0, 10), textcoords="offset points",
                         fontsize=9, color="#FFD700", ha="center", fontweight="bold")

        # 최신값 강조 가로선
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
    fig1, ax1 = plt.subplots(figsize=(14, max(7, len(cc_list) * 0.18 + 5)))
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
    ax1.grid(axis="y", color=GRID, linestyle="--", alpha=0.5)

    # 레전드를 그래프 위(제목 아래)에 가로로 배치
    handles, labels = ax1.get_legend_handles_labels()
    ncol = min(len(labels), 16)  # 최대 16열로 2줄까지 허용
    fig1.legend(handles, labels,
                loc="upper center", bbox_to_anchor=(0.5, 0.97),
                ncol=ncol, fontsize=8,
                framealpha=0.25, labelcolor="white", facecolor="#2A3F5F",
                edgecolor="none", handlelength=1.5, columnspacing=1.0)

    fig1.tight_layout()
    fig1.subplots_adjust(top=0.78)  # 다국 legend 2줄 공간 확보

    buf1 = io.BytesIO()
    fig1.savefig(buf1, format="png", dpi=130, bbox_inches="tight", facecolor=BG)
    buf1.seek(0)
    plt.close(fig1)

    # 국기 색상 표현 (국가별 대표 2색: [배경, 텍스트색])
    FLAG_COLORS = {
        # 기존
        "US": ("#3C3B6E", "#FFFFFF"),
        "GB": ("#C8102E", "#FFFFFF"),
        "DE": ("#000000", "#FFD700"),
        "FR": ("#0055A4", "#FFFFFF"),
        "CA": ("#FF0000", "#FFFFFF"),
        "BR": ("#009C3B", "#FFD700"),
        "JP": ("#BC002D", "#FFFFFF"),
        "KR": ("#003478", "#FFFFFF"),
        "CN": ("#DE2910", "#FFD700"),
        "RU": ("#0039A6", "#FFFFFF"),
        "AU": ("#00008B", "#FFFFFF"),
        "ES": ("#AA151B", "#F1BF00"),
        "IT": ("#009246", "#FFFFFF"),
        "PL": ("#DC143C", "#FFFFFF"),
        "TR": ("#E30A17", "#FFFFFF"),
        "MX": ("#006847", "#FFFFFF"),
        # 신규
        "NL": ("#AE1C28", "#FFFFFF"),
        "SE": ("#006AA7", "#FECC02"),
        "NO": ("#EF2B2D", "#FFFFFF"),
        "DK": ("#C60C30", "#FFFFFF"),
        "FI": ("#003580", "#FFFFFF"),
        "PT": ("#006600", "#FFFFFF"),
        "AT": ("#ED2939", "#FFFFFF"),
        "CH": ("#FF0000", "#FFFFFF"),
        "CZ": ("#D7141A", "#FFFFFF"),
        "HU": ("#CE2939", "#FFFFFF"),
        "RO": ("#002B7F", "#FFD700"),
        "AR": ("#74ACDF", "#FFFFFF"),
        "CL": ("#D52B1E", "#FFFFFF"),
        "CO": ("#003087", "#FFD116"),
        "SG": ("#EF3340", "#FFFFFF"),
        "ZA": ("#007A4D", "#FFFFFF"),
        "BE": ("#FAE042", "#000000"),
        "HK": ("#DE2910", "#FFD700"),
        "NZ": ("#00247D", "#FFFFFF"),
        "TW": ("#FE0000", "#FFFFFF"),
        "TH": ("#A51931", "#FFD700"),
        "ID": ("#CE1126", "#FFFFFF"),
        "MY": ("#CC0001", "#FFD100"),
        "PH": ("#0038A8", "#FFFFFF"),
        "VN": ("#DA251D", "#FFD700"),
        "IN": ("#FF9933", "#FFFFFF"),
        "UA": ("#005BBB", "#FFD700"),
        "PE": ("#D91023", "#FFFFFF"),
    }

    # ── 2. 막대 그래프 (최신 스냅샷) ─────────────────────────
    latest_ranks = {}
    prev_ranks_bar = {}
    for entry in reversed(history):
        results = entry.get("results", {})
        if results:
            for cc in cc_list:
                name = name_by_cc[cc]
                if name in results and results[name].get("rank") is not None:
                    latest_ranks[cc.upper()] = results[name]["rank"]
            if latest_ranks:
                break

    # 이전 스냅샷 순위
    found_latest = False
    for entry in reversed(history):
        results_e = entry.get("results", {})
        if not results_e:
            continue
        if not found_latest:
            found_latest = True
            continue
        for cc in cc_list:
            name = name_by_cc[cc]
            if name in results_e and results_e[name].get("rank") is not None:
                prev_ranks_bar[cc.upper()] = results_e[name]["rank"]
        break

    # 전체 히스토리에서 국가별 최고/최저/평균
    all_ranks_by_cc = {cc.upper(): [] for cc in cc_list}
    for entry in history:
        results_e = entry.get("results", {})
        for cc in cc_list:
            name = name_by_cc[cc]
            r = results_e.get(name, {}).get("rank") if name in results_e else None
            if r is not None:
                all_ranks_by_cc[cc.upper()].append(r)

    if not latest_ranks:
        return buf1, None

    sorted_items = sorted(latest_ranks.items(), key=lambda x: x[1])
    bar_ccs = [c for c, _ in sorted_items]
    values  = [r for _, r in sorted_items]
    colors  = [COUNTRY_COLORS.get(c, "#888") for c in bar_ccs]

    fig2, ax2 = plt.subplots(figsize=(13, max(6, len(bar_ccs) * 0.6 + 1.5)))
    fig2.patch.set_facecolor(BG)
    ax2.set_facecolor(BG)

    bars = ax2.barh(range(len(bar_ccs)), values, color=colors,
                    edgecolor="#2A3F5F", height=0.6)
    ax2.invert_yaxis()
    ax2.set_yticks(range(len(bar_ccs)))
    ax2.set_yticklabels([""] * len(bar_ccs))

    max_val = max(values) if values else 10
    ax2.set_xlim(0, max_val * 1.6)

    for i, (bar, val, cc) in enumerate(zip(bars, values, bar_ccs)):
        y_mid = bar.get_y() + bar.get_height() / 2

        # ── 국가 컬러 박스 ──
        fc, tc = FLAG_COLORS.get(cc, ("#555", "#FFF"))
        ax2.text(-max_val * 0.02, y_mid, f" {cc} ",
                 va="center", ha="right", fontsize=11, fontweight="bold",
                 color=tc,
                 bbox=dict(boxstyle="round,pad=0.3", facecolor=fc,
                           edgecolor="white", linewidth=0.8))

        x_cur = bar.get_width() + max_val * 0.02

        # ── 현재 순위 ──
        ax2.text(x_cur, y_mid, f"#{val}",
                 va="center", ha="left", color="white",
                 fontsize=13, fontweight="bold")

        # ── 변동 화살표 ──
        prev_r = prev_ranks_bar.get(cc)
        if prev_r is not None and prev_r != val:
            diff = prev_r - val
            arrow = f"▲{diff}" if diff > 0 else f"▼{abs(diff)}"
            diff_col = "#2ECC71" if diff > 0 else "#E74C3C"
            ax2.text(x_cur + max_val * 0.07, y_mid, arrow,
                     va="center", ha="left", color=diff_col,
                     fontsize=12, fontweight="bold")

        # ── 최고 순위 ──
        ranks_hist = all_ranks_by_cc.get(cc, [])
        if ranks_hist:
            best_r = min(ranks_hist)
            ax2.text(x_cur + max_val * 0.15, y_mid,
                     f"(best:#{best_r})",
                     va="center", ha="left", color="#A0AEC0", fontsize=12)

    ax2.set_xlabel("Rank", color=TEXT, fontsize=10)
    ax2.set_title("Crimson Desert — Latest Snapshot", color="white", fontsize=13, pad=12)
    ax2.tick_params(colors=TEXT)
    ax2.set_xlim(left=-max_val * 0.15)   # 왼쪽 CC박스 공간
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
def load_baseline():
    """마지막 Discord 알림 발송 시점의 wavg 로드"""
    if not os.path.exists(BASELINE_FILE):
        return None
    try:
        with open(BASELINE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("wavg")
    except:
        return None

def save_baseline(wavg):
    """Discord 알림 발송 시점의 wavg 저장"""
    with open(BASELINE_FILE, "w", encoding="utf-8") as f:
        json.dump({"wavg": wavg, "timestamp": datetime.now(KST).isoformat()}, f)

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
    print("🎮 Steam Top Seller 순위 추적기 (44개국)")
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

    # 히스토리 저장 (이전 레코드 먼저 가져오기)
    history = load_history()
    # 이전 레코드 추출 — 국가 수 무관하게 가장 최근 유효 레코드 사용
    prev_results = None
    for entry in reversed(history):
        if entry.get("results"):
            prev_results = entry["results"]
            break

    schedule_meta = read_schedule_meta()  # yml에서 cron 파싱
    history.append({"timestamp": timestamp, "results": results})
    save_history(history, schedule_meta)
    print(f"\n✅ 히스토리 저장 완료 (총 {len(history)}개)")

    # 가중평균 계산 + 변동량
    wavg = calc_weighted_avg(results)
    wavg_str = f"{wavg:.1f}" if wavg else "N/A"
    wavg_diff = ""
    prev_wavg = None
    if wavg and prev_results:
        prev_wavg = calc_weighted_avg(prev_results)
        if prev_wavg:
            diff = prev_wavg - wavg  # 순위 낮아지면(숫자 커지면) 음수
            if diff > 0:
                wavg_diff = f" (▲{diff:.1f})"
            elif diff < 0:
                wavg_diff = f" (▼{abs(diff):.1f})"

    # 평균 순위 변동량 계산 (baseline 기준 1.0 이상 변동 시에만 전송)
    baseline_wavg = load_baseline()
    if wavg is not None and baseline_wavg is not None:
        diff_from_baseline = abs(wavg - baseline_wavg)
        avg_changed = diff_from_baseline >= 1.0
        if not avg_changed:
            print(f"ℹ️  기준점 대비 변화 미미 (기준: {baseline_wavg:.1f} → 현재: {wavg_str}위, 차이: {diff_from_baseline:.2f}) → 디스코드 알림 생략")
            print("✅ 완료!")
            return
        print(f"🔔 기준점 대비 변화 감지 (기준: {baseline_wavg:.1f} → 현재: {wavg_str}위, 차이: {diff_from_baseline:.2f}) → 알림 발송")
    else:
        avg_changed = wavg is not None  # 첫 실행 시 baseline 없으면 무조건 전송
        if not avg_changed:
            print("ℹ️  평균 순위 없음 → 디스코드 알림 생략")
            print("✅ 완료!")
            return

    # Discord 텍스트 embed
    cc_by_name = {v: k for k, v in TARGET_COUNTRIES.items()}

    # 순위권 진입 국가만 별도 추출 (통계용)
    ranked_results = {name: data for name, data in results.items() if data.get("rank")}
    total_tracked  = len(results)
    found_count    = len(ranked_results)

    # 순위권 단순평균 / 1위 / 최하위 국가
    rank_vals = [(name, data["rank"]) for name, data in ranked_results.items()]
    simple_avg = round(sum(r for _, r in rank_vals) / len(rank_vals), 1) if rank_vals else None
    best_entry  = min(rank_vals, key=lambda x: x[1]) if rank_vals else None
    worst_entry = max(rank_vals, key=lambda x: x[1]) if rank_vals else None

    # 요약 헤더 라인
    summary_lines = []
    if simple_avg:
        summary_lines.append(f"📊 순위권 평균: **#{simple_avg}** ({found_count}/{total_tracked}개국 진입)")
    if best_entry:
        summary_lines.append(f"🥇 최고순위: **{best_entry[0]} #{best_entry[1]}**")
    if worst_entry:
        summary_lines.append(f"🔻 최하위: **{worst_entry[0]} #{worst_entry[1]}**")

    # 국가 목록 (시장 가중치 내림차순, 순위권/미진입 구분)
    lines = []
    sorted_names = sorted(results.keys(),
                          key=lambda n: STEAM_WEIGHTS.get(cc_by_name.get(n, ""), 0),
                          reverse=True)
    for name in sorted_names:
        data = results[name]
        rank = data.get("rank")
        rank_str = f"**#{rank}**" if rank else "~~미진입~~"
        diff_str = ""
        if rank and prev_results and prev_results.get(name):
            prev_rank = prev_results[name].get("rank")
            if prev_rank:
                diff = prev_rank - rank
                if diff > 0:
                    diff_str = f" **(▲{diff})**"
                elif diff < 0:
                    diff_str = f" **(▼{abs(diff)})**"
        cc = cc_by_name.get(name, "")
        link = STORE_LINKS.get(cc, "")
        lines.append(f"[**{name}**]({link}): {rank_str}{diff_str}")

    embed = {
        "title": "🎮 Steam Top Seller — Crimson Desert",
        "description": (
            f"📅 {now_kst.strftime('%Y-%m-%d %H:%M KST')}\n"
            f"⚖️ 가중 평균: **#{wavg_str}**{wavg_diff}\n"
            + "\n".join(summary_lines)
            + "\n\n"
            + "\n".join(lines)
        ),
        "color": 0x1B2838,
    }

    # 4096자 초과 시 국가 목록을 분할 전송
    LIMIT = 3800
    header = (
        f"📅 {now_kst.strftime('%Y-%m-%d %H:%M KST')}\n"
        f"⚖️ 가중 평균: **#{wavg_str}**{wavg_diff}\n"
        + "\n".join(summary_lines)
        + "\n\n"
    )
    body = "\n".join(lines)
    if len(header) + len(body) > LIMIT:
        # 헤더 embed 먼저
        send_discord_text({
            "title": "🎮 Steam Top Seller — Crimson Desert",
            "description": header.rstrip(),
            "color": 0x1B2838,
        })
        time.sleep(1)
        # 국가 목록 청크 분할
        chunks, cur, cur_len = [], [], 0
        for line in lines:
            if cur_len + len(line) + 1 > LIMIT and cur:
                chunks.append(cur); cur = [line]; cur_len = len(line)
            else:
                cur.append(line); cur_len += len(line) + 1
        if cur:
            chunks.append(cur)
        for i, chunk in enumerate(chunks):
            part = f" ({i+1}/{len(chunks)})" if len(chunks) > 1 else ""
            send_discord_text({
                "title": f"🌍 국가별 현황{part}",
                "description": "\n".join(chunk),
                "color": 0x1B2838,
            })
            time.sleep(1)
    else:
        send_discord_text(embed)

    # Discord 그래프
    print("\n📊 그래프 생성 중...")
    buf_wavg, buf_line, buf_bar = make_graphs(history)

    if buf_wavg:
        send_discord_image(buf_wavg, "weighted.png", "⚖️ 평균 순위 추이")
        print("  ✅ 평균 순위 그래프 전송")
    if buf_line:
        send_discord_image(buf_line, "trend.png", "📈 전체 기간 순위 추이")
        print("  ✅ 꺾은선 그래프 전송")
    if buf_bar:
        send_discord_image(buf_bar, "snapshot.png", "📊 최신 스냅샷")
        print("  ✅ 막대 그래프 전송")

    # 알림 발송 완료 → baseline 갱신
    if wavg is not None:
        save_baseline(wavg)
        print(f"✅ baseline 갱신: {wavg:.1f}")

    print("✅ 완료!")

if __name__ == "__main__":
    main()
