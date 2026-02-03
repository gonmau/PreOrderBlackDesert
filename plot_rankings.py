#!/usr/bin/env python3
"""
일별 국가별 S,D 순위 그래프 생성 스크립트
"""
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os
import requests
from pathlib import Path

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

def load_data(filepath):
    """JSON 데이터 로드"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_data(data):
    """데이터 파싱 및 구조화"""
    countries = set()
    dates = []
    
    # 모든 국가 목록 추출
    for entry in data:
        countries.update(entry['raw_results'].keys())
        dates.append(datetime.fromisoformat(entry['timestamp']))
    
    countries = sorted(list(countries))
    
    # 국가별 데이터 구조 생성
    country_data = {
        country: {
            'dates': [],
            'standard': [],
            'deluxe': []
        }
        for country in countries
    }
    
    # 데이터 채우기
    for entry in data:
        date = datetime.fromisoformat(entry['timestamp'])
        for country in countries:
            if country in entry['raw_results']:
                country_data[country]['dates'].append(date)
                country_data[country]['standard'].append(entry['raw_results'][country]['standard'])
                country_data[country]['deluxe'].append(entry['raw_results'][country]['deluxe'])
    
    return country_data, sorted(dates)

def plot_country_rankings(country_data, output_dir='output'):
    """각 국가별 S,D 순위 그래프 생성"""
    os.makedirs(output_dir, exist_ok=True)
    
    for country, data in country_data.items():
        if not data['dates']:
            continue
            
        fig, ax = plt.subplots(figsize=(14, 7))
        
        # 순위 그래프 (낮을수록 좋으므로 y축 반전)
        ax.plot(data['dates'], data['standard'], 'o-', label='Standard', linewidth=2, markersize=4)
        ax.plot(data['dates'], data['deluxe'], 's-', label='Deluxe', linewidth=2, markersize=4)
        
        # 축 설정
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Rank', fontsize=12)
        ax.set_title(f'{country} - Daily Ranking Trends', fontsize=14, fontweight='bold')
        ax.invert_yaxis()  # 순위는 낮을수록 좋음
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        
        # 날짜 포맷 설정
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(data['dates'])//10)))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # 파일명에서 특수문자 제거
        safe_country = country.replace('/', '_').replace('\\', '_')
        plt.savefig(f'{output_dir}/{safe_country}_ranking.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f'✓ Generated: {safe_country}_ranking.png')

def plot_all_countries_standard(country_data, output_dir='output'):
    """모든 국가의 Standard 순위를 하나의 그래프에"""
    os.makedirs(output_dir, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(16, 10))
    
    for country, data in sorted(country_data.items()):
        if data['dates']:
            ax.plot(data['dates'], data['standard'], 'o-', label=country, linewidth=1.5, markersize=3, alpha=0.7)
    
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Rank', fontsize=12)
    ax.set_title('All Countries - Standard Ranking Trends', fontsize=14, fontweight='bold')
    ax.invert_yaxis()
    ax.grid(True, alpha=0.3)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/all_countries_standard.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f'✓ Generated: all_countries_standard.png')

def plot_all_countries_deluxe(country_data, output_dir='output'):
    """모든 국가의 Deluxe 순위를 하나의 그래프에"""
    os.makedirs(output_dir, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(16, 10))
    
    for country, data in sorted(country_data.items()):
        if data['dates']:
            ax.plot(data['dates'], data['deluxe'], 's-', label=country, linewidth=1.5, markersize=3, alpha=0.7)
    
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Rank', fontsize=12)
    ax.set_title('All Countries - Deluxe Ranking Trends', fontsize=14, fontweight='bold')
    ax.invert_yaxis()
    ax.grid(True, alpha=0.3)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/all_countries_deluxe.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f'✓ Generated: all_countries_deluxe.png')

def send_discord_notification(webhook_url, country_data, dates, output_dir='output'):
    """디스코드 웹훅으로 알림 전송"""
    if not webhook_url:
        print('⚠️  Discord webhook URL not provided, skipping notification')
        return
    
    try:
        # 기본 통계 계산
        num_countries = len(country_data)
        date_range = f"{dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}"
        
        # 최근 순위 변화가 큰 국가 찾기
        top_changes = []
        for country, data in country_data.items():
            if len(data['standard']) >= 2:
                change = abs(data['standard'][-1] - data['standard'][-2])
                top_changes.append((country, change, data['standard'][-1]))
        
        top_changes.sort(key=lambda x: x[1], reverse=True)
        top_5_changes = top_changes[:5]
        
        # 디스코드 임베드 메시지 생성
        embed = {
            "title": "📊 Ranking Graphs Generated!",
            "description": f"새로운 순위 그래프가 생성되었습니다.",
            "color": 5814783,  # 파란색
            "fields": [
                {
                    "name": "📅 Date Range",
                    "value": date_range,
                    "inline": False
                },
                {
                    "name": "🌍 Countries",
                    "value": str(num_countries),
                    "inline": True
                },
                {
                    "name": "📈 Total Graphs",
                    "value": f"{num_countries + 2} files",
                    "inline": True
                }
            ],
            "footer": {
                "text": "Ranking Visualization Bot"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 최근 변화가 큰 국가 추가
        if top_5_changes:
            changes_text = "\n".join([
                f"**{country}**: Rank {rank} (±{int(change)})"
                for country, change, rank in top_5_changes
            ])
            embed["fields"].append({
                "name": "🔥 Top Ranking Changes (Standard)",
                "value": changes_text,
                "inline": False
            })
        
        # 웹훅으로 전송
        payload = {
            "username": "Ranking Bot",
            "embeds": [embed]
        }
        
        response = requests.post(webhook_url, json=payload)
        
        if response.status_code == 204:
            print('✅ Discord notification sent successfully!')
        else:
            print(f'⚠️  Discord notification failed: {response.status_code}')
            
    except Exception as e:
        print(f'❌ Error sending Discord notification: {e}')

def main():
    """메인 실행 함수"""
    # 데이터 파일 경로
    data_file = 'rank_history__2_.json'
    
    # 디스코드 웹훅 URL (환경 변수에서 가져오기)
    discord_webhook = os.environ.get('DISCORD_WEBHOOK_URL', '')
    
    if not os.path.exists(data_file):
        print(f'❌ Error: {data_file} not found')
        return
    
    print('📊 Loading data...')
    data = load_data(data_file)
    
    print('📈 Parsing data...')
    country_data, dates = parse_data(data)
    
    print(f'📅 Date range: {dates[0].date()} to {dates[-1].date()}')
    print(f'🌍 Countries: {len(country_data)}')
    print()
    
    print('🎨 Generating individual country plots...')
    plot_country_rankings(country_data)
    print()
    
    print('🎨 Generating combined Standard plot...')
    plot_all_countries_standard(country_data)
    print()
    
    print('🎨 Generating combined Deluxe plot...')
    plot_all_countries_deluxe(country_data)
    print()
    
    print('✅ All plots generated successfully!')
    print(f'📁 Output directory: output/')
    print()
    
    # 디스코드 알림 전송
    if discord_webhook:
        print('📤 Sending Discord notification...')
        send_discord_notification(discord_webhook, country_data, dates)
    else:
        print('ℹ️  Set DISCORD_WEBHOOK_URL environment variable to enable notifications')

if __name__ == '__main__':
    main()
