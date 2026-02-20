#!/usr/bin/env python3
"""
일별 국가별 S,D 순위 그래프 생성 스크립트
"""
import json
import copy  # ✅ FIX: deepcopy를 위해 추가
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
            plt.rcParams['font.family'] = [font_name, 'DejaVu Sans', 'sans-serif']
            plt.rcParams['font.sans-serif'] = [font_name, 'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            print(f'✓ Korean font set: {font_name} (with emoji support)')
        else:
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

_US_BASE = 30.0
PS_MARKET_MULTIPLIER = {
    # Americas
    '미국': 30.0 / _US_BASE * 10,
    '캐나다': 4.5  / _US_BASE * 10,
    '브라질': 2.5  / _US_BASE * 10,
    '멕시코': 2.0  / _US_BASE * 10,
    '아르헨티나': 0.9 / _US_BASE * 10,
    '칠레':   0.8 / _US_BASE * 10,
    '콜롬비아': 0.7 / _US_BASE * 10,
    '페루':   0.4 / _US_BASE * 10,
    '우루과이': 0.3 / _US_BASE * 10,
    '볼리비아': 0.2 / _US_BASE * 10,
    '과테말라': 0.2 / _US_BASE * 10,
    '온두라스': 0.2 / _US_BASE * 10,
    # Europe & Middle East
    '영국':   8.5 / _US_BASE * 10,
    '독일':   6.5 / _US_BASE * 10,
    '프랑스':  6.0 / _US_BASE * 10,
    '스페인':  4.0 / _US_BASE * 10,
    '이탈리아': 3.5 / _US_BASE * 10,
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
    '일본':   8.0 / _US_BASE * 10,
    '호주':   3.0 / _US_BASE * 10,
    '한국':   2.8 / _US_BASE * 10,
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
PS_MARKET_MULTIPLIER_DEFAULT = 0.10

import math as _math

_A1   = 600.0
_A20  = 70.0
_A100 = 15.0
_k1   = _math.log(_A1 / _A20)  / (20 - 1)
_k2   = _math.log(_A20 / _A100) / (100 - 20)

def rank_to_daily_sales(rank):
    """
    순위 → 일일 판매량(기본 시장 기준).
    1위=600, 20위=70, 100위=15 앵커 기반 두 구간 지수 곡선
    """
    if rank is None or rank == '-':
        return 0.0
    r = int(rank)
    if r <= 20:
        return _A1 * _math.exp(-_k1 * (r - 1))
    else:
        return _A20 * _math.exp(-_k2 * (r - 20))

def get_multiplier(country: str) -> float:
    """국가명 → PS 시장 배율 반환"""
    return PS_MARKET_MULTIPLIER.get(country, PS_MARKET_MULTIPLIER_DEFAULT)

def parse_data(data):
    """데이터 파싱 및 구조화"""
    countries = set()
    dates = []
    
    for entry in data:
        countries.update(entry['raw_results'].keys())
        dates.append(datetime.fromisoformat(entry['timestamp']))
    
    countries = sorted(list(countries))
    
    country_data = {
        country: {
            'dates': [],
            'standard': [],
            'deluxe': []
        }
        for country in countries
    }
    
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
    
    return {
        'standard': std_text,
        'deluxe': dlx_text
    }

def get_latest_rankings(data):
    """최신 순위 데이터를 딕셔너리 형태로 반환"""
    latest_entry = data[-1]
    timestamp = datetime.fromisoformat(latest_entry['timestamp'])
    
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

    # ✅ FIX: 원본 data를 건드리지 않도록 deepcopy 사용
    # 기존 data.copy()는 얕은 복사(shallow copy)라 내부 딕셔너리가
    # 같은 참조를 공유 → is_historical 플래그 추가 시 원본이 오염되어
    # rank_history.json이 변경된 것으로 감지 → git rebase 에러 발생
    sales_data_raw = copy.deepcopy(data)

    historical_file = 'historical_ranking_data.json'
    sales_data = sales_data_raw

    if os_module.path.exists(historical_file):
        with open(historical_file, 'r', encoding='utf-8') as f:
            historical_data = json.load(f)
        
        print(f'📜 Loaded {len(historical_data)} historical ranking points for sales estimation')
        
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
        
        historical_entries = []
        
        if data:
            countries = list(data[0]['raw_results'].keys())
        else:
            countries = ['미국', '일본', '영국', '독일', '프랑스', '한국']
        
        for item in historical_data:
            date_str  = item['date']
            country_ranks = item.get('country_ranks', {})

            wa_num, wa_den = 0.0, 0.0
            for c, v in country_ranks.items():
                if v is not None:
                    m = get_multiplier(c)
                    wa_num += v * m
                    wa_den += m
            if wa_den > 0:
                weighted_avg_rank = wa_num / wa_den
            else:
                weighted_avg_rank = item.get('average_rank', 15)

            raw_results = {}
            for country in countries:
                if country in country_ranks and country_ranks[country] is not None:
                    base = country_ranks[country]
                else:
                    base = weighted_avg_rank
                std_r = max(1, int(base + rank_gap / 2))
                dlx_r = max(1, int(base - rank_gap / 2))
                raw_results[country] = {
                    'standard': std_r,
                    'deluxe':   dlx_r
                }

            historical_entries.append({
                'timestamp': f'{date_str}T08:00:00',
                'raw_results': raw_results,
                'is_historical': True  # ✅ FIX: 새로 만드는 객체에 직접 플래그 설정
            })
        
        # ✅ FIX: deepcopy된 sales_data_raw에만 플래그 추가 (원본 data는 절대 수정 안 함)
        for e in sales_data_raw:
            e['is_historical'] = False

        sales_data = historical_entries + sales_data_raw
        print(f'   Total data points for sales estimation: {len(sales_data)}')
    else:
        # historical 파일이 없는 경우에도 deepcopy 본에 플래그 추가
        for e in sales_data_raw:
            e['is_historical'] = False
        sales_data = sales_data_raw

    os.makedirs(output_dir, exist_ok=True)

    # 날짜별 그룹화 → 국가별 최고 순위 → 판매량 계산
    daily_sales: list = []
    date_groups: dict = {}

    for entry in sales_data:
        timestamp = datetime.fromisoformat(entry['timestamp'])
        date_str  = timestamp.strftime('%Y-%m-%d')
        date_groups.setdefault(date_str, []).append({
            'timestamp':     timestamp,
            'raw_results':   entry['raw_results'],
            'is_historical': entry.get('is_historical', False)
        })

    for date_str in sorted(date_groups.keys()):
        entries = date_groups[date_str]
        representative_timestamp = entries[0]['timestamp']
        is_historical = all(e['is_historical'] for e in entries)

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
            'date':          representative_timestamp,
            'date_str':      date_str,
            'standard':      round(std_sales, 2),
            'deluxe':        round(dlx_sales, 2),
            'total':         round(std_sales + dlx_sales, 2),
            'is_historical': is_historical
        })
    
    # 표 데이터 생성
    table_data = []
    for item in daily_sales:
        table_data.append([
            item['date_str'] + (' *' if item['is_historical'] else ''),
            f"{int(item['standard']):,}",
            f"{int(item['deluxe']):,}",
            f"{int(item['total']):,}"
        ])
    
    fig, ax = plt.subplots(figsize=(10, max(10, len(table_data) * 0.35)))
    ax.axis('tight')
    ax.axis('off')
    
    headers = ['Date (* = estimated)', 'Standard\n(Units)', 'Deluxe\n(Units)', 'Total\n(Units)']
    
    table = ax.table(
        cellText=table_data,
        colLabels=headers,
        cellLoc='center',
        loc='center',
        colWidths=[0.34, 0.22, 0.22, 0.22]
    )
    
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.8)
    
    for i in range(4):
        cell = table[(0, i)]
        cell.set_facecolor('#2E5984')
        cell.set_text_props(weight='bold', color='white')
    
    for i, item in enumerate(daily_sales, start=1):
        for j in range(4):
            cell = table[(i, j)]
            if item['is_historical']:
                cell.set_facecolor('#FFF3CD' if i % 2 == 0 else '#FFEAA7')
                cell.set_text_props(color='#856404')
            else:
                cell.set_facecolor('#F0F0F0' if i % 2 == 0 else '#FFFFFF')
    
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
    
    plt.tight_layout(rect=[0, 0.15, 1, 1])
    sales_table_path = f'{output_dir}/daily_sales_estimate.png'
    plt.savefig(sales_table_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f'✓ Generated: daily_sales_estimate.png')
    
    # 히스토리 / 실제 구간 분리
    hist_items = [item for item in daily_sales if     item['is_historical']]
    real_items = [item for item in daily_sales if not item['is_historical']]

    # 경계 연결용
    bridge_std, bridge_dlx, bridge_tot, bridge_dates = [], [], [], []
    if hist_items and real_items:
        bridge_items = [hist_items[-1], real_items[0]]
        bridge_dates = [it['date']     for it in bridge_items]
        bridge_std   = [it['standard'] for it in bridge_items]
        bridge_dlx   = [it['deluxe']   for it in bridge_items]
        bridge_tot   = [it['total']    for it in bridge_items]

    h_dates = [it['date']     for it in hist_items]
    h_std   = [it['standard'] for it in hist_items]
    h_dlx   = [it['deluxe']   for it in hist_items]
    h_tot   = [it['total']    for it in hist_items]

    r_dates = [it['date']     for it in real_items]
    r_std   = [it['standard'] for it in real_items]
    r_dlx   = [it['deluxe']   for it in real_items]
    r_tot   = [it['total']    for it in real_items]

    # 누적 계산 (전체 순서 유지)
    all_dates = [it['date'] for it in daily_sales]
    cumulative_std   = []
    cumulative_dlx   = []
    cumulative_total = []
    for i in range(len(daily_sales)):
        cumulative_std.append(sum(it['standard'] for it in daily_sales[:i+1]))
        cumulative_dlx.append(sum(it['deluxe']   for it in daily_sales[:i+1]))
        cumulative_total.append(sum(it['total']  for it in daily_sales[:i+1]))

    # ✅ FIX: 누적 구간 분리 — len(hist_items) 인덱스 슬라이싱 대신
    # daily_sales의 is_historical 플래그 기준으로 직접 분리
    # 기존 방식은 hist_items가 daily_sales 앞부분에 연속적으로 위치한다고
    # 가정하지만, 날짜 겹침 등으로 순서가 뒤섞일 경우 인덱스가 틀어짐
    h_cum_dates, h_cum_std, h_cum_dlx, h_cum_tot = [], [], [], []
    r_cum_dates, r_cum_std, r_cum_dlx, r_cum_tot = [], [], [], []

    for i, item in enumerate(daily_sales):
        if item['is_historical']:
            h_cum_dates.append(all_dates[i])
            h_cum_std.append(cumulative_std[i])
            h_cum_dlx.append(cumulative_dlx[i])
            h_cum_tot.append(cumulative_total[i])
        else:
            r_cum_dates.append(all_dates[i])
            r_cum_std.append(cumulative_std[i])
            r_cum_dlx.append(cumulative_dlx[i])
            r_cum_tot.append(cumulative_total[i])

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))

    # 상단: 일별 에디션별 판매량
    if h_dates:
        ax1.plot(h_dates, h_std, 'o--', label='Standard – Est. (historical avg)',
                 linewidth=1.5, markersize=4, color='#90CAF9', alpha=0.8)
        ax1.plot(h_dates, h_dlx, 's--', label='Deluxe – Est. (historical avg)',
                 linewidth=1.5, markersize=4, color='#F48FB1', alpha=0.8)
        ax1.fill_between(h_dates, h_std, alpha=0.06, color='#2E86AB')
        ax1.fill_between(h_dates, h_dlx, alpha=0.06, color='#A23B72')

    if bridge_dates:
        ax1.plot(bridge_dates, bridge_std, '--', linewidth=1, color='#90CAF9', alpha=0.5)
        ax1.plot(bridge_dates, bridge_dlx, '--', linewidth=1, color='#F48FB1', alpha=0.5)

    if r_dates:
        ax1.plot(r_dates, r_std, 'o-', label='Standard – Est. (per-country data)',
                 linewidth=2, markersize=5, color='#2E86AB')
        ax1.plot(r_dates, r_dlx, 's-', label='Deluxe – Est. (per-country data)',
                 linewidth=2, markersize=5, color='#A23B72')

    if hist_items and real_items:
        boundary = real_items[0]['date']
        ax1.axvline(x=boundary, color='gray', linestyle=':', linewidth=1.5, alpha=0.7)
        ax1.text(boundary, ax1.get_ylim()[1] if ax1.get_ylim()[1] != 1.0 else 5000,
                 ' ← per-country\ndata starts',
                 fontsize=8, color='gray', va='top')

    ax1.set_ylabel('Estimated Daily Sales (Units)', fontsize=12)
    ax1.set_title('Daily Estimated Sales by Edition\n'
                  '(dashed = historical avg estimate  |  solid = per-country data)',
                  fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=9, loc='upper right')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

    # 하단: 누적 판매량
    if hist_items:
        ax2.axvspan(all_dates[0], all_dates[len(hist_items) - 1],
                    alpha=0.07, color='orange', label='Historical estimate period')

    if h_cum_dates:
        ax2.plot(h_cum_dates, h_cum_std, 'o--', linewidth=1.5, markersize=3,
                 color='#90CAF9', alpha=0.8)
        ax2.plot(h_cum_dates, h_cum_dlx, 's--', linewidth=1.5, markersize=3,
                 color='#F48FB1', alpha=0.8)
        ax2.plot(h_cum_dates, h_cum_tot, '^--', linewidth=1.5, markersize=3,
                 color='#A8D5A2', alpha=0.8)

    # 경계 연결 (누적)
    if hist_items and real_items and h_cum_dates and r_cum_dates:
        for cum_list, color in [
            (cumulative_std,   '#2E86AB'),
            (cumulative_dlx,   '#A23B72'),
            (cumulative_total, '#27AE60'),
        ]:
            ax2.plot(
                [h_cum_dates[-1], r_cum_dates[0]],
                [cum_list[len(hist_items) - 1], cum_list[len(hist_items)]],
                '--', linewidth=1, color=color, alpha=0.5
            )

    if r_cum_dates:
        ax2.plot(r_cum_dates, r_cum_std,  'o-',
                 label='Standard (Cumulative)', linewidth=2, markersize=4, color='#2E86AB')
        ax2.plot(r_cum_dates, r_cum_dlx,  's-',
                 label='Deluxe (Cumulative)',   linewidth=2, markersize=4, color='#A23B72')
        ax2.plot(r_cum_dates, r_cum_tot,  '^-',
                 label='Total (Cumulative)',     linewidth=2, markersize=4, color='#27AE60')

    # 최종 누적 값 표시
    if cumulative_std:
        for cum, label_txt, color in [
            (cumulative_std,   f"{int(cumulative_std[-1]):,}",   '#2E86AB'),
            (cumulative_dlx,   f"{int(cumulative_dlx[-1]):,}",   '#A23B72'),
            (cumulative_total, f"{int(cumulative_total[-1]):,}", '#27AE60'),
        ]:
            ax2.annotate(label_txt,
                         xy=(all_dates[-1], cum[-1]),
                         xytext=(8, 0), textcoords='offset points',
                         fontsize=9, fontweight='bold', color=color)

    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('Cumulative Sales (Units)', fontsize=12)
    ax2.set_title('Cumulative Estimated Sales\n'
                  '(shaded area = historical estimate  |  solid = per-country data)',
                  fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=9, loc='upper left')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
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
    
    plt.tight_layout(rect=[0, 0.05, 1, 1])
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
        
        ax.plot(data['dates'], data['standard'], 'o-', label='Standard', linewidth=2, markersize=4)
        ax.plot(data['dates'], data['deluxe'], 's-', label='Deluxe', linewidth=2, markersize=4)
        
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Rank', fontsize=12)
        ax.set_title(f'{country} - Daily Ranking Trends', fontsize=14, fontweight='bold')
        ax.invert_yaxis()
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
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
            if data['standard'][i] is not None:
                date_averages[date_str]['standard'].append(data['standard'][i])
            if data['deluxe'][i] is not None:
                date_averages[date_str]['deluxe'].append(data['deluxe'][i])
    
    dates = []
    standard_avgs = []
    deluxe_avgs = []
    
    for date_str in sorted(date_averages.keys()):
        std_list = date_averages[date_str]['standard']
        dlx_list = date_averages[date_str]['deluxe']
        
        if std_list and dlx_list:
            dates.append(date_averages[date_str]['date'])
            standard_avgs.append(sum(std_list) / len(std_list))
            deluxe_avgs.append(sum(dlx_list) / len(dlx_list))
    
    if not dates:
        print('⚠️  No data to plot for daily averages')
        return
    
    fig, ax = plt.subplots(figsize=(14, 7))
    
    ax.plot(dates, deluxe_avgs, 's-', label='Deluxe Average', linewidth=2, markersize=5, color='#A23B72')
    ax.plot(dates, standard_avgs, 'o-', label='Standard Average', linewidth=2, markersize=5, color='#2E86AB')
    
    for i, date in enumerate(dates):
        ax.annotate(f'{deluxe_avgs[i]:.1f}',
                   xy=(date, deluxe_avgs[i]),
                   xytext=(0, 8), textcoords='offset points',
                   fontsize=7, ha='center',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.6, edgecolor='none'))
        
        ax.annotate(f'{standard_avgs[i]:.1f}',
                   xy=(date, standard_avgs[i]),
                   xytext=(0, -12), textcoords='offset points',
                   fontsize=7, ha='center',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.6, edgecolor='none'))
    
    std_min_rank = min(standard_avgs)
    std_max_rank = max(standard_avgs)
    std_min_idx = standard_avgs.index(std_min_rank)
    std_max_idx = standard_avgs.index(std_max_rank)
    ax.plot(dates[std_min_idx], std_min_rank, 'go', markersize=10, label=f'Std Best: {std_min_rank:.1f}', zorder=5)
    ax.plot(dates[std_max_idx], std_max_rank, 'ro', markersize=10, label=f'Std Worst: {std_max_rank:.1f}', zorder=5)
    
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
    
    for country in countries_to_plot:
        if country in country_data and country_data[country]['dates']:
            data = country_data[country]
            ax1.plot(data['dates'], data['standard'], 'o-', label=country, linewidth=2, markersize=4)
            
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
    
    for country in countries_to_plot:
        if country in country_data and country_data[country]['dates']:
            data = country_data[country]
            ax2.plot(data['dates'], data['deluxe'], 's-', label=country, linewidth=2, markersize=4)
            
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
        
        latest_sales = calculate_current_sales(rankings) if rankings else None
        
        embed = {
            "title": "📊 Latest Rankings Update",
            "description": f"**{timestamp.strftime('%Y-%m-%d %H:%M:%S')}** 기준 최신 순위",
            "color": 3066993,
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
        
        if table_texts:
            embed["fields"].append({
                "name": "📋 All Rankings (Standard)",
                "value": table_texts['standard'][:1024],
                "inline": False
            })
            embed["fields"].append({
                "name": "📋 All Rankings (Deluxe)",
                "value": table_texts['deluxe'][:1024],
                "inline": False
            })
        
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
    
    print(f'🔍 Discord webhook URL: {webhook_url[:50]}...')
    
    try:
        num_countries = len(country_data)
        date_range = f"{dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}"
        
        target_countries = ['일본', '미국', '영국', '독일', '프랑스', '한국']
        countries_to_plot = []
        
        for target in target_countries:
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
        
        if countries_to_plot:
            plot_top_countries(country_data, countries_to_plot, output_dir)
        
        # 최근 순위 변화가 큰 국가 찾기
        top_changes = []
        for country, data in country_data.items():
            if len(data['standard']) >= 2:
                prev_std = data['standard'][-2]
                curr_std = data['standard'][-1]
                if prev_std is not None and curr_std is not None:
                    change = prev_std - curr_std  # 양수 = 순위 상승
                    top_changes.append((country, change, curr_std))
        
        top_changes.sort(key=lambda x: abs(x[1]), reverse=True)
        top_changes = top_changes[:5]
        
        changes_text = ""
        for country, change, curr_rank in top_changes:
            arrow = "⬆️" if change > 0 else "⬇️" if change < 0 else "➡️"
            changes_text += f"{arrow} **{country}**: {abs(int(change))} ranks ({'up' if change > 0 else 'down' if change < 0 else 'no change'}) → #{int(curr_rank)}\n"
        
        embed = {
            "title": "📈 Ranking Update - Charts",
            "description": f"**{date_range}** | {num_countries} countries tracked",
            "color": 5814783,
            "fields": [],
            "footer": {
                "text": "Ranking Bot | Auto-update"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if changes_text:
            embed["fields"].append({
                "name": "🔄 Notable Changes (Standard)",
                "value": changes_text,
                "inline": False
            })
        
        files_to_send = {}
        image_files = [
            ('daily_sales_chart.png', 'sales_chart'),
            ('top_countries_rankings.png', 'top_countries'),
            ('all_countries_deluxe.png', 'deluxe_chart'),
            ('all_countries_standard.png', 'standard_chart'),
            ('daily_averages.png', 'averages_chart')
        ]
        
        for filename, file_key in image_files:
            filepath = os.path.join(output_dir, filename)
            if os.path.exists(filepath):
                files_to_send[file_key] = (filename, open(filepath, 'rb'), 'image/png')
        
        if files_to_send:
            embed["image"] = {"url": f"attachment://{image_files[0][0]}"}
        
        payload = {
            "username": "Ranking Bot",
            "embeds": [embed]
        }
        
        print(f'📤 Sending to Discord with {len(files_to_send)} images...')
        
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

def build_historical_data_from_weekly(output_path='historical_ranking_data.json'):
    """
    이미지에서 수집한 주단위 국가별 순위를 historical_ranking_data.json 형식으로 변환.
    """
    import math as _m
    from datetime import timedelta

    weekly_raw = [
        ("2025-09-22", {"미국":12,"일본":17,"홍콩":14,"인도":4, "영국":18,"독일":12,"프랑스":9, "멕시코":17,"캐나다":15,"한국":4, "호주":12,"브라질":12,"스페인":14}),
        ("2025-09-29", {"미국":11,"일본":None,"홍콩":17,"인도":6, "영국":22,"독일":16,"프랑스":12,"멕시코":13,"캐나다":20,"한국":4, "호주":21,"브라질":11,"스페인":11}),
        ("2025-10-06", {"미국":16,"일본":15,"홍콩":12,"인도":17,"영국":18,"독일":19,"프랑스":13,"멕시코":13,"캐나다":20,"한국":4, "호주":21,"브라질":11,"스페인":11}),
        ("2025-10-13", {"미국":16,"일본":22,"홍콩":11,"인도":14,"영국":None,"독일":23,"프랑스":16,"멕시코":7, "캐나다":18,"한국":3, "호주":17,"브라질":12,"스페인":11}),
        ("2025-10-20", {"미국":21,"일본":None,"홍콩":22,"인도":20,"영국":None,"독일":None,"프랑스":23,"멕시코":14,"캐나다":24,"한국":4, "호주":23,"브라질":18,"스페인":None}),
        ("2025-10-27", {"미국":11,"일본":8, "홍콩":23,"인도":None,"영국":None,"독일":None,"프랑스":23,"멕시코":13,"캐나다":15,"한국":8, "호주":None,"브라질":12,"스페인":16}),
        ("2025-11-03", {"미국":8, "일본":23,"홍콩":None,"인도":20,"영국":None,"독일":None,"프랑스":22,"멕시코":14,"캐나다":12,"한국":7, "호주":16,"브라질":8, "스페인":13}),
        ("2025-11-10", {"미국":8, "일본":24,"홍콩":23,"인도":1, "영국":None,"독일":None,"프랑스":22,"멕시코":14,"캐나다":12,"한국":7, "호주":16,"브라질":7, "스페인":15}),
        ("2025-11-17", {"미국":23,"일본":None,"홍콩":17,"인도":11,"영국":None,"독일":None,"프랑스":24,"멕시코":16,"캐나다":None,"한국":14,"호주":None,"브라질":15,"스페인":17}),
        ("2025-11-24", {"미국":None,"일본":None,"홍콩":24,"인도":13,"영국":19,"독일":None,"프랑스":22,"멕시코":10,"캐나다":22,"한국":9, "호주":19,"브라질":13,"스페인":None}),
        ("2025-12-01", {"미국":20,"일본":None,"홍콩":20,"인도":14,"영국":20,"독일":16,"프랑스":18,"멕시코":17,"캐나다":18,"한국":12,"호주":15,"브라질":12,"스페인":22}),
        ("2025-12-08", {"미국":17,"일본":None,"홍콩":23,"인도":14,"영국":13,"독일":21,"프랑스":11,"멕시코":12,"캐나다":22,"한국":9, "호주":11,"브라질":10,"스페인":21}),
        ("2025-12-15", {"미국":9, "일본":21,"홍콩":12,"인도":8, "영국":10,"독일":12,"프랑스":9, "멕시코":9, "캐나다":7, "한국":9, "호주":6, "브라질":7, "스페인":12}),
        ("2025-12-22", {"미국":22,"일본":None,"홍콩":None,"인도":23,"영국":None,"독일":18,"프랑스":23,"멕시코":15,"캐나다":19,"한국":18,"호주":None,"브라질":23,"스페인":19}),
        ("2025-12-29", {"미국":20,"일본":21,"홍콩":23,"인도":17,"영국":None,"독일":20,"프랑스":10,"멕시코":19,"캐나다":21,"한국":11,"호주":10,"브라질":11,"스페인":23}),
        ("2026-01-05", {"미국":15,"일본":None,"홍콩":15,"인도":9, "영국":17,"독일":14,"프랑스":11,"멕시코":14,"캐나다":15,"한국":10,"호주":20,"브라질":11,"스페인":13}),
    ]

    CUTOFF = datetime.strptime("2026-01-11", "%Y-%m-%d")

    from datetime import timedelta
    result = []
    for week_start_str, country_ranks in weekly_raw:
        week_start = datetime.strptime(week_start_str, "%Y-%m-%d")

        wa_num, wa_den = 0.0, 0.0
        for c, v in country_ranks.items():
            if v is not None:
                m = get_multiplier(c)
                wa_num += v * m; wa_den += m
        avg_rank = round(wa_num / wa_den, 1) if wa_den > 0 else 15.0

        for day_offset in range(7):
            day = week_start + timedelta(days=day_offset)
            if day >= CUTOFF:
                break
            result.append({
                "date": day.strftime("%Y-%m-%d"),
                "average_rank": avg_rank,
                "country_ranks": country_ranks
            })

    seen = {}
    for item in result:
        seen[item['date']] = item
    result = sorted(seen.values(), key=lambda x: x['date'])

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f'✓ historical_ranking_data.json 생성: {len(result)}일치 데이터 → {output_path}')
    return result


def main():
    """메인 실행 함수"""
    setup_korean_font()
    
    data_file = 'rank_history.json'
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
    
    print('📋 Creating ranking text...')
    table_texts = create_ranking_table(data)
    print()
    
    historical_file = 'historical_ranking_data.json'
    if not os.path.exists(historical_file):
        print('📅 historical_ranking_data.json not found → building from weekly data...')
        build_historical_data_from_weekly(historical_file)
        print()

    print('💰 Estimating daily sales...')
    sales_table_path, sales_chart_path, daily_sales = estimate_daily_sales(data)
    print()
    
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
    
    if discord_webhook:
        print('📤 Sending latest rankings to Discord...')
        send_latest_rankings_to_discord(discord_webhook, latest_rankings, table_texts, daily_sales)
        print()
        
        print('📤 Sending graph notification to Discord...')
        send_discord_notification(discord_webhook, country_data, dates)
    else:
        print('ℹ️  Set DISCORD_WEBHOOK environment variable to enable notifications')

if __name__ == '__main__':
    main()
