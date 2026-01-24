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
    """FinanceDataReader로 주식 데이터 수집"""
    try:
        import FinanceDataReader as fdr
        
        # 최근 1주일 데이터
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        df = fdr.DataReader(code, start_date, end_date)
        
        if df.empty:
            print(f"  데이터 없음")
            return None
        
        # 최근 종가
        latest = df.iloc[-1]
        price = int(latest['Close'])
        
        # 상장주식수 및 시가총액 추정 (KRX 데이터)
        try:
            # StockListing으로 시가총액 정보 가져오기
            stocks = fdr.StockListing('KRX')
            stock_info = stocks[stocks['Code'] == code]
            
            if not stock_info.empty:
                # 시가총액은 보통 Market Cap 컬럼에 있음 (억원)
                market_cap_col = None
                for col in ['MarketCap', 'Market Cap', 'Marcap', '시가총액']:
                    if col in stock_info.columns:
                        market_cap_col = col
                        break
                
                if market_cap_col:
                    market_cap = float(stock_info.iloc[0][market_cap_col]) / 10000  # 조원
                else:
                    # 컬럼이 없으면 Stocks 컬럼과 Close 가격으로 계산
                    if 'Stocks' in stock_info.columns:
                        stocks_count = float(stock_info.iloc[0]['Stocks'])
                        market_cap = (price * stocks_count) / 1000000000000  # 조원
                    else:
                        market_cap = 0
            else:
                market_cap = 0
                
        except Exception as e:
            print(f"  시총 계산 오류: {e}")
            market_cap = 0
        
        # PER, PBR은 FDR에서 직접 제공하지 않으므로 0으로 설정
        # (별도 API나 크롤링 필요)
        return {
            'price': price,
            'market_cap': round(market_cap, 2),
            'per': 0,  # FDR은 PER 미제공
            'pbr': 0   # FDR은 PBR 미제공
        }
        
    except ImportError:
        print(f"  FinanceDataReader 미설치 - pip install finance-datareader")
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
        "description": f"**분석 시각**: {datetime.now().strftime('%Y-%m-%d %H:%M')} KST",
        "color": 3447003,
        "fields": [],
        "footer": {
            "text": "게임테마주 자동 분석 시스템 (주가 기준)"
        },
        "timestamp": datetime.now().isoformat()
    }
    
    # 대장주
    embed["fields"].append({
        "name": "👑 테마 대장주 (시총 기준)",
        "value": f"**{leader['name']}**\n현재가: {int(leader['price']):,}원 | 시총: {leader['market_cap']}조원",
        "inline": False
    })
    
    # 펄어비스 특별 분석
    if pearl is not None and pearl['price'] > 0:
        pearl_value = f"```\n현재가: {int(pearl['price']):,}원\n시가총액: {pearl['market_cap']}조원\n```"
        
        embed["fields"].append({
            "name": "⭐ 펄어비스 현황",
            "value": pearl_value,
            "inline": False
        })
    
    # 상위 5개 종목
    top5 = df.head(5)
    top5_text = "\n".join([
        f"{i+1}. **{row['name']}**: {int(row['price']):,}원 ({row['market_cap']}조원)"
        for i, (_, row) in enumerate(top5.iterrows())
    ])
    embed["fields"].append({
        "name": "📈 시총 상위 5개 종목",
        "value": top5_text,
        "inline": False
    })
    
    # 전체 종목 가격 현황
    all_stocks_text = "\n".join([
        f"• **{row['name']}**: {int(row['price']):,}원"
        for _, row in df.iterrows()
    ])
    embed["fields"].append({
        "name": "💰 전체 종목 현재가",
        "value": all_stocks_text,
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
    
    print("=" * 60)
    print(f"게임테마주 분석 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    for code, name in GAME_STOCKS.items():
        print(f"분석중: {name} ({code})...")
        data = get_stock_data(code)
        
        if data:
            data['code'] = code
            data['name'] = name
            results.append(data)
            print(f"  ✓ 가격: {data['price']:,}원, 시총: {data['market_cap']}조원")
    
    if not results:
        print("\n❌ 데이터 수집 실패")
        print("FinanceDataReader 설치 확인: pip install finance-datareader")
        return
    
    df = pd.DataFrame(results)
    
    # 시가총액 기준 정렬
    df = df.sort_values('market_cap', ascending=False)
    
    print("\n" + "=" * 60)
    print("분석 결과")
    print("=" * 60)
    
    print("\n[전체 종목]")
    print(df[['name', 'price', 'market_cap']].to_string(index=False))
    
    print("\n[대장주]")
    leader = df.iloc[0]
    print(f"{leader['name']}: 시총 {leader['market_cap']}조원, 현재가 {int(leader['price']):,}원")
    
    # 펄어비스 분석
    print("\n" + "=" * 60)
    print("펄어비스 상세 분석")
    print("=" * 60)
    pearl = df[df['name'] == '펄어비스']
    if len(pearl) > 0:
        p = pearl.iloc[0]
        print(f"현재가: {int(p['price']):,}원")
        print(f"시가총액: {p['market_cap']}조원")
        rank = df[df['name'] == '펄어비스'].index[0] + 1
        print(f"시총 순위: {rank}위 / {len(df)}개 종목")
    
    # 디스코드 알림
    print("\n" + "=" * 60)
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
    print("=" * 60)

if __name__ == "__main__":
    analyze_stocks()
