# -*- coding: utf-8 -*-
"""
크림슨 데저트 스팀×PS 순위 + 일정(판매량 공지/게임 업데이트/펄어비스 일정) 결합 분석기
-------------------------------------------------------------
1) steam_topseller_history.json(국가별 스팀 Top Seller 순위, 30분 간격 스냅샷),
   bestseller_history.json(국가별 PS Store 순위, averages.combined 포함)을 읽어
   일자별 평균 순위(전체 추적 국가 평균, 스냅샷 평균의 일 평균)를 각각 계산
2) sell.html에 이미 반영된 판매량 공지 하드앵커, 게임 업데이트 일정(공식 발표 기반),
   주요 펄어비스 IR 일정을 결합
3) 결과를 crimson_desert_schedule_analysis.json 으로 저장
4) steam_rank_timeline.html (Chart.js 대시보드)로 시각화

사용법:
    python3 build_schedule_analysis.py

입력:
    steam_topseller_history.json   (레포 루트, 이미 존재)
    bestseller_history.json        (레포 루트, 이미 존재 — PS Store 순위)
출력:
    crimson_desert_schedule_analysis.json
    steam_rank_timeline.html
"""

import json
import os
import statistics
from collections import defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STEAM_INPUT_FILE = os.path.join(BASE_DIR, "steam_topseller_history.json")
PS_INPUT_FILE = os.path.join(BASE_DIR, "bestseller_history.json")
OUTPUT_JSON = os.path.join(BASE_DIR, "crimson_desert_schedule_analysis.json")
OUTPUT_HTML = os.path.join(BASE_DIR, "steam_rank_timeline.html")

LAUNCH_DATE = datetime.fromisoformat("2026-03-19T00:00:00+09:00")


# ─────────────────────────────────────────────
# 1a. 스팀 순위 → 일자별 평균 순위
# ─────────────────────────────────────────────
def load_daily_average_rank_steam(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    history = data["history"]

    # 스냅샷별 평균 순위 (해당 스냅샷에서 추적된 국가들의 null 제외 평균)
    daily_snapshot_avgs = defaultdict(list)
    daily_country_counts = defaultdict(list)

    for entry in history:
        ts_raw = entry.get("timestamp")
        if not ts_raw:
            continue
        try:
            ts = datetime.fromisoformat(ts_raw)
        except ValueError:
            continue

        ranks = [
            v.get("rank")
            for v in entry.get("results", {}).values()
            if isinstance(v, dict) and v.get("rank") is not None
        ]
        if not ranks:
            continue

        snapshot_avg = statistics.mean(ranks)
        date_key = ts.date().isoformat()
        daily_snapshot_avgs[date_key].append(snapshot_avg)
        daily_country_counts[date_key].append(len(ranks))

    return _aggregate_daily(daily_snapshot_avgs, daily_country_counts)


# ─────────────────────────────────────────────
# 1b. PS Store 순위 → 일자별 평균 순위
#     (bestseller_history.json은 스냅샷마다 averages.combined를
#      이미 계산해서 들고 있으므로 그대로 사용)
# ─────────────────────────────────────────────
def load_daily_average_rank_ps(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    history = data["history"]

    daily_snapshot_avgs = defaultdict(list)
    daily_country_counts = defaultdict(list)

    for entry in history:
        ts_raw = entry.get("timestamp")
        if not ts_raw:
            continue
        try:
            ts = datetime.fromisoformat(ts_raw)
        except ValueError:
            continue

        combined = entry.get("averages", {}).get("combined")
        raw_results = entry.get("raw_results", {})
        country_count = sum(1 for v in raw_results.values() if v is not None)

        if combined is None:
            # averages.combined가 없는 옛날 스냅샷 대비 폴백: 직접 계산
            ranks = [v for v in raw_results.values() if isinstance(v, (int, float))]
            if not ranks:
                continue
            combined = statistics.mean(ranks)

        date_key = ts.date().isoformat()
        daily_snapshot_avgs[date_key].append(combined)
        daily_country_counts[date_key].append(country_count)

    return _aggregate_daily(daily_snapshot_avgs, daily_country_counts)


def _aggregate_daily(daily_snapshot_avgs, daily_country_counts):
    daily_average_rank = []
    for date_key in sorted(daily_snapshot_avgs.keys()):
        snap_avgs = daily_snapshot_avgs[date_key]
        counts = daily_country_counts[date_key]
        launch_dt = datetime.fromisoformat(date_key + "T00:00:00+09:00")
        day_num = (launch_dt - LAUNCH_DATE).days
        daily_average_rank.append({
            "date": date_key,
            "day": day_num,
            "avg_rank": round(statistics.mean(snap_avgs), 2),
            "best_snapshot_rank": round(min(snap_avgs), 2),
            "worst_snapshot_rank": round(max(snap_avgs), 2),
            "avg_countries_tracked": round(statistics.mean(counts), 1),
            "snapshots": len(snap_avgs),
        })
    return daily_average_rank


# ─────────────────────────────────────────────
# 2. 판매량 공지 일정 (sell.html HARD_ANCHORS 그대로)
# ─────────────────────────────────────────────
SALES_MILESTONES = [
    {"date": "2026-03-20T23:46:00+09:00", "day": 0,  "units": 2_000_000,  "label": "200만장 판매 공지"},
    {"date": "2026-03-24T19:19:00+09:00", "day": 4,  "units": 3_000_000,  "label": "300만장 판매 공지"},
    {"date": "2026-04-01T11:00:00+09:00", "day": 12, "units": 4_000_000,  "label": "400만장 판매 공지"},
    {"date": "2026-04-15T12:00:00+09:00", "day": 26, "units": 5_000_000,  "label": "500만장 판매 공지"},
    {"date": "2026-06-11T12:00:00+09:00", "day": 83, "units": 6_000_000,  "label": "600만장 판매 공지 (공식 보도자료)"},
]

# ─────────────────────────────────────────────
# 3. 게임 업데이트 일정 (공식 발표/패치 기반, 출시 이후)
# ─────────────────────────────────────────────
GAME_UPDATES = [
    {"date": "2026-03-19", "label": "출시 & 데이원 패치 (1.000.142)", "type": "launch"},
    {"date": "2026-04-24", "label": "난이도 설정 · 컨트롤 프리셋 · 인벤토리 탭 패치", "type": "patch"},
    {"date": "2026-06-02", "label": "6~9월 로드맵 Dev Update 공개 (Re-Blockade, 크로스세이브, DLC 개발 확인)", "type": "roadmap"},
    {"date": "2026-06-19", "label": "업데이트 1.000.352 (v1.12.0) — 하우징 신규 아이템", "type": "patch"},
    {"date": "2026-07-15", "label": "7월 업데이트 — 장비 밸런스, 오옹카/다미안 확장", "type": "patch"},
    {"date": "2026-08-12", "label": "출시 후 17개 메이저 업데이트 회고 인포그래픽 공개 + DLC Q4 출시 예정 확인", "type": "retrospective"},
    {"date": "2026-10-15", "label": "DLC 'Crimson Desert Enhanced: Charting the Unknown' 프리오더 오픈", "type": "dlc"},
]

# ─────────────────────────────────────────────
# 4. 주요 펄어비스 일정 (IR/기업 이벤트)
# ─────────────────────────────────────────────
PEARL_ABYSS_EVENTS = [
    {"date": "2026-05-07", "label": "2026년 1분기 실적 발표 (영업이익 +2,585% YoY, 사상 최대)", "type": "earnings"},
    {"date": "2026-06-11", "label": "붉은사막 600만장 판매 공식 보도자료", "type": "milestone"},
    {"date": "2026-06-30", "label": "자사주 50%(1,403,945주) 소각", "type": "shareholder_return"},
    {"date": "2026-08-11", "label": "2026년 2분기 실적 발표 (가이던스 하회, 연간 가이던스 하향)", "type": "earnings"},
    {"date": "2026-08-12", "label": "붉은사막 DLC Q4 출시 예정 공식 확인", "type": "dlc_guidance"},
    {"date": "2026-12-31", "label": "자사주 매입 프로그램(1,000억원) 종료 예정", "type": "shareholder_return"},
]


def build():
    daily_avg_steam = load_daily_average_rank_steam(STEAM_INPUT_FILE)
    daily_avg_ps = load_daily_average_rank_ps(PS_INPUT_FILE)

    result = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "source_files": {
            "steam": "steam_topseller_history.json",
            "ps": "bestseller_history.json",
        },
        "launch_date": LAUNCH_DATE.isoformat(),
        "daily_average_rank_steam": daily_avg_steam,
        "daily_average_rank_ps": daily_avg_ps,
        "sales_milestones": SALES_MILESTONES,
        "game_updates": GAME_UPDATES,
        "pearl_abyss_events": PEARL_ABYSS_EVENTS,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] {OUTPUT_JSON} 저장 완료 — Steam 일자 수: {len(daily_avg_steam)}, PS 일자 수: {len(daily_avg_ps)}")
    return result


if __name__ == "__main__":
    build()
