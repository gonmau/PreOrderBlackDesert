#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
실용적인 해결책: 수동 데이터 입력 방식

사용 방법:
1. SteamDB에서 직접 확인한 데이터를 manual_data.json에 작성
2. Git에 커밋하면 자동으로 Discord에 전송 및 그래프 생성
"""

import os
import json
import requests
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
HISTORY_FILE = "store_data_history.json"
MANUAL_DATA_FILE = "manual_data.json"

def get_manual_data():
    """manual_data.json에서 최신 데이터 읽기"""
    print("📊 수동 입력 데이터 읽기 중...")
    
    if not os.path.exists(MANUAL_DATA_FILE):
        print(f"   ❌ {MANUAL_DATA_FILE} 파일이 없습니다.")
        print("\n   📝 다음 내용으로 manual_data.json 파일을 만들어주세요:")
        print("""
{
  "top_sellers": 408,
  "top_wishlists": 25,
  "wishlist_activity": 36,
  "followers": 61663,
  "updated_at": "2026-01-18 15:30"
}
""")
        return None
    
    try:
        with open(MANUAL_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        store_data = {
            'top_sellers': data.get('top_sellers'),
            'top_wishlists': data.get('top_wishlists'),
            'wishlist_activity': data.get('wishlist_activity'),
            'followers': data.get('followers'),
        }
        
        # 데이터 검증
        if not any(v is not None for v in store_data.values()):
            print("   ⚠️  유효한 데이터가 없습니다.")
            return None
        
        print(f"   ✅ {MANUAL_DATA_FILE}에서 데이터 로드")
        updated_at = data.get('updated_at', 'Unknown')
        print(f"   📅 업데이트 시간: {updated_at}")
        
        for key, label in [
            ('top_sellers', '📈 Top Sellers'),
            ('top_wishlists', '💚 Top Wishlists'),
            ('wishlist_activity', '🔥 Wishlist Activity'),
            ('followers', '👥 Followers')
        ]:
            value = store_data.get(key)
            if value is not None:
                if key == 'followers':
                    print(f"   {label}: {value:,}")
                else:
                    print(f"   {label}: #{value}")
        
        return store_data
        
    except json.JSONDecodeError as e:
        print(f"   ❌ JSON 파싱 오류: {e}")
        return None
    except Exception as e:
        print(f"   ❌ 파일 읽기 오류: {e}")
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
    
    # 중복 방지: 마지막 데이터와 동일하면 저장 안 함
    if history:
        last_data = history[-1].get('data', {})
        if last_data == store_data:
            print("   ℹ️  이전 데이터와 동일하여 저장하지 않습니다.")
            return history
    
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
    
    plt.rcParams['font.family'] = 'DejaVu Sans'
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Crimson Desert - SteamDB Store Data Tracking', fontsize=16, fontweight='bold')
    
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
    
    # Followers
    if any(x is not None for x in followers):
        ax4.plot(timestamps, followers, marker='o', linewidth=2, markersize=6, color='#d62728')
        ax4.set_title('Followers Count', fontsize=12, fontweight='bold')
        ax4.set_ylabel('Followers', fontsize=10)
        ax4.grid(True, alpha=0.3)
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right')
        ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
    
    plt.tight_layout()
    
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
                    diff = curr - prev
                    if diff > 0:
                        changes.append(f"{label}: +{diff:,} ⬆️")
                    elif diff < 0:
                        changes.append(f"{label}: {diff:,} ⬇️")
                else:
                    diff = curr - prev
                    if diff < 0:
                        changes.append(f"{label}: {abs(diff)} 상승 ⬆️")
                    elif diff > 0:
                        changes.append(f"{label}: {diff} 하락 ⬇️")
        
        if changes:
            current_data += "\n**📈 변화:**\n" + "\n".join(changes)
    
    current_data += "\n\n📝 *수동 입력 데이터*"
    
    embed = {
        "title": "🎮 Crimson Desert - SteamDB Store Tracker",
        "description": current_data,
        "color": 0x00D9FF,
        "url": "https://steamdb.info/app/3321460/charts/",
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": f"총 {len(history)}회 추적"}
    }
    
    try:
        files = {}
        if graph_buffer:
            files = {'file': ('chart.png', graph_buffer, 'image/png')}
            embed["image"] = {"url": "attachment://chart.png"}
        
        payload = {"embeds": [embed]}
        
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
    except Exception as e:
        print(f"   ❌ Discord 전송 오류: {e}")

def main():
    print("=" * 70)
    print("🎮 Crimson Desert - Manual Data Tracker")
    print("=" * 70)
    print()
    
    store_data = get_manual_data()
    
    if store_data is None or not any(store_data.values()):
        print("\n❌ 데이터 없음")
        print("\n💡 해결 방법:")
        print("   1. SteamDB에서 직접 데이터 확인")
        print("   2. manual_data.json 파일 생성/수정")
        print("   3. 이 스크립트 다시 실행")
        return
    
    print()
    print("=" * 70)
    print("💾 데이터 저장")
    print("=" * 70)
    
    history = save_history(store_data)
    
    print()
    print("=" * 70)
    print("📊 그래프 생성")
    print("=" * 70)
    
    graph_buffer = create_graph(history)
    
    print()
    print("=" * 70)
    print("📤 Discord 전송")
    print("=" * 70)
    
    send_discord(store_data, history, graph_buffer)
    
    print()
    print("=" * 70)
    print("✅ 모든 작업 완료!")
    print("=" * 70)

if __name__ == "__main__":
    main()
