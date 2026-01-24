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
        
        # 이동평균선 계산 (5일, 20일, 60일)
        ma5 = df_year['Close'].tail(5).mean() if len(df_year) >= 5 else price
        ma20 = df_year['Close'].tail(20).mean() if len(df_year) >= 20 else price
        ma60 = df_year['Close'].tail(60).mean() if len(df_year) >= 60 else price
        
        # 골든크로스/데드크로스 체크
        if len(df_year) >= 20:
            ma5_prev = df_year['Close'].tail(6).head(5).mean()
            ma20_prev = df_year['Close'].tail(21).head(20).mean()
            
            if ma5_prev <= ma20_prev and ma5 > ma20:
                cross_signal = "골든크로스"
            elif ma5_prev >= ma20_prev and ma5 < ma20:
                cross_signal = "데드크로스"
            else:
                cross_signal = None
        else:
            cross_signal = None
        
        # RSI 계산 (14일)
        if len(df_year) >= 15:
            delta = df_year['Close'].diff()
            gain = (delta.where(delta > 0, 0)).tail(14).mean()
            loss = (-delta.where(delta < 0, 0)).tail(14).mean()
            rs = gain / loss if loss != 0 else 0
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 50
        
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
        
        # 수급 및 공매도 정보
        try:
            from pykrx import stock
            
            # 최근 영업일 찾기
            trade_date = end_date
            for i in range(7):
                date_str = (trade_date - timedelta(days=i)).strftime('%Y%m%d')
                
                try:
                    # 투자자별 거래 (외국인, 기관)
                    investor_df = stock.get_market_trading_value_by_date(date_str, date_str, code)
                    if not investor_df.empty:
                        latest_trade = investor_df.iloc[-1]
                        foreign_net = latest_trade.get('외국인', 0) if '외국인' in latest_trade else 0
                        institution_net = latest_trade.get('기관', 0) if '기관' in latest_trade else 0
                        
                        # 순매수를 거래량으로 나눠서 비율 계산 (간이)
                        total_value = abs(foreign_net) + abs(institution_net)
                        foreign_ratio = (foreign_net / total_value * 100) if total_value > 0 else 0
                        institution_ratio = (institution_net / total_value * 100) if total_value > 0 else 0
                        break
                except:
                    continue
            else:
                foreign_ratio = 0
                institution_ratio = 0
            
            # 공매도 잔고 비율
            try:
                short_date = end_date
                for i in range(7):
                    date_str = (short_date - timedelta(days=i)).strftime('%Y%m%d')
                    try:
                        short_df = stock.get_shorting_balance_by_ticker(date_str, code)
                        if not short_df.empty and code in short_df.index:
                            short_info = short_df.loc[code]
                            # 공매도잔고비율 = (공매도잔고 / 상장주식수) * 100
                            short_balance = short_info.get('공매도잔고', 0) if '공매도잔고' in short_info else 0
                            short_ratio = short_info.get('공매도잔고비율', 0) if '공매도잔고비율' in short_info else 0
                            break
                    except:
                        continue
                else:
                    short_ratio = 0
            except:
                short_ratio = 0
                
        except ImportError:
            foreign_ratio = 0
            institution_ratio = 0
            short_ratio = 0
        except Exception as e:
            print(f"  수급 데이터 오류: {e}")
            foreign_ratio = 0
            institution_ratio = 0
            short_ratio = 0
        
        return {
            'price': price,
            'volume': volume,
            'market_cap': round(market_cap, 2),
            'day_change': round(day_change, 2),
            'week_change': round(week_change, 2),
            'month_change': round(month_change, 2),
            'high_52w': int(high_52w),
            'low_52w': int(low_52w),
            'from_high': round(from_high, 2),
            'ma5': round(ma5, 0),
            'ma20': round(ma20, 0),
            'ma60': round(ma60, 0),
            'cross_signal': cross_signal,
            'rsi': round(rsi, 1),
            'short_ratio': round(short_ratio, 2),
            'foreign_net': round(foreign_ratio, 1),
            'institution_net': round(institution_ratio, 1)
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
        
        # 기본 정보
        pearl_value = f"{pearl_emoji} **현재가**: {int(pearl['price']):,}원\n"
        pearl_value += f"**일일**: {pearl['day_change']:+.2f}% | **주간**: {pearl['week_change']:+.2f}% | **월간**: {pearl['month_change']:+.2f}%\n"
        pearl_value += f"**시가총액**: {pearl['market_cap']:.2f}조원\n"
        pearl_value += f"**52주 최고**: {int(pearl['high_52w']):,}원 | **최저**: {int(pearl['low_52w']):,}원\n"
        pearl_value += f"**고점대비**: {pearl['from_high']:+.2f}%"
        
        embed["fields"].append({
            "name": "⭐ 펄어비스 기본 정보",
            "value": pearl_value,
            "inline": False
        })
        
        # 차트 분석
        chart_value = f"**MA5**: {int(pearl['ma5']):,}원 | **MA20**: {int(pearl['ma20']):,}원 | **MA60**: {int(pearl['ma60']):,}원\n"
        
        # 이평선 배열
        if pearl['price'] > pearl['ma5'] > pearl['ma20'] > pearl['ma60']:
            chart_value += "**이평선 배열**: 정배열 (강세) 📈\n"
        elif pearl['price'] < pearl['ma5'] < pearl['ma20'] < pearl['ma60']:
            chart_value += "**이평선 배열**: 역배열 (약세) 📉\n"
        else:
            chart_value += "**이평선 배열**: 혼조세\n"
        
        # 골든/데드 크로스
        if pearl['cross_signal']:
            signal_emoji = "🟢" if pearl['cross_signal'] == "골든크로스" else "🔴"
            chart_value += f"**신호**: {signal_emoji} {pearl['cross_signal']} 발생!\n"
        
        # RSI
        rsi = pearl['rsi']
        if rsi >= 70:
            rsi_status = "과매수 (조정 가능성)"
        elif rsi <= 30:
            rsi_status = "과매도 (반등 가능성)"
        else:
            rsi_status = "중립"
        chart_value += f"**RSI(14)**: {rsi:.1f} - {rsi_status}"
        
        embed["fields"].append({
            "name": "📊 펄어비스 차트 분석",
            "value": chart_value,
            "inline": False
        })
        
        # 수급 현황
        supply_value = ""
        
        # 외국인/기관 순매수 현황
        if pearl['foreign_net'] > 0:
            supply_value += f"**외국인**: 🟢 순매수 {abs(pearl['foreign_net']):.1f}%\n"
        elif pearl['foreign_net'] < 0:
            supply_value += f"**외국인**: 🔴 순매도 {abs(pearl['foreign_net']):.1f}%\n"
        else:
            supply_value += f"**외국인**: ⚪ 보합\n"
        
        if pearl['institution_net'] > 0:
            supply_value += f"**기관**: 🟢 순매수 {abs(pearl['institution_net']):.1f}%\n"
        elif pearl['institution_net'] < 0:
            supply_value += f"**기관**: 🔴 순매도 {abs(pearl['institution_net']):.1f}%\n"
        else:
            supply_value += f"**기관**: ⚪ 보합\n"
        
        # 공매도 비율
        if pearl['short_ratio'] > 10:
            supply_value += f"**공매도 비율**: 🔴 {pearl['short_ratio']:.2f}% (높음)"
        elif pearl['short_ratio'] > 5:
            supply_value += f"**공매도 비율**: 🟡 {pearl['short_ratio']:.2f}% (보통)"
        elif pearl['short_ratio'] > 0:
            supply_value += f"**공매도 비율**: 🟢 {pearl['short_ratio']:.2f}% (낮음)"
        else:
            supply_value += f"**공매도 비율**: 데이터 없음"
        
        embed["fields"].append({
            "name": "💰 펄어비스 수급 현황",
            "value": supply_value,
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
        print(f"\n[차트 분석]")
        print(f"MA5: {int(p['ma5']):,}원 | MA20: {int(p['ma20']):,}원 | MA60: {int(p['ma60']):,}원")
        if p['cross_signal']:
            print(f"신호: {p['cross_signal']} 발생!")
        print(f"RSI(14): {p['rsi']:.1f}")
        print(f"\n[수급 현황]")
        print(f"외국인 순매수: {p['foreign_net']:+.1f}%")
        print(f"기관 순매수: {p['institution_net']:+.1f}%")
        print(f"공매도 잔고비율: {p['short_ratio']:.2f}%")
    
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
