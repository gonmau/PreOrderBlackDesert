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
    """한글 폰트 설정 (이모지 지원 포함)"""
    try:
        # 시스템에 설치된 한글 폰트 찾기
        font_list = fm.findSystemFonts(fontpaths=None, fontext='ttf')
        korean_fonts = [
            'NanumGothic', 'NanumBarunGothic', 'NanumSquare',
            'Malgun Gothic', 'AppleGothic', 'Noto Sans KR', 'Noto Sans CJK KR'
        ]
        
        korean_font_found = False
        for font_path in font_list:
            for korean_font in korean_fonts:
                if korean_font.lower() in font_path.lower():
                    font_name = fm.FontProperties(fname=font_path).get_name()
                    korean_font_found = True
                    break
            if korean_font_found:
                break
        
        if korean_font_found:
            # 이모지 지원을 위한 폰트 폴백 설정
            # Noto Color Emoji, Apple Color Emoji, Segoe UI Emoji 등을 fallback으로 추가
            plt.rcParams['font.family'] = [font_name, 'DejaVu Sans', 'sans-serif']
            plt.rcParams['font.sans-serif'] = [font_name, 'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            print(f'✓ Korean font set: {font_name} (with emoji support)')
        else:
            # 한글 폰트를 찾지 못한 경우 기본 설정 + 이모지 지원
            print('⚠️  Korean font not found, using default font with emoji support')
            plt.rcParams['font.family'] = ['DejaVu Sans', 'sans-serif']
            plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji']
            plt.rcParams['axes.unicode_minus'] = False
        
    except Exception as e:
        print(f'⚠️  Font setup error: {e}')
        plt.rcParams['font.family'] = 'DejaVu Sans'
        plt.rcParams['axes.unicode_minus'] = False

def load_data(filepath):
    """JSON 데이터 로드"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

# =============================================================================
# 공통 상수 (crimson_tracker의 MARKET_WEIGHTS와 통일)
# =============================================================================

# crimson_tracker MARKET_WEIGHTS 기준, 미국=10으로 정규화
_US_BASE = 30.0
PS_MARKET_MULTIPLIER = {
    # Americas
    '미국': 30.0 / _US_BASE * 10,   # 10.00
    '캐나다': 4.5  / _US_BASE * 10,  # 1.50
    '브라질': 2.5  / _US_BASE * 10,  # 0.83
    '멕시코': 2.0  / _US_BASE * 10,  # 0.67
    '아르헨티나': 0.9 / _US_BASE * 10,
    '칠레':   0.8 / _US_BASE * 10,
    '콜롬비아': 0.7 / _US_BASE * 10,
    '페루':   0.4 / _US_BASE * 10,
    '우루과이': 0.3 / _US_BASE * 10,
    '볼리비아': 0.2 / _US_BASE * 10,
    '과테말라': 0.2 / _US_BASE * 10,
    '온두라스': 0.2 / _US_BASE * 10,
    # Europe & Middle East
    '영국':   8.5 / _US_BASE * 10,  # 2.83
    '독일':   6.5 / _US_BASE * 10,  # 2.17
    '프랑스':  6.0 / _US_BASE * 10,  # 2.00
    '스페인':  4.0 / _US_BASE * 10,  # 1.33
    '이탈리아': 3.5 / _US_BASE * 10,  # 1.17
    '네덜란드': 1.8 / _US_BASE * 10,
    '사우디아라비아': 1.5 / _US_BASE * 10,
    '아랍에미리트': 1.2 / _US_BASE * 10,
    '폴란드':  1.2 / _US_BASE * 10,
    '스위스':  1.0 / _US_BASE * 10,
    '스웨덴':  1.0 / _US_BASE * 10,
    '덴마크':  0.9 / _US_BASE * 10,
    '포르투갈': 0.8 / _US_BASE * 10,
    '핀란드':  0.8 / _US_BASE * 10,
    '노르웨이': 0.8 / _US_BASE * 10,
    '남아공':  0.8 / _US_BASE * 10,
    '체코':   0.7 / _US_BASE * 10,
    '루마니아': 0.6 / _US_BASE * 10,
    '그리스':  0.5 / _US_BASE * 10,
    '헝가리':  0.5 / _US_BASE * 10,
    '우크라이나': 0.5 / _US_BASE * 10,
    '슬로바키아': 0.3 / _US_BASE * 10,
    '슬로베니아': 0.3 / _US_BASE * 10,
    # Asia & Oceania
    '일본':   8.0 / _US_BASE * 10,  # 2.67
    '호주':   3.0 / _US_BASE * 10,  # 1.00
    '한국':   2.8 / _US_BASE * 10,  # 0.93
    '인도':   2.0 / _US_BASE * 10,
    '대만':   1.0 / _US_BASE * 10,
    '싱가포르': 0.8 / _US_BASE * 10,
    '태국':   0.9 / _US_BASE * 10,
    '홍콩':   0.9 / _US_BASE * 10,
    '인도네시아': 0.8 / _US_BASE * 10,
    '말레이시아': 0.7 / _US_BASE * 10,
    '베트남':  0.7 / _US_BASE * 10,
    '필리핀':  0.6 / _US_BASE * 10,
    '뉴질랜드': 0.6 / _US_BASE * 10,
    '중국':   0.2 / _US_BASE * 10,
}
# 위 테이블에 없는 국가의 기본값
PS_MARKET_MULTIPLIER_DEFAULT = 0.10

import math as _math

# 연속성 확보를 위한 구간 계수 사전 계산
# 앵커: 1위=600, 20위=70, 100위=15
_A1   = 600.0
_A20  = 70.0
_A100 = 15.0
_k1   = _math.log(_A1 / _A20)  / (20 - 1)   # 1~20위 감쇠 상수
_k2   = _math.log(_A20 / _A100) / (100 - 20) # 20~100위 감쇠 상수

def rank_to_daily_sales(rank):
    """
    순위 → 일일 판매량(기본 시장 기준).
    - 1위=600, 20위=70, 100위=15 앵커 기반 두 구간 지수 곡선
    - 경계(20위)에서 완전 연속, 50→51 역전 버그 없음
    """
    if rank is None or rank == '-':
        return 0.0
    r = int(rank)
    if r <= 20:
        return _A1 * _math.exp(-_k1 * (r - 1))
    else:
        return _A20 * _math.exp(-_k2 * (r - 20))

def get_multiplier(country: str) -> float:
    """국가명 → PS 시장 배율 반환 (PS_MARKET_MULTIPLIER 단일 소스)"""
    return PS_MARKET_MULTIPLIER.get(country, PS_MARKET_MULTIPLIER_DEFAULT)

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
    """에디션별 순위를 텍스트 형식으로 생성 (Discord용)"""
    
    # 국기 이모지 매핑 (PlayStation Store가 있는 국가만)
    country_flags = {
        # 아메리카
        '미국': '🇺🇸', 'USA': '🇺🇸', 'United States': '🇺🇸', 'US': '🇺🇸',
        '캐나다': '🇨🇦', 'Canada': '🇨🇦',
        '브라질': '🇧🇷', 'Brazil': '🇧🇷',
        '멕시코': '🇲🇽', 'Mexico': '🇲🇽',
        '아르헨티나': '🇦🇷', 'Argentina': '🇦🇷',
        '칠레': '🇨🇱', 'Chile': '🇨🇱',
        '콜롬비아': '🇨🇴', 'Colombia': '🇨🇴',
        '페루': '🇵🇪', 'Peru': '🇵🇪',
        
        # 유럽 - 서유럽
        '영국': '🇬🇧', 'UK': '🇬🇧', 'United Kingdom': '🇬🇧', 'Britain': '🇬🇧',
        '독일': '🇩🇪', 'Germany': '🇩🇪', 'Deutschland': '🇩🇪',
        '프랑스': '🇫🇷', 'France': '🇫🇷',
        '스페인': '🇪🇸', 'Spain': '🇪🇸', 'España': '🇪🇸',
        '이탈리아': '🇮🇹', 'Italy': '🇮🇹', 'Italia': '🇮🇹',
        '네덜란드': '🇳🇱', 'Netherlands': '🇳🇱',
        '벨기에': '🇧🇪', 'Belgium': '🇧🇪',
        '스위스': '🇨🇭', 'Switzerland': '🇨🇭',
        '오스트리아': '🇦🇹', 'Austria': '🇦🇹',
        '아일랜드': '🇮🇪', 'Ireland': '🇮🇪',
        '포르투갈': '🇵🇹', 'Portugal': '🇵🇹',
        '룩셈부르크': '🇱🇺', 'Luxembourg': '🇱🇺',
        
        # 유럽 - 북유럽
        '스웨덴': '🇸🇪', 'Sweden': '🇸🇪',
        '노르웨이': '🇳🇴', 'Norway': '🇳🇴',
        '덴마크': '🇩🇰', 'Denmark': '🇩🇰',
        '핀란드': '🇫🇮', 'Finland': '🇫🇮',
        '아이슬란드': '🇮🇸', 'Iceland': '🇮🇸',
        
        # 유럽 - 동유럽
        '폴란드': '🇵🇱', 'Poland': '🇵🇱',
        '체코': '🇨🇿', 'Czech Republic': '🇨🇿', 'Czechia': '🇨🇿',
        '헝가리': '🇭🇺', 'Hungary': '🇭🇺',
        '슬로바키아': '🇸🇰', 'Slovakia': '🇸🇰',
        '루마니아': '🇷🇴', 'Romania': '🇷🇴',
        '불가리아': '🇧🇬', 'Bulgaria': '🇧🇬',
        '크로아티아': '🇭🇷', 'Croatia': '🇭🇷',
        '슬로베니아': '🇸🇮', 'Slovenia': '🇸🇮',
        '그리스': '🇬🇷', 'Greece': '🇬🇷',
        '러시아': '🇷🇺', 'Russia': '🇷🇺',
        '우크라이나': '🇺🇦', 'Ukraine': '🇺🇦',
        
        # 유럽 - 발트 3국
        '에스토니아': '🇪🇪', 'Estonia': '🇪🇪',
        '라트비아': '🇱🇻', 'Latvia': '🇱🇻',
        '리투아니아': '🇱🇹', 'Lithuania': '🇱🇹',
        
        # 유럽 - 기타
        '터키': '🇹🇷', 'Turkey': '🇹🇷', 'Türkiye': '🇹🇷',
        '키프로스': '🇨🇾', 'Cyprus': '🇨🇾',
        '몰타': '🇲🇹', 'Malta': '🇲🇹',
        
        # 아시아-태평양
        '일본': '🇯🇵', 'Japan': '🇯🇵',
        '한국': '🇰🇷', '대한민국': '🇰🇷', 'Korea': '🇰🇷', 'South Korea': '🇰🇷',
        '중국': '🇨🇳', 'China': '🇨🇳',
        '홍콩': '🇭🇰', 'Hong Kong': '🇭🇰',
        '대만': '🇹🇼', 'Taiwan': '🇹🇼',
        '호주': '🇦🇺', 'Australia': '🇦🇺',
        '뉴질랜드': '🇳🇿', 'New Zealand': '🇳🇿',
        '싱가포르': '🇸🇬', 'Singapore': '🇸🇬',
        '말레이시아': '🇲🇾', 'Malaysia': '🇲🇾',
        '태국': '🇹🇭', 'Thailand': '🇹🇭',
        '인도네시아': '🇮🇩', 'Indonesia': '🇮🇩',
        '인도': '🇮🇳', 'India': '🇮🇳',
        
        # 중동
        '사우디아라비아': '🇸🇦', 'Saudi Arabia': '🇸🇦',
        '아랍에미리트': '🇦🇪', 'UAE': '🇦🇪', 'United Arab Emirates': '🇦🇪',
        '쿠웨이트': '🇰🇼', 'Kuwait': '🇰🇼',
        '카타르': '🇶🇦', 'Qatar': '🇶🇦',
        '바레인': '🇧🇭', 'Bahrain': '🇧🇭',
        '오만': '🇴🇲', 'Oman': '🇴🇲',
        '이스라엘': '🇮🇱', 'Israel': '🇮🇱',
        
        # 아프리카
        '남아공': '🇿🇦', 'South Africa': '🇿🇦',
    }
    
    # PlayStation 국가별 시장 규모 배율 → 공통 get_multiplier() 사용
    
    # 최신 데이터 가져오기
    latest_entry = data[-1]
    raw_results = latest_entry['raw_results']
    
    # Standard Edition 순위 텍스트 생성
    rank_groups_std = {}
    for country, ranks in raw_results.items():
        std_rank = ranks['standard']
        if std_rank is not None:
            if std_rank not in rank_groups_std:
                rank_groups_std[std_rank] = []
            rank_groups_std[std_rank].append(country)
    
    # 각 순위 내에서 점유율 순으로 정렬
    for rank in rank_groups_std:
        rank_groups_std[rank] = sorted(
            rank_groups_std[rank],
            key=lambda c: get_multiplier(c),
            reverse=True
        )
    
    std_text = "**Standard Edition Rankings:**\n"
    for rank in sorted(rank_groups_std.keys()):
        countries = rank_groups_std[rank]
        countries_with_flags = [f"{country_flags.get(c, '🏳️')} {c}" for c in countries]
        std_text += f"**#{rank}** {', '.join(countries_with_flags)}\n"
    
    # Deluxe Edition 순위 텍스트 생성
    rank_groups_dlx = {}
    for country, ranks in raw_results.items():
        dlx_rank = ranks['deluxe']
        if dlx_rank is not None:
            if dlx_rank not in rank_groups_dlx:
                rank_groups_dlx[dlx_rank] = []
            rank_groups_dlx[dlx_rank].append(country)
    
    # 각 순위 내에서 점유율 순으로 정렬
    for rank in rank_groups_dlx:
        rank_groups_dlx[rank] = sorted(
            rank_groups_dlx[rank],
            key=lambda c: get_multiplier(c),
            reverse=True
        )
    
    dlx_text = "**Deluxe Edition Rankings:**\n"
    for rank in sorted(rank_groups_dlx.keys()):
        countries = rank_groups_dlx[rank]
        countries_with_flags = [f"{country_flags.get(c, '🏳️')} {c}" for c in countries]
        dlx_text += f"**#{rank}** {', '.join(countries_with_flags)}\n"
    
    print('✓ Generated ranking text for Discord')
    
    # 텍스트를 반환 (이미지 파일 대신)
    return {
        'standard': std_text,
        'deluxe': dlx_text
    }

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
    """현재 순위 기반으로 실시간 판매량 추산 (공통 rank_to_daily_sales / get_multiplier 사용)"""
    std_sales = 0.0
    dlx_sales = 0.0

    for country, ranks in rankings:
        multiplier = get_multiplier(country)

        if ranks['standard'] is not None:
            std_sales += rank_to_daily_sales(ranks['standard']) * multiplier

        if ranks['deluxe'] is not None:
            dlx_sales += rank_to_daily_sales(ranks['deluxe']) * multiplier

    return {
        'standard': round(std_sales, 2),
        'deluxe':   round(dlx_sales, 2),
        'total':    round(std_sales + dlx_sales, 2)
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

    # ── 날짜별 그룹화 → 국가별 최고 순위 → 판매량 계산 ─────────────────
    # 공통 rank_to_daily_sales / get_multiplier 사용
    daily_sales: list = []
    date_groups: dict = {}

    for entry in sales_data:
        timestamp = datetime.fromisoformat(entry['timestamp'])
        date_str  = timestamp.strftime('%Y-%m-%d')
        date_groups.setdefault(date_str, []).append({
            'timestamp':   timestamp,
            'raw_results': entry['raw_results']
        })

    for date_str in sorted(date_groups.keys()):
        entries = date_groups[date_str]
        representative_timestamp = entries[0]['timestamp']

        # 해당 날짜의 모든 항목에서 국가별 최고 순위 취합
        all_countries: set = set()
        for e in entries:
            all_countries.update(e['raw_results'].keys())

        best_ranks: dict = {}
        for country in all_countries:
            best_std, best_dlx = None, None
            for e in entries:
                if country in e['raw_results']:
                    s = e['raw_results'][country]['standard']
                    d = e['raw_results'][country]['deluxe']
                    if s is not None and (best_std is None or s < best_std):
                        best_std = s
                    if d is not None and (best_dlx is None or d < best_dlx):
                        best_dlx = d
            best_ranks[country] = {'standard': best_std, 'deluxe': best_dlx}

        std_sales = 0.0
        dlx_sales = 0.0
        for country, ranks in best_ranks.items():
            m = get_multiplier(country)
            if ranks['standard'] is not None:
                std_sales += rank_to_daily_sales(ranks['standard']) * m
            if ranks['deluxe'] is not None:
                dlx_sales += rank_to_daily_sales(ranks['deluxe']) * m

        daily_sales.append({
            'date':     representative_timestamp,
            'date_str': date_str,
            'standard': round(std_sales, 2),
            'deluxe':   round(dlx_sales, 2),
            'total':    round(std_sales + dlx_sales, 2)
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
        "• Rank → Base Sales (continuous 2-segment curve):\n"
        "  1st: 600 units/day\n"
        "  5th: 382 units/day\n"
        "  10th: 217 units/day\n"
        "  20th:  70 units/day  ← boundary (smooth)\n"
        "  50th:  39 units/day\n"
        " 100th:  15 units/day\n\n"
        "• Market size multiplier (crimson_tracker\n"
        "  MARKET_WEIGHTS, US=10 normalized):\n"
        "  US ×10, JP ×2.67, UK ×2.83\n"
        "  DE ×2.17, FR ×2.0, KR ×0.93\n"
        "  Others ×0.03~1.5\n\n"
        "• Total: 49 countries combined"
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
        "Rank → Base Sales (continuous 2-segment curve): "
        "1st=600/day, 5th=382/day, 10th=217/day, 20th=70/day (boundary), 50th=39/day, 100th=15/day\n"
        "Market Multiplier (crimson_tracker MARKET_WEIGHTS, US=10): "
        "US ×10, JP ×2.67, UK ×2.83, DE ×2.17, FR ×2.0, KR ×0.93, Others ×0.03~1.5\n"
        "Total: 49 countries combined (PlayStation Store pre-order rankings)"
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

def send_latest_rankings_to_discord(webhook_url, latest_rankings, table_texts, daily_sales):
    """오늘 날짜 최신 순위를 디스코드로 전송 (텍스트 형식)"""
    if not webhook_url:
        print('⚠️  Discord webhook URL not provided, skipping latest rankings notification')
        return
    
    try:
        timestamp = latest_rankings['timestamp']
        rankings = latest_rankings['rankings']
        
        # 최신 판매량 추산 데이터 (현재 순위로 실시간 계산)
        latest_sales = calculate_current_sales(rankings) if rankings else None
        
        # 디스코드 임베드 메시지 생성
        embed = {
            "title": "📊 Latest Rankings Update",
            "description": f"**{timestamp.strftime('%Y-%m-%d %H:%M:%S')}** 기준 최신 순위",
            "color": 3066993,  # 초록색
            "fields": [
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
            embed["fields"].insert(0, {
                "name": "💰 Estimated Sales (Current)",
                "value": sales_text,
                "inline": True
            })
        
        # 순위 텍스트 추가 (이미지 대신)
        if table_texts:
            embed["fields"].append({
                "name": "📋 All Rankings (Standard)",
                "value": table_texts['standard'][:1024],  # Discord 필드 제한
                "inline": False
            })
            embed["fields"].append({
                "name": "📋 All Rankings (Deluxe)",
                "value": table_texts['deluxe'][:1024],  # Discord 필드 제한
                "inline": False
            })
        
        # 웹훅으로 전송
        payload = {
            "username": "Ranking Bot",
            "embeds": [embed]
        }
        
        print(f'📤 Sending latest rankings to Discord...')
        
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
    
    # 순위 텍스트 생성
    print('📋 Creating ranking text...')
    table_texts = create_ranking_table(data)
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
        send_latest_rankings_to_discord(discord_webhook, latest_rankings, table_texts, daily_sales)
        print()
        
        # 2. 그래프 알림 전송
        print('📤 Sending graph notification to Discord...')
        send_discord_notification(discord_webhook, country_data, dates)
    else:
        print('ℹ️  Set DISCORD_WEBHOOK environment variable to enable notifications')

if __name__ == '__main__':
    main()
