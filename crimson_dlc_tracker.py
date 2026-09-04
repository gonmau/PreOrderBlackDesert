#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import re
import os
import json
import requests
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# =============================================================================
# 설정
# =============================================================================

# 지역별 분류
REGIONS = {
    "Europe & Middle East": [
        "영국", "독일", "프랑스", "스페인", "이탈리아", "네덜란드",
        "폴란드", "스위스", "스웨덴", "노르웨이", "덴마크", "핀란드",
        "포르투갈", "그리스", "체코", "헝가리", "루마니아", "슬로바키아",
        "슬로베니아", "우크라이나", "사우디아라비아", "아랍에미리트", "남아공",
        "터키", "벨기에", "오스트리아", "이스라엘", "크로아티아", "불가리아",
        "키프로스", "아이슬란드", "아일랜드", "쿠웨이트", "레바논",
        "룩셈부르크", "몰타", "오만", "카타르", "바레인"
    ],
    "Americas": [
        "미국", "캐나다", "브라질", "멕시코", "아르헨티나", "칠레",
        "콜롬비아", "페루", "우루과이", "볼리비아", "과테말라", "온두라스",
        "코스타리카", "에콰도르", "엘살바도르", "니카라과", "파나마", "파라과이"
    ],
    "Asia & Oceania": [
        "일본", "한국", "중국", "호주", "인도", "태국", "싱가포르",
        "말레이시아", "인도네시아", "필리핀", "베트남", "홍콩", "대만",
        "뉴질랜드"
    ]
}

MARKET_WEIGHTS = {
    # Americas
    "미국": 30.0, "캐나다": 4.5, "브라질": 2.5, "멕시코": 2.0,
    "아르헨티나": 0.9, "칠레": 0.8, "콜롬비아": 0.7, "페루": 0.4,
    "우루과이": 0.3, "볼리비아": 0.2, "과테말라": 0.2, "온두라스": 0.2,
    "코스타리카": 0.2, "에콰도르": 0.3, "엘살바도르": 0.1, "니카라과": 0.1,
    "파나마": 0.2, "파라과이": 0.2,
    # Europe & Middle East
    "영국": 8.5, "독일": 6.5, "프랑스": 6.0, "스페인": 4.0, "이탈리아": 3.5,
    "네덜란드": 1.8, "사우디아라비아": 1.5, "아랍에미리트": 1.2,
    "폴란드": 1.2, "스위스": 1.0, "스웨덴": 1.0, "덴마크": 0.9, "포르투갈": 0.8,
    "핀란드": 0.8, "노르웨이": 0.8, "남아공": 0.8, "체코": 0.7, "루마니아": 0.6,
    "그리스": 0.5, "헝가리": 0.5, "우크라이나": 0.5, "슬로바키아": 0.3,
    "슬로베니아": 0.3, "터키": 0.8, "벨기에": 1.2, "오스트리아": 1.0,
    "이스라엘": 0.8, "크로아티아": 0.2, "불가리아": 0.3, "키프로스": 0.1,
    "아이슬란드": 0.1, "아일랜드": 0.8, "쿠웨이트": 0.3, "레바논": 0.1,
    "룩셈부르크": 0.1, "몰타": 0.1, "오만": 0.2, "카타르": 0.3, "바레인": 0.2,
    # Asia & Oceania
    "일본": 8.0, "호주": 3.0, "한국": 2.8, "인도": 2.0, "대만": 1.0,
    "싱가포르": 0.8, "태국": 0.9, "홍콩": 0.9, "인도네시아": 0.8,
    "말레이시아": 0.7, "베트남": 0.7, "필리핀": 0.6, "뉴질랜드": 0.6,
    "중국": 0.2
}

URLS = {
    # Americas
    "미국": "https://store.playstation.com/en-us/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "캐나다": "https://store.playstation.com/en-ca/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "브라질": "https://store.playstation.com/pt-br/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "멕시코": "https://store.playstation.com/es-mx/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "아르헨티나": "https://store.playstation.com/es-ar/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "칠레": "https://store.playstation.com/es-cl/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "콜롬비아": "https://store.playstation.com/es-co/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "페루": "https://store.playstation.com/es-pe/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "우루과이": "https://store.playstation.com/es-uy/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "볼리비아": "https://store.playstation.com/es-bo/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "과테말라": "https://store.playstation.com/es-gt/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "온두라스": "https://store.playstation.com/es-hn/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "코스타리카": "https://store.playstation.com/es-cr/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "에콰도르": "https://store.playstation.com/es-ec/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "엘살바도르": "https://store.playstation.com/es-sv/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "니카라과": "https://store.playstation.com/es-ni/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "파나마": "https://store.playstation.com/es-pa/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "파라과이": "https://store.playstation.com/es-py/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    # Europe & Middle East
    "영국": "https://store.playstation.com/en-gb/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "독일": "https://store.playstation.com/de-de/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "프랑스": "https://store.playstation.com/fr-fr/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "스페인": "https://store.playstation.com/es-es/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "이탈리아": "https://store.playstation.com/it-it/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "네덜란드": "https://store.playstation.com/nl-nl/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "폴란드": "https://store.playstation.com/pl-pl/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "스위스": "https://store.playstation.com/de-ch/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "스웨덴": "https://store.playstation.com/sv-se/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "노르웨이": "https://store.playstation.com/no-no/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "덴마크": "https://store.playstation.com/da-dk/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "핀란드": "https://store.playstation.com/fi-fi/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "포르투갈": "https://store.playstation.com/pt-pt/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "그리스": "https://store.playstation.com/en-gr/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "체코": "https://store.playstation.com/en-cz/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "헝가리": "https://store.playstation.com/en-hu/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "루마니아": "https://store.playstation.com/en-ro/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "슬로바키아": "https://store.playstation.com/en-sk/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "슬로베니아": "https://store.playstation.com/en-si/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "우크라이나": "https://store.playstation.com/uk-ua/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "사우디아라비아": "https://store.playstation.com/en-sa/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "아랍에미리트": "https://store.playstation.com/en-ae/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "남아공": "https://store.playstation.com/en-za/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "터키": "https://store.playstation.com/en-tr/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "벨기에": "https://store.playstation.com/nl-be/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "오스트리아": "https://store.playstation.com/de-at/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "이스라엘": "https://store.playstation.com/en-il/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "크로아티아": "https://store.playstation.com/en-hr/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "불가리아": "https://store.playstation.com/en-bg/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "키프로스": "https://store.playstation.com/en-cy/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "아이슬란드": "https://store.playstation.com/en-is/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "아일랜드": "https://store.playstation.com/en-ie/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "쿠웨이트": "https://store.playstation.com/en-kw/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "레바논": "https://store.playstation.com/en-lb/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "룩셈부르크": "https://store.playstation.com/fr-lu/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "몰타": "https://store.playstation.com/en-mt/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "오만": "https://store.playstation.com/en-om/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "카타르": "https://store.playstation.com/en-qa/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "바레인": "https://store.playstation.com/en-bh/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    # Asia & Oceania
    "일본": "https://store.playstation.com/ja-jp/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "한국": "https://store.playstation.com/ko-kr/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "중국": "https://store.playstation.com/zh-cn/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "호주": "https://store.playstation.com/en-au/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "인도": "https://store.playstation.com/en-in/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "태국": "https://store.playstation.com/en-th/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "싱가포르": "https://store.playstation.com/en-sg/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "말레이시아": "https://store.playstation.com/en-my/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "인도네시아": "https://store.playstation.com/en-id/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "필리핀": "https://store.playstation.com/en-ph/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "베트남": "https://store.playstation.com/en-vn/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "홍콩": "https://store.playstation.com/zh-hant-hk/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "대만": "https://store.playstation.com/zh-hant-tw/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1", "뉴질랜드": "https://store.playstation.com/en-nz/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
}

FLAGS = {
    # Americas
    "미국": "🇺🇸", "캐나다": "🇨🇦", "브라질": "🇧🇷", "멕시코": "🇲🇽",
    "아르헨티나": "🇦🇷", "칠레": "🇨🇱", "콜롬비아": "🇨🇴", "페루": "🇵🇪",
    "우루과이": "🇺🇾", "볼리비아": "🇧🇴", "과테말라": "🇬🇹", "온두라스": "🇭🇳",
    "코스타리카": "🇨🇷", "에콰도르": "🇪🇨", "엘살바도르": "🇸🇻",
    "니카라과": "🇳🇮", "파나마": "🇵🇦", "파라과이": "🇵🇾",
    # Europe & Middle East
    "영국": "🇬🇧", "독일": "🇩🇪", "프랑스": "🇫🇷", "스페인": "🇪🇸",
    "이탈리아": "🇮🇹", "네덜란드": "🇳🇱", "폴란드": "🇵🇱", "스위스": "🇨🇭",
    "스웨덴": "🇸🇪", "노르웨이": "🇳🇴", "덴마크": "🇩🇰", "핀란드": "🇫🇮",
    "포르투갈": "🇵🇹", "그리스": "🇬🇷", "체코": "🇨🇿", "헝가리": "🇭🇺",
    "루마니아": "🇷🇴", "슬로바키아": "🇸🇰", "슬로베니아": "🇸🇮",
    "우크라이나": "🇺🇦", "사우디아라비아": "🇸🇦", "아랍에미리트": "🇦🇪",
    "남아공": "🇿🇦", "터키": "🇹🇷", "벨기에": "🇧🇪", "오스트리아": "🇦🇹",
    "이스라엘": "🇮🇱", "크로아티아": "🇭🇷", "불가리아": "🇧🇬",
    "키프로스": "🇨🇾", "아이슬란드": "🇮🇸", "아일랜드": "🇮🇪",
    "쿠웨이트": "🇰🇼", "레바논": "🇱🇧", "룩셈부르크": "🇱🇺",
    "몰타": "🇲🇹", "오만": "🇴🇲", "카타르": "🇶🇦", "바레인": "🇧🇭",
    # Asia & Oceania
    "일본": "🇯🇵", "한국": "🇰🇷", "중국": "🇨🇳", "호주": "🇦🇺",
    "인도": "🇮🇳", "태국": "🇹🇭", "싱가포르": "🇸🇬", "말레이시아": "🇲🇾",
    "인도네시아": "🇮🇩", "필리핀": "🇵🇭", "베트남": "🇻🇳",
    "홍콩": "🇭🇰", "대만": "🇹🇼", "뉴질랜드": "🇳🇿",
}

SEARCH_TERMS = {
    "일본": ["crimson desert", "紅の砂漠"],
    "중국": ["crimson desert", "红之沙漠"],
    "한국": ["crimson desert", "붉은사막"],
    "홍콩": ["crimson desert", "赤血沙漠"],
    "대만": ["crimson desert", "赤血沙漠"],
}
# 주의: DLC 현지화 타이틀("Charting the Unknown" 등)은 국가별로 다를 수 있는데
# 전부 확인하지 못했습니다. "crimson desert"가 프랜차이즈 접두사로 유지된다는
# 가정 하에 기존 검색어를 그대로 재사용합니다 — 특정 국가에서 매칭이 안 되면
# 해당 국가 페이지를 직접 열어 정확한 표기를 확인해 SEARCH_TERMS에 추가해야 합니다.

# 모든 국가에 대해 기본 검색어 추가
ALL_COUNTRIES = set()
for region_countries in REGIONS.values():
    ALL_COUNTRIES.update(region_countries)

for country in ALL_COUNTRIES:
    if country not in SEARCH_TERMS:
        SEARCH_TERMS[country] = ["crimson desert"]

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
BASELINE_FILE   = "crimson_dlc_discord_baseline.json"  # 마지막 알림 발송 시점 기준값
HISTORY_FILE    = "crimson_dlc_rank_history.json"
WORKFLOW_FILE   = ".github/workflows/crimson_dlc_workflow.yml"  # 스케줄 소스


# =============================================================================
# 스케줄 파싱 (yml → JSON 메타 → 대시보드)
# =============================================================================

def parse_cron_to_kst_slots(cron_expr: str) -> list:
    """
    'MIN HOUR * * *' cron 표현식 → KST 고정 슬롯 목록 반환.
    반환: {"type": "fixed", "slots_kst": [(h, m), ...]}
    """
    parts = cron_expr.strip().split()
    if len(parts) < 2:
        return {"type": "unknown"}
    min_field, hour_field = parts[0], parts[1]
    if hour_field == '*':
        # 인터벌형 (매 N분)
        mins = [int(m) for m in min_field.replace('*/', '').split(',') if m.strip().replace('*/','').isdigit()]
        interval = mins[1] - mins[0] if len(mins) >= 2 else int(min_field.split('/')[1]) if '/' in min_field else 60
        return {"type": "interval", "interval_min": interval}
    slots = []
    for h_tok in hour_field.split(','):
        if not h_tok.strip().isdigit():
            continue
        kst_h = (int(h_tok) + 9) % 24
        for m_tok in min_field.split(','):
            if m_tok.strip().isdigit():
                slots.append([kst_h, int(m_tok)])
    return {"type": "fixed", "slots_kst": sorted(set(map(tuple, slots)))}


def read_schedule_meta_from_yml(yml_path: str) -> dict:
    """
    yml에서 모든 cron 표현식을 읽어 슬롯을 합산, 스케줄 메타 반환.
    복수 cron 스케줄도 통합 처리.
    """
    if not os.path.exists(yml_path):
        print(f"ℹ️  {yml_path} 없음 → 스케줄 메타 업데이트 스킵")
        return None
    try:
        with open(yml_path, "r", encoding="utf-8") as f:
            content = f.read()
        cron_exprs = re.findall(r"cron:\s*['\"]([^'\"]+)['\"]", content)
        if not cron_exprs:
            print("ℹ️  cron 표현식 없음 → 스케줄 메타 업데이트 스킵")
            return None
        all_slots = set()
        for expr in cron_exprs:
            parsed = parse_cron_to_kst_slots(expr)
            if parsed.get("type") == "fixed":
                all_slots.update(parsed["slots_kst"])
        meta = {
            "cron": cron_exprs,          # 원본 표현식 목록
            "type": "fixed",
            "slots_kst": sorted(all_slots)  # [[h, m], ...]
        }
        print(f"✅  스케줄 파싱: {cron_exprs} → {len(all_slots)}개 슬롯 (KST)")
        return meta
    except Exception as e:
        print(f"⚠️  스케줄 파싱 오류: {e}")
        return None

# =============================================================================
# DLC 사전예약 설정
# =============================================================================

# DLC("Charting the Unknown") 출시일 — 2026-10-15 (PS Store 표기 기준, 참고용)
DLC_RELEASE_DATE_KST = datetime(2026, 10, 15, tzinfo=KST)

# 본편과 달리 DLC는 출시 전까지 항상 "사전예약" 카테고리에만 존재하므로
# 본편처럼 베스트셀러 카테고리로 전환하는 로직이 필요 없음.
SKIP_COUNTRIES = {"중국", "베트남", "슬로베니아", "필리핀"}  # 추적 제외 국가 (본편과 동일하게 맞춤)

PREORDER_CATEGORY   = "3bf499d7-7acf-4931-97dd-2667494ee2c9"

LOCALE_MAP = {
    # Americas
    "미국": "en-us", "캐나다": "en-ca", "브라질": "pt-br", "멕시코": "es-mx",
    "아르헨티나": "es-ar", "칠레": "es-cl", "콜롬비아": "es-co", "페루": "es-pe",
    "우루과이": "es-uy", "볼리비아": "es-bo", "과테말라": "es-gt", "온두라스": "es-hn",
    "코스타리카": "es-cr", "에콰도르": "es-ec", "엘살바도르": "es-sv",
    "니카라과": "es-ni", "파나마": "es-pa", "파라과이": "es-py",
    # Europe & Middle East
    "영국": "en-gb", "독일": "de-de", "프랑스": "fr-fr", "스페인": "es-es",
    "이탈리아": "it-it", "네덜란드": "nl-nl", "폴란드": "pl-pl", "스위스": "de-ch",
    "스웨덴": "sv-se", "노르웨이": "no-no", "덴마크": "da-dk", "핀란드": "fi-fi",
    "포르투갈": "pt-pt", "그리스": "en-gr", "체코": "en-cz", "헝가리": "en-hu",
    "루마니아": "en-ro", "슬로바키아": "en-sk", "슬로베니아": "en-si",
    "우크라이나": "uk-ua", "사우디아라비아": "en-sa", "아랍에미리트": "en-ae",
    "남아공": "en-za", "터키": "en-tr", "벨기에": "nl-be", "오스트리아": "de-at",
    "이스라엘": "en-il", "크로아티아": "en-hr", "불가리아": "en-bg",
    "키프로스": "en-cy", "아이슬란드": "en-is", "아일랜드": "en-ie",
    "쿠웨이트": "en-kw", "레바논": "en-lb", "룩셈부르크": "fr-lu",
    "몰타": "en-mt", "오만": "en-om", "카타르": "en-qa", "바레인": "en-bh",
    # Asia & Oceania
    "일본": "ja-jp", "한국": "ko-kr", "중국": "zh-cn", "호주": "en-au",
    "인도": "en-in", "태국": "en-th", "싱가포르": "en-sg", "말레이시아": "en-my",
    "인도네시아": "en-id", "필리핀": "en-ph", "베트남": "en-vn",
    "홍콩": "zh-hant-hk", "대만": "zh-hant-tw", "뉴질랜드": "en-nz",
}

def get_active_url(country):
    """
    DLC는 항상 사전예약 카테고리 URL 사용 (본편처럼 출시 후 전환 없음).
    중국 등 제외 국가 → None 반환
    """
    if country in SKIP_COUNTRIES:
        return None
    locale = LOCALE_MAP.get(country)
    if not locale:
        return URLS.get(country)  # fallback: 기존 URL
    return f"https://store.playstation.com/{locale}/category/{PREORDER_CATEGORY}/1"

# =============================================================================
# 유틸리티
# =============================================================================

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def crawl_country(driver, country, url):
    """DLC는 단일 상품(프리오더 번들)만 존재하므로 첫 매칭 1건의 순위만 반환."""
    terms = SEARCH_TERMS.get(country, ["crimson desert"])
    total_rank = 0

    for page in range(1, 4):
        try:
            driver.get(url.replace("/1", f"/{page}"))
            time.sleep(3)
            items = driver.find_elements(By.CSS_SELECTOR, "li[data-qa*='grid-item'], a[href*='/product/']")
            for item in items:
                try:
                    link_el = item if item.tag_name == 'a' else item.find_element(By.CSS_SELECTOR, "a")
                    href = link_el.get_attribute("href")
                    if not href or "/product/" not in href:
                        continue
                    total_rank += 1
                    label = (link_el.get_attribute("aria-label") or "").lower()
                    text = (item.text or "").lower()
                    if any(t.lower() in label or t.lower() in text for t in terms):
                        return {"rank": total_rank}
                except:
                    continue
        except:
            continue
    return {"rank": None}

def calculate_avg(results):
    """가중 평균 순위 계산"""
    total_sum, total_w = 0, 0
    for c, data in results.items():
        if not data:
            continue
        w = MARKET_WEIGHTS.get(c, 1.0)
        rank = data.get('rank')
        if rank:
            total_sum += rank * w
            total_w += w
    return total_sum / total_w if total_w > 0 else None

def load_baseline():
    """마지막 Discord 알림 발송 시점의 combined_avg 로드"""
    if not os.path.exists(BASELINE_FILE):
        return None
    try:
        with open(BASELINE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("combined_avg")
    except:
        return None

def save_baseline(combined_avg):
    """Discord 알림 발송 시점의 combined_avg 저장"""
    with open(BASELINE_FILE, "w", encoding="utf-8") as f:
        json.dump({"combined_avg": combined_avg, "timestamp": datetime.now(KST).isoformat()}, f)

def format_diff(current, previous):
    """순위 숫자 증감 포맷팅"""
    if previous is None or current is None:
        return ""
    diff = previous - current  # 작아질수록 순위 상승
    if diff > 0:
        return f"▲{diff}"
    elif diff < 0:
        return f"▼{abs(diff)}"
    else:
        return "0"

def get_emoji(diff_text):
    """순위 변동에 따른 이모지 반환"""
    if not diff_text or diff_text == "0":
        return "⚪"  # 변동 없음
    elif "▲" in diff_text:
        return "🟢"  # 상승 (순위가 좋아짐)
    elif "▼" in diff_text:
        return "🔴"  # 하락 (순위가 나빠짐)
    return ""

def load_history_safe(history_file):
    """
    rank_history.json을 안전하게 읽어 반환한다.
    - 신규 포맷: {"schedule": ..., "history": [...]}
    - 구버전 포맷: 리스트 그대로
    - 읽기/파싱 실패 시 .backup 파일로 자동 복구 시도
    - .backup도 실패하면 RuntimeError를 raise해 호출부에서 스크립트를 중단
    - 성공 시 (history 리스트, 복구 여부 bool) 튜플 반환
    """
    import shutil

    backup_file = history_file + ".backup"

    def _try_load(path):
        """파일을 읽어 list를 반환. 실패 시 None 반환."""
        if not os.path.exists(path):
            print(f"⚠️  파일 없음: {path}")
            return None
        try:
            file_size = os.path.getsize(path)
            print(f"📁 확인: {path} ({file_size:,} bytes)")
            if file_size == 0:
                print(f"⚠️  파일이 비어 있습니다: {path}")
                return None

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 신규 포맷: {"schedule": ..., "history": [...]}
            if isinstance(data, dict) and "history" in data:
                return data["history"]
            if not isinstance(data, list):
                print(f"⚠️  {path} 형식 오류: list가 아닙니다.")
                return None
            return data
        except json.JSONDecodeError as e:
            print(f"⚠️  {path} JSON 파싱 실패: {e}")
            return None
        except Exception as e:
            print(f"⚠️  {path} 읽기 실패: {e}")
            return None

    # 1차: 메인 파일 시도
    history = _try_load(history_file)
    if history is not None:
        return history, False  # 정상 로드, 복구 없음

    # 2차: backup 파일로 복구 시도
    print(f"⚠️  메인 파일 로드 실패 → {backup_file} 으로 복구를 시도합니다...")
    history = _try_load(backup_file)
    if history is not None:
        # backup → 메인 파일로 복원
        shutil.copy2(backup_file, history_file)
        print(f"✅  {backup_file} 에서 복구 성공! ({len(history)}개 레코드)")
        return history, True  # 복구 성공

    # 둘 다 실패 → 호출부에서 중단 처리
    raise RuntimeError(
        f"❌  {history_file} 과 {backup_file} 모두 읽기 실패.\n"
        f"   데이터 손실 방지를 위해 스크립트를 중단합니다.\n"
        f"   파일을 수동으로 확인해 주세요."
    )



def save_history_safe(history_file, payload):
    """
    히스토리를 원자적으로(atomic) 저장한다.
    - 기존 정상 메인 파일을 .backup으로 보관
    - .tmp에 저장 후 JSON 재검증
    - 검증 성공 시 os.replace()로 메인 파일 교체
    """
    import shutil

    backup_file = history_file + ".backup"
    temp_file = history_file + ".tmp"

    try:
        # 기존 정상 파일을 백업
        if os.path.exists(history_file) and os.path.getsize(history_file) > 0:
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    json.load(f)
                shutil.copy2(history_file, backup_file)
                print(f"💾 히스토리 백업 완료: {backup_file}")
            except Exception as e:
                print(f"⚠️ 기존 메인 파일이 정상 JSON이 아니므로 backup 갱신 생략: {e}")

        # 임시 파일에 먼저 저장
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        # 임시 파일 JSON 검증
        with open(temp_file, "r", encoding="utf-8") as f:
            test_data = json.load(f)

        if not isinstance(test_data, dict) or not isinstance(test_data.get("history"), list):
            raise ValueError("저장된 히스토리 형식 검증 실패")

        # 검증 성공 후 원자적 교체
        os.replace(temp_file, history_file)
        print(f"✅ 히스토리 안전 저장 완료 ({len(payload['history'])}개 레코드)")

    except Exception as e:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception:
            pass
        print(f"❌ 히스토리 안전 저장 실패: {type(e).__name__}: {e}")
        raise

def generate_csv_buffer(results):
    """순위 결과를 CSV 형식의 BytesIO 버퍼로 반환"""
    import csv
    from io import StringIO
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=["region", "country", "flag", "combined"])
    writer.writeheader()
    for region_name, region_countries in REGIONS.items():
        for country in region_countries:
            if country not in results or country in SKIP_COUNTRIES:
                continue
            data = results[country]
            rank = data.get("rank") if data else None
            writer.writerow({
                "region": region_name,
                "country": country,
                "flag": FLAGS.get(country, ""),
                "combined": rank if rank else "-",
            })
    from io import BytesIO
    return BytesIO(buf.getvalue().encode("utf-8-sig"))


def send_discord(results, combined_avg):
    if not DISCORD_WEBHOOK:
        return

    import shutil

    history_file = HISTORY_FILE
    backup_file = history_file + ".backup"

    # 안전하게 히스토리 로드 (실패 시 backup 자동 복구, 둘 다 실패 시 중단)
    try:
        history, was_recovered = load_history_safe(history_file)
    except RuntimeError as e:
        print(str(e))
        raise SystemExit(1)  # 다른 코드들도 오염되지 않도록 즉시 종료

    # 이전 실행 데이터
    prev_run = history[-1] if history else None

    # 평균 변동폭
    prev_combined_avg = prev_run['averages'].get('combined') if prev_run else None
    combined_diff_text = format_diff(combined_avg, prev_combined_avg)

    # 히스토리 업데이트
    new_entry = {
        "timestamp": datetime.now(KST).isoformat(),
        "averages": {"combined": combined_avg},
        "raw_results": results
    }
    history.append(new_entry)

    # schedule 메타 읽기 (yml → JSON에 포함시켜 대시보드가 활용)
    schedule_meta = read_schedule_meta_from_yml(WORKFLOW_FILE)

    # 기존 파일에서 schedule 유지 (메타 파싱 실패 시)
    existing_schedule = None
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as _f:
                _existing = json.load(_f)
            if isinstance(_existing, dict):
                existing_schedule = _existing.get("schedule")
        except Exception:
            pass
    final_schedule = schedule_meta if schedule_meta is not None else existing_schedule

    payload = {"history": history}
    if final_schedule:
        payload["schedule"] = final_schedule

    # 직접 덮어쓰지 않고 임시 파일 → 검증 → 원자적 교체 방식으로 안전 저장
    save_history_safe(history_file, payload)


    if was_recovered:
        print(f"✅  backup에서 복구된 데이터에 새 항목을 추가해 저장했습니다.")

    # ── 전체 평균 변동 여부 확인 (baseline 기준 1.0 이상 변동 시에만 요약+그래프 전송) ──
    baseline_avg = load_baseline()
    if combined_avg is not None and baseline_avg is not None:
        diff_from_baseline = abs(combined_avg - baseline_avg)
        avg_changed = diff_from_baseline >= 1.0
        if not avg_changed:
            print(f"ℹ️  기준점 대비 변화 미미 (기준: {baseline_avg:.1f} → 현재: {combined_avg:.1f}, 차이: {diff_from_baseline:.2f}) - 요약 스킵")
        else:
            print(f"🔔 기준점 대비 변화 감지 (기준: {baseline_avg:.1f} → 현재: {combined_avg:.1f}, 차이: {diff_from_baseline:.2f}) - 요약 전송")
    else:
        avg_changed = combined_avg is not None  # 첫 실행 시 baseline 없으면 무조건 전송

    # ── 지역별: 순위 변화 있는 나라만 수집 ──
    region_changed_lines = {}  # {region_name: [line, ...]}

    for region_name, region_countries in REGIONS.items():
        lines = []

        # 가중치 순으로 정렬
        sorted_countries = sorted(
            [c for c in region_countries if c in results],
            key=lambda x: MARKET_WEIGHTS.get(x, 0),
            reverse=True
        )

        for c in sorted_countries:
            curr_rank = (results[c] or {}).get('rank')

            # 이전 개별 국가 순위
            prev_rank = None
            if prev_run and "raw_results" in prev_run:
                prev_country_data = prev_run["raw_results"].get(c, {})
                prev_rank = prev_country_data.get("rank")

            # 순위 변화 없으면 스킵
            if prev_rank == curr_rank:
                continue
            # 이전 데이터 없으면 스킵 (첫 실행)
            if prev_run is None:
                continue

            r_diff  = format_diff(curr_rank, prev_rank)
            r_emoji = get_emoji(r_diff)
            r_part  = f"{curr_rank or '-'} {r_diff}" if r_diff else f"{curr_rank or '-'}"

            store_url = get_active_url(c)
            flag = FLAGS.get(c, "")
            country_label = f"{flag} [{c}]({store_url})" if store_url else f"{flag} {c}"

            lines.append(f"**{country_label}**: {r_emoji}`{r_part}`")

        if lines:
            region_changed_lines[region_name] = lines

    any_country_changed = bool(region_changed_lines)

    # 아무 변화도 없으면 조용히 종료
    if not avg_changed and not any_country_changed:
        print("ℹ️  순위 변화 없음 → 디스코드 알림 생략")
        return

    # avg_changed=False면 요약+그래프는 전송하지 않고 국가 변화만 전송
    if not avg_changed:
        print("ℹ️  평균 변화 없음 → 요약+그래프 스킵, 국가 순위 변화만 전송")

    # ── 전체 평균이 1위 이상 변동했을 때만 요약+그래프 전송 ──
    if avg_changed:
        # 그래프 생성
        img_buf = None
        if HAS_MATPLOTLIB and len(history) >= 2:
            plt.figure(figsize=(10, 5))
            dates = [datetime.fromisoformat(h['timestamp']) for h in history]
            combined_ranks = [h['averages'].get('combined') for h in history]

            filtered_dates = [d for d, r in zip(dates, combined_ranks) if r is not None]
            filtered_ranks = [r for r in combined_ranks if r is not None]

            if filtered_dates:
                plt.plot(filtered_dates, filtered_ranks, label='Combined Rank',
                        color='#00B0F4', marker='o', linewidth=2, markersize=8)
                plt.gca().invert_yaxis()
                plt.title("Crimson Desert Enhanced: Charting the Unknown - PS Store 사전예약 순위", fontsize=13, fontweight='bold')
                plt.xlabel('Date', fontsize=12)
                plt.ylabel('Rank (weighted avg)', fontsize=12)
                plt.legend()
                plt.grid(True, alpha=0.2)
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                plt.gcf().autofmt_xdate()
                plt.tight_layout()

                img_buf = BytesIO()
                plt.savefig(img_buf, format='png', dpi=150)
                img_buf.seek(0)
                plt.close()

        summary_desc = f"📊 **전체 가중 평균**: `{combined_avg:.1f}위` {'(' + combined_diff_text + ')' if combined_diff_text else ''}\n"
        summary_desc += f"🌐 **추적 중인 국가**: {len(results)}개국 | ⏳ 사전예약 차트 (출시일 {DLC_RELEASE_DATE_KST.strftime('%Y-%m-%d')})\n\n"

        for rn in ["Americas", "Europe & Middle East", "Asia & Oceania"]:
            region_countries = REGIONS[rn]
            region_results = {c: results[c] for c in region_countries if c in results}
            region_avg = calculate_avg(region_results)
            if region_avg:
                summary_desc += f"**{rn}**: `{region_avg:.1f}위`\n"

        summary_payload = {
            "embeds": [{
                "title": "🎮 붉은사막 DLC(Charting the Unknown) PS Store 사전예약 순위 리포트",
                "description": summary_desc,
                "color": 0x00B0F4,
                "image": {"url": "attachment://graph.png"} if img_buf else None,
                "timestamp": datetime.now(KST).isoformat()
            }]
        }

        if img_buf:
            files = {"file": ("graph.png", img_buf, "image/png")}
            payload = {"payload_json": json.dumps(summary_payload)}
            requests.post(DISCORD_WEBHOOK, data=payload, files=files)
        else:
            requests.post(DISCORD_WEBHOOK, json=summary_payload)

        time.sleep(1)

    # ── 순위 변화 있는 나라만 지역별 메시지 전송 ──
    for region_name, lines in region_changed_lines.items():
        CHUNK_LIMIT = 3800
        chunks = []
        current_chunk = []
        current_len = 0
        for line in lines:
            if current_len + len(line) + 1 > CHUNK_LIMIT and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [line]
                current_len = len(line)
            else:
                current_chunk.append(line)
                current_len += len(line) + 1
        if current_chunk:
            chunks.append(current_chunk)

        for i, chunk in enumerate(chunks):
            part_label = f" ({i+1}/{len(chunks)})" if len(chunks) > 1 else ""
            region_payload = {
                "embeds": [{
                    "title": f"🌐 {region_name}{part_label}",
                    "description": "\n".join(chunk),
                    "color": 0x00B0F4,
                    "timestamp": datetime.now(KST).isoformat()
                }]
            }
            requests.post(DISCORD_WEBHOOK, json=region_payload)
            time.sleep(1)  # Discord API rate limit 방지

    # 알림 발송 완료 → baseline 갱신
    if avg_changed and combined_avg is not None:
        save_baseline(combined_avg)
        print(f"✅ baseline 갱신: {combined_avg:.1f}")



def main():
    print("=" * 60)
    print("🎮 붉은사막 DLC(Charting the Unknown) PS Store 사전예약 순위 추적")
    print("=" * 60)
    print(f"   (DLC 출시일 기준: {DLC_RELEASE_DATE_KST.strftime('%Y-%m-%d')} KST)")
    print()

    start_time = time.time()
    driver = setup_driver()

    results = {}

    try:
        all_countries = []
        for region_countries in REGIONS.values():
            all_countries.extend(region_countries)

        for country in all_countries:
            if country in SKIP_COUNTRIES:
                print(f"⏭️  스킵: {country} (추적 제외 국가)")
                results[country] = {"rank": None}
                continue

            url = get_active_url(country)
            if url:
                print(f"크롤링 중: {country}...")
                results[country] = crawl_country(driver, country, url) or {"rank": None}
            else:
                print(f"URL 없음: {country}")
                results[country] = {"rank": None}
    finally:
        driver.quit()
    
    elapsed = (time.time() - start_time) / 60
    print(f"\n⏱️ 소요 시간: {elapsed:.1f}분")
    
    # 가중 평균 계산
    combined_avg = calculate_avg(results)
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("📊 결과 요약")
    print("=" * 60)
    
    for region_name, region_countries in REGIONS.items():
        print(f"\n{region_name}:")
        for country in region_countries:
            if country in results:
                data = results[country] or {}
                print(f"  {country}: {data.get('rank', '-')}위")
    
    if combined_avg:
        print(f"\n전체 가중 평균: {combined_avg:.1f}위")
    
    # Discord 전송
    send_discord(results, combined_avg)

if __name__ == "__main__":
    main()
