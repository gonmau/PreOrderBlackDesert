#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
from datetime import datetime
from io import BytesIO

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

# YouTube Data API v3 키 (GitHub Secrets에서 가져옴)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# Crimson Desert 공식 영상 ID들
VIDEO_IDS = {
    # Preview #2
    "Preview #2 - PS": "pG_lpBoGK1c",
    "Preview #2 - Crimson Desert": "srQ-NtGNBpY",
    "Preview #2 - IGN": "cNT1NrYvwPE",
    
    # Preview #1
    "Preview #1 - PS": "Li9Cxhxw8WA",
    "Preview #1 - Crimson Desert": "MfZCV8EySac",
    "Preview #1 - IGN": "RbGbqVIXbMI",
}

# 그래프에 표시할 영상 그룹
PREVIEW_2_VIDEOS = [
    "Preview #2 - PS",
    "Preview #2 - Crimson Desert", 
    "Preview #2 - IGN",
]

PREVIEW_1_VIDEOS = [
    "Preview #1 - PS",
    "Preview #1 - Crimson Desert",
    "Preview #1 - IGN",
]

# =============================================================================
# 함수들
# =============================================================================

def get_video_stats(video_id):
    """YouTube API로 조회수, 좋아요 수 가져오기"""
    if not YOUTUBE_API_KEY:
        print("⚠️  YOUTUBE_API_KEY 환경변수 없음")
        return None
    
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "statistics,snippet",
        "id": video_id,
        "key": YOUTUBE_API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("items"):
            print(f"⚠️  영상을 찾을 수 없음: {video_id}")
            return None
        
        item = data["items"][0]
        stats = item["statistics"]
        snippet = item["snippet"]
        
        return {
            "title": snippet["title"],
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0))
        }
    except Exception as e:
        print(f"❌ YouTube API 오류: {e}")
        return None

def load_history():
    """기존 히스토리 데이터 로드"""
    history_file = "youtube_history.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(stats_all):
    """히스토리 저장"""
    history = load_history()
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "videos": stats_all
    }
    
    history.append(entry)
    
    # 모든 히스토리 유지 (제한 없음)
    
    with open("youtube_history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    print("✅ youtube_history.json 저장 완료")

def create_views_graph():
    """조회수 변화 그래프 생성 (Preview #1과 #2 각각)"""
    if not HAS_MATPLOTLIB:
        print("⚠️  matplotlib 없음 - 그래프 생략")
        return None
    
    history = load_history()
    if len(history) < 2:
        print("⚠️  데이터 부족 (2개 이상 필요) - 그래프 생략")
        return None
    
    # 채널별 스타일 정의
    CHANNEL_STYLES = {
        "PS": {
            "color": "#0070CC",  # PlayStation 블루
            "marker": "o",
            "linewidth": 3,
            "markersize": 8
        },
        "Crimson Desert": {
            "color": "#DC143C",  # Crimson 레드
            "marker": "s",
            "linewidth": 2.5,
            "markersize": 7
        },
        "IGN": {
            "color": "#FF6B00",  # IGN 오렌지
            "marker": "^",
            "linewidth": 2.5,
            "markersize": 7
        },
        "Epic Games": {
            "color": "#313131",  # Epic Games 다크그레이
            "marker": "D",
            "linewidth": 2.5,
            "markersize": 6
        }
    }
    
    # 데이터 파싱 - Preview #2
    timestamps_p2 = []
    views_data_p2 = {name: [] for name in PREVIEW_2_VIDEOS}
    
    # 데이터 파싱 - Preview #1
    timestamps_p1 = []
    views_data_p1 = {name: [] for name in PREVIEW_1_VIDEOS}
    
    for entry in history:
        try:
            dt = datetime.fromisoformat(entry['timestamp'])
            
            # Preview #2 데이터 수집
            has_p2_data = False
            for name in PREVIEW_2_VIDEOS:
                video_data = entry['videos'].get(name, {})
                if video_data:
                    has_p2_data = True
                    break
            
            if has_p2_data:
                timestamps_p2.append(dt)
                for name in PREVIEW_2_VIDEOS:
                    video_data = entry['videos'].get(name, {})
                    views = video_data.get('views', 0) if video_data else 0
                    views_data_p2[name].append(views)
            
            # Preview #1 데이터 수집
            has_p1_data = False
            for name in PREVIEW_1_VIDEOS:
                video_data = entry['videos'].get(name, {})
                if video_data:
                    has_p1_data = True
                    break
            
            if has_p1_data:
                timestamps_p1.append(dt)
                for name in PREVIEW_1_VIDEOS:
                    video_data = entry['videos'].get(name, {})
                    views = video_data.get('views', 0) if video_data else 0
                    views_data_p1[name].append(views)
        except:
            continue
    
    if not timestamps_p2 and not timestamps_p1:
        return None
    
    # 그래프 생성 (2개 서브플롯)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # Preview #2 그래프
    if timestamps_p2:
        for name, views in views_data_p2.items():
            if any(v > 0 for v in views):
                channel = name.replace("Preview #2 - ", "")
                style = CHANNEL_STYLES.get(channel, {
                    "color": "#666666",
                    "marker": "o",
                    "linewidth": 2,
                    "markersize": 6
                })
                
                ax1.plot(timestamps_p2, views, 
                        marker=style["marker"], 
                        linewidth=style["linewidth"], 
                        markersize=style["markersize"], 
                        label=channel, 
                        color=style["color"],
                        markeredgewidth=1.5,
                        markeredgecolor='white')
        
        ax1.set_xlabel('Date', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Views', fontsize=11, fontweight='bold')
        ax1.set_title('Preview #2 - YouTube Views Trend', 
                     fontsize=13, fontweight='bold', pad=15)
        ax1.legend(loc='best', fontsize=10, framealpha=0.9)
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    else:
        ax1.text(0.5, 0.5, 'No Preview #2 data yet', 
                ha='center', va='center', fontsize=14, color='gray')
        ax1.set_xticks([])
        ax1.set_yticks([])
    
    # Preview #1 그래프
    if timestamps_p1:
        for name, views in views_data_p1.items():
            if any(v > 0 for v in views):
                channel = name.replace("Preview #1 - ", "")
                style = CHANNEL_STYLES.get(channel, {
                    "color": "#666666",
                    "marker": "o",
                    "linewidth": 2,
                    "markersize": 6
                })
                
                ax2.plot(timestamps_p1, views, 
                        marker=style["marker"], 
                        linewidth=style["linewidth"], 
                        markersize=style["markersize"], 
                        label=channel, 
                        color=style["color"],
                        markeredgewidth=1.5,
                        markeredgecolor='white')
        
        ax2.set_xlabel('Date', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Views', fontsize=11, fontweight='bold')
        ax2.set_title('Preview #1 - YouTube Views Trend', 
                     fontsize=13, fontweight='bold', pad=15)
        ax2.legend(loc='upper left', fontsize=10, framealpha=0.9)
        ax2.grid(True, alpha=0.3)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    else:
        ax2.text(0.5, 0.5, 'No Preview #1 data yet', 
                ha='center', va='center', fontsize=14, color='gray')
        ax2.set_xticks([])
        ax2.set_yticks([])
    
    fig.autofmt_xdate()
    plt.tight_layout()
    
    # BytesIO로 저장
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    print("✅ 그래프 생성 완료 (Preview #1 & #2)")
    return buf

def format_number(num):
    """숫자를 K, M 단위로 포맷"""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    else:
        return str(num)

def format_diff(current, previous):
    """증감 포맷팅"""
    if previous is None or current is None:
        return ""
    diff = current - previous
    if diff > 0:
        return f"+{format_number(diff)}"
    elif diff < 0:
        return f"{format_number(diff)}"
    else:
        return "0"

def send_discord(stats_all):
    """Discord로 결과 전송 (그래프 포함)"""
    if not DISCORD_WEBHOOK:
        print("⚠️  DISCORD_WEBHOOK 환경변수 없음")
        return
    
    history = load_history()
    prev_data = history[-1]['videos'] if history else {}
    
    # 영상별 통계 라인 생성
    lines = []
    
    # Preview #2 섹션
    lines.append("**🎬 Preview #2**")
    p2_total_views = 0
    p2_total_likes = 0
    
    for name in PREVIEW_2_VIDEOS:
        stats = stats_all.get(name)
        if not stats:
            channel = name.replace("Preview #2 - ", "")
            lines.append(f"  • {channel}: ⚠️ 데이터 없음")
            continue
        
        views = stats['views']
        likes = stats['likes']
        p2_total_views += views
        p2_total_likes += likes
        
        # 이전 데이터와 비교
        prev_stats = prev_data.get(name, {})
        prev_views = prev_stats.get('views')
        prev_likes = prev_stats.get('likes')
        
        views_diff = format_diff(views, prev_views)
        likes_diff = format_diff(likes, prev_likes)
        
        views_display = f"`{format_number(views)}`"
        if views_diff:
            views_display += f" ({views_diff})"
        
        likes_display = f"`{format_number(likes)}`"
        if likes_diff:
            likes_display += f" ({likes_diff})"
        
        channel = name.replace("Preview #2 - ", "")
        lines.append(f"  • **{channel}**")
        lines.append(f"    👁️ {views_display} | 👍 {likes_display}")
    
    if p2_total_views > 0:
        lines.append(f"  📊 소계: 조회수 `{format_number(p2_total_views)}` | 좋아요 `{format_number(p2_total_likes)}`")
    
    # Preview #1 섹션
    lines.append("\n**🎬 Preview #1**")
    p1_total_views = 0
    p1_total_likes = 0
    
    for name in PREVIEW_1_VIDEOS:
        stats = stats_all.get(name)
        if not stats:
            channel = name.replace("Preview #1 - ", "")
            lines.append(f"  • {channel}: ⚠️ 데이터 없음")
            continue
        
        views = stats['views']
        likes = stats['likes']
        p1_total_views += views
        p1_total_likes += likes
        
        # 이전 데이터와 비교
        prev_stats = prev_data.get(name, {})
        prev_views = prev_stats.get('views')
        prev_likes = prev_stats.get('likes')
        
        views_diff = format_diff(views, prev_views)
        likes_diff = format_diff(likes, prev_likes)
        
        views_display = f"`{format_number(views)}`"
        if views_diff:
            views_display += f" ({views_diff})"
        
        likes_display = f"`{format_number(likes)}`"
        if likes_diff:
            likes_display += f" ({likes_diff})"
        
        channel = name.replace("Preview #1 - ", "")
        lines.append(f"  • **{channel}**")
        lines.append(f"    👁️ {views_display} | 👍 {likes_display}")
    
    if p1_total_views > 0:
        lines.append(f"  📊 소계: 조회수 `{format_number(p1_total_views)}` | 좋아요 `{format_number(p1_total_likes)}`")
    
    # 전체 합계
    total_views = p2_total_views + p1_total_views
    total_likes = p2_total_likes + p1_total_likes
    
    if total_views > 0:
        lines.append(f"\n**📊 전체 합계**")
        lines.append(f"조회수: `{format_number(total_views)}` | 좋아요: `{format_number(total_likes)}`")
    
    desc = "\n".join(lines)
    
    # 그래프 생성
    graph_buf = create_views_graph()
    
    # Discord embed
    embed = {
        "title": "🎬 Crimson Desert - YouTube 트레일러",
        "description": desc,
        "color": 0xFF0000,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "YouTube Tracker"}
    }
    
    try:
        if graph_buf:
            embed['image'] = {'url': 'attachment://youtube_trend.png'}
            payload = {'payload_json': json.dumps({'embeds': [embed]})}
            files = {'file': ('youtube_trend.png', graph_buf, 'image/png')}
            response = requests.post(DISCORD_WEBHOOK, data=payload, files=files)
        else:
            payload = {"embeds": [embed]}
            response = requests.post(DISCORD_WEBHOOK, json=payload)
        
        if response.status_code in [204, 200]:
            print("✅ Discord 전송 성공!")
        else:
            print(f"⚠️  Discord 전송 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ Discord 오류: {e}")

# =============================================================================
# 메인
# =============================================================================

def main():
    print("=" * 60)
    print("🎬 Crimson Desert YouTube 트레일러 추적")
    print("=" * 60)
    
    stats_all = {}
    
    for name, video_id in VIDEO_IDS.items():
        print(f"\n[{name}] 조회 중...")
        stats = get_video_stats(video_id)
        
        if stats:
            print(f"  ✅ 조회수: {stats['views']:,}")
            print(f"  ✅ 좋아요: {stats['likes']:,}")
            print(f"  ✅ 댓글: {stats['comments']:,}")
            stats_all[name] = stats
        else:
            stats_all[name] = None
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("📊 결과 요약")
    print("=" * 60)
    
    # Preview #2 합계
    p2_views = sum(s['views'] for name, s in stats_all.items() 
                   if s and name.startswith("Preview #2"))
    p2_likes = sum(s['likes'] for name, s in stats_all.items() 
                   if s and name.startswith("Preview #2"))
    
    print(f"\nPreview #2:")
    print(f"  조회수: {p2_views:,}")
    print(f"  좋아요: {p2_likes:,}")
    
    # Preview #1 합계
    p1_views = sum(s['views'] for name, s in stats_all.items() 
                   if s and name.startswith("Preview #1"))
    p1_likes = sum(s['likes'] for name, s in stats_all.items() 
                   if s and name.startswith("Preview #1"))
    
    print(f"\nPreview #1:")
    print(f"  조회수: {p1_views:,}")
    print(f"  좋아요: {p1_likes:,}")
    
    # 전체 합계
    print(f"\n전체:")
    print(f"  조회수: {p2_views + p1_views:,}")
    print(f"  좋아요: {p2_likes + p1_likes:,}")
    
    # 히스토리 저장
    save_history(stats_all)
    
    # Discord 전송
    send_discord(stats_all)

if __name__ == "__main__":
    main()
