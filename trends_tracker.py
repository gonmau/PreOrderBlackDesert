#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import requests
from datetime import datetime
from io import BytesIO

try:
    from pytrends.request import TrendReq
    HAS_PYTRENDS = True
except ImportError:
    HAS_PYTRENDS = False
    print("⚠️ pytrends 설치 필요: pip install pytrends")

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

KEYWORD = "Crimson Desert"
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# 콘솔게임 주요 5개국 (시장 규모 순)
CONSOLE_MARKETS = {
    'United States': 'US',
    'Japan': 'JP', 
    'United Kingdom': 'GB',
    'Germany': 'DE',
    'France': 'FR'
}

# =============================================================================
# 함수들
# =============================================================================

def get_google_trends():
    """GitHub Actions 안전 Google Trends 수집"""
    if not HAS_PYTRENDS:
        return None

    print("🔍 Google Trends 데이터 수집 중 (Actions 안전모드)...")

    pytrends = TrendReq(
        hl='en-US',
        tz=360,
        timeout=(10, 30),  # 타임아웃 증가
        retries=2,
        backoff_factor=2,
        requests_args={
            'headers': {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                )
            }
        }
    )

    timeframe = 'today 3-m'

    for attempt in range(3):
        try:
            print(f"  ⏳ 시도 {attempt + 1}/3")

            pytrends.build_payload(
                kw_list=[KEYWORD],
                cat=0,
                timeframe=timeframe,
                geo='',
                gprop=''
            )

            interest_over_time = pytrends.interest_over_time()

            if interest_over_time.empty:
                print("  ⚠️ 데이터 없음")
                return None

            latest_score = int(interest_over_time[KEYWORD].iloc[-1])
            avg_score = int(interest_over_time[KEYWORD].mean())

            print(f"  ✅ 현재 점수: {latest_score}/100")
            print(f"  📊 평균 점수: {avg_score}/100")

            return {
                "score": latest_score,
                "avg_7d": avg_score,
                "top_regions": {},
                "data": interest_over_time
            }

        except Exception as e:
            print(f"  ❌ 오류 발생: {e}")
            if attempt < 2:
                wait_time = 60 * (attempt + 1)  # 60초, 120초
                print(f"  💤 {wait_time}초 대기 후 재시도...")
                time.sleep(wait_time)
            else:
                print("  ❌ 모든 재시도 실패")
                return None


def get_console_markets_trends():
    """콘솔게임 주요 5개국 Google 검색 트렌드 (Rate Limit 대응)"""
    if not HAS_PYTRENDS:
        return None
    
    print("\n🎮 콘솔게임 주요국 Google 검색 트렌드 수집 중...")
    
    results = {}
    failed_count = 0
    
    for idx, (country_name, geo_code) in enumerate(CONSOLE_MARKETS.items()):
        # Rate limit 방지: 처음부터 긴 대기
        if idx > 0:
            wait_time = 10  # 국가 간 10초 대기
            print(f"  ⏰ {wait_time}초 대기 중...")
            time.sleep(wait_time)
        
        # 연속 실패 시 중단
        if failed_count >= 3:
            print(f"  ⚠️ 연속 실패 3회 - 나머지 국가 스킵")
            for remaining_country in list(CONSOLE_MARKETS.keys())[idx:]:
                results[remaining_country] = None
            break
        
        for attempt in range(2):  # 국가별 2회 시도
            try:
                print(f"  🌍 {country_name} 데이터 수집 중... (시도 {attempt + 1}/2)")
                
                pytrends = TrendReq(
                    hl='en-US', 
                    tz=360,
                    timeout=(10, 30),
                    retries=1,
                    backoff_factor=2
                )
                
                # 최근 1개월 Google 검색 트렌드
                pytrends.build_payload(
                    kw_list=[KEYWORD],
                    cat=0,
                    timeframe='today 1-m',
                    geo=geo_code,
                    gprop=''
                )
                
                interest_over_time = pytrends.interest_over_time()
                
                if not interest_over_time.empty:
                    latest_score = int(interest_over_time[KEYWORD].iloc[-1])
                    avg_score = int(interest_over_time[KEYWORD].mean())
                    
                    results[country_name] = {
                        "score": latest_score,
                        "avg_1m": avg_score,
                        "geo_code": geo_code
                    }
                    
                    print(f"    ✅ 현재: {latest_score}/100, 평균: {avg_score}/100")
                    failed_count = 0  # 성공 시 실패 카운트 리셋
                    break  # 성공하면 다음 국가로
                else:
                    print(f"    ⚠️ 데이터 없음")
                    results[country_name] = None
                    break
                
            except Exception as e:
                error_msg = str(e)
                
                if '429' in error_msg:
                    print(f"    ⚠️ Rate Limit (429) - 대기 필요")
                    failed_count += 1
                    
                    if attempt < 1:  # 1회 재시도
                        wait_time = 30 * (attempt + 2)  # 60초, 90초
                        print(f"    💤 {wait_time}초 대기 후 재시도...")
                        time.sleep(wait_time)
                    else:
                        print(f"    ❌ {country_name} 최종 실패")
                        results[country_name] = None
                        break
                else:
                    print(f"    ❌ {country_name} 오류: {error_msg[:100]}")
                    results[country_name] = None
                    failed_count += 1
                    break
    
    return results


def load_history():
    """기존 히스토리 로드"""
    history_file = "trends_history.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []


def save_history(google_data, console_data):
    """히스토리 저장"""
    history = load_history()
    
    # Google 데이터
    google_entry = None
    if google_data:
        google_entry = {
            "score": google_data.get("score"),
            "avg_7d": google_data.get("avg_7d"),
            "top_regions": google_data.get("top_regions", {})
        }
    
    # 콘솔 시장 데이터
    console_entry = None
    if console_data:
        console_entry = {country: data for country, data in console_data.items() if data}
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "google": google_entry,
        "console_markets": console_entry
    }
    
    history.append(entry)

    with open("trends_history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    print("✅ trends_history.json 저장 완료")


def create_trends_graph():
    """트렌드 그래프 생성 (Google + 콘솔 주요국) - 데이터 길이 불일치 해결"""
    if not HAS_MATPLOTLIB:
        print("⚠️ matplotlib 없음 - 그래프 생략")
        return None
    
    history = load_history()
    if len(history) < 2:
        print("⚠️ 데이터 부족 (2개 이상 필요) - 그래프 생략")
        return None
    
    # Google 글로벌 데이터
    google_timestamps = []
    google_scores = []
    
    # 콘솔 국가별 데이터
    console_timestamps = []
    console_scores = {country: [] for country in CONSOLE_MARKETS.keys()}
    
    for entry in history:
        try:
            dt = datetime.fromisoformat(entry['timestamp'])
            
            # Google 글로벌 (모든 히스토리)
            if entry.get('google'):
                google_timestamps.append(dt)
                g_score = entry['google'].get('score')
                google_scores.append(g_score if g_score else 0)
            
            # 콘솔 주요국 (console_markets가 있는 경우만)
            console_data = entry.get('console_markets')
            if console_data:
                console_timestamps.append(dt)
                for country in CONSOLE_MARKETS.keys():
                    country_data = console_data.get(country)
                    score = country_data.get('score') if country_data else None
                    console_scores[country].append(score if score else 0)
        except:
            continue
    
    if not google_timestamps:
        return None
    
    # 콘솔 데이터 충분한지 확인
    has_console_data = len(console_timestamps) >= 2
    
    # 그래프 생성
    if has_console_data:
        # 콘솔 데이터 충분: 2개 서브플롯
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # 1. Google 글로벌 트렌드
        ax1.plot(google_timestamps, google_scores, marker='o', linewidth=2, 
                markersize=6, label='Global', color='#4285F4')
        ax1.set_xlabel('Date', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Interest Score (0-100)', fontsize=11, fontweight='bold')
        ax1.set_title('Crimson Desert - Google Search Trends (Global)', 
                     fontsize=13, fontweight='bold', pad=15)
        ax1.legend(loc='best', fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 105)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        
        # 2. 콘솔 주요 5개국 (console_timestamps 사용!)
        colors = ['#EA4335', '#34A853', '#FBBC05', '#FF6D01', '#46BDC6']
        for idx, (country, scores) in enumerate(console_scores.items()):
            if any(s > 0 for s in scores):
                ax2.plot(console_timestamps, scores, marker='o', linewidth=2,
                        markersize=5, label=country, color=colors[idx])
        
        ax2.set_xlabel('Date', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Interest Score (0-100)', fontsize=11, fontweight='bold')
        ax2.set_title('Crimson Desert - Console Market Trends (Top 5 Countries)', 
                     fontsize=13, fontweight='bold', pad=15)
        ax2.legend(loc='best', fontsize=9, ncol=2)
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(0, 105)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        
        fig.autofmt_xdate()
        plt.tight_layout()
        
        print("✅ 그래프 생성 완료 (글로벌 + 콘솔 5개국)")
    else:
        # 콘솔 데이터 부족: Google만
        fig, ax1 = plt.subplots(1, 1, figsize=(12, 6))
        plt.style.use('seaborn-v0_8-darkgrid')
        
        ax1.plot(google_timestamps, google_scores, marker='o', linewidth=2, 
                markersize=6, label='Global', color='#4285F4')
        ax1.set_xlabel('Date', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Interest Score (0-100)', fontsize=11, fontweight='bold')
        ax1.set_title('Crimson Desert - Google Search Trends (Global)', 
                     fontsize=13, fontweight='bold', pad=15)
        ax1.legend(loc='best', fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 105)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        
        fig.autofmt_xdate()
        plt.tight_layout()
        
        print(f"ℹ️  콘솔 데이터 부족 ({len(console_timestamps)}개) - Google 트렌드만 표시")
    
    # BytesIO로 저장
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf


def format_diff(current, previous):
    """점수 증감 포맷팅"""
    if previous is None or current is None:
        return ""
    diff = current - previous
    if diff > 0:
        return f"+{diff}"
    elif diff < 0:
        return f"{diff}"
    else:
        return "0"


def send_discord(google_data, console_data):
    """Discord로 결과 전송 (그래프 포함)"""
    if not DISCORD_WEBHOOK:
        print("⚠️ DISCORD_WEBHOOK 환경변수 없음")
        return
    
    history = load_history()
    prev_data = history[-1] if history else {}
    
    # Discord 메시지 구성
    lines = []
    
    # 1. Google Trends (글로벌)
    if google_data:
        g_score = google_data['score']
        g_avg = google_data['avg_7d']
        prev_g_score = prev_data.get('google', {}).get('score')
        g_diff = format_diff(g_score, prev_g_score)
        
        lines.append(f"**🔍 Google 검색 (글로벌, 최근 3개월)**")
        lines.append(f"현재 관심도: `{g_score}/100` {f'({g_diff})' if g_diff else ''}")
        lines.append(f"평균: `{g_avg}/100`")
    else:
        lines.append("**🔍 Google 검색 (글로벌)**: 데이터 없음")
    
    # 2. 콘솔게임 주요 5개국
    if console_data:
        lines.append(f"\n**🎮 콘솔게임 주요 5개국 (최근 1개월)**")
        
        prev_console = prev_data.get('console_markets', {})
        
        success_count = sum(1 for d in console_data.values() if d)
        lines.append(f"_수집 성공: {success_count}/5개국_\n")
        
        for country in CONSOLE_MARKETS.keys():
            country_data = console_data.get(country)
            if country_data:
                score = country_data['score']
                avg = country_data['avg_1m']
                
                prev_score = None
                if prev_console and country in prev_console:
                    prev_score = prev_console[country].get('score')
                
                diff = format_diff(score, prev_score)
                
                flag = {
                    'United States': '🇺🇸',
                    'Japan': '🇯🇵',
                    'United Kingdom': '🇬🇧',
                    'Germany': '🇩🇪',
                    'France': '🇫🇷'
                }.get(country, '🌍')
                
                lines.append(f"{flag} {country}: `{score}/100` {f'({diff})' if diff else ''} (평균: {avg})")
            else:
                flag = {
                    'United States': '🇺🇸',
                    'Japan': '🇯🇵',
                    'United Kingdom': '🇬🇧',
                    'Germany': '🇩🇪',
                    'France': '🇫🇷'
                }.get(country, '🌍')
                lines.append(f"{flag} {country}: `수집 실패`")
    else:
        lines.append(f"\n**🎮 콘솔게임 주요국**: 데이터 수집 실패")
    
    desc = "\n".join(lines)
    
    # 그래프 생성
    graph_buf = create_trends_graph()
    
    # Discord embed
    embed = {
        "title": "📊 Crimson Desert - Google 검색 트렌드",
        "description": desc,
        "color": 0x4285F4,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "Google Trends Tracker"}
    }
    
    try:
        if graph_buf:
            embed['image'] = {'url': 'attachment://trends.png'}
            payload = {'payload_json': json.dumps({'embeds': [embed]})}
            files = {'file': ('trends.png', graph_buf, 'image/png')}
            response = requests.post(DISCORD_WEBHOOK, data=payload, files=files)
        else:
            payload = {"embeds": [embed]}
            response = requests.post(DISCORD_WEBHOOK, json=payload)
        
        if response.status_code in [204, 200]:
            print("✅ Discord 전송 성공!")
        else:
            print(f"⚠️ Discord 전송 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ Discord 오류: {e}")


# =============================================================================
# 메인
# =============================================================================

def main():
    if not HAS_PYTRENDS:
        print("❌ pytrends 라이브러리가 필요합니다!")
        print("설치: pip install pytrends")
        return
    
    print("=" * 60)
    print("📊 Crimson Desert 검색 트렌드 추적")
    print("=" * 60)
    
    start_time = time.time()
    
    # 1. Google Trends (글로벌)
    google_data = get_google_trends()
    
    # Rate limit 방지: 글로벌 수집 후 충분히 대기
    print("\n⏰ Rate Limit 방지 대기 (60초)...")
    time.sleep(60)
    
    # 2. 콘솔게임 주요 5개국
    console_data = get_console_markets_trends()
    
    elapsed = (time.time() - start_time) / 60
    print(f"\n⏱️ 소요 시간: {elapsed:.1f}분")
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("📊 결과 요약")
    print("=" * 60)
    
    if google_data:
        print(f"🌍 Google 검색 (글로벌): {google_data['score']}/100 (평균: {google_data['avg_7d']})")
    else:
        print("🌍 Google 검색 (글로벌): 데이터 없음")
    
    if console_data:
        print(f"\n🎮 콘솔게임 주요 5개국:")
        for country, data in console_data.items():
            if data:
                print(f"  • {country}: {data['score']}/100 (평균: {data['avg_1m']})")
            else:
                print(f"  • {country}: 수집 실패")
    
    # 히스토리 저장
    save_history(google_data, console_data)
    
    # Discord 전송
    send_discord(google_data, console_data)


if __name__ == "__main__":
    main()
