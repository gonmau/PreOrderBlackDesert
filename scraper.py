import requests
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime

# 설정
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK')
DATA_FILE = 'rank_history.csv'

# 국가 설정
COUNTRIES = ["미국", "일본", "홍콩", "인도", "영국", "독일", "프랑스", "멕시코", "캐나다", "한국", "호주", "브라질", "스페인"]

def get_real_rank(country):
    """
    실제 데이터 수집 로직 (PS Store API 혹은 트래커 활용)
    여기서는 시뮬레이션 데이터를 생성합니다. 
    (실제 구현 시 위에서 드린 API 접근 로직을 결합)
    """
    import random
    return random.randint(5, 25) # 실제 데이터로 교체되는 부분

def save_and_plot():
    today = datetime.now().strftime('%Y-%m-%d')
    new_data = {'date': today}
    
    # 1. 데이터 수집
    for c in COUNTRIES:
        new_data[c] = get_real_rank(c)
    
    # 2. CSV 저장
    df = pd.read_csv(DATA_FILE) if os.path.exists(DATA_FILE) else pd.DataFrame()
    df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    
    # 3. 그래프 생성 (최근 14일치)
    plt.figure(figsize=(12, 6))
    for c in COUNTRIES:
        plt.plot(df['date'].tail(14), df[c].tail(14), marker='o', label=c)
    
    plt.gca().invert_yaxis() # 순위이므로 y축 반전
    plt.title("붉은사막(Crimson Desert) PS5 글로벌 순위 변동 추세")
    plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
    plt.grid(True, linestyle='--')
    plt.tight_layout()
    plt.savefig('rank_trend.png')

def send_to_discord():
    # 텍스트 메시지 구성
    today_rank = pd.read_csv(DATA_FILE).iloc[-1]
    msg = f"📊 **붉은사막 글로벌 순위 리포트 ({today_rank['date']})**\n"
    for c in COUNTRIES:
        msg += f"{c.ljust(6)}: {int(today_rank[c])}위\n"
    
    # 파일과 함께 전송
    with open('rank_trend.png', 'rb') as f:
        requests.post(DISCORD_WEBHOOK_URL, data={'content': msg}, files={'file': f})

if __name__ == "__main__":
    save_and_plot()
    send_to_discord()
