#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import re
import time

STEAMDB_CHARTS_URL = "https://steamdb.info/app/3321460/charts/"
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
HISTORY_FILE = "store_data_history.json"

def scrape_store_data():
    """SteamDB에서 Store data 스크래핑 (requests + BeautifulSoup 사용)"""
    print(f"📊 SteamDB Store data 수집 중...")
    print(f"   URL: {STEAMDB_CHARTS_URL}")
    
    try:
        # 더 정교한 헤더 설정으로 봇 차단 우회
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ko;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        
        print("   📥 페이지 다운로드 중...")
        session = requests.Session()
        
        # 재시도 로직 (최대 3번)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # 지수 백오프
                    print(f"   ⏳ {wait_time}초 대기 후 재시도 ({attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                
                response = session.get(STEAMDB_CHARTS_URL, headers=headers, timeout=30, allow_redirects=True)
                
                if response.status_code == 403:
                    print(f"   ⚠️  403 오류 발생 (시도 {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        print("   ❌ 모든 재시도 실패 - SteamDB가 접근을 차단했습니다.")
                        print("   💡 해결 방법: SteamDB API 또는 공식 데이터 소스 사용을 권장합니다.")
                        return None
                
                response.raise_for_status()
                print(f"   ✅ 페이지 다운로드 완료 ({len(response.content)} bytes)")
                break
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"   ⚠️  오류 발생: {e}")
                    continue
                else:
                    raise
        
        soup = BeautifulSoup(response.text, 'html.parser')
        store_data = {}
        
        # HTML 구조에 맞게 파싱
        # <ul class="app-chart-numbers"> 안에 데이터가 있음
        print("   🔍 데이터 파싱 중...")
        
        try:
            # app-chart-numbers 클래스 찾기
            chart_numbers = soup.find('ul', class_='app-chart-numbers')
            
            if chart_numbers:
                # 모든 li 태그 찾기
                list_items = chart_numbers.find_all('li')
                
                for li in list_items:
                    # strong 태그에서 숫자 추출
                    strong = li.find('strong')
                    # a 태그에서 텍스트 추출
                    link = li.find('a')
                    
                    if strong and link:
                        number_text = strong.get_text().strip()
                        link_text = link.get_text().strip().lower()
                        
                        # # 제거하고 숫자만 추출
                        if number_text.startswith('#'):
                            number = int(number_text[1:].replace(',', ''))
                        else:
                            number = int(number_text.replace(',', ''))
                        
                        # 링크 텍스트로 구분
                        if 'top sellers' in link_text:
                            store_data['top_sellers'] = number
                            print(f"   📈 Top Sellers: #{number}")
                        elif 'top wishlists' in link_text:
                            store_data['top_wishlists'] = number
                            print(f"   💚 Top Wishlists: #{number}")
                        elif 'wishlist activity' in link_text:
                            store_data['wishlist_activity'] = number
                            print(f"   🔥 Wishlist Activity: #{number}")
                        elif 'followers' in link_text:
                            store_data['followers'] = number
                            print(f"   👥 Followers: {number:,}")
            
            else:
                print("   ⚠️  app-chart-numbers 클래스를 찾을 수 없습니다.")
        
        except Exception as e:
            print(f"   ⚠️  구조 파싱 실패: {e}")
            import traceback
            traceback.print_exc()
        
        # 방법 2: 모든 텍스트에서 패턴 찾기 (백업)
        if not any(store_data.values()):
            print("   🔄 대체 파싱 방법 시도...")
            text = soup.get_text()
            
            # Top sellers
            sellers_match = re.search(r'#(\d+)\s+in top sellers', text, re.IGNORECASE)
            if sellers_match:
                store_data['top_sellers'] = int(sellers_match.group(1))
                print(f"   📈 Top Sellers: #{sellers_match.group(1)}")
            
            # Top wishlists
            wishlists_match = re.search(r'#(\d+)\s+in top wishlists', text, re.IGNORECASE)
            if wishlists_match:
                store_data['top_wishlists'] = int(wishlists_match.group(1))
                print(f"   💚 Top Wishlists: #{wishlists_match.group(1)}")
            
            # Wishlist activity
            activity_match = re.search(r'#(\d+)\s+in wishlist activity', text, re.IGNORECASE)
            if activity_match:
                store_data['wishlist_activity'] = int(activity_match.group(1))
                print(f"   🔥 Wishlist Activity: #{activity_match.group(1)}")
            
            # Followers
            followers_match = re.search(r'([\d,]+)\s+followers', text, re.IGNORECASE)
            if followers_match:
                followers_count = followers_match.group(1).replace(',', '')
                store_data['followers'] = int(followers_count)
                print(f"   👥 Followers: {followers_match.group(1)}")
        
        # 최소한 하나의 데이터라도 있는지 확인
        if any(v is not None for v in store_data.values()):
            print("   ✅ 데이터 수집 성공")
            return store_data
        else:
            print("   ⚠️  데이터를 찾을 수 없습니다. HTML 구조가 변경되었을 수 있습니다.")
            # 디버깅을 위해 HTML 일부 저장
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(response.text[:5000])
            print("   💾 debug_page.html에 페이지 일부 저장됨")
            return None
            
    except Exception as e:
        print(f"   ❌ 스크래핑 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

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
    
    # 한글 폰트 설정 (GitHub Actions 환경 고려)
    plt.rcParams['font.family'] = 'DejaVu Sans'
    
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
