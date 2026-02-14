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
    """에디션별 순위를 표로 생성 (PNG 이미지) - 같은 순위의 국가들을 열로 배치"""
    os.makedirs(output_dir, exist_ok=True)
    
    # PlayStation 국가별 시장 규모 배율 (점유율)
    ps_market_multiplier = {
        '미국': 10.0, 'USA': 10.0, 'United States': 10.0, 'US': 10.0,
        '일본': 5.0, 'Japan': 5.0,
        '영국': 2.7, 'UK': 2.7, 'United Kingdom': 2.7, 'Britain': 2.7,
        '독일': 2.3, 'Germany': 2.3, 'Deutschland': 2.3,
        '프랑스': 2.0, 'France': 2.0,
        '한국': 1.3, '대한민국': 1.3, 'Korea': 1.3, 'South Korea': 1.3,
        '스페인': 1.0, 'Spain': 1.0, 'España': 1.0,
        '이탈리아': 1.0, 'Italy': 1.0, 'Italia': 1.0,
        '캐나다': 1.0, 'Canada': 1.0,
        '호주': 0.7, 'Australia': 0.7,
        '네덜란드': 0.5, 'Netherlands': 0.5,
        '스웨덴': 0.35, 'Sweden': 0.35,
        '벨기에': 0.35, 'Belgium': 0.35,
        '스위스': 0.35, 'Switzerland': 0.35,
        '오스트리아': 0.27, 'Austria': 0.27,
        '폴란드': 0.27, 'Poland': 0.27,
        '노르웨이': 0.23, 'Norway': 0.23,
        '덴마크': 0.2, 'Denmark': 0.2,
        '핀란드': 0.17, 'Finland': 0.17,
        '포르투갈': 0.17, 'Portugal': 0.17,
    }
    
    # Top 10 시장 국가 목록
    top_10_markets = {'미국', 'USA', 'United States', 'US', '일본', 'Japan', 
                      '영국', 'UK', 'United Kingdom', 'Britain',
                      '독일', 'Germany', 'Deutschland',
                      '프랑스', 'France',
                      '한국', '대한민국', 'Korea', 'South Korea',
                      '스페인', 'Spain', 'España',
                      '이탈리아', 'Italy', 'Italia',
                      '캐나다', 'Canada',
                      '호주', 'Australia'}
    
    # 최신 데이터 가져오기
    latest_entry = data[-1]
    timestamp = datetime.fromisoformat(latest_entry['timestamp'])
    raw_results = latest_entry['raw_results']
    
    table_paths = []
    
    def create_edition_table(edition_name, rank_key, header_color):
        """에디션별 표 생성 - 국가를 열로 배치"""
        # 순위별로 국가 그룹화
        rank_groups = {}
        for country, ranks in raw_results.items():
            rank = ranks[rank_key]
            if rank is not None:
                if rank not in rank_groups:
                    rank_groups[rank] = []
                rank_groups[rank].append(country)
        
        if not rank_groups:
            return None
        
        # 순위 순서대로 정렬
        sorted_ranks = sorted(rank_groups.keys())
        
        # 각 순위의 국가들을 점유율 순으로 정렬
        for rank in sorted_ranks:
            countries = rank_groups[rank]
            rank_groups[rank] = sorted(
                countries, 
                key=lambda c: ps_market_multiplier.get(c, 0.15),
                reverse=True
            )
        
        # 최대 국가 수 찾기 (가장 많은 국가가 있는 순위)
        max_countries = max(len(countries) for countries in rank_groups.values())
        
        # 표 데이터 구성
        table_data = []
        for rank in sorted_ranks:
            countries = rank_groups[rank]
            row = [rank] + countries + [''] * (max_countries - len(countries))
            table_data.append(row)
        
        # 헤더 생성
        headers = ['Rank'] + [str(i+1) for i in range(max_countries)]
        
        # 표 생성
        num_cols = max_countries + 1
        col_widths = [0.12] + [0.88 / max_countries] * max_countries
        
        fig_height = max(8, len(table_data) * 0.5 + 2)
        fig_width = max(10, num_cols * 2)
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))
        ax.axis('tight')
        ax.axis('off')
        
        table = ax.table(
            cellText=table_data,
            colLabels=headers,
            cellLoc='center',
            loc='center',
            colWidths=col_widths
        )
        
        table.auto_set_font_size(False)
        table.set_fontsize(14)  # 글자 크기 증가
        table.scale(1, 2.8)  # 행 높이 증가
        
        # 헤더 스타일
        for i in range(len(headers)):
            cell = table[(0, i)]
            cell.set_facecolor(header_color)
            cell.set_text_props(weight='bold', color='white', ha='center', fontsize=15)
        
        # 데이터 행 스타일
        for i in range(1, len(table_data) + 1):
            for j in range(len(headers)):
                cell = table[(i, j)]
                cell.set_text_props(ha='center')
                
                if j == 0:
                    # Rank 열
                    cell.set_text_props(weight='bold', ha='center', fontsize=14)
                    if i % 2 == 0:
                        cell.set_facecolor('#E7E6E6')
                    else:
                        cell.set_facecolor('#FFFFFF')
                else:
                    # Country 열들
                    country_name = table_data[i-1][j]
                    
                    if country_name == '':
                        # 빈 셀
                        cell.set_facecolor('#F5F5F5')
                    elif country_name in top_10_markets:
                        # Top 10 시장: 굵은 글씨 + 강조 색
                        cell.set_facecolor('#FFE699')
                        cell.set_text_props(weight='bold', ha='center', fontsize=14)
                    else:
                        # 일반 국가
                        cell.set_text_props(ha='center', fontsize=14)
                        if i % 2 == 0:
                            cell.set_facecolor('#E7E6E6')
                        else:
                            cell.set_facecolor('#FFFFFF')
        
        plt.tight_layout()
        
        filename = f'ranking_table_{rank_key}.png'
        filepath = f'{output_dir}/{filename}'
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f'✓ Generated: {filename}')
        return filepath
    
    # Standard Edition 표 생성
    std_path = create_edition_table(
        'Standard Edition Rankings',
        'standard',
        '#4472C4'  # 파란색 헤더
    )
    if std_path:
        table_paths.append(std_path)
    
    # Deluxe Edition 표 생성
    dlx_path = create_edition_table(
        'Deluxe Edition Rankings',
        'deluxe',
        '#ED7D31'  # 오렌지색 헤더
    )
    if dlx_path:
        table_paths.append(dlx_path)
    
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

def calculate_current_sales(rankings):
    """현재 순위 기반으로 실시간 판매량 추산"""
    import math
    
    # PlayStation 국가별 시장 규모 배율
    ps_market_multiplier = {
        '미국': 10.0, 'USA': 10.0, 'United States': 10.0, 'US': 10.0,
        '일본': 5.0, 'Japan': 5.0,
        '영국': 2.7, 'UK': 2.7, 'United Kingdom': 2.7, 'Britain': 2.7,
        '독일': 2.3, 'Germany': 2.3, 'Deutschland': 2.3,
        '프랑스': 2.0, 'France': 2.0,
        '한국': 1.3, '대한민국': 1.3, 'Korea': 1.3, 'South Korea': 1.3,
        '스페인': 1.0, 'Spain': 1.0, 'España': 1.0,
        '이탈리아': 1.0, 'Italy': 1.0, 'Italia': 1.0,
        '캐나다': 1.0, 'Canada': 1.0,
        '호주': 0.7, 'Australia': 0.7,
        '네덜란드': 0.5, 'Netherlands': 0.5,
        '스웨덴': 0.35, 'Sweden': 0.35,
        '벨기에': 0.35, 'Belgium': 0.35,
        '스위스': 0.35, 'Switzerland': 0.35,
        '오스트리아': 0.27, 'Austria': 0.27,
        '폴란드': 0.27, 'Poland': 0.27,
        '노르웨이': 0.23, 'Norway': 0.23,
        '덴마크': 0.2, 'Denmark': 0.2,
        '핀란드': 0.17, 'Finland': 0.17,
        '포르투갈': 0.17, 'Portugal': 0.17,
    }
    
    def rank_to_daily_sales(rank):
        """순위를 일일 판매량으로 변환"""
        if rank is None or rank == '-':
            return 0
        rank = int(rank)
        
        if rank == 1:
            return 600
        elif rank <= 5:
            return 600 * math.exp(-0.18 * (rank - 1))
        elif rank <= 10:
            return 250 * math.exp(-0.13 * (rank - 5))
        elif rank <= 20:
            return 130 * math.exp(-0.06 * (rank - 10))
        elif rank <= 50:
            return 70 * math.exp(-0.03 * (rank - 20))
        else:
            return 30 * math.exp(-0.01 * (rank - 50))
    
    std_sales = 0
    dlx_sales = 0
    
    for country, ranks in rankings:
        multiplier = ps_market_multiplier.get(country, 0.15)
        
        if ranks['standard'] is not None:
            base_sales = rank_to_daily_sales(ranks['standard'])
            std_sales += base_sales * multiplier
        
        if ranks['deluxe'] is not None:
            base_sales = rank_to_daily_sales(ranks['deluxe'])
            dlx_sales += base_sales * multiplier
    
    return {
        'standard': round(std_sales, 2),
        'deluxe': round(dlx_sales, 2),
        'total': round(std_sales + dlx_sales, 2)
    }


def estimate_daily_sales(data, output_dir='output'):
    """일별 에디션별 판매량 추산 (PS 점유율 기반 가중치)"""
    import os as os_module
    
    # 히스토리 데이터 로드 및 병합 (판매량 추산용)
    historical_file = 'historical_ranking_data.json'
    sales_data = data.copy()  # 원본 데이터는 건드리지 않음
    
    if os_module.path.exists(historical_file):
        with open(historical_file, 'r', encoding='utf-8') as f:
            historical_data = json.load(f)
        
        print(f'📜 Loaded {len(historical_data)} historical ranking points for sales estimation')
        
        # 현재 데이터에서 Standard/Deluxe 평균 이격도 계산
        std_ranks = []
        dlx_ranks = []
        
        for entry in data:
            for country, ranks in entry['raw_results'].items():
                if ranks['standard'] is not None:
                    std_ranks.append(ranks['standard'])
                if ranks['deluxe'] is not None:
                    dlx_ranks.append(ranks['deluxe'])
        
        avg_std = sum(std_ranks) / len(std_ranks) if std_ranks else 15
        avg_dlx = sum(dlx_ranks) / len(dlx_ranks) if dlx_ranks else 8
        rank_gap = avg_std - avg_dlx
        
        print(f'   Average rank gap (Std - Dlx): {rank_gap:.1f}')
        
        # 히스토리 데이터를 현재 데이터 형식으로 변환
        historical_entries = []
        
        if data:
            countries = list(data[0]['raw_results'].keys())
        else:
            countries = ['미국', '일본', '영국', '독일', '프랑스', '한국']
        
        for item in historical_data:
            date_str = item['date']
            avg_rank = item['average_rank']
            
            # 평균 순위를 Standard/Deluxe로 분할
            std_rank = int(avg_rank + (rank_gap / 2))
            dlx_rank = int(avg_rank - (rank_gap / 2))
            
            # 모든 국가에 동일한 순위 적용
            raw_results = {}
            for country in countries:
                raw_results[country] = {
                    'standard': std_rank,
                    'deluxe': dlx_rank
                }
            
            historical_entries.append({
                'timestamp': f'{date_str}T08:00:00',
                'raw_results': raw_results
            })
        
        # 히스토리 + 현재 데이터 병합 (판매량 추산용만)
        sales_data = historical_entries + data
        print(f'   Total data points for sales estimation: {len(sales_data)}')
    
    os.makedirs(output_dir, exist_ok=True)
    
    # PlayStation 국가별 시장 규모 배율 (미국 기준 = 10)
    # 출처: VGChartz, Statista 등의 게임 시장 데이터 기반
    ps_market_multiplier = {
        # 주요 시장 (대형)
        '미국': 10.0, 'USA': 10.0, 'United States': 10.0, 'US': 10.0,
        '일본': 5.0, 'Japan': 5.0,
        
        # 주요 시장 (중대형)
        '영국': 2.7, 'UK': 2.7, 'United Kingdom': 2.7, 'Britain': 2.7,
        '독일': 2.3, 'Germany': 2.3, 'Deutschland': 2.3,
        '프랑스': 2.0, 'France': 2.0,
        
        # 중형 시장
        '한국': 1.3, '대한민국': 1.3, 'Korea': 1.3, 'South Korea': 1.3,
        '스페인': 1.0, 'Spain': 1.0, 'España': 1.0,
        '이탈리아': 1.0, 'Italy': 1.0, 'Italia': 1.0,
        '캐나다': 1.0, 'Canada': 1.0,
        '호주': 0.7, 'Australia': 0.7,
        
        # 중소 시장
        '네덜란드': 0.5, 'Netherlands': 0.5,
        '스웨덴': 0.35, 'Sweden': 0.35,
        '벨기에': 0.35, 'Belgium': 0.35,
        '스위스': 0.35, 'Switzerland': 0.35,
        '오스트리아': 0.27, 'Austria': 0.27,
        '폴란드': 0.27, 'Poland': 0.27,
        '노르웨이': 0.23, 'Norway': 0.23,
        '덴마크': 0.2, 'Denmark': 0.2,
        '핀란드': 0.17, 'Finland': 0.17,
        '포르투갈': 0.17, 'Portugal': 0.17,
    }
    
    # 순위별 일일 판매량 추정 (PlayStation Store 베스트셀러 순위 기반)
    # 중소 국가 기준 판매량 (대형 국가는 배율로 조정)
    def rank_to_daily_sales(rank):
        """순위를 일일 판매량으로 변환 (기본 시장 기준) - 로그 스케일 기반"""
        if rank is None or rank == '-':
            return 0
        rank = int(rank)
        
        # 더 현실적인 판매량 곡선 (로그 기반 완만한 감소)
        # 1위와 20위의 차이를 약 8배로 조정 (기존 60배에서 대폭 완화)
        import math
        
        if rank == 1:
            return 600   # 1위: ~600개/일 (기존 1500 → 600)
        elif rank <= 5:
            # 1~5위: 600 → 250 (완만한 감소)
            # e^(-0.18 * 4) ≈ 0.48
            return 600 * math.exp(-0.18 * (rank - 1))
        elif rank <= 10:
            # 6~10위: 250 → 130
            return 250 * math.exp(-0.13 * (rank - 5))
        elif rank <= 20:
            # 11~20위: 130 → 70
            return 130 * math.exp(-0.06 * (rank - 10))
        elif rank <= 50:
            # 21~50위: 70 → 30
            return 70 * math.exp(-0.03 * (rank - 20))
        else:
            # 50위 이상: 30 이하로 천천히 감소
            return 30 * math.exp(-0.01 * (rank - 50))
    
    # 날짜별 판매량 추산 (같은 날짜는 최고 순위만 사용)
    daily_sales = []
    
    # 먼저 날짜별로 그룹화
    date_groups = {}
    
    for entry in sales_data:
        timestamp = datetime.fromisoformat(entry['timestamp'])
        date_str = timestamp.strftime('%Y-%m-%d')
        
        if date_str not in date_groups:
            date_groups[date_str] = []
        
        date_groups[date_str].append({
            'timestamp': timestamp,
            'raw_results': entry['raw_results']
        })
    
    # 각 날짜별로 최고 순위(가장 낮은 숫자) 데이터만 사용
    for date_str in sorted(date_groups.keys()):
        entries = date_groups[date_str]
        
        # 각 국가별로 최고 순위 선택
        best_ranks = {}
        representative_timestamp = entries[0]['timestamp']
        
        # 첫 번째 항목의 국가 목록 가져오기
        countries = list(entries[0]['raw_results'].keys())
        
        for country in countries:
            best_std = None
            best_dlx = None
            
            # 같은 날짜의 모든 측정값 중 최고 순위 찾기
            for entry in entries:
                if country in entry['raw_results']:
                    std_rank = entry['raw_results'][country]['standard']
                    dlx_rank = entry['raw_results'][country]['deluxe']
                    
                    if std_rank is not None:
                        if best_std is None or std_rank < best_std:
                            best_std = std_rank
                    
                    if dlx_rank is not None:
                        if best_dlx is None or dlx_rank < best_dlx:
                            best_dlx = dlx_rank
            
            best_ranks[country] = {
                'standard': best_std,
                'deluxe': best_dlx
            }
        
        # 최고 순위로 판매량 계산
        std_sales = 0
        dlx_sales = 0
        
        for country, ranks in best_ranks.items():
            multiplier = ps_market_multiplier.get(country, 0.15)
            
            if ranks['standard'] is not None:
                base_sales = rank_to_daily_sales(ranks['standard'])
                std_sales += base_sales * multiplier
            
            if ranks['deluxe'] is not None:
                base_sales = rank_to_daily_sales(ranks['deluxe'])
                dlx_sales += base_sales * multiplier
        
        daily_sales.append({
            'date': representative_timestamp,
            'date_str': date_str,
            'standard': round(std_sales, 2),
            'deluxe': round(dlx_sales, 2),
            'total': round(std_sales + dlx_sales, 2)
        })
    
    # 표 데이터 생성
    table_data = []
    for item in daily_sales:
        table_data.append([
            item['date_str'],
            f"{int(item['standard']):,}",
            f"{int(item['deluxe']):,}",
            f"{int(item['total']):,}"
        ])
    
    # matplotlib 표 생성
    fig, ax = plt.subplots(figsize=(10, max(10, len(table_data) * 0.35)))
    ax.axis('tight')
    ax.axis('off')
    
    headers = ['Date', 'Standard\n(Units)', 'Deluxe\n(Units)', 'Total\n(Units)']
    
    table = ax.table(
        cellText=table_data,
        colLabels=headers,
        cellLoc='center',
        loc='center',
        colWidths=[0.3, 0.23, 0.23, 0.24]
    )
    
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.8)
    
    # 헤더 스타일
    for i in range(4):
        cell = table[(0, i)]
        cell.set_facecolor('#2E5984')
        cell.set_text_props(weight='bold', color='white')
    
    # 행 스타일
    for i in range(1, len(table_data) + 1):
        for j in range(4):
            cell = table[(i, j)]
            if i % 2 == 0:
                cell.set_facecolor('#F0F0F0')
            else:
                cell.set_facecolor('#FFFFFF')
    
    # 추정 기준 정보 추가 (좌측 하단)
    criteria_text = (
        "Estimation Criteria:\n"
        "• Rank-based sales (base market):\n"
        "  1st: 600 units/day\n"
        "  3rd: 390 units/day\n"
        "  5th: 250 units/day\n"
        "  10th: 130 units/day\n"
        "  15th: 97 units/day\n"
        "  (Log-scale curve)\n\n"
        "• Market size multiplier:\n"
        "  US ×10, JP ×5, UK ×2.7\n"
        "  DE ×2.3, FR ×2.0, KR ×1.3\n"
        "  Others ×0.15~1.0\n\n"
        "• Total: 48 countries combined"
    )
    
    fig.text(0.02, 0.02, criteria_text, 
             fontsize=7, 
             verticalalignment='bottom',
             horizontalalignment='left',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    plt.tight_layout(rect=[0, 0.15, 1, 1])  # 하단 여백 확보
    sales_table_path = f'{output_dir}/daily_sales_estimate.png'
    plt.savefig(sales_table_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f'✓ Generated: daily_sales_estimate.png')
    
    # 그래프도 생성
    dates = [item['date'] for item in daily_sales]
    std_sales = [item['standard'] for item in daily_sales]
    dlx_sales = [item['deluxe'] for item in daily_sales]
    total_sales = [item['total'] for item in daily_sales]
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    # 상단: 에디션별 판매량
    ax1.plot(dates, std_sales, 'o-', label='Standard (Est.)', linewidth=2, markersize=5, color='#2E86AB')
    ax1.plot(dates, dlx_sales, 's-', label='Deluxe (Est.)', linewidth=2, markersize=5, color='#A23B72')
    
    ax1.set_ylabel('Estimated Daily Sales (Units)', fontsize=12)
    ax1.set_title('Daily Estimated Sales by Edition (PS Market Share Weighted)', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=10)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    
    # 하단: 누적 판매량
    cumulative_std = []
    cumulative_dlx = []
    cumulative_total = []
    
    for i in range(len(std_sales)):
        cumulative_std.append(sum(std_sales[:i+1]))
        cumulative_dlx.append(sum(dlx_sales[:i+1]))
        cumulative_total.append(sum(total_sales[:i+1]))
    
    ax2.plot(dates, cumulative_std, 'o-', label='Standard (Cumulative)', linewidth=2, markersize=5, color='#2E86AB')
    ax2.plot(dates, cumulative_dlx, 's-', label='Deluxe (Cumulative)', linewidth=2, markersize=5, color='#A23B72')
    ax2.plot(dates, cumulative_total, '^-', label='Total (Cumulative)', linewidth=2, markersize=5, color='#27AE60')
    
    # 최종 누적 값 표시
    ax2.annotate(f'{int(cumulative_std[-1]):,}',
                xy=(dates[-1], cumulative_std[-1]),
                xytext=(10, 0), textcoords='offset points',
                fontsize=9, fontweight='bold')
    ax2.annotate(f'{int(cumulative_dlx[-1]):,}',
                xy=(dates[-1], cumulative_dlx[-1]),
                xytext=(10, 0), textcoords='offset points',
                fontsize=9, fontweight='bold')
    ax2.annotate(f'{int(cumulative_total[-1]):,}',
                xy=(dates[-1], cumulative_total[-1]),
                xytext=(10, 0), textcoords='offset points',
                fontsize=9, fontweight='bold')
    
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('Cumulative Sales (Units)', fontsize=12)
    ax2.set_title('Cumulative Estimated Sales', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=10)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
    # 추정 기준 정보 추가
    criteria_text = (
        "Estimation Criteria:\n"
        "Rank → Base Sales: 1st=600/day, 3rd=390/day, 5th=250/day, 10th=130/day (Log-scale curve)\n"
        "Market Multiplier: US ×10, JP ×5, UK ×2.7, DE ×2.3, FR ×2.0, KR ×1.3, Others ×0.15~1.0\n"
        "Total: 48 countries combined (PlayStation Store pre-order rankings)"
    )
    
    fig.text(0.5, 0.01, criteria_text, 
             fontsize=8, 
             verticalalignment='bottom',
             horizontalalignment='center',
             bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.3))
    
    plt.tight_layout(rect=[0, 0.05, 1, 1])  # 하단 여백 확보
    sales_chart_path = f'{output_dir}/daily_sales_chart.png'
    plt.savefig(sales_chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f'✓ Generated: daily_sales_chart.png')
    
    return sales_table_path, sales_chart_path, daily_sales

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
    ax.set_title('Daily Average Rankings - Standard vs Deluxe', fontsize=14, fontweight='bold')
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

def send_latest_rankings_to_discord(webhook_url, latest_rankings, table_paths, daily_sales):
    """오늘 날짜 최신 순위를 디스코드로 전송 (Standard와 Deluxe 표 모두 포함)"""
    if not webhook_url:
        print('⚠️  Discord webhook URL not provided, skipping latest rankings notification')
        return
    
    try:
        timestamp = latest_rankings['timestamp']
        rankings = latest_rankings['rankings']
        
        # 최신 판매량 추산 데이터 (현재 순위로 실시간 계산)
        latest_sales = calculate_current_sales(rankings) if rankings else None
        
        # Standard Edition Top 3 추출
        std_top_3 = []
        for country, ranks in rankings:
            if ranks['standard'] is not None and len(std_top_3) < 3:
                std_top_3.append((country, ranks['standard'], ranks['deluxe']))
        
        # Deluxe Edition Top 3 추출
        dlx_sorted = sorted(
            [(country, ranks) for country, ranks in rankings if ranks['deluxe'] is not None],
            key=lambda x: x[1]['deluxe']
        )
        dlx_top_3 = [(country, ranks['deluxe'], ranks['standard']) for country, ranks in dlx_sorted[:3]]
        
        # Standard Top 3 텍스트
        std_ranking_text = ""
        for idx, (country, std_rank, dlx_rank) in enumerate(std_top_3, 1):
            medal = "🥇 " if idx == 1 else "🥈 " if idx == 2 else "🥉 "
            dlx_display = f"#{dlx_rank}" if dlx_rank is not None else "-"
            std_ranking_text += f"{medal}**{country}**\n"
            std_ranking_text += f"   Standard: #{std_rank} | Deluxe: {dlx_display}\n"
        
        # Deluxe Top 3 텍스트
        dlx_ranking_text = ""
        for idx, (country, dlx_rank, std_rank) in enumerate(dlx_top_3, 1):
            medal = "🥇 " if idx == 1 else "🥈 " if idx == 2 else "🥉 "
            std_display = f"#{std_rank}" if std_rank is not None else "-"
            dlx_ranking_text += f"{medal}**{country}**\n"
            dlx_ranking_text += f"   Deluxe: #{dlx_rank} | Standard: {std_display}\n"
        
        # 디스코드 임베드 메시지 생성
        embed = {
            "title": "📊 Latest Rankings Update",
            "description": f"**{timestamp.strftime('%Y-%m-%d %H:%M:%S')}** 기준 최신 순위",
            "color": 3066993,  # 초록색
            "fields": [
                {
                    "name": "🏆 Top 3 Countries (Standard Edition)",
                    "value": std_ranking_text,
                    "inline": True
                },
                {
                    "name": "🏆 Top 3 Countries (Deluxe Edition)",
                    "value": dlx_ranking_text,
                    "inline": True
                },
                {
                    "name": "📈 Total Countries Tracked",
                    "value": str(len(rankings)),
                    "inline": False
                }
            ],
            "footer": {
                "text": "Ranking Bot | Auto-update"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 판매량 추산 정보 추가
        if latest_sales:
            sales_text = (
                f"**Standard**: {int(latest_sales['standard']):,} units\n"
                f"**Deluxe**: {int(latest_sales['deluxe']):,} units\n"
                f"**Total**: {int(latest_sales['total']):,} units\n"
                f"*(PS Market Share Weighted)*"
            )
            embed["fields"].insert(2, {
                "name": "💰 Estimated Sales (Current)",
                "value": sales_text,
                "inline": True
            })
        
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
            ('daily_sales_chart.png', 'sales_chart'),  # 판매량 그래프 추가
            ('top_countries_rankings.png', 'top_countries'),
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
    
    # 판매량 추산
    print('💰 Estimating daily sales...')
    sales_table_path, sales_chart_path, daily_sales = estimate_daily_sales(data)
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
        send_latest_rankings_to_discord(discord_webhook, latest_rankings, table_paths, daily_sales)
        print()
        
        # 2. 그래프 알림 전송
        print('📤 Sending graph notification to Discord...')
        send_discord_notification(discord_webhook, country_data, dates)
    else:
        print('ℹ️  Set DISCORD_WEBHOOK environment variable to enable notifications')

if __name__ == '__main__':
    main()
