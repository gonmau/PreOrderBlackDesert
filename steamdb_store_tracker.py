#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crimson Desert Complete Store Tracker
- SteamDB Charts: wishlist 순위, wishlist activity, top sellers, followers
- Xbox: 검색 기반 예구 오픈
- SOP(State of Play): PlayStation Blog 감지
- 모든 데이터 히스토리 저장 및 그래프 생성
"""

import json
import os
import time
from datetime import datetime, date
import requests
from io import BytesIO

# Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# ======================
# 환경 설정
# ======================
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

RELEASE_DATE = date(2026, 3, 19)

STEAMDB_URL = "https://steamdb.info/app/3321460/charts/"
STEAM_URL = "https://store.steampowered.com/app/3321460"

PS_US_CATEGORY_URL = (
    "https://store.playstation.com/en-us/category/"
    "3bf499d7-7acf-4931-97dd-2667494ee2c9/1"
)

XBOX_SEARCH_URL = "https://www.xbox.com/en-US/search?q=Crimson+Desert"
PS_BLOG_URL = "https://blog.playstation.com/tag/state-of-play/"

STATE_FILE = "store_state.json"
HISTORY_FILE = "steam_history.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ======================
# Selenium 설정
# ======================
def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

# ======================
# SteamDB 데이터 수집
# ======================
def get_steamdb_stats():
    """SteamDB Charts에서 모든 지표 수집"""
    print("🎮 SteamDB Charts 데이터 수집 중...")
    
    driver = setup_driver()
    stats = {
        "top_sellers_rank": None,
        "wishlist_rank": None,
        "wishlist_activity_rank": None,
        "followers": None
    }
    
    try:
        driver.get(STEAMDB_URL)
        print(f"  ⏳ 페이지 로딩 및 JavaScript 렌더링 대기...")
        
        # 명시적 대기: ul.app-chart-numbers가 나타날 때까지 최대 20초 대기
        wait = WebDriverWait(driver, 20)
        
        try:
            chart_list = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ul.app-chart-numbers"))
            )
            print(f"  ✅ app-chart-numbers 발견!")
            
            list_items = chart_list.find_elements(By.TAG_NAME, "li")
            print(f"  🔍 발견된 차트 항목: {len(list_items)}개")
            
            for idx, item in enumerate(list_items):
                try:
                    # <strong> 태그에서 숫자 추출
                    strong = item.find_element(By.TAG_NAME, "strong")
                    number_text = strong.text.strip().replace('#', '').replace(',', '')
                    
                    # 전체 텍스트와 HTML 확인
                    full_text = item.text.lower()
                    inner_html = item.get_attribute('innerHTML').lower()
                    
                    print(f"  📝 항목 {idx+1}: {item.text[:80]}")
                    
                    if "in top sellers" in full_text or "globaltopsellers" in inner_html:
                        stats["top_sellers_rank"] = int(number_text)
                        print(f"    ✅ Top Sellers: #{stats['top_sellers_rank']}")
                    
                    elif "in top wishlists" in full_text or "mostwished" in inner_html:
                        stats["wishlist_rank"] = int(number_text)
                        print(f"    ✅ Wishlist: #{stats['wishlist_rank']}")
                    
                    elif "in wishlist activity" in full_text or "wishlistactivity" in inner_html:
                        stats["wishlist_activity_rank"] = int(number_text)
                        print(f"    ✅ Wishlist Activity: #{stats['wishlist_activity_rank']}")
                    
                    elif "followers" in full_text or "mostfollowed" in inner_html:
                        stats["followers"] = int(number_text)
                        print(f"    ✅ Followers: {stats['followers']:,}")
                
                except Exception as e:
                    print(f"    ⚠️ 항목 {idx+1} 파싱 실패: {e}")
                    continue
        
        except Exception as e:
            print(f"  ❌ app-chart-numbers 타임아웃: {e}")
            print(f"  ℹ️ 페이지 소스 길이: {len(driver.page_source)} bytes")
            
            # 페이지 소스에서 직접 찾기 시도
            page_source = driver.page_source
            if "app-chart-numbers" in page_source:
                print(f"  ⚠️ app-chart-numbers는 소스에 있지만 렌더링 안됨")
            else:
                print(f"  ⚠️ app-chart-numbers가 페이지 소스에 없음")
        
        # 스크린샷 저장
        try:
            screenshot_path = "steamdb_debug.png"
            driver.save_screenshot(screenshot_path)
            print(f"  📸 스크린샷 저장: {screenshot_path}")
        except Exception as e:
            print(f"  ⚠️ 스크린샷 실패: {e}")
        
    except Exception as e:
        print(f"  ❌ SteamDB 수집 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
    
    print(f"  📊 최종 수집 결과: {stats}")
    return stats

# ======================
# 상태 관리
# ======================
def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def ensure_key(state, key, default):
    if key not in state:
        state[key] = default

# ======================
# 히스토리 관리
# ======================
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def add_history_entry(stats):
    history = load_history()
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        **stats
    }
    history.append(entry)
    save_history(history)
    return history

# ======================
# 그래프 생성
# ======================
def create_stats_graph(history):
    """모든 지표를 한 그래프에 표시"""
    if not HAS_MATPLOTLIB or len(history) < 2:
        return None
    
    # 유효한 데이터만 필터링
    valid_entries = [e for e in history if "timestamp" in e]
    if len(valid_entries) < 2:
        return None
    
    dates = [datetime.fromisoformat(e["timestamp"]) for e in valid_entries]
    
    # 4개의 서브플롯 생성
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Crimson Desert - SteamDB Stats History', fontsize=16, fontweight='bold')
    
    # 1. Top Sellers Rank
    sellers_data = [(d, e.get("top_sellers_rank")) for d, e in zip(dates, valid_entries) 
                    if e.get("top_sellers_rank")]
    if sellers_data:
        d, v = zip(*sellers_data)
        ax1.plot(d, v, marker='o', linewidth=2, color='#FF6B6B', label='Top Sellers')
        ax1.invert_yaxis()
        ax1.set_title('Top Sellers Rank', fontweight='bold')
        ax1.set_ylabel('Rank')
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    
    # 2. Wishlist Rank
    wishlist_data = [(d, e.get("wishlist_rank")) for d, e in zip(dates, valid_entries)
                     if e.get("wishlist_rank")]
    if wishlist_data:
        d, v = zip(*wishlist_data)
        ax2.plot(d, v, marker='o', linewidth=2, color='#4ECDC4', label='Wishlist')
        ax2.invert_yaxis()
        ax2.set_title('Wishlist Rank', fontweight='bold')
        ax2.set_ylabel('Rank')
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    
    # 3. Wishlist Activity Rank
    activity_data = [(d, e.get("wishlist_activity_rank")) for d, e in zip(dates, valid_entries)
                     if e.get("wishlist_activity_rank")]
    if activity_data:
        d, v = zip(*activity_data)
        ax3.plot(d, v, marker='o', linewidth=2, color='#95E1D3', label='Activity')
        ax3.invert_yaxis()
        ax3.set_title('Wishlist Activity Rank', fontweight='bold')
        ax3.set_ylabel('Rank')
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    
    # 4. Followers
    followers_data = [(d, e.get("followers")) for d, e in zip(dates, valid_entries)
                      if e.get("followers")]
    if followers_data:
        d, v = zip(*followers_data)
        ax4.plot(d, v, marker='o', linewidth=2, color='#F38181', label='Followers')
        ax4.set_title('Followers', fontweight='bold')
        ax4.set_ylabel('Count')
        ax4.grid(True, alpha=0.3)
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
    
    # 날짜 레이블 회전
    for ax in [ax1, ax2, ax3, ax4]:
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf

# ======================
# 유틸
# ======================
def calc_dday():
    today = date.today()
    diff = (RELEASE_DATE - today).days
    if diff > 0:
        return f"D-{diff}"
    if diff == 0:
        return "D-DAY"
    return f"D+{abs(diff)}"

# ======================
# Xbox 예구 감지
# ======================
def detect_xbox_preorder():
    try:
        r = requests.get(XBOX_SEARCH_URL, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return False
        text = r.text.lower()
        return any(k in text for k in ["pre-order", "preorder", "buy", "purchase"])
    except Exception:
        return False

# ======================
# SOP 감지
# ======================
def detect_sop():
    try:
        r = requests.get(PS_BLOG_URL, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return False
        t = r.text.lower()
        if "state of play" not in t:
            return False
        return any(k in t for k in ["announce", "broadcast", "watch live", "returns"])
    except Exception:
        return False

# ======================
# Discord
# ======================
def send_discord(msg, embed=None, file_data=None, filename=None):
    if not DISCORD_WEBHOOK:
        return
    
    files = None
    if file_data and filename:
        files = {"file": (filename, file_data, "image/png")}
    
    payload = {"content": msg}
    if embed:
        payload["embeds"] = [embed]
    
    if files:
        requests.post(
            DISCORD_WEBHOOK,
            data={"payload_json": json.dumps(payload)},
            files=files,
            timeout=10
        )
    else:
        requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)

# ======================
# 메인
# ======================
def main():
    print("=" * 60)
    print("🎮 Crimson Desert Complete Tracker")
    print("=" * 60)
    
    state = load_state()
    ensure_key(state, "xbox_preorder_open", False)
    ensure_key(state, "sop_detected", False)

    alerts = []

    # SteamDB 데이터 수집
    steam_stats = get_steamdb_stats()
    if any(steam_stats.values()):
        history = add_history_entry(steam_stats)
        print(f"✅ 히스토리 저장 완료 (총 {len(history)}개)")

    # Xbox
    xbox_open = detect_xbox_preorder()
    if xbox_open and not state["xbox_preorder_open"]:
        alerts.append("🟢 **Xbox 예구 오픈 (검색 기반)**")
        state["xbox_preorder_open"] = True

    # SOP
    sop_open = detect_sop()
    if sop_open and not state["sop_detected"]:
        alerts.append("🎥 **State of Play 행사 감지**")
        state["sop_detected"] = True

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    dday = calc_dday()

    # 그래프 생성
    history = load_history()
    graph_buffer = create_stats_graph(history)

    # 통계 텍스트
    stats_text = "📊 **SteamDB Stats**\n"
    if steam_stats["top_sellers_rank"]:
        stats_text += f"🔥 Top Sellers: **#{steam_stats['top_sellers_rank']}**\n"
    if steam_stats["wishlist_rank"]:
        stats_text += f"⭐ Wishlist: **#{steam_stats['wishlist_rank']}**\n"
    if steam_stats["wishlist_activity_rank"]:
        stats_text += f"📈 Activity: **#{steam_stats['wishlist_activity_rank']}**\n"
    if steam_stats["followers"]:
        stats_text += f"👥 Followers: **{steam_stats['followers']:,}**\n"

    embed = {
        "title": "📊 Crimson Desert Complete Tracker",
        "description": (
            f"📅 **출시일**: 2026-03-19 ({dday})\n\n"
            f"{stats_text}\n"
            f"📈 **총 {len(history)}개 히스토리 기록**\n\n"
            f"🔗 **플랫폼 바로가기**\n"
            f"[SteamDB Charts]({STEAMDB_URL}) | "
            f"[PlayStation US]({PS_US_CATEGORY_URL}) | "
            f"[Xbox]({XBOX_SEARCH_URL}) | "
            f"[Steam]({STEAM_URL})\n\n"
            f"🟢 **Steam**: 예구 오픈\n"
            f"🟢 **PlayStation US**: 예구 오픈\n"
            f"🟢 **Xbox**: 예구 오픈 (검색 기반)\n"
            f"🎥 [**SOP: {'감지됨' if state['sop_detected'] else '미감지'}**]({PS_BLOG_URL})\n\n"
            f"자동 추적 · {now}"
        ),
        "color": 0x1B2838
    }

    if graph_buffer:
        embed["image"] = {"url": "attachment://stats_graph.png"}

    if alerts:
        send_discord(
            "🚨 **변경 감지 발생**\n" + "\n".join(alerts),
            embed,
            graph_buffer,
            "stats_graph.png" if graph_buffer else None
        )
    else:
        send_discord(
            "🔔 **Crimson Desert 상태 업데이트**",
            embed,
            graph_buffer,
            "stats_graph.png" if graph_buffer else None
        )

    save_state(state)
    print("✅ 완료!")

if __name__ == "__main__":
    main()
