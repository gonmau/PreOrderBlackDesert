import pandas as pd
import requests
from datetime import datetime, timedelta
import json
import os

# 게임 테마주 목록
GAME_STOCKS = {
    '036570': '엔씨소프트',
    '251270': '넷마블',
    '263750': '펄어비스',
    '112040': '위메이드',
    '259960': '크래프톤',
    '293490': '카카오게임즈',
    '194480': '데브시스터즈',
    '225570': '넥슨게임즈',
    '095660': '네오위즈',
    '376300': '디어유'
}

DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')

def get_stock_data(code):
    """FinanceDataReader로 주식 데이터 수집 및 분석"""
    try:
        import FinanceDataReader as fdr
        
        end_date = datetime.now()
        start_date_week = end_date - timedelta(days=7)
        start_date_month = end_date - timedelta(days=30)
        start_date_year = end_date - timedelta(days=365)
        
        # 1년치 데이터 가져오기
        df_year = fdr.DataReader(code, start_date_year, end_date)
        
        if df_year.empty:
            print(f"  데이터 없음")
            return None
        
        # 최근 종가 및 거래량
        latest = df_year.iloc[-1]
        price = int(latest['Close'])
        volume = int(latest['Volume'])
        
        # 1일 전 데이터 (일일 변동률)
        if len(df_year) >= 2:
            prev_day = df_year.iloc[-2]
            day_change = ((price - prev_day['Close']) / prev_day['Close']) * 100
        else:
            day_change = 0
        
        # 1주일 전 데이터
        df_week = df_year[df_year.index >= start_date_week]
        if len(df_week) >= 2:
            week_ago = df_week.iloc[0]['Close']
            week_change = ((price - week_ago) / week_ago) * 100
        else:
            week_change = 0
        
        # 1개월 전 데이터
        df_month = df_year[df_year.index >= start_date_month]
        if len(df_month) >= 2:
            month_ago = df_month.iloc[0]['Close']
            month_change = ((price - month_ago) / month_ago) * 100
        else:
            month_change = 0
        
        # 52주 최고가/최저가
        high_52w = df_year['High'].max()
        low_52w = df_year['Low'].min()
        
        # 현재가 대비 52주 최고가 비율
        from_high = ((price - high_52w) / high_52w) * 100
        
        # 시가총액 계산 (StockListing에서 상장주식수 가져오기)
        try:
            stocks_listing = fdr.StockListing('KRX')
            stock_info = stocks_listing[stocks_listing['Code'] == code]
            
            if not stock_info.empty:
                # Stocks 컬럼 (상장주식수)
                if 'Stocks' in stock_info.columns:
                    shares = float(stock_info.iloc[0]['Stocks'])
                    market_cap = (price * shares) / 1000000000000  # 조원
                elif 'ListedShares' in stock_info.columns:
                    shares = float(stock_info.iloc[0]['ListedShares'])
                    market_cap = (price * shares) / 1000000000000
                else:
                    market_cap = 0
            else:
                market_cap = 0
        except:
            market_cap = 0
        
        return {
            'price': price,
            'volume': volume,
            'market_cap': round(market_cap, 2),
            'day_change': round(day_change, 2),
            'week_change': round(week_change, 2),
            'month_change': round(month_change, 2),
            'high_52w': int(high_52w),
            'low_52w': int(low_52w),
            'from_high': round(from_high, 2)
        }
        
    except ImportError:
        print(f"  FinanceDataReader 미설치")
        return None
    except Exception as e:
        print(f"  오류: {str(e)}")
        return None

def send_discord_notification(df, leader):
    """디스코드로 분석 결과 전송"""
    if not DISCORD_WEBHOOK:
        print("DISCORD_WEBHOOK 환경변수가 설정되지 않았습니다.")
        return
    
    # 펄어비스 데이터
    pearl = df[df['name'] == '펄어비스'].iloc[0] if len(df[df['name'] == '펄어비스']) > 0 else None
    
    # Embed 메시지 생성
    embed = {
        "title": "🎮 게임테마주 일일 분석 리포트",
        "description": f"**분석 시각**: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')} KST",
        "color": 3447003,
        "fields": [],
        "footer": {
            "text": "게임테마주 자동 분석 시스템"
        },
        "timestamp": datetime.now().isoformat()
    }
    
    # 대장주
    leader_color = "🟢" if leader['day_change'] > 0 else "🔴" if leader['day_change'] < 0 else "⚪"
    embed["fields"].append({
        "name": "👑 테마 대장주 (시총 기준)",
        "value": f"**{leader['name']}** {leader_color}\n"
                 f"현재가: **{int(leader['price']):,}원** ({leader['day_change']:+.2f}%)\n"
                 f"시가총액: {leader['market_cap']:.2f}조원",
        "inline": False
    })
    
    # 일일 상승/하락 TOP3
    df_sorted_gain = df.sort_values('day_change', ascending=False)
    top_gainers = df_sorted_gain.head(3)
    gainers_text = "\n".join([
        f"{i+1}. **{row['name']}**: {row['day_change']:+.2f}% ({int(row['price']):,}원)"
        for i, (_, row) in enumerate(top_gainers.iterrows())
    ])
    
    df_sorted_loss = df.sort_values('day_change', ascending=True)
    top_losers = df_sorted_loss.head(3)
    losers_text = "\n".join([
        f"{i+1}. **{row['name']}**: {row['day_change']:+.2f}% ({int(row['price']):,}원)"
        for i, (_, row) in enumerate(top_losers.iterrows())
    ])
    
    embed["fields"].append({
        "name": "📈 일일 상승 TOP3",
        "value": gainers_text,
        "inline": True
    })
    
    embed["fields"].append({
        "name": "📉 일일 하락 TOP3",
        "value": losers_text,
        "inline": True
    })
    
    # 펄어비스 상세
    if pearl is not None:
        pearl_emoji = "🟢" if pearl['day_change'] > 0 else "🔴" if pearl['day_change'] < 0 else "⚪"
        
        pearl_value = f"{pearl_emoji} **현재가**: {int(pearl['price']):,}원\n"
        pearl_value += f"**일일**: {pearl['day_change']:+.2f}% | **주간**: {pearl['week_change']:+.2f}% | **월간**: {pearl['month_change']:+.2f}%\n"
        pearl_value += f"**시가총액**: {pearl['market_cap']:.2f}조원\n"
        pearl_value += f"**52주 최고**: {int(pearl['high_52w']):,}원 | **최저**: {int(pearl['low_52w']):,}원\n"
        pearl_value += f"**고점대비**: {pearl['from_high']:+.2f}%"
        
        embed["fields"].append({
            "name": "⭐ 펄어비스 상세 분석",
            "value": pearl_value,
            "inline": False
        })
    
    # 주간/월간 수익률 TOP3
    df_sorted_week = df.sort_values('week_change', ascending=False)
    top_week = df_sorted_week.head(3)
    week_text = "\n".join([
        f"{i+1}. **{row['name']}**: {row['week_change']:+.2f}%"
        for i, (_, row) in enumerate(top_week.iterrows())
    ])
    
    df_sorted_month = df.sort_values('month_change', ascending=False)
    top_month = df_sorted_month.head(3)
    month_text = "\n".join([
        f"{i+1}. **{row['name']}**: {row['month_change']:+.2f}%"
        for i, (_, row) in enumerate(top_month.iterrows())
    ])
    
    embed["fields"].append({
        "name": "📊 주간 수익률 TOP3",
        "value": week_text,
        "inline": True
    })
    
    embed["fields"].append({
        "name": "📊 월간 수익률 TOP3",
        "value": month_text,
        "inline": True
    })
    
    # 52주 신고가 근접 종목 (고점대비 -5% 이내)
    near_high = df[df['from_high'] >= -5]
    if len(near_high) > 0:
        near_high_text = "\n".join([
            f"• **{row['name']}**: 고점대비 {row['from_high']:+.2f}%"
            for _, row in near_high.iterrows()
        ])
        embed["fields"].append({
            "name": "🔥 52주 신고가 근접 (5% 이내)",
            "value": near_high_text,
            "inline": False
        })
    
    # 디스코드 전송
    payload = {"embeds": [embed]}
    
    try:
        response = requests.post(DISCORD_WEBHOOK, json=payload)
        if response.status_code == 204:
            print("✅ 디스코드 알림 전송 완료")
        else:
            print(f"❌ 디스코드 전송 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ 디스코드 전송 오류: {e}")

def analyze_stocks():
    """전체 게임주 분석"""
    results = []
    
    print("=" * 70)
    print(f"게임테마주 종합 분석 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    for code, name in GAME_STOCKS.items():
        print(f"분석중: {name} ({code})...")
        data = get_stock_data(code)
        
        if data:
            data['code'] = code
            data['name'] = name
            results.append(data)
            print(f"  ✓ 현재가: {data['price']:,}원 ({data['day_change']:+.2f}%), 시총: {data['market_cap']:.2f}조원")
    
    if not results:
        print("\n❌ 데이터 수집 실패")
        return
    
    df = pd.DataFrame(results)
    df = df.sort_values('market_cap', ascending=False)
    
    print("\n" + "=" * 70)
    print("분석 결과")
    print("=" * 70)
    
    print("\n[전체 종목 현황]")
    display_df = df[['name', 'price', 'day_change', 'week_change', 'month_change', 'market_cap']].copy()
    display_df.columns = ['종목명', '현재가', '일일%', '주간%', '월간%', '시총(조)']
    print(display_df.to_string(index=False))
    
    print("\n[시가총액 TOP 5]")
    for i, (_, row) in enumerate(df.head(5).iterrows(), 1):
        print(f"{i}. {row['name']}: {row['market_cap']:.2f}조원 ({int(row['price']):,}원)")
    
    print("\n[일일 변동률 상위]")
    top_change = df.nlargest(3, 'day_change')
    for i, (_, row) in enumerate(top_change.iterrows(), 1):
        print(f"{i}. {row['name']}: {row['day_change']:+.2f}% ({int(row['price']):,}원)")
    
    print("\n" + "=" * 70)
    print("펄어비스 상세 분석")
    print("=" * 70)
    pearl = df[df['name'] == '펄어비스']
    if len(pearl) > 0:
        p = pearl.iloc[0]
        print(f"현재가: {int(p['price']):,}원")
        print(f"일일 변동: {p['day_change']:+.2f}%")
        print(f"주간 변동: {p['week_change']:+.2f}%")
        print(f"월간 변동: {p['month_change']:+.2f}%")
        print(f"시가총액: {p['market_cap']:.2f}조원")
        print(f"52주 최고가: {int(p['high_52w']):,}원")
        print(f"52주 최저가: {int(p['low_52w']):,}원")
        print(f"고점 대비: {p['from_high']:+.2f}%")
    
    # 디스코드 알림
    print("\n" + "=" * 70)
    leader = df.iloc[0]
    send_discord_notification(df, leader)
    
    # 파일 저장
    df.to_csv('game_stocks_analysis.csv', index=False, encoding='utf-8-sig')
    print(f"결과 저장: game_stocks_analysis.csv")
    
    result_json = {
        'timestamp': datetime.now().isoformat(),
        'stocks': df.to_dict('records'),
        'leader': leader.to_dict()
    }
    
    with open('game_stocks_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(result_json, f, ensure_ascii=False, indent=2)
    
    print("결과 저장: game_stocks_analysis.json")
    print("=" * 70)

if __name__ == "__main__":
    analyze_stocks()
