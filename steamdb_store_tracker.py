#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crimson Desert Complete Store Tracker
- Steam 공식: Wishlist 순위 (검색 기반)
- Steambase: Followers 수
- Steam API: 리뷰 수
- SteamSpy: 소유자 수
"""

import json
import os
import time
import re
from datetime import datetime, date
import requests
from io import BytesIO

# Selenium (Wishlist 검색용)
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

STEAM_APP_ID = "3321460"
SEARCH_TERM = "crimson desert"

# URLs
STEAM_WISHLIST_URL = "https://store.steampowered.com/search/?filter=popularwishlist"
STEAMBASE_URL = f"https://steambase.io/games/crimson-desert/steam-charts"
STEAM_REVIEWS_URL = f"https://store.steampowered.com/appreviews/{STEAM_APP_ID}?json=1&language=all&purchase_type=all"
STEAMSPY_URL = f"https://steamspy.com/api.php?request=appdetails&appid={STEAM_APP_ID}"
STEAM_URL = f"https://store.steampowered.com/app/{STEAM_APP_ID}"
STEAMDB_URL = f"https://steamdb.info/app/{STEAM_APP_ID}/charts/"

PS_US_CATEGORY_URL = "https://store.playstation.com/en-us/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1"
XBOX_SEARCH_URL = "https://www.xbox.com/en-US/search?q=Crimson+Desert"
PS_BLOG_URL = "https://blog.playstation.com/tag/state-of-play/"

STATE_FILE = "store_state.json"
HISTORY_FILE = "steam_history.json"
MAX_PAGES = 3  # Wishlist 검색 최대 페이지

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

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
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

# ======================
# Steam Wishlist 순위
# ======================
def get_wishlist_rank():
    """Steam 공식 wishlist 검색에서 순위 찾기"""
    print("🔍 Steam Wishlist 순위 검색 중...")
    driver = setup_driver()
    
    try:
        rank = 0
        for page in range(MAX_PAGES):
            url = f"{STEAM_WISHLIST_URL}&page={page + 1}"
            driver.get(url)
            time.sleep(3)
            
            items = driver.find_elements(By.CSS_SELECTOR, "a.search_result_row")
            
            for item in items:
                rank += 1
                try:
                    title_elem = item.find_element(By.CSS_SELECTOR, ".title")
                    title = title_elem.text.lower()
                    
                    if SEARCH_TERM.lower() in title:
                        print(f"  ✅ Wishlist 순위: #{rank}")
                        return rank
                except:
                    continue
            
            print(f"  📄 페이지 {page + 1} 완료 (현재까지 {rank}개)")
        
        print(f"  ⚠️ {MAX_PAGES}페이지 내에서 찾지 못함")
        return None
        
    except Exception as e:
        print(f"  ❌ Wishlist 검색 오류: {e}")
        return None
    finally:
        driver.quit()

# ======================
# Steambase Followers
# ======================
def get_steambase_followers():
    """Steambase에서 Followers 수 크롤링"""
    print("👥 Steambase Followers 수집 중...")
    
    try:
        r = requests.get(STEAMBASE_URL, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            print(f"  ⚠️ Steambase 응답 실패: {r.status_code}")
            return None
        
        # "61,890 community hub followers" 패턴 찾기
        match = re.search(r'([\d,]+)\s+community hub followers', r.text, re.IGNORECASE)
        if match:
            followers_str = match.group(1).replace(',', '')
            followers = int(followers_str)
            print(f"  ✅ Followers: {followers:,}")
            return followers
        
        print(f"  ⚠️ Followers 텍스트를 찾을 수 없음")
        return None
        
    except Exception as e:
        print(f"  ❌ Steambase 오류: {e}")
        return None

# ======================
# Steam 리뷰 & SteamSpy
# ======================
def get_steam_review_stats():
    """Steam Reviews API에서 리뷰 수집"""
    print("📊 Steam Reviews 수집 중...")
    stats = {"review_count": None, "positive_reviews": None, "negative_reviews": None}
    
    try:
        r = requests.get(STEAM_REVIEWS_URL, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if 'query_summary' in data:
                summary = data['query_summary']
                stats["review_count"] = summary.get('total_reviews', 0)
                stats["positive_reviews"] = summary.get('total_positive', 0)
                stats["negative_reviews"] = summary.get('total_negative', 0)
                print(f"  ✅ 리뷰: {stats['review_count']:,} (👍 {stats['positive_reviews']:,} | 👎 {stats['negative_reviews']:,})")
    except Exception as e:
        print(f"  ⚠️ Steam Reviews 실패: {e}")
    
    return stats

def get_steamspy_stats():
    """SteamSpy에서 소유자/플레이어 수집"""
    print("📊 SteamSpy 데이터 수집 중...")
    stats = {"owners": None, "players_2weeks": None}
    
    try:
        r = requests.get(STEAMSPY_URL, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            stats["owners"] = data.get('owners', '0')
            stats["players_2weeks"] = data.get('players_2weeks', 0)
            print(f"  ✅ 소유자: {stats['owners']} | 플레이어(2주): {stats['players_2weeks']:,}")
    except Exception as e:
        print(f"  ⚠️ SteamSpy 실패: {e}")
    
    return stats

# ======================
# 상태/히스토리 관리
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
    entry = {"timestamp": datetime.utcnow().isoformat(), **stats}
    history.append(entry)
    save_history(history)
    return history

# ======================
# 그래프 생성
# ======================
def create_stats_graph(history):
    """Wishlist 순위, Followers, 리뷰 그래프"""
    if not HAS_MATPLOTLIB or len(history) < 2:
        return None
    
    valid_entries = [e for e in history if "timestamp" in e]
    if len(valid_entries) < 2:
        return None
    
    dates = [datetime.fromisoformat(e["timestamp"]) for e in valid_entries]
    
    # 2x2 서브플롯
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Crimson Desert - Steam Stats History', fontsize=16, fontweight='bold')
    
    # 1. Wishlist 순위
    wishlist_data = [(d, e.get("wishlist_rank")) for d, e in zip(dates, valid_entries) if e.get("wishlist_rank")]
    if wishlist_data:
        d, v = zip(*wishlist_data)
        ax1.plot(d, v, marker='o', linewidth=2, color='#4ECDC4')
        ax1.invert_yaxis()
        ax1.set_title('Wishlist Rank', fontweight='bold')
        ax1.set_ylabel('Rank')
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    
    # 2. Followers
    followers_data = [(d, e.get("followers")) for d, e in zip(dates, valid_entries) if e.get("followers")]
    if followers_data:
        d, v = zip(*followers_data)
        ax2.plot(d, v, marker='o', linewidth=2, color='#F38181')
        ax2.set_title('Steam Followers', fontweight='bold')
        ax2.set_ylabel('Count')
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
    
    # 3. 리뷰 수
    review_data = [(d, e.get("review_count")) for d, e in zip(dates, valid_entries) if e.get("review_count")]
    if review_data:
        d, v = zip(*review_data)
        ax3.plot(d, v, marker='o', linewidth=2, color='#1B2838')
        ax3.set_title('Total Reviews', fontweight='bold')
        ax3.set_ylabel('Count')
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
    
    # 4. 최근 플레이어
    players_data = [(d, e.get("players_2weeks")) for d, e in zip(dates, valid_entries) if e.get("players_2weeks")]
    if players_data:
        d, v = zip(*players_data)
        ax4.plot(d, v, marker='o', linewidth=2, color='#95E1D3')
        ax4.set_title('Players (Last 2 Weeks)', fontweight='bold')
        ax4.set_ylabel('Count')
        ax4.grid(True, alpha=0.3)
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
    
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
    return f"D-{diff}" if diff > 0 else "D-DAY" if diff == 0 else f"D+{abs(diff)}"

def detect_xbox_preorder():
    try:
        r = requests.get(XBOX_SEARCH_URL, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return False
        return any(k in r.text.lower() for k in ["pre-order", "preorder", "buy", "purchase"])
    except:
        return False

def detect_sop():
    try:
        r = requests.get(PS_BLOG_URL, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return False
        t = r.text.lower()
        if "state of play" not in t:
            return False
        return any(k in t for k in ["announce", "broadcast", "watch live", "returns"])
    except:
        return False

def send_discord(msg, embed=None, file_data=None, filename=None):
    if not DISCORD_WEBHOOK:
        return
    
    files = {"file": (filename, file_data, "image/png")} if file_data and filename else None
    payload = {"content": msg}
    if embed:
        payload["embeds"] = [embed]
    
    if files:
        requests.post(DISCORD_WEBHOOK, data={"payload_json": json.dumps(payload)}, files=files, timeout=10)
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
    
    # 데이터 수집
    wishlist_rank = get_wishlist_rank()
    followers = get_steambase_followers()
    review_stats = get_steam_review_stats()
    steamspy_stats = get_steamspy_stats()
    
    # 통합 stats
    all_stats = {
        "wishlist_rank": wishlist_rank,
        "followers": followers,
        **review_stats,
        **steamspy_stats
    }
    
    if any(v for v in all_stats.values() if v):
        history = add_history_entry(all_stats)
        print(f"✅ 히스토리 저장 완료 (총 {len(history)}개)")
    
    # Xbox / SOP
    xbox_open = detect_xbox_preorder()
    if xbox_open and not state["xbox_preorder_open"]:
        alerts.append("🟢 **Xbox 예구 오픈**")
        state["xbox_preorder_open"] = True
    
    sop_open = detect_sop()
    if sop_open and not state["sop_detected"]:
        alerts.append("🎥 **State of Play 감지**")
        state["sop_detected"] = True
    
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    dday = calc_dday()
    
    # 그래프
    history = load_history()
    graph_buffer = create_stats_graph(history)
    
    # Discord Embed
    stats_text = "📊 **Steam Stats**\n"
    if wishlist_rank:
        stats_text += f"⭐ Wishlist: **#{wishlist_rank}**\n"
    if followers:
        stats_text += f"👥 Followers: **{followers:,}**\n"
    if review_stats["review_count"]:
        stats_text += f"📝 Reviews: **{review_stats['review_count']:,}**\n"
    if steamspy_stats["owners"]:
        stats_text += f"🎮 Owners: **{steamspy_stats['owners']}**\n"
    
    embed = {
        "title": "📊 Crimson Desert Complete Tracker",
        "description": (
            f"📅 **출시일**: 2026-03-19 ({dday})\n\n"
            f"{stats_text}\n"
            f"📈 **총 {len(history)}개 히스토리**\n\n"
            f"🔗 [Steam]({STEAM_URL}) | [SteamDB]({STEAMDB_URL}) | [Steambase]({STEAMBASE_URL})\n\n"
            f"🟢 Steam: 예구 오픈 | 🟢 PS: 예구 오픈 | 🟢 Xbox: 예구 오픈\n"
            f"🎥 SOP: {'감지됨' if state['sop_detected'] else '미감지'}\n\n"
            f"_Steam + Steambase · {now}_"
        ),
        "color": 0x1B2838
    }
    
    if graph_buffer:
        embed["image"] = {"url": "attachment://stats_graph.png"}
    
    if alerts:
        send_discord("🚨 **변경 감지**\n" + "\n".join(alerts), embed, graph_buffer, "stats_graph.png" if graph_buffer else None)
    else:
        send_discord("🔔 **상태 업데이트**", embed, graph_buffer, "stats_graph.png" if graph_buffer else None)
    
    save_state(state)
    print("✅ 완료!")

if __name__ == "__main__":
    main()
