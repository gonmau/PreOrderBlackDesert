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
            
            # 최근 날짜의 순위 표시
            if data['standard'] and data['standard'][-1] is not None:
                last_date = data['dates'][-1]
                last_rank = data['standard'][-1]
                ax.annotate(f'{int(last_rank)}', 
                           xy=(last_date, last_rank),
                           xytext=(5, 0), textcoords='offset points',
                           fontsize=7, fontweight='bold',
                           bbox=dict(boxstyle='round,pad=0.2', facecolor='lightblue', alpha=0.6, edgecolor='none'))
    
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
            
            # 최근 날짜의 순위 표시
            if data['deluxe'] and data['deluxe'][-1] is not None:
                last_date = data['dates'][-1]
                last_rank = data['deluxe'][-1]
                ax.annotate(f'{int(last_rank)}', 
                           xy=(last_date, last_rank),
                           xytext=(5, 0), textcoords='offset points',
                           fontsize=7, fontweight='bold',
                           bbox=dict(boxstyle='round,pad=0.2', facecolor='yellow', alpha=0.6, edgecolor='none'))
    
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
    
    ax.plot(dates, deluxe_avgs, 's-', label='Deluxe Average', linewidth=2, markersize=5, color='#A23B72')
    ax.plot(dates, standard_avgs, 'o-', label='Standard Average', linewidth=2, markersize=5, color='#2E86AB')
    
    # 날짜별 순위 표시
    for i, date in enumerate(dates):
        # Deluxe 순위 표시
        ax.annotate(f'{deluxe_avgs[i]:.1f}', 
                   xy=(date, deluxe_avgs[i]),
                   xytext=(0, 8), textcoords='offset points',
                   fontsize=7, ha='center',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.6, edgecolor='none'))
        
        # Standard 순위 표시
        ax.annotate(f'{standard_avgs[i]:.1f}', 
                   xy=(date, standard_avgs[i]),
                   xytext=(0, -12), textcoords='offset points',
                   fontsize=7, ha='center',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.6, edgecolor='none'))
    
    # Standard 최고/최저 표시
    std_min_rank = min(standard_avgs)
    std_max_rank = max(standard_avgs)
    std_min_idx = standard_avgs.index(std_min_rank)
    std_max_idx = standard_avgs.index(std_max_rank)
    ax.plot(dates[std_min_idx], std_min_rank, 'go', markersize=10, label=f'Std Best: {std_min_rank:.1f}', zorder=5)
    ax.plot(dates[std_max_idx], std_max_rank, 'ro', markersize=10, label=f'Std Worst: {std_max_rank:.1f}', zorder=5)
    
    # Deluxe 최고/최저 표시
    dlx_min_rank = min(deluxe_avgs)
    dlx_max_rank = max(deluxe_avgs)
    dlx_min_idx = deluxe_avgs.index(dlx_min_rank)
    dlx_max_idx = deluxe_avgs.index(dlx_max_rank)
    ax.plot(dates[dlx_min_idx], dlx_min_rank, 'g^', markersize=10, label=f'Dlx Best: {dlx_min_rank:.1f}', zorder=5)
    ax.plot(dates[dlx_max_idx], dlx_max_rank, 'r^', markersize=10, label=f'Dlx Worst: {dlx_max_rank:.1f}', zorder=5)
    
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Average Rank', fontsize=12)
    ax.set_title('Crimson Desert PS Pre-Order - Daily Average Rankings - Deluxe vs Standard', fontsize=14, fontweight='bold')
    ax.invert_yaxis()
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10, loc='best')
    
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

def plot_top_countries(country_data, countries_to_plot, output_dir='output'):
    """주요 국가(일본, 미국, 영국, 독일, 프랑스, 한국)의 Standard & Deluxe 순위 그래프"""
    os.makedirs(output_dir, exist_ok=True)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))
    
    # Deluxe 그래프 (위)
    for country in countries_to_plot:
        if country in country_data and country_data[country]['dates']:
            data = country_data[country]
            linewidth = 3 if '한국' in country or 'Korea' in country else 2
            ax1.plot(data['dates'], data['deluxe'], 's-', label=country, 
                    linewidth=linewidth, markersize=5, alpha=0.8)
            
            # 최근 날짜의 순위 표시
            if data['deluxe'] and data['deluxe'][-1] is not None:
                last_date = data['dates'][-1]
                last_rank = data['deluxe'][-1]
                ax1.annotate(f'{int(last_rank)}', 
                           xy=(last_date, last_rank),
                           xytext=(5, 0), textcoords='offset points',
                           fontsize=9, fontweight='bold',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
    
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('Rank', fontsize=12)
    ax1.set_title('Major Countries - Deluxe Ranking Trends', fontsize=14, fontweight='bold')
    ax1.invert_yaxis()
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=10, loc='best')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    
    # Standard 그래프 (아래)
    for country in countries_to_plot:
        if country in country_data and country_data[country]['dates']:
            data = country_data[country]
            linewidth = 3 if '한국' in country or 'Korea' in country else 2
            ax2.plot(data['dates'], data['standard'], 'o-', label=country, 
                    linewidth=linewidth, markersize=5, alpha=0.8)
            
            # 최근 날짜의 순위 표시
            if data['standard'] and data['standard'][-1] is not None:
                last_date = data['dates'][-1]
                last_rank = data['standard'][-1]
                ax2.annotate(f'{int(last_rank)}', 
                           xy=(last_date, last_rank),
                           xytext=(5, 0), textcoords='offset points',
                           fontsize=9, fontweight='bold',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.7))
    
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('Rank', fontsize=12)
    ax2.set_title('Major Countries - Standard Ranking Trends', fontsize=14, fontweight='bold')
    ax2.invert_yaxis()
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=10, loc='best')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/top_countries_rankings.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f'✓ Generated: top_countries_rankings.png')

def send_discord_notification(webhook_url, country_data, dates, output_dir='output'):
    """디스코드 웹훅으로 알림 전송 (그래프 이미지 포함)"""
    if not webhook_url:
        print('⚠️  Discord webhook URL not provided, skipping notification')
        return
    
    print(f'🔍 Discord webhook URL: {webhook_url[:50]}...')  # 앞부분만 출력
    
    try:
        # 기본 통계 계산
        num_countries = len(country_data)
        date_range = f"{dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}"
        
        # 주요 국가 지정 (일본, 미국, 영국, 독일, 프랑스, 한국)
        target_countries = ['일본', '미국', '영국', '독일', '프랑스', '한국']
        countries_to_plot = []
        
        # 실제 데이터에서 해당 국가 찾기
        for target in target_countries:
            # 여러 표기법 체크
            possible_names = [target]
            if target == '한국':
                possible_names.extend(['대한민국', 'Korea', 'South Korea'])
            elif target == '미국':
                possible_names.extend(['USA', 'United States', 'US'])
            elif target == '영국':
                possible_names.extend(['UK', 'United Kingdom', 'Britain'])
            elif target == '독일':
                possible_names.extend(['Germany', 'Deutschland'])
            elif target == '프랑스':
                possible_names.extend(['France'])
            elif target == '일본':
                possible_names.extend(['Japan'])
            
            for name in possible_names:
                if name in country_data:
                    countries_to_plot.append(name)
                    break
        
        # 주요 국가 그래프 생성
        if countries_to_plot:
            plot_top_countries(country_data, countries_to_plot, output_dir)
        
        # 최근 순위 변화가 큰 국가 찾기
        top_changes = []
        for country, data in country_data.items():
            if len(data['standard']) >= 2:
                # None 값 체크 및 실제 변화가 있는 경우만
                if data['standard'][-1] is not None and data['standard'][-2] is not None:
                    change = abs(data['standard'][-1] - data['standard'][-2])
                    if change > 0:  # 변화가 있는 경우만 추가
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
        
        # 주요 국가 정보 추가
        if countries_to_plot:
            countries_text = ", ".join([f"**{country}**" for country in countries_to_plot])
            embed["fields"].append({
                "name": "🌏 Major Countries",
                "value": countries_text,
                "inline": False
            })
        
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
        
        # 주요 그래프 이미지 첨부
        files_to_send = {}
        image_files = [
            ('top_countries_rankings.png', 'top_countries'),  # 새로 추가된 그래프
            ('all_countries_deluxe.png', 'deluxe_chart'),
            ('all_countries_standard.png', 'standard_chart'),
            ('daily_averages.png', 'averages_chart')
        ]
        
        for filename, file_key in image_files:
            filepath = os.path.join(output_dir, filename)
            if os.path.exists(filepath):
                files_to_send[file_key] = (filename, open(filepath, 'rb'), 'image/png')
        
        # 첫 번째 이미지를 임베드에 표시
        if files_to_send:
            embed["image"] = {"url": f"attachment://{image_files[0][0]}"}
        
        # 웹훅으로 전송
        payload = {
            "username": "Ranking Bot",
            "embeds": [embed]
        }
        
        print(f'📤 Sending to Discord with {len(files_to_send)} images...')
        
        if files_to_send:
            # 파일과 함께 전송
            response = requests.post(
                webhook_url, 
                data={"payload_json": json.dumps(payload)},
                files=files_to_send,
                timeout=30
            )
            # 파일 핸들 닫기
            for file_tuple in files_to_send.values():
                file_tuple[1].close()
        else:
            # 파일 없이 전송
            response = requests.post(webhook_url, json=payload, timeout=10)
        
        print(f'📬 Response status: {response.status_code}')
        
        if response.status_code == 204 or response.status_code == 200:
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
