import os
import requests
from datetime import datetime
import pytz

# 환경 변수
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

class ExchangeRateBot:
    def __init__(self):
        # 한국수출입은행 환율 API (무료, 인증 불필요)
        self.api_url = "https://www.koreaexim.go.kr/site/program/financial/exchangeJSON"
        
    def get_exchange_rate(self):
        """환율 정보 조회 (한국수출입은행 API)"""
        params = {
            "authkey": "nrKMMXyRWF0FXu9qzYVzCHyi0nDJWEUe",  # 공개 테스트 키
            "data": "AP01"  # 환율 데이터
        }
        
        try:
            res = requests.get(self.api_url, params=params)
            data = res.json()
            
            # USD 찾기
            for item in data:
                if item['cur_unit'] == 'USD':
                    return {
                        'rate': float(item['deal_bas_r'].replace(',', '')),
                        'change': float(item['change_rate'].replace(',', '')) if 'change_rate' in item else 0,
                        'currency_name': item['cur_nm']
                    }
        except Exception as e:
            print(f"환율 조회 실패: {e}")
        
        return None
    
    def get_exchangerate_api(self):
        """대체 API - ExchangeRate-API.com (무료)"""
        try:
            res = requests.get("https://api.exchangerate-api.com/v4/latest/USD")
            data = res.json()
            
            if 'rates' in data and 'KRW' in data['rates']:
                return {
                    'rate': data['rates']['KRW'],
                    'change': 0,  # 변동률은 제공 안됨
                    'currency_name': '미국 달러'
                }
        except Exception as e:
            print(f"대체 API 조회 실패: {e}")
        
        return None
    
    def send_discord_message(self, exchange_info):
        """디스코드 메시지 전송"""
        if not DISCORD_WEBHOOK_URL:
            print("Discord Webhook URL이 설정되지 않았습니다.")
            print(f"현재 환율: {exchange_info['rate']:,.2f}원")
            return
        
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        
        # 변동 방향에 따라 색상 결정
        if exchange_info['change'] > 0:
            color = 0xFF0000  # 빨강 (원화 약세)
            emoji = "🔴"
            direction = "상승 (원화 약세)"
        elif exchange_info['change'] < 0:
            color = 0x0000FF  # 파랑 (원화 강세)
            emoji = "🔵"
            direction = "하락 (원화 강세)"
        else:
            color = 0x00FF00  # 초록
            emoji = "💚"
            direction = "현재 환율"
        
        fields = [
            {
                "name": "현재 환율",
                "value": f"**{exchange_info['rate']:,.2f}원**",
                "inline": True
            }
        ]
        
        # 변동률 정보가 있으면 추가
        if exchange_info['change'] != 0:
            fields.append({
                "name": "전일 대비",
                "value": f"{exchange_info['change']:+,.2f}원",
                "inline": True
            })
        
        fields.append({
            "name": "통화",
            "value": exchange_info['currency_name'],
            "inline": True
        })
        
        embed = {
            "title": f"{emoji} USD/KRW 환율 정보",
            "color": color,
            "description": direction,
            "fields": fields,
            "footer": {
                "text": "한국수출입은행 환율 API"
            },
            "timestamp": now.isoformat()
        }
        
        data = {
            "content": f"💵 **환율 알림** ({now.strftime('%Y-%m-%d %H:%M')})",
            "embeds": [embed]
        }
        
        try:
            res = requests.post(DISCORD_WEBHOOK_URL, json=data)
            if res.status_code == 204:
                print("메시지 전송 성공")
            else:
                print(f"메시지 전송 실패: {res.status_code}")
        except Exception as e:
            print(f"메시지 전송 오류: {e}")
    
    def run(self):
        """환율 정보 조회 및 전송"""
        # 메인 API 시도
        exchange_info = self.get_exchange_rate()
        
        # 실패시 대체 API 시도
        if not exchange_info:
            print("메인 API 실패, 대체 API 시도...")
            exchange_info = self.get_exchangerate_api()
        
        if exchange_info:
            print(f"현재 환율: {exchange_info['rate']:,.2f}원")
            if exchange_info['change'] != 0:
                print(f"전일대비: {exchange_info['change']:+,.2f}원")
            self.send_discord_message(exchange_info)
        else:
            print("모든 환율 API 조회 실패")

if __name__ == "__main__":
    bot = ExchangeRateBot()
    bot.run()