#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import base64

STEAMDB_CHARTS_URL = "https://steamdb.info/app/3321460/charts/"
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
HISTORY_FILE = "store_data_history.json"

def setup_driver():
    """Selenium 드라이버 설정"""
    print("🔧 Chrome 드라이버 설정 중...")
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def scrape_store_data():
    """SteamDB에서 Store data 스크래핑"""
    print(f"📊 SteamDB Store data 수집 중...")
    print(f"   URL: {STEAMDB_CHARTS_URL}")
    
    driver = None
    try:
        driver = setup_driver()
        driver.get(STEAMDB_CHARTS_URL)
        
        # 페이지 로딩 대기
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "app-data")))
        
        print("   ✅ 페이지 로딩 완료")
        
        # Store data 섹션 찾기
        store_data = {}
        
        try:
            # in top sellers
            sellers_elem = driver.find_element(By.XPATH, "//a[contains(text(), 'in top sellers')]")
            sellers_rank = sellers_elem.find_element(By.XPATH, "./preceding-sibling::*[1]").text.strip('#')
            store_data['top_sellers'] = int(sellers_rank)
            print(f"   📈 Top Sellers: #{sellers_rank}")
        except:
            print("   ⚠️  Top Sellers 정보 없음")
            store_data['top_sellers'] = None
        
        try:
            # in top wishlists
            wishlists_elem = driver.find_element(By.XPATH, "//a[contains(text(), 'in top wishlists')]")
            wishlists_rank = wishlists_elem.find_element(By.XPATH, "./preceding-sibling::*[1]").text.strip('#')
            store_data['top_wishlists'] = int(wishlists_rank)
            print(f"   💚 Top Wishlists: #{wishlists_rank}")
        except:
            print("   ⚠️  Top Wishlists 정보 없음")
            store_data['top_wishlists'] = None
        
        try:
            # in wishlist activity
            activity_elem = driver.find_element(By.XPATH, "//a[contains(text(), 'in wishlist activity')]")
            activity_rank = activity_elem.find_element(By.XPATH, "./preceding-sibling::*[1]").text.strip('#')
            store_data['wishlist_activity'] = int(activity_rank)
            print(f"   🔥 Wishlist Activity: #{activity_rank}")
        except:
            print("   ⚠️  Wishlist Activity 정보 없음")
            store_data['wishlist_activity'] = None
        
        try:
            # followers
            followers_elem = driver.find_element(By.XPATH, "//a[contains(text(), 'followers')]")
            followers_count = followers_elem.find_element(By.XPATH, "./preceding-sibling::*[1]").text.replace(',', '')
            store_data['followers'] = int(followers_count)
            print(f"   👥 Followers: {followers_count}")
        except:
            print("   ⚠️  Followers 정보 없음")
            store_data['followers'] = None
        
        return store_data
        
    except Exception as e:
        print(f"   ❌ 스크래핑 오류: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if driver:
            driver.quit()
            print("   🔚 드라이버 종료")

def load_history():
    """저장된 히스토리 로드"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(store_data):
    """히스토리에 데이터 추가 및 저장"""
    history = load_history()
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "data": store_data
    }
    
    history.append(entry)
    
    # 최근 1000개만 유지
    if len(history) > 1000:
        history = history[-1000:]
    
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    print(f"✅ {HISTORY_FILE} 저장 완료 (총 {len(history)}개 항목)")
    return history

def create_graph(history):
    """순위 변화 그래프 생성"""
    print("📈 그래프 생성 중...")
    
    if len(history) < 2:
        print("   ⚠️  데이터가 부족하여 그래프를 생성하지 않습니다.")
        return None
    
    # 최근 30개 데이터만 사용
    recent_history = history[-30:]
    
    timestamps = []
    top_sellers = []
    top_wishlists = []
    wishlist_activity = []
    followers = []
    
    for entry in recent_history:
        try:
            dt = datetime.fromisoformat(entry['timestamp'])
            timestamps.append(dt)
            
            data = entry.get('data', {})
            top_sellers.append(data.get('top_sellers'))
            top_wishlists.append(data.get('top_wishlists'))
            wishlist_activity.append(data.get('wishlist_activity'))
            followers.append(data.get('followers'))
        except:
            continue
    
    if not timestamps:
        print("   ⚠️  유효한 데이터가 없습니다.")
        return None
    
    # 2x2 서브플롯 생성
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Crimson Desert - SteamDB Store Data Tracking', fontsize=16, fontweight='bold')
    
    # 순위는 낮을수록 좋으므로 y축 반전
    # Top Sellers
    if any(x is not None for x in top_sellers):
        ax1.plot(timestamps, top_sellers, marker='o', linewidth=2, markersize=6, color='#1f77b4')
        ax1.set_title('Top Sellers Rank', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Rank', fontsize=10)
        ax1.invert_yaxis()
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Top Wishlists
    if any(x is not None for x in top_wishlists):
        ax2.plot(timestamps, top_wishlists, marker='o', linewidth=2, markersize=6, color='#2ca02c')
        ax2.set_title('Top Wishlists Rank', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Rank', fontsize=10)
        ax2.invert_yaxis()
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Wishlist Activity
    if any(x is not None for x in wishlist_activity):
        ax3.plot(timestamps, wishlist_activity, marker='o', linewidth=2, markersize=6, color='#ff7f0e')
        ax3.set_title('Wishlist Activity Rank', fontsize=12, fontweight='bold')
        ax3.set_ylabel('Rank', fontsize=10)
        ax3.invert_yaxis()
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Followers (절대값이므로 y축 반전 안함)
    if any(x is not None for x in followers):
        ax4.plot(timestamps, followers, marker='o', linewidth=2, markersize=6, color='#d62728')
        ax4.set_title('Followers Count', fontsize=12, fontweight='bold')
        ax4.set_ylabel('Followers', fontsize=10)
        ax4.grid(True, alpha=0.3)
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # 팔로워 수에 천 단위 구분 추가
        ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
    
    plt.tight_layout()
    
    # 이미지를 바이트로 변환
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    print("   ✅ 그래프 생성 완료")
    return buf

def send_discord(store_data, history, graph_buffer):
    """Discord로 결과 전송"""
    if not DISCORD_WEBHOOK:
        print("⚠️  DISCORD_WEBHOOK 환경변수가 설정되지 않았습니다.")
        return
    
    print("📤 Discord 전송 중...")
    
    # 현재 데이터
    current_data = f"""
**📊 현재 Store Data** (KST {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

🏆 Top Sellers: **#{store_data.get('top_sellers', 'N/A')}**
💚 Top Wishlists: **#{store_data.get('top_wishlists', 'N/A')}**
🔥 Wishlist Activity: **#{store_data.get('wishlist_activity', 'N/A')}**
👥 Followers: **{store_data.get('followers', 'N/A'):,}** 명
"""
    
    # 이전 데이터와 비교
    if len(history) >= 2:
        prev_data = history[-2]['data']
        changes = []
        
        for key, label in [
            ('top_sellers', '🏆 Top Sellers'),
            ('top_wishlists', '💚 Top Wishlists'),
            ('wishlist_activity', '🔥 Wishlist Activity'),
            ('followers', '👥 Followers')
        ]:
            curr = store_data.get(key)
            prev = prev_data.get(key)
            
            if curr is not None and prev is not None:
                if key == 'followers':
                    # 팔로워는 증가가 긍정적
                    diff = curr - prev
                    if diff > 0:
                        changes.append(f"{label}: +{diff:,} ⬆️")
                    elif diff < 0:
                        changes.append(f"{label}: {diff:,} ⬇️")
                else:
                    # 순위는 감소(숫자가 작아짐)가 긍정적
                    diff = curr - prev
                    if diff < 0:
                        changes.append(f"{label}: {abs(diff)} 상승 ⬆️")
                    elif diff > 0:
                        changes.append(f"{label}: {diff} 하락 ⬇️")
        
        if changes:
            current_data += "\n**📈 변화:**\n" + "\n".join(changes)
    
    embed = {
        "title": "🎮 Crimson Desert - SteamDB Store Tracker",
        "description": current_data,
        "color": 0x5865F2,
        "url": STEAMDB_CHARTS_URL,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": f"총 {len(history)}회 추적 | 다음 업데이트: 12시간 후"}
    }
    
    try:
        # 그래프가 있으면 이미지로 첨부
        files = {}
        if graph_buffer:
            files = {
                'file': ('chart.png', graph_buffer, 'image/png')
            }
            embed["image"] = {"url": "attachment://chart.png"}
        
        payload = {
            "embeds": [embed]
        }
        
        response = requests.post(
            DISCORD_WEBHOOK,
            json=payload if not files else None,
            data={'payload_json': json.dumps(payload)} if files else None,
            files=files
        )
        
        if response.status_code in [200, 204]:
            print("   ✅ Discord 전송 성공!")
        else:
            print(f"   ⚠️  Discord 전송 실패: {response.status_code}")
            print(f"   응답: {response.text}")
    
    except Exception as e:
        print(f"   ❌ Discord 전송 오류: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("=" * 70)
    print("🎮 Crimson Desert - SteamDB Store Data Tracker")
    print("=" * 70)
    print()
    
    # 데이터 수집
    store_data = scrape_store_data()
    
    if store_data is None:
        print("\n❌ 데이터 수집 실패")
        return
    
    print()
    print("=" * 70)
    print("💾 데이터 저장")
    print("=" * 70)
    
    # 히스토리 저장
    history = save_history(store_data)
    
    print()
    print("=" * 70)
    print("📊 그래프 생성")
    print("=" * 70)
    
    # 그래프 생성
    graph_buffer = create_graph(history)
    
    print()
    print("=" * 70)
    print("📤 Discord 전송")
    print("=" * 70)
    
    # Discord 전송
    send_discord(store_data, history, graph_buffer)
    
    print()
    print("=" * 70)
    print("✅ 모든 작업 완료!")
    print("=" * 70)

if __name__ == "__main__":
    main()
