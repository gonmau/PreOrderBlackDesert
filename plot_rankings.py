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
import matplotlib.font_manager as fm

# 한글 폰트 설정
def setup_korean_font():
    """한글 폰트 설정"""
    try:
        # 시스템에 설치된 한글 폰트 찾기
        font_list = fm.findSystemFonts(fontpaths=None, fontext='ttf')
        korean_fonts = [
            'NanumGothic', 'NanumBarunGothic', 'NanumSquare',
            'Malgun Gothic', 'AppleGothic', 'Noto Sans KR', 'Noto Sans CJK KR'
        ]
        
        for font_path in font_list:
            for korean_font in korean_fonts:
                if korean_font.lower() in font_path.lower():
                    font_name = fm.FontProperties(fname=font_path).get_name()
                    plt.rcParams['font.family'] = font_name
                    plt.rcParams['axes.unicode_minus'] = False
                    print(f'✓ Korean font set: {font_name}')
                    return
        
        # 한글 폰트를 찾지 못한 경우 기본 설정
        print('⚠️  Korean font not found, using default font')
        plt.rcParams['font.family'] = 'DejaVu Sans'
        plt.rcParams['axes.unicode_minus'] = False
        
    except Exception as e:
        print(f'⚠️  Font setup error: {e}')
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
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
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
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
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
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/all_countries_deluxe.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f'✓ Generated: all_countries_deluxe.png')

def plot_daily_averages(country_data, output_dir='output'):
    """일별 Standard와 Deluxe 평균 순위 그래프"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 날짜별로 평균 계산
    date_averages = {}
    
    for country, data in country_data.items():
        for i, date in enumerate(data['dates']):
            date_str = date.strftime('%Y-%m-%d')
            if date_str not in date_averages:
                date_averages[date_str] = {
                    'date': date,
                    'standard': [],
                    'deluxe': []
                }
            # None 값 필터링
            if data['standard'][i] is not None:
                date_averages[date_str]['standard'].append(data['standard'][i])
            if data['deluxe'][i] is not None:
                date_averages[date_str]['deluxe'].append(data['deluxe'][i])
    
    # 날짜별 평균 계산
    dates = []
    standard_avgs = []
    deluxe_avgs = []
    
    for date_str in sorted(date_averages.keys()):
        std_list = date_averages[date_str]['standard']
        dlx_list = date_averages[date_str]['deluxe']
        
        # 데이터가 있는 경우에만 추가
        if std_list and dlx_list:
            dates.append(date_averages[date_str]['date'])
            standard_avgs.append(sum(std_list) / len(std_list))
            deluxe_avgs.append(sum(dlx_list) / len(dlx_list))
    
    if not dates:
        print('⚠️  No data available for daily averages')
        return
    
    # 그래프 생성
    fig, ax = plt.subplots(figsize=(14, 7))
    
    ax.plot(dates, standard_avgs, 'o-', label='Standard Average', linewidth=2, markersize=5, color='#2E86AB')
    ax.plot(dates, deluxe_avgs, 's-', label='Deluxe Average', linewidth=2, markersize=5, color='#A23B72')
    
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Average Rank', fontsize=12)
    ax.set_title('Daily Average Rankings - Standard vs Deluxe', fontsize=14, fontweight='bold')
    ax.invert_yaxis()
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/daily_averages.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f'✓ Generated: daily_averages.png')
    
    # 개별 그래프도 생성
    plot_daily_standard_average(dates, standard_avgs, output_dir)
    plot_daily_deluxe_average(dates, deluxe_avgs, output_dir)

def plot_daily_standard_average(dates, averages, output_dir='output'):
    """일별 Standard 평균 순위만 표시"""
    fig, ax = plt.subplots(figsize=(14, 7))
    
    ax.plot(dates, averages, 'o-', linewidth=2.5, markersize=6, color='#2E86AB')
    ax.fill_between(dates, averages, alpha=0.3, color='#2E86AB')
    
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Average Rank', fontsize=12)
    ax.set_title('Daily Average Ranking - Standard', fontsize=14, fontweight='bold')
    ax.invert_yaxis()
    ax.grid(True, alpha=0.3)
    
    # 최고/최저 평균 표시
    min_rank = min(averages)
    max_rank = max(averages)
    min_idx = averages.index(min_rank)
    max_idx = averages.index(max_rank)
    
    ax.plot(dates[min_idx], min_rank, 'go', markersize=10, label=f'Best Avg: {min_rank:.1f}')
    ax.plot(dates[max_idx], max_rank, 'ro', markersize=10, label=f'Worst Avg: {max_rank:.1f}')
    ax.legend(fontsize=10)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/daily_standard_average.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f'✓ Generated: daily_standard_average.png')

def plot_daily_deluxe_average(dates, averages, output_dir='output'):
    """일별 Deluxe 평균 순위만 표시"""
    fig, ax = plt.subplots(figsize=(14, 7))
    
    ax.plot(dates, averages, 's-', linewidth=2.5, markersize=6, color='#A23B72')
    ax.fill_between(dates, averages, alpha=0.3, color='#A23B72')
    
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Average Rank', fontsize=12)
    ax.set_title('Daily Average Ranking - Deluxe', fontsize=14, fontweight='bold')
    ax.invert_yaxis()
    ax.grid(True, alpha=0.3)
    
    # 최고/최저 평균 표시
    min_rank = min(averages)
    max_rank = max(averages)
    min_idx = averages.index(min_rank)
    max_idx = averages.index(max_rank)
    
    ax.plot(dates[min_idx], min_rank, 'go', markersize=10, label=f'Best Avg: {min_rank:.1f}')
    ax.plot(dates[max_idx], max_rank, 'ro', markersize=10, label=f'Worst Avg: {max_rank:.1f}')
    ax.legend(fontsize=10)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/daily_deluxe_average.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f'✓ Generated: daily_deluxe_average.png')

def send_discord_notification(webhook_url, country_data, dates, output_dir='output'):
    """디스코드 웹훅으로 알림 전송"""
    if not webhook_url:
        print('⚠️  Discord webhook URL not provided, skipping notification')
        return
    
    print(f'🔍 Discord webhook URL: {webhook_url[:50]}...')  # 앞부분만 출력
    
    try:
        # 기본 통계 계산
        num_countries = len(country_data)
        date_range = f"{dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}"
        
        # 최근 순위 변화가 큰 국가 찾기
        top_changes = []
        for country, data in country_data.items():
            if len(data['standard']) >= 2:
                # None 값 체크
                if data['standard'][-1] is not None and data['standard'][-2] is not None:
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
                    "value": f"{num_countries + 5} files",  # 개별 + 통합 + 평균 그래프들
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
        
        print(f'📤 Sending to Discord...')
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        print(f'📬 Response status: {response.status_code}')
        
        if response.status_code == 204:
            print('✅ Discord notification sent successfully!')
        elif response.status_code == 200:
            print('✅ Discord notification sent successfully!')
        else:
            print(f'⚠️  Discord notification failed: {response.status_code}')
            print(f'Response: {response.text}')
            
    except requests.exceptions.Timeout:
        print(f'❌ Discord notification timeout - check your network connection')
    except requests.exceptions.RequestException as e:
        print(f'❌ Discord notification error: {e}')
    except Exception as e:
        print(f'❌ Error sending Discord notification: {e}')

def main():
    """메인 실행 함수"""
    # 한글 폰트 설정
    setup_korean_font()
    
    # 데이터 파일 경로
    data_file = 'rank_history.json'
    
    # 디스코드 웹훅 URL (환경 변수에서 가져오기)
    discord_webhook = os.environ.get('DISCORD_WEBHOOK', '')
    
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
    
    print('🎨 Generating daily average plots...')
    plot_daily_averages(country_data)
    print()
    
    print('✅ All plots generated successfully!')
    print(f'📁 Output directory: output/')
    print()
    
    # 디스코드 알림 전송
    if discord_webhook:
        print('📤 Sending Discord notification...')
        send_discord_notification(discord_webhook, country_data, dates)
    else:
        print('ℹ️  Set DISCORD_WEBHOOK environment variable to enable notifications')

if __name__ == '__main__':
    main()
