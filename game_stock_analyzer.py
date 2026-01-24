import pandas as pd
import requests
from datetime import datetime
import json
import os

# 게임 테마주 목록
GAME_STOCKS = {
    '036570.KS': '엔씨소프트',
    '251270.KS': '넷마블',
    '263750.KQ': '펄어비스',
    '112040.KQ': '위메이드',
    '259960.KS': '크래프톤',
    '293490.KQ': '카카오게임즈',
    '194480.KQ': '데브시스터즈',
    '225570.KQ': '넥슨게임즈',
    '095660.KQ': '네오위즈',
    '376300.KQ': '디어유'
}

DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')

def get_stock_data(symbol):
    """Yahoo Finance API로 주식 데이터 수집"""
    try:
        # Yahoo Finance API
        base_url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
        params = {
            'modules': 'price,summaryDetail,defaultKeyStatistics'
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"  HTTP {response.status_code}")
            return None
        
        data = response.json()
        result = data['quoteSummary']['result'][0]
        
        price_data = result.get('price', {})
        summary = result.get('summaryDetail', {})
        stats = result.get('defaultKeyStatistics', {})
        
        # 현재가
        price = price_data.get('regularMarketPrice', {}).get('raw', 0)
        
        # 시가총액 (원화)
        market_cap_raw = price_data.get('marketCap', {}).get('raw', 0)
        market_cap = market_cap_raw / 1000000000000  # 조원
        
        # PER
        per = summary.get('trailingPE', {}).get('raw', 0) or stats.get('trailingPE', {}).get('raw', 0)
        
        # PBR
        pbr = summary.get('priceToBook', {}).get('raw', 0) or stats.get('priceToBook', {}).get('raw', 0)
        
        if price == 0:
            print(f"  가격 데이터 없음")
            return None
        
        return {
            'price': int(price),
            'market_cap': round(market_cap, 2),
            'per': round(float(per), 2) if per else 0,
            'pbr': round(float(pbr), 2) if pbr else 0
        }
        
    except Exception as e:
        print(f"  오류: {str(e)}")
        return None

def send_discord_notification(df, avg_per, avg_pbr, undervalued, leader):
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
            "text": "게임테마주 자동 분석 시스템"
        },
        "timestamp": datetime.now().isoformat()
    }
    
    # 섹터 평균
    if avg_per > 0 or avg_pbr > 0:
        embed["fields"].append({
            "name": "📊 섹터 평균",
            "value": f"```\nPER: {avg_per:.2f}배\nPBR: {avg_pbr:.2f}배\n```",
            "inline": False
        })
    
    # 대장주
    embed["fields"].append({
        "name": "👑 테마 대장주 (시총 기준)",
        "value": f"**{leader['name']}**\n시총: {leader['market_cap']}조원 | PER: {leader['per']}배 | PBR: {leader['pbr']}배",
        "inline": False
    })
    
    # 저평가 종목
    if len(undervalued) > 0:
        undervalued_text = "\n".join([
            f"• **{row['name']}**: {int(row['price']):,}원 (PER {row['per']}배, PBR {row['pbr']}배)"
            for _, row in undervalued.head(5).iterrows()
        ])
        embed["fields"].append({
            "name": "💎 저평가 종목 (PER/PBR 기준)",
            "value": undervalued_text,
            "inline": False
        })
    else:
        embed["fields"].append({
            "name": "💎 저평가 종목",
            "value": "해당 없음",
            "inline": False
        })
    
    # 펄어비스 특별 분석
    if pearl is not None and pearl['price'] > 0:
        pearl_status = "🟢 저평가" if pearl['undervalued'] else "🔴 고평가" if avg_per > 0 else "⚪ 데이터 부족"
        pearl_value = f"{pearl_status}\n```\n현재가: {int(pearl['price']):,}원\n시가총액: {pearl['market_cap']}조원\n"
        
        if pearl['per'] > 0:
            if avg_per > 0:
                diff = pearl['per'] - avg_per
                pearl_value += f"PER: {pearl['per']}배 (평균 {'+' if diff > 0 else ''}{diff:.2f})\n"
            else:
                pearl_value += f"PER: {pearl['per']}배\n"
        
        if pearl['pbr'] > 0:
            if avg_pbr > 0:
                diff = pearl['pbr'] - avg_pbr
                pearl_value += f"PBR: {pearl['pbr']}배 (평균 {'+' if diff > 0 else ''}{diff:.2f})\n"
            else:
                pearl_value += f"PBR: {pearl['pbr']}배\n"
        
        pearl_value += "```"
        
        embed["fields"].append({
            "name": "⭐ 펄어비스 상세",
            "value": pearl_value,
            "inline": False
        })
    
    # 상위 5개 종목
    top5 = df.head(5)
    top5_text = "\n".join([
        f"{i+1}. **{row['name']}**: {row['market_cap']}조원"
        for i, (_, row) in enumerate(top5.iterrows())
    ])
    embed["fields"].append({
        "name": "📈 시총 상위 5개 종목",
        "value": top5_text,
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
    
    for symbol, name in GAME_STOCKS.items():
        print(f"분석중: {name} ({symbol})...")
        data = get_stock_data(symbol)
        
        if data:
            data['symbol'] = symbol
            data['name'] = name
            results.append(data)
            print(f"  ✓ 가격: {data['price']:,}원, 시총: {data['market_cap']}조원")
    
    if not results:
        print("\n❌ 데이터 수집 실패 - Yahoo Finance API 접근 불가")
        print("대안: FinanceDataReader 설치 후 사용 (pip install finance-datareader)")
        return
    
    df = pd.DataFrame(results)
    
    # 섹터 평균
    valid_per = df[df['per'] > 0]['per']
    valid_pbr = df[df['pbr'] > 0]['pbr']
    
    avg_per = valid_per.mean() if len(valid_per) > 0 else 0
    avg_pbr = valid_pbr.mean() if len(valid_pbr) > 0 else 0
    
    # 저평가 판단
    if avg_per > 0 and avg_pbr > 0:
        df['undervalued'] = ((df['per'] > 0) & (df['per'] < avg_per) & 
                             (df['pbr'] > 0) & (df['pbr'] < avg_pbr))
    else:
        df['undervalued'] = False
    
    # 시가총액 기준 정렬
    df = df.sort_values('market_cap', ascending=False)
    
    print("\n" + "=" * 60)
    print("분석 결과")
    print("=" * 60)
    print(f"\n섹터 평균 PER: {avg_per:.2f}배")
    print(f"섹터 평균 PBR: {avg_pbr:.2f}배")
    
    print("\n[전체 종목]")
    print(df[['name', 'price', 'market_cap', 'per', 'pbr', 'undervalued']].to_string(index=False))
    
    print("\n[저평가 종목]")
    undervalued = df[df['undervalued'] == True]
    if len(undervalued) > 0:
        print(undervalued[['name', 'price', 'market_cap', 'per', 'pbr']].to_string(index=False))
    else:
        print("해당 없음")
    
    print("\n[대장주]")
    leader = df.iloc[0]
    print(f"{leader['name']}: 시총 {leader['market_cap']}조원")
    
    # 펄어비스 분석
    print("\n" + "=" * 60)
    print("펄어비스 상세 분석")
    print("=" * 60)
    pearl = df[df['name'] == '펄어비스']
    if len(pearl) > 0:
        p = pearl.iloc[0]
        print(f"현재가: {int(p['price']):,}원")
        print(f"시가총액: {p['market_cap']}조원")
        if p['per'] > 0:
            status = "저평가" if avg_per > 0 and p['per'] < avg_per else "고평가" if avg_per > 0 else ""
            print(f"PER: {p['per']}배 {status}")
        if p['pbr'] > 0:
            status = "저평가" if avg_pbr > 0 and p['pbr'] < avg_pbr else "고평가" if avg_pbr > 0 else ""
            print(f"PBR: {p['pbr']}배 {status}")
        print(f"종합 평가: {'저평가' if p['undervalued'] else '고평가 또는 적정'}")
    
    # 디스코드 알림
    print("\n" + "=" * 60)
    send_discord_notification(df, avg_per, avg_pbr, undervalued, leader)
    
    # 파일 저장
    df.to_csv('game_stocks_analysis.csv', index=False, encoding='utf-8-sig')
    print(f"결과 저장: game_stocks_analysis.csv")
    
    result_json = {
        'timestamp': datetime.now().isoformat(),
        'sector_avg': {
            'per': round(avg_per, 2),
            'pbr': round(avg_pbr, 2)
        },
        'stocks': df.to_dict('records'),
        'undervalued': undervalued.to_dict('records'),
        'leader': leader.to_dict()
    }
    
    with open('game_stocks_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(result_json, f, ensure_ascii=False, indent=2)
    
    print("결과 저장: game_stocks_analysis.json")
    print("=" * 60)

if __name__ == "__main__":
    analyze_stocks()
