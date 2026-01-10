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
    print("⚠️  pytrends 설치 필요: pip install pytrends")

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

# =============================================================================
# 함수들
# =============================================================================

def get_google_trends():
    """Google Trends에서 검색 관심도 가져오기"""
    if not HAS_PYTRENDS:
        return None
    
    print("🔍 Google Trends 데이터 수집 중...")
    
    try:
        # Pytrends 초기화
        pytrends = TrendReq(hl='en-US', tz=360)
        
        # YouTube 검색 트렌드
        pytrends.build_payload(
            kw_list=[KEYWORD],
            cat=0,
            timeframe='now 1-m',  # 7일 → 1개월로 변경
            geo='',  # 전세계
            gprop=''  # 일반 Google 검색
        )
        
        # 시간별 관심도
        interest_over_time = pytrends.interest_over_time()
        
        if interest_over_time.empty:
            print("  ⚠️  데이터 없음")
            return None
        
        # 최신 점수 (가장 최근 데이터)
        latest_score = int(interest_over_time[KEYWORD].iloc[-1])
        avg_score = int(interest_over_time[KEYWORD].mean())
        
        print(f"  ✅ 현재 점수: {latest_score}/100")
        print(f"  📊 7일 평균: {avg_score}/100")
        
        # 지역별 관심도
        try:
            print("  🌍 지역별 데이터 수집 시도...")
            interest_by_region = pytrends.interest_by_region(
                resolution='COUNTRY', 
                inc_low_vol=True,  # 낮은 검색량도 포함
                inc_geo_code=False
            )
            
            if interest_by_region.empty:
                print("  ⚠️  지역별 데이터가 비어있음")
                top_regions_dict = {}
            else:
                # 디버깅: 실제 국가명 출력
                print(f"  🌍 감지된 국가 수: {len(interest_by_region)}")
                
                # 0보다 큰 값만 필터링
                filtered = interest_by_region[interest_by_region[KEYWORD] > 0]
                print(f"  🌍 데이터가 있는 국가 수: {len(filtered)}")
                
                top_10 = filtered.sort_values(by=KEYWORD, ascending=False).head(10)
                
                print(f"  🔝 Top 10 국가:")
                for country, score in top_10[KEYWORD].items():
                    print(f"    - '{country}': {score}")
                
                # 전체 데이터를 딕셔너리로 저장 (Top 10뿐만 아니라 전체)
                top_regions_dict = filtered[KEYWORD].to_dict()
                
        except Exception as e:
            print(f"  ⚠️  지역별 데이터 수집 오류: {e}")
            import traceback
            traceback.print_exc()
            top_regions_dict = {}
        
        return {
            "score": latest_score,
            "avg_7d": avg_score,
            "top_regions": top_regions_dict,
            "data": interest_over_time
        }
        
    except Exception as e:
        print(f"  ❌ Google Trends 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_youtube_trends():
    """YouTube 검색 트렌드 가져오기 (주요 국가별 + 다국어)"""
    if not HAS_PYTRENDS:
        return None
    
    print("🎬 YouTube 검색 트렌드 수집 중...")
    
    # 주요 시장별 검색어 (현지어 + 영어)
    search_configs = {
        'Global': [
            ('', 'Crimson Desert'),
            ('', '붉은사막'),
            ('', '紅の砂漠'),
            ('', '红色沙漠')  # 중국어 간체
        ],
        'South Korea': [
            ('KR', '붉은사막'),
            ('KR', 'Crimson Desert')
        ],
        'United States': [
            ('US', 'Crimson Desert')
        ],
        'Japan': [
            ('JP', '紅の砂漠'),
            ('JP', 'Crimson Desert')
        ],
        'United Kingdom': [
            ('GB', 'Crimson Desert')
        ]
    }
    
    results = {}
    
    for country_name, configs in search_configs.items():
        try:
            print(f"  📍 {country_name} 데이터 수집 중...")
            
            country_scores = []
            keywords_used = []
            
            for geo_code, keyword in configs:
                try:
                    print(f"    🔍 '{keyword}' 검색 중...")
                    
                    # Pytrends 초기화 (매번 새로 생성)
                    pytrends = TrendReq(hl='en-US', tz=360)
                    
                    # YouTube 검색 트렌드
                    pytrends.build_payload(
                        kw_list=[keyword],
                        cat=0,
                        timeframe='now 1-m',  # 7일 → 1개월로 변경
                        geo=geo_code,
                        gprop='youtube'
                    )
                    
                    # 시간별 관심도
                    interest_over_time = pytrends.interest_over_time()
                    
                    if not interest_over_time.empty:
                        latest_score = int(interest_over_time[keyword].iloc[-1])
                        avg_score = int(interest_over_time[keyword].mean())
                        
                        # 0점이라도 데이터가 있으면 저장
                        country_scores.append({
                            'keyword': keyword,
                            'score': latest_score,
                            'avg': avg_score
                        })
                        keywords_used.append(keyword)
                        
                        if latest_score > 0:
                            print(f"      ✅ {latest_score}/100 (평균: {avg_score})")
                        else:
                            print(f"      ℹ️  0점 (하지만 데이터 있음)")
                    else:
                        print(f"      ⚠️  데이터 없음")
                    
                    time.sleep(3)  # Rate limit 방지 (1초 → 3초로 증가)
                    
                except Exception as e:
                    print(f"      ❌ '{keyword}' 오류: {str(e)[:100]}")
                    time.sleep(5)  # 에러 발생 시 더 길게 대기
                    continue
            
            if country_scores:
                # 가장 높은 점수 사용
                best = max(country_scores, key=lambda x: x['score'])
                
                # 여러 검색어의 평균도 계산
                total_score = sum(s['score'] for s in country_scores)
                avg_of_all = sum(s['avg'] for s in country_scores) // len(country_scores)
                
                results[country_name] = {
                    "score": best['score'],  # 최고 점수
                    "avg_7d": avg_of_all,
                    "keywords": keywords_used,
                    "all_scores": country_scores  # 모든 검색어 점수 저장
                }
                
                print(f"    ✅ {country_name} 최고 점수: {best['score']}/100 ('{best['keyword']}')")
            else:
                print(f"    ⚠️  {country_name} 모든 검색어에서 데이터 없음")
                results[country_name] = None
            
            time.sleep(2)  # 국가 간 추가 대기
            
        except Exception as e:
            print(f"    ❌ {country_name} 전체 오류: {str(e)[:100]}")
            import traceback
            traceback.print_exc()
            results[country_name] = None
            continue
    
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

def save_history(google_data, youtube_data):
    """히스토리 저장"""
    history = load_history()
    
    # Google 데이터만 저장
    google_entry = None
    if google_data:
        google_entry = {
            "score": google_data.get("score"),
            "avg_7d": google_data.get("avg_7d"),
            "top_regions": google_data.get("top_regions", {})
        }
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "google": google_entry
    }
    
    history.append(entry)
    
    # 최근 200개만 유지
    if len(history) > 200:
        history = history[-200:]
    
    with open("trends_history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    print("✅ trends_history.json 저장 완료")

def create_trends_graph():
    """트렌드 그래프 생성 (Google만)"""
    if not HAS_MATPLOTLIB:
        print("⚠️  matplotlib 없음 - 그래프 생략")
        return None
    
    history = load_history()
    if len(history) < 2:
        print("⚠️  데이터 부족 (2개 이상 필요) - 그래프 생략")
        return None
    
    # 데이터 파싱
    timestamps = []
    google_scores = []
    
    for entry in history:
        try:
            dt = datetime.fromisoformat(entry['timestamp'])
            g_score = entry.get('google', {}).get('score')
            
            timestamps.append(dt)
            google_scores.append(g_score if g_score else 0)
        except:
            continue
    
    if not timestamps:
        return None
    
    # 그래프 생성
    plt.figure(figsize=(12, 6))
    plt.style.use('seaborn-v0_8-darkgrid')
    
    plt.plot(timestamps, google_scores, marker='o', linewidth=2, 
            markersize=6, label='Google Search', color='#4285F4')
    
    plt.xlabel('Date', fontsize=12, fontweight='bold')
    plt.ylabel('Interest Score (0-100)', fontsize=12, fontweight='bold')
    plt.title('Crimson Desert - Google Search Trends', 
             fontsize=14, fontweight='bold', pad=20)
    plt.legend(loc='best', fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.ylim(0, 100)
    
    # 날짜 포맷
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    plt.gcf().autofmt_xdate()
    
    plt.tight_layout()
    
    # BytesIO로 저장
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    print("✅ 그래프 생성 완료")
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

def send_discord(google_data, youtube_data):
    """Discord로 결과 전송 (그래프 포함)"""
    if not DISCORD_WEBHOOK:
        print("⚠️  DISCORD_WEBHOOK 환경변수 없음")
        return
    
    history = load_history()
    prev_data = history[-1] if history else {}
    
    # Discord 메시지 구성
    lines = []
    
    # Google Trends만
    if google_data:
        g_score = google_data['score']
        g_avg = google_data['avg_7d']
        prev_g_score = prev_data.get('google', {}).get('score')
        g_diff = format_diff(g_score, prev_g_score)
        
        lines.append(f"**🔍 Google 검색 (최근 1개월)**")
        lines.append(f"현재 관심도: `{g_score}/100` {f'({g_diff})' if g_diff else ''}")
        lines.append(f"평균: `{g_avg}/100`")
        
        # 지역별 관심도
        if google_data.get('top_regions'):
            regions = google_data['top_regions']
            
            print(f"📍 전체 지역 데이터 수: {len(regions)}")
            
            # 주요 시장 국가명
            major_market_keys = {
                'South Korea': 'South Korea',
                'United States': 'United States', 
                'United Kingdom': 'United Kingdom',
                'Japan': 'Japan'
            }
            
            # 주요 시장 점수 찾기
            major_markets = {}
            for display_name, key in major_market_keys.items():
                score = regions.get(key, 0)
                major_markets[display_name] = score
                if score > 0:
                    print(f"  ✅ {display_name} 발견: {score}")
                else:
                    # 비슷한 이름 찾기 시도
                    for region_name in regions.keys():
                        if key.lower() in region_name.lower() or region_name.lower() in key.lower():
                            score = regions[region_name]
                            major_markets[display_name] = score
                            print(f"  ✅ {display_name} 발견 ('{region_name}'): {score}")
                            break
                    else:
                        print(f"  ⚠️  {display_name} 데이터 없음")
            
            lines.append(f"\n**📍 주요 시장:**")
            for country, score in major_markets.items():
                if score > 0:
                    lines.append(f"• {country}: `{score}/100`")
                else:
                    lines.append(f"• {country}: `데이터 없음`")
            
            # Top 5 (전체 지역 중)
            sorted_regions = sorted(regions.items(), key=lambda x: x[1], reverse=True)
            
            lines.append(f"\n**🏆 전체 인기 지역 Top 5:**")
            for idx, (region, score) in enumerate(sorted_regions[:5], 1):
                if score > 0:
                    lines.append(f"{idx}. {region}: `{score}/100`")
    else:
        lines.append("**🔍 Google 검색**: 데이터 없음")
    
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
            print(f"⚠️  Discord 전송 실패: {response.status_code}")
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
    
    # Google Trends만 수집
    google_data = get_google_trends()
    
    elapsed = (time.time() - start_time) / 60
    print(f"\n⏱️  소요 시간: {elapsed:.1f}분")
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("📊 결과 요약")
    print("=" * 60)
    
    if google_data:
        print(f"Google 검색 관심도: {google_data['score']}/100 (평균: {google_data['avg_7d']})")
        if google_data.get('top_regions'):
            print(f"\n인기 지역 Top 5:")
            for idx, (region, score) in enumerate(list(google_data['top_regions'].items())[:5], 1):
                print(f"  {idx}. {region}: {score}/100")
    else:
        print("Google 검색 관심도: 데이터 없음")
    
    # 히스토리 저장 (YouTube 데이터 없이)
    save_history(google_data, None)
    
    # Discord 전송 (YouTube 데이터 없이)
    send_discord(google_data, None)

if __name__ == "__main__":
    main()
