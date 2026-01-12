#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crimson Desert PS Store 순위 추적기
PlayStation Store의 Pre-Order 목록에서 Crimson Desert 관련 상품 순위를 국가별로 추적하고,
가중 평균 순위를 계산해 Discord로 리포트하는 스크립트
"""

import time
import json
import os
import requests
from datetime import datetime
from io import BytesIO

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# matplotlib은 선택적 (없어도 동작)
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# =============================================================================
# 설정값
# =============================================================================

MARKET_WEIGHTS = {
    "미국": 30.0, "영국": 8.5, "일본": 8.0, "독일": 6.5, "프랑스": 6.0,
    "캐나다": 4.5, "스페인": 4.0, "이탈리아": 3.5, "호주": 3.0, "한국": 2.8,
    "브라질": 2.5, "멕시코": 2.0, "네덜란드": 1.8, "사우디아라비아": 1.5,
    "아랍에미리트": 1.2, "중국": 0.2
}

COUNTRIES = sorted(MARKET_WEIGHTS.keys(), key=lambda x: MARKET_WEIGHTS[x], reverse=True)

URLS = {
    "미국": "https://store.playstation.com/en-us/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "영국": "https://store.playstation.com/en-gb/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "프랑스": "https://store.playstation.com/fr-fr/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "독일": "https://store.playstation.com/de-de/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "일본": "https://store.playstation.com/ja-jp/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "스페인": "https://store.playstation.com/es-es/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "캐나다": "https://store.playstation.com/en-ca/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "호주": "https://store.playstation.com/en-au/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "이탈리아": "https://store.playstation.com/it-it/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "브라질": "https://store.playstation.com/pt-br/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "사우디아라비아": "https://store.playstation.com/en-sa/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "아랍에미리트": "https://store.playstation.com/en-ae/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "멕시코": "https://store.playstation.com/es-mx/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "중국": "https://store.playstation.com/zh-cn/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "네덜란드": "https://store.playstation.com/nl-nl/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "한국": "https://store.playstation.com/ko-kr/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
}

FLAGS = {
    "미국": "🇺🇸", "영국": "🇬🇧", "일본": "🇯🇵", "독일": "🇩🇪", "프랑스": "🇫🇷",
    "캐나다": "🇨🇦", "스페인": "🇪🇸", "이탈리아": "🇮🇹", "호주": "🇦🇺", "한국": "🇰🇷",
    "브라질": "🇧🇷", "멕시코": "🇲🇽", "네덜란드": "🇳🇱", "사우디아라비아": "🇸🇦",
    "아랍에미리트": "🇦🇪", "중국": "🇨🇳",
}

SEARCH_TERMS = {
    "미국": ["crimson desert"], "영국": ["crimson desert"], "프랑스": ["crimson desert"],
    "독일": ["crimson desert"], "일본": ["crimson desert", "紅の砂漠"],
    "스페인": ["crimson desert"], "캐나다": ["crimson desert"], "호주": ["crimson desert"],
    "이탈리아": ["crimson desert"], "브라질": ["crimson desert"],
    "사우디아라비아": ["crimson desert"], "아랍에미리트": ["crimson desert"],
    "멕시코": ["crimson desert"], "중국": ["crimson desert", "红之沙漠"],
    "네덜란드": ["crimson desert"], "한국": ["crimson desert", "붉은사막", "크림슨 데저트"],
}

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")


# =============================================================================
# 유틸리티 함수
# =============================================================================

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-gpu')              # headless에서 종종 필요
    options.add_argument('--disable-blink-features=AutomationControlled')

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def crawl_country(driver, country: str, url: str) -> dict:
    terms = SEARCH_TERMS.get(country, ["crimson desert"])
    found_ranks = []
    total_rank = 0

    for page in range(1, 4):
        try:
            driver.get(url.replace("/1", f"/{page}"))
            time.sleep(3.5 + page * 0.4)  # 페이지별 약간의 지연 증가

            items = driver.find_elements(By.CSS_SELECTOR, "li[data-qa*='grid-item'], a[href*='/product/']")
            for item in items:
                try:
                    link_el = item if item.tag_name == 'a' else item.find_element(By.CSS_SELECTOR, "a")
                    href = link_el.get_attribute("href") or ""
                    if "/product/" not in href:
                        continue

                    total_rank += 1
                    label = (link_el.get_attribute("aria-label") or "").lower()
                    text = (item.text or "").lower()

                    if any(t.lower() in label or t.lower() in text for t in terms):
                        found_ranks.append(total_rank)
                        if len(found_ranks) >= 2:
                            break
                except:
                    continue

            if len(found_ranks) >= 2:
                break
        except Exception as e:
            print(f"[{country}] 페이지 {page} 크롤링 실패: {e}")
            continue

    result = {"standard": None, "deluxe": None}

    if len(found_ranks) >= 2:
        # 한국/스페인은 Standard가 먼저 나오는 경향 → 순서 조정
        if country in ["한국", "스페인"]:
            result["standard"], result["deluxe"] = found_ranks[0], found_ranks[1]
        else:
            result["deluxe"], result["standard"] = found_ranks[0], found_ranks[1]
    elif len(found_ranks) == 1:
        result["standard"] = found_ranks[0]

    return result


def calculate_combined_rank(standard: int | None, deluxe: int | None) -> int | None:
    if standard is not None and deluxe is not None:
        return min(standard, deluxe)
    return standard or deluxe


def calculate_weighted_avg(results: dict) -> float | None:
    total_sum = 0.0
    total_weight = 0.0

    for country, data in results.items():
        weight = MARKET_WEIGHTS.get(country, 1.0)
        combined = calculate_combined_rank(data['standard'], data['deluxe'])

        if combined is not None:
            total_sum += combined * weight
            total_weight += weight

    return total_sum / total_weight if total_weight > 0 else None


def format_diff(current: int | None, previous: int | None) -> str:
    if previous is None or current is None:
        return ""
    diff = previous - current
    if diff > 0:
        return f"▲{diff}"
    if diff < 0:
        return f"▼{abs(diff)}"
    return ""


def send_discord_report(results: dict, combined_avg: float | None):
    if not DISCORD_WEBHOOK:
        print("DISCORD_WEBHOOK 환경변수가 없음 → 알림 전송 스킵")
        return

    history_file = "rank_history.json"
    history = []

    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            history = []

    prev_run = history[-1] if history else None

    lines = []
    for country in COUNTRIES:
        data = results[country]
        curr_s = data['standard']
        curr_d = data['deluxe']
        curr_combined = calculate_combined_rank(curr_s, curr_d)

        prev_s = prev_d = prev_combined = None
        if prev_run and "raw_results" in prev_run:
            prev_data = prev_run["raw_results"].get(country, {})
            prev_s = prev_data.get("standard")
            prev_d = prev_data.get("deluxe")
            prev_combined = calculate_combined_rank(prev_s, prev_d)

        s_diff = format_diff(curr_s, prev_s)
        d_diff = format_diff(curr_d, prev_d)
        c_diff = format_diff(curr_combined, prev_combined)

        s_text = f"{curr_s or '-'}{f'({s_diff})' if s_diff else ''}"
        d_text = f"{curr_d or '-'}{f'({d_diff})' if d_diff else ''}"
        c_text = f"{curr_combined or '-'}{f'({c_diff})' if c_diff else ''}"

        flag = FLAGS.get(country, "")
        store_url = URLS.get(country, "")
        label = f"[{flag} {country}]({store_url})" if store_url else f"{flag} {country}"

        lines.append(f"**{label}**: S `{s_text}` / D `{d_text}` → `{c_text}`")

    prev_avg = prev_run["averages"].get("combined") if prev_run else None
    avg_diff = format_diff(combined_avg, prev_avg)

    description = (
        "\n".join(lines) +
        f"\n\n📊 **가중 평균 순위**: `{combined_avg:.1f}위` {f'({avg_diff})' if avg_diff else ''}"
    )

    # 히스토리 저장 (최근 100개만)
    history.append({
        "timestamp": datetime.now().isoformat(),
        "averages": {"combined": combined_avg},
        "raw_results": results
    })
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history[-100:], f, ensure_ascii=False, indent=2)

    # 그래프 생성 (선택적)
    image_attachment = None
    if HAS_MATPLOTLIB and len(history) >= 2:
        try:
            plt.figure(figsize=(10, 5))
            dates = [datetime.fromisoformat(h["timestamp"]) for h in history]
            ranks = [h["averages"].get("combined") for h in history]

            valid = [(d, r) for d, r in zip(dates, ranks) if r is not None]
            if valid:
                valid_dates, valid_ranks = zip(*valid)
                plt.plot(valid_dates, valid_ranks, color='#00B0F4', marker='o',
                         linewidth=2, markersize=8, label='Combined Rank')
                plt.gca().invert_yaxis()
                plt.title("Crimson Desert - PS Store Ranking Trend")
                plt.xlabel("Date")
                plt.ylabel("Weighted Average Rank")
                plt.legend()
                plt.grid(True, alpha=0.3)
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                plt.gcf().autofmt_xdate()
                plt.tight_layout()

                buf = BytesIO()
                plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                buf.seek(0)
                plt.close()
                image_attachment = ("graph.png", buf, "image/png")
        except Exception as e:
            print(f"그래프 생성 실패: {e}")

    # Discord Embed 전송
    embed = {
        "title": "🎮 Crimson Desert PS Store 순위 업데이트",
        "description": description,
        "color": 0x00B0F4,
        "timestamp": datetime.utcnow().isoformat()
    }
    if image_attachment:
        embed["image"] = {"url": "attachment://graph.png"}

    payload = {"payload_json": json.dumps({"embeds": [embed]})}
    files = {"file": image_attachment} if image_attachment else None

    try:
        r = requests.post(DISCORD_WEBHOOK, data=payload, files=files)
        if r.status_code == 204:
            print("Discord 알림 전송 완료")
        else:
            print(f"Discord 전송 실패: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Discord 요청 예외: {e}")


# =============================================================================
# 메인 로직
# =============================================================================

def main():
    print("=" * 70)
    print("🎮 Crimson Desert PlayStation Store 순위 추적 시작")
    print("=" * 70)

    start_time = time.time()

    driver = None
    try:
        driver = setup_driver()
        results = {}

        for country in COUNTRIES:
            print(f"→ {country} 크롤링 중...")
            results[country] = crawl_country(driver, country, URLS[country])

        combined_avg = calculate_weighted_avg(results)

        # 콘솔 출력
        print("\n" + "=" * 70)
        print("📊 국가별 결과")
        print("=" * 70)
        for c in COUNTRIES:
            s = results[c]['standard']
            d = results[c]['deluxe']
            comb = calculate_combined_rank(s, d)
            print(f"{c:8} | S {s:3}위 / D {d:3}위 → {comb:3}위")

        if combined_avg:
            print(f"\n가중 평균 순위: {combined_avg:.1f}위")

        # Discord 보고서 전송
        send_discord_report(results, combined_avg)

    except Exception as e:
        print(f"\n실행 중 오류 발생: {e}")
    finally:
        if driver:
            driver.quit()

    elapsed = time.time() - start_time
    print(f"\n총 소요 시간: {elapsed/60:.1f}분 ({elapsed:.0f}초)")


if __name__ == "__main__":
    main()