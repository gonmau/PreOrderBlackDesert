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
from io import BytesIO

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

def create_ranking_table(data, output_dir='output'):
    """에디션별, 나라별 순위를 표로 생성 (PNG 이미지) - Standard와 Deluxe 각각 생성"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 최신 데이터 가져오기
    latest_entry = data[-1]
    timestamp = datetime.fromisoformat(latest_entry['timestamp'])
    raw_results = latest_entry['raw_results']
    
    table_paths = []
    
    # 1. Standard Edition 표
    countries_sorted_std = sorted(
        raw_results.items(),
        key=lambda x: x[1]['standard'] if x[1]['standard'] is not None else 999
    )
    
    std_table_data = []
    for rank, (country, ranks) in enumerate(countries_sorted_std, 1):
        std_rank = ranks['standard'] if ranks['standard'] is not None else '-'
        if std_rank != '-':
            std_table_data.append([rank, country, std_rank])
    
    # Standard 표 생성
    fig, ax = plt.subplots(figsize=(8, max(8, len(std_table_data) * 0.3)))
    ax.axis('tight')
    ax.axis('off')
    
    headers_std = ['#', 'Country', 'Rank']
    
    table_std = ax.table(
        cellText=std_table_data,
        colLabels=headers_std,
        cellLoc='center',
        loc='center',
        colWidths=[0.15, 0.6, 0.25]
    )
    
    table_std.auto_set_font_size(False)
    table_std.set_fontsize(10)
    table_std.scale(1, 2)
    
    # 헤더 스타일
    for i in range(3):
        cell = table_std[(0, i)]
        cell.set_facecolor('#4472C4')
        cell.set_text_props(weight='bold', color='white')
    
    # 행 스타일
    for i in range(1, len(std_table_data) + 1):
        for j in range(3):
            cell = table_std[(i, j)]
            if i % 2 == 0:
                cell.set_facecolor('#E7E6E6')
            else:
                cell.set_facecolor('#FFFFFF')
    
    plt.tight_layout()
    std_table_path = f'{output_dir}/ranking_table_standard.png'
    plt.savefig(std_table_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f'✓ Generated: ranking_table_standard.png')
    table_paths.append(std_table_path)
    
    # 2. Deluxe Edition 표
    countries_sorted_dlx = sorted(
        raw_results.items(),
        key=lambda x: x[1]['deluxe'] if x[1]['deluxe'] is not None else 999
    )
    
    dlx_table_data = []
    for rank, (country, ranks) in enumerate(countries_sorted_dlx, 1):
        dlx_rank = ranks['deluxe'] if ranks['deluxe'] is not None else '-'
        if dlx_rank != '-':
            dlx_table_data.append([rank, country, dlx_rank])
    
    # Deluxe 표 생성
    fig, ax = plt.subplots(figsize=(8, max(8, len(dlx_table_data) * 0.3)))
    ax.axis('tight')
    ax.axis('off')
    
    headers_dlx = ['#', 'Country', 'Rank']
    
    table_dlx = ax.table(
        cellText=dlx_table_data,
        colLabels=headers_dlx,
        cellLoc='center',
        loc='center',
        colWidths=[0.15, 0.6, 0.25]
    )
    
    table_dlx.auto_set_font_size(False)
    table_dlx.set_fontsize(10)
    table_dlx.scale(1, 2)
    
    # 헤더 스타일
    for i in range(3):
        cell = table_dlx[(0, i)]
        cell.set_facecolor('#ED7D31')
        cell.set_text_props(weight='bold', color='white')
    
    # 행 스타일
    for i in range(1, len(dlx_table_data) + 1):
        for j in range(3):
            cell = table_dlx[(i, j)]
            if i % 2 == 0:
                cell.set_facecolor('#FFF2CC')
            else:
                cell.set_facecolor('#FFFFFF')
    
    plt.tight_layout()
    dlx_table_path = f'{output_dir}/ranking_table_deluxe.png'
    plt.savefig(dlx_table_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f'✓ Generated: ranking_table_deluxe.png')
    table_paths.append(dlx_table_path)
    
    return table_paths

def get_latest_rankings(data):
    """최신 순위 데이터를 딕셔너리 형태로 반환"""
    latest_entry = data[-1]
    timestamp = datetime.fromisoformat(latest_entry['timestamp'])
    
    # Standard 순위로 정렬
    countries_sorted = sorted(
        latest_entry['raw_results'].items(),
        key=lambda x: x[1]['standard'] if x[1]['standard'] is not None else 999
    )
    
    return {
        'timestamp': timestamp,
        'rankings': countries_sorted
    }

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
        print('⚠️  No data to plot for daily averages')
        return
    
    # 그래프 생성
    fig, ax = plt.subplots(figsize=(14, 7))
    
    ax.plot(dates, standard_avgs, 'o-', label='Standard Average', linewidth=2, markersize=6, color='#2E86DE')
    ax.plot(dates, deluxe_avgs, 's-', label='Deluxe Average', linewidth=2, markersize=6, color='#EE5A6F')
    
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Average Rank', fontsize=12)
    ax.set_title('Daily Average Rankings - Standard vs Deluxe', fontsize=14, fontweight='bold')
    ax.invert_yaxis()
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/daily_averages.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f'✓ Generated: daily_averages.png')

def plot_top_countries(country_data, countries_to_plot, output_dir='output'):
    """주요 국가들의 Standard와 Deluxe 순위 비교"""
    os.makedirs(output_dir, exist_ok=True)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))
    
    # Standard 그래프
    for country in countries_to_plot:
        if country in country_data and country_data[country]['dates']:
            data = country_data[country]
            ax1.plot(data['dates'], data['standard'], 'o-', label=country, linewidth=2, markersize=4)
            
            # 최근 순위 표시
            if data['standard'] and data['standard'][-1] is not None:
                last_date = data['dates'][-1]
                last_rank = data['standard'][-1]
                ax1.annotate(f'{int(last_rank)}', 
                           xy=(last_date, last_rank),
                           xytext=(5, 0), textcoords='offset points',
                           fontsize=8, fontweight='bold')
    
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('Rank', fontsize=12)
    ax1.set_title('Major Countries - Standard Ranking', fontsize=14, fontweight='bold')
    ax1.invert_yaxis()
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=10)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    
    # Deluxe 그래프
    for country in countries_to_plot:
        if country in country_data and country_data[country]['dates']:
            data = country_data[country]
            ax2.plot(data['dates'], data['deluxe'], 's-', label=country, linewidth=2, markersize=4)
            
            # 최근 순위 표시
            if data['deluxe'] and data['deluxe'][-1] is not None:
                last_date = data['dates'][-1]
                last_rank = data['deluxe'][-1]
                ax2.annotate(f'{int(last_rank)}', 
                           xy=(last_date, last_rank),
                           xytext=(5, 0), textcoords='offset points',
                           fontsize=8, fontweight='bold')
    
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('Rank', fontsize=12)
    ax2.set_title('Major Countries - Deluxe Ranking', fontsize=14, fontweight='bold')
    ax2.invert_yaxis()
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=10)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/top_countries_rankings.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f'✓ Generated: top_countries_rankings.png')

def send_latest_rankings_to_discord(webhook_url, latest_rankings, table_paths):
    """오늘 날짜 최신 순위를 디스코드로 전송 (Standard와 Deluxe 표 모두 포함)"""
    if not webhook_url:
        print('⚠️  Discord webhook URL not provided, skipping latest rankings notification')
        return
    
    try:
        timestamp = latest_rankings['timestamp']
        rankings = latest_rankings['rankings']
        
        # Top 10 국가 추출
        top_10 = rankings[:10]
        
        # 임베드 필드 생성 (Standard 순위)
        ranking_text = ""
        for idx, (country, ranks) in enumerate(top_10, 1):
            std_rank = ranks['standard'] if ranks['standard'] is not None else '-'
            dlx_rank = ranks['deluxe'] if ranks['deluxe'] is not None else '-'
            
            # 메달 이모지 추가
            medal = ""
            if idx == 1:
                medal = "🥇 "
            elif idx == 2:
                medal = "🥈 "
            elif idx == 3:
                medal = "🥉 "
            
            ranking_text += f"{medal}**{idx}. {country}**\n"
            ranking_text += f"   Standard: #{std_rank} | Deluxe: #{dlx_rank}\n"
        
        # 디스코드 임베드 메시지 생성
        embed = {
            "title": "📊 Latest Rankings Update",
            "description": f"**{timestamp.strftime('%Y-%m-%d %H:%M:%S')}** 기준 최신 순위",
            "color": 3066993,  # 초록색
            "fields": [
                {
                    "name": "🏆 Top 10 Countries (by Standard Edition)",
                    "value": ranking_text,
                    "inline": False
                },
                {
                    "name": "📈 Total Countries Tracked",
                    "value": str(len(rankings)),
                    "inline": True
                }
            ],
            "footer": {
                "text": "Ranking Bot | Auto-update"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 표 이미지 첨부 (Standard와 Deluxe 모두)
        files_to_send = {}
        
        # Standard 표
        if len(table_paths) > 0 and os.path.exists(table_paths[0]):
            files_to_send['ranking_table_standard'] = (
                'ranking_table_standard.png',
                open(table_paths[0], 'rb'),
                'image/png'
            )
            embed["image"] = {"url": "attachment://ranking_table_standard.png"}
        
        # Deluxe 표
        if len(table_paths) > 1 and os.path.exists(table_paths[1]):
            files_to_send['ranking_table_deluxe'] = (
                'ranking_table_deluxe.png',
                open(table_paths[1], 'rb'),
                'image/png'
            )
        
        # 웹훅으로 전송
        payload = {
            "username": "Ranking Bot",
            "embeds": [embed]
        }
        
        print(f'📤 Sending latest rankings to Discord...')
        
        if files_to_send:
            response = requests.post(
                webhook_url,
                data={"payload_json": json.dumps(payload)},
                files=files_to_send,
                timeout=30
            )
            for file_tuple in files_to_send.values():
                file_tuple[1].close()
        else:
            response = requests.post(webhook_url, json=payload, timeout=10)
        
        if response.status_code in [200, 204]:
            print('✅ Latest rankings sent to Discord successfully!')
        else:
            print(f'⚠️  Failed to send latest rankings: {response.status_code}')
            print(f'Response: {response.text}')
            
    except Exception as e:
        print(f'❌ Error sending latest rankings to Discord: {e}')

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
    
    # 순위 표 생성
    print('📋 Creating ranking tables...')
    table_paths = create_ranking_table(data)
    print()
    
    # 최신 순위 정보 추출
    latest_rankings = get_latest_rankings(data)
    
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
        # 1. 최신 순위 전송
        print('📤 Sending latest rankings to Discord...')
        send_latest_rankings_to_discord(discord_webhook, latest_rankings, table_paths)
        print()
        
        # 2. 그래프 알림 전송
        print('📤 Sending graph notification to Discord...')
        send_discord_notification(discord_webhook, country_data, dates)
    else:
        print('ℹ️  Set DISCORD_WEBHOOK environment variable to enable notifications')

if __name__ == '__main__':
    main()
