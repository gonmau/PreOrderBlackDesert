"""
PS Store 국가별 특정 게임 베스트셀러 순위 추적기

- 국가(로케일)별 PS Store 베스트셀러 카테고리 페이지를 headless 브라우저로 렌더링해서
  타이틀 목록을 뽑고, 그 안에서 대상 게임의 순위(인덱스)를 찾아 표로 정리합니다.
- PS Store는 공식 공개 API가 없고 페이지가 JS로 렌더링되므로 Playwright로 실제 DOM을 읽습니다.

사용 전 확인할 것 (딱 1곳만 손보면 됩니다):
  BESTSELLER_URL_TEMPLATE 의 카테고리 ID가 실제로 각 로케일에서 "베스트셀러/인기 다운로드"
  차트로 뜨는지 브라우저로 한 번 확인하세요. PS Store > 세일/차트 > Best Sellers 메뉴에서
  URL을 복사해 {locale} 부분만 바꿔주면 됩니다. (blackdesert-cawling에서 쓰던 URL 그대로
  써도 됩니다 — 있으면 그걸로 교체.)

설치:
    pip install playwright pandas tabulate --break-system-packages
    playwright install chromium

실행 (나라마다 타이틀 언어가 다르므로 콤마로 여러 언어 별칭을 같이 넣어주세요):
    python ps_rank_tracker.py "붉은사막,Crimson Desert,クリムゾン・デザート"
    python ps_rank_tracker.py "붉은사막,Crimson Desert" --out rank.csv
"""

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd
from playwright.sync_api import sync_playwright

# 국가코드: PS Store 로케일 코드. 필요에 따라 추가/삭제하세요.
COUNTRIES = {
    "KR": "ko-kr",
    "US": "en-us",
    "JP": "ja-jp",
    "GB": "en-gb",
    "DE": "de-de",
    "FR": "fr-fr",
    "CA": "en-ca",
    "AU": "en-au",
    "BR": "pt-br",
    "MX": "es-mx",
    "IT": "it-it",
    "ES": "es-es",
    "SA": "ar-sa",   # 사우디
    "AE": "ar-ae",   # UAE
    "SE": "sv-se",
    "NO": "no-no",
    "NL": "nl-nl",
    "PL": "pl-pl",
    "PT": "pt-pt",
    "TR": "tr-tr",
    "HK": "zh-hant-hk",
    "TW": "zh-hant-tw",
    "TH": "th-th",
    "ID": "en-id",
    "SG": "en-sg",
    "IN": "en-in",
    "ZA": "en-za",
    "AT": "de-at",
    "CH": "de-ch",
}

# ⚠️ 카테고리 ID는 로케일마다 동일하게 쓰이는 값이지만 PS 쪽에서 바뀔 수 있습니다.
# 안 맞으면 브라우저에서 PS Store > Best Sellers 차트 URL을 복사해 이 템플릿에 맞게 바꿔주세요.
BESTSELLER_URL_TEMPLATE = "https://store.playstation.com/{locale}/category/3f772501-f6f8-49b7-abac-874a88ca4897"

MAX_RANK_TO_SCAN = 50  # 이 순위 밖이면 "50위 밖"으로 표기


@dataclass
class RankResult:
    country: str
    locale: str
    rank: int | None
    title_matched: str | None
    checked_at: str
    error: str | None = None


def normalize(text: str) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]", "", text or "").lower()


def fetch_titles(page, url: str) -> list[str]:
    page.goto(url, wait_until="networkidle", timeout=30000)
    # 무한 스크롤 로딩 대응: 아래로 몇 번 스크롤해서 카드 더 불러오기
    for _ in range(4):
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(500)

    # PS Store 상품 카드의 타이틀은 상품 링크의 aria-label / 텍스트에 들어있습니다.
    cards = page.locator("a[href*='/product/'], a[href*='/concept/']")
    count = min(cards.count(), MAX_RANK_TO_SCAN)
    titles = []
    for i in range(count):
        label = cards.nth(i).get_attribute("aria-label") or cards.nth(i).inner_text()
        if label:
            titles.append(label.strip())
    return titles


def find_rank(titles: list[str], aliases: list[str]) -> tuple[int | None, str | None]:
    targets = [normalize(a) for a in aliases if a.strip()]
    for idx, title in enumerate(titles, start=1):
        norm_title = normalize(title)
        if any(t in norm_title for t in targets):
            return idx, title
    return None, None


def run(aliases: list[str]) -> pd.DataFrame:
    results: list[RankResult] = []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        for country, locale in COUNTRIES.items():
            url = BESTSELLER_URL_TEMPLATE.format(locale=locale)
            try:
                titles = fetch_titles(page, url)
                rank, matched = find_rank(titles, aliases)
                results.append(RankResult(country, locale, rank, matched, now))
            except Exception as e:
                results.append(RankResult(country, locale, None, None, now, error=str(e)[:120]))

        browser.close()

    df = pd.DataFrame([r.__dict__ for r in results])
    df["rank_display"] = df["rank"].apply(lambda r: r if pd.notna(r) else f"{MAX_RANK_TO_SCAN}위 밖/미확인")
    df = df.sort_values(by="rank", na_position="last")
    return df


def main():
    parser = argparse.ArgumentParser(description="PS Store 국가별 게임 순위 추적")
    parser.add_argument(
        "game_names",
        help="추적할 게임 이름(들). 나라마다 타이틀이 다르므로 콤마로 여러 언어 병기 "
             "(예: '붉은사막,Crimson Desert,クリムゾン・デザート')",
    )
    parser.add_argument("--out", default=None, help="결과를 저장할 CSV 경로")
    args = parser.parse_args()

    aliases = [a.strip() for a in args.game_names.split(",")]
    df = run(aliases)

    view = df[["country", "rank_display", "title_matched", "checked_at", "error"]]
    try:
        print(view.to_markdown(index=False))
    except ImportError:
        print(view.to_string(index=False))

    if args.out:
        df.to_csv(args.out, index=False, encoding="utf-8-sig")
        print(f"\n저장됨: {args.out}")


if __name__ == "__main__":
    sys.exit(main())
