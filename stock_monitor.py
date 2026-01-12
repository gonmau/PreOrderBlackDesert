import os
import requests
import json
from datetime import datetime, timedelta
import pytz

# 환경 변수
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')
KIS_APP_KEY = os.environ.get('KIS_APP_KEY')
KIS_APP_SECRET = os.environ.get('KIS_APP_SECRET')
DART_API_KEY = os.environ.get('DART_API_KEY')

# 모니터링 종목
STOCKS = {
    '263750': {'name': '펄어비스', 'last_price': 0},
    '065350': {'name': '신성델타테크', 'last_price': 0},
    '140410': {'name': '메지온', 'last_price': 0}
}

DART_CORP_CODES = {
    '263750': '00164681',  # 펄어비스
    '065350': '00120361',  # 신성델타테크
    '140410': '00352335'   # 메지온
}

class StockMonitor:
    def __init__(self):
        self.access_token = None
        self.base_url = "https://openapi.koreainvestment.com:9443"
        
    def get_access_token(self):
        """한국투자증권 액세스 토큰 발급"""
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": KIS_APP_KEY,
            "appsecret": KIS_APP_SECRET
        }
        
        try:
            res = requests.post(url, headers=headers, json=body)
            self.access_token = res.json()['access_token']
            return True
        except Exception as e:
            print(f"토큰 발급 실패: {e}")
            return False
    
    def get_current_price(self, stock_code):
        """현재가 조회"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": KIS_APP_KEY,
            "appsecret": KIS_APP_SECRET,
            "tr_id": "FHKST01010100"
        }
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": stock_code
        }
        
        try:
            res = requests.get(url, headers=headers, params=params)
            data = res.json()
            if data['rt_cd'] == '0':
                output = data['output']
                return {
                    'price': int(output['stck_prpr']),
                    'change_rate': float(output['prdy_ctrt']),
                    'volume': int(output['acml_vol'])
                }
        except Exception as e:
            print(f"주가 조회 실패 {stock_code}: {e}")
        return None
    
    def get_exchange_rate(self):
        """환율 정보 조회"""
        url = f"{self.base_url}/uapi/overseas-price/v1/quotations/price"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": KIS_APP_KEY,
            "appsecret": KIS_APP_SECRET,
            "tr_id": "HHDFS00000300"
        }
        params = {
            "AUTH": "",
            "EXCD": "FHS",
            "SYMB": "FX@KRW"
        }
        
        try:
            res = requests.get(url, headers=headers, params=params)
            data = res.json()
            if data['rt_cd'] == '0':
                return float(data['output']['last'])
        except Exception as e:
            print(f"환율 조회 실패: {e}")
        return None
    
    def get_dart_disclosures(self, corp_code, days=1):
        """공시 정보 조회"""
        url = "https://opendart.fss.or.kr/api/list.json"
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        params = {
            "crtfc_key": DART_API_KEY,
            "corp_code": corp_code,
            "bgn_de": start_date.strftime("%Y%m%d"),
            "end_de": end_date.strftime("%Y%m%d"),
            "page_count": 10
        }
        
        try:
            res = requests.get(url, params=params)
            data = res.json()
            if data['status'] == '000' and 'list' in data:
                return data['list']
        except Exception as e:
            print(f"공시 조회 실패: {e}")
        return []
    
    def get_naver_news(self, company_name, count=1):
        """네이버 뉴스 검색 (간단 버전)"""
        # 실제로는 네이버 API 키가 필요하지만, 여기서는 더미 데이터 반환
        return [f"{company_name} 관련 최신 뉴스"]
    
    def send_discord_message(self, content, embeds=None):
        """디스코드 메시지 전송"""
        if not DISCORD_WEBHOOK_URL:
            print("Discord Webhook URL이 설정되지 않았습니다.")
            return
        
        data = {"content": content}
        if embeds:
            data["embeds"] = embeds
        
        try:
            res = requests.post(DISCORD_WEBHOOK_URL, json=data)
            if res.status_code == 204:
                print("메시지 전송 성공")
            else:
                print(f"메시지 전송 실패: {res.status_code}")
        except Exception as e:
            print(f"메시지 전송 오류: {e}")
    
    def morning_report(self):
        """오전 8시 5분 일일 리포트"""
        if not self.get_access_token():
            return
        
        embeds = []
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        
        # 환율 정보
        exchange_rate = self.get_exchange_rate()
        exchange_text = f"💵 USD/KRW: {exchange_rate:,.2f}원" if exchange_rate else "환율 정보 없음"
        
        for stock_code, info in STOCKS.items():
            price_info = self.get_current_price(stock_code)
            
            if price_info:
                STOCKS[stock_code]['last_price'] = price_info['price']
                
                # 공시 정보
                corp_code = DART_CORP_CODES.get(stock_code)
                disclosures = self.get_dart_disclosures(corp_code, days=1) if corp_code else []
                disclosure_text = disclosures[0]['report_nm'] if disclosures else "최근 공시 없음"
                
                # 뉴스 정보
                news = self.get_naver_news(info['name'])
                news_text = news[0] if news else "최근 뉴스 없음"
                
                color = 0xFF0000 if price_info['change_rate'] < 0 else 0x0000FF if price_info['change_rate'] > 0 else 0x808080
                
                embed = {
                    "title": f"📊 {info['name']} ({stock_code})",
                    "color": color,
                    "fields": [
                        {
                            "name": "현재가",
                            "value": f"{price_info['price']:,}원 ({price_info['change_rate']:+.2f}%)",
                            "inline": True
                        },
                        {
                            "name": "거래량",
                            "value": f"{price_info['volume']:,}주",
                            "inline": True
                        },
                        {
                            "name": "📰 최근 뉴스",
                            "value": news_text,
                            "inline": False
                        },
                        {
                            "name": "📋 최근 공시",
                            "value": disclosure_text,
                            "inline": False
                        }
                    ],
                    "timestamp": now.isoformat()
                }
                embeds.append(embed)
        
        self.send_discord_message(
            f"🌅 **주식 모닝 리포트** ({now.strftime('%Y-%m-%d %H:%M')})\n{exchange_text}",
            embeds
        )
    
    def price_monitor(self):
        """주가 변동 모니터링 (±5% 이상)"""
        if not self.get_access_token():
            return
        
        alerts = []
        
        for stock_code, info in STOCKS.items():
            price_info = self.get_current_price(stock_code)
            
            if price_info and abs(price_info['change_rate']) >= 5.0:
                emoji = "🔴" if price_info['change_rate'] < 0 else "🔵"
                alerts.append({
                    "title": f"{emoji} {info['name']} 급등락 알림",
                    "color": 0xFF0000 if price_info['change_rate'] < 0 else 0x0000FF,
                    "fields": [
                        {
                            "name": "현재가",
                            "value": f"{price_info['price']:,}원",
                            "inline": True
                        },
                        {
                            "name": "변동률",
                            "value": f"{price_info['change_rate']:+.2f}%",
                            "inline": True
                        },
                        {
                            "name": "거래량",
                            "value": f"{price_info['volume']:,}주",
                            "inline": True
                        }
                    ]
                })
                
                STOCKS[stock_code]['last_price'] = price_info['price']
        
        # 공시 체크
        for stock_code, info in STOCKS.items():
            corp_code = DART_CORP_CODES.get(stock_code)
            if corp_code:
                disclosures = self.get_dart_disclosures(corp_code, days=0)
                
                for disclosure in disclosures[:1]:  # 최신 1개만
                    alerts.append({
                        "title": f"📋 {info['name']} 공시",
                        "color": 0x00FF00,
                        "fields": [
                            {
                                "name": "공시명",
                                "value": disclosure['report_nm'],
                                "inline": False
                            },
                            {
                                "name": "제출일",
                                "value": disclosure['rcept_dt'],
                                "inline": True
                            }
                        ]
                    })
        
        if alerts:
            kst = pytz.timezone('Asia/Seoul')
            now = datetime.now(kst)
            self.send_discord_message(
                f"⚠️ **주식 알림** ({now.strftime('%Y-%m-%d %H:%M')})",
                alerts
            )
        else:
            print("알림 조건에 해당하는 항목 없음")

def main():
    import sys
    
    monitor = StockMonitor()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "morning":
            monitor.morning_report()
        elif sys.argv[1] == "monitor":
            monitor.price_monitor()
    else:
        print("Usage: python stock_monitor.py [morning|monitor]")

if __name__ == "__main__":
    main()