"""
Black Desert Game - Real-time Platform Sales Ranking Scraper
실제 웹사이트에서 전세계 각 플랫폼별 판매량 순위를 수집하는 시스템
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from typing import Dict, List, Optional
import time
import re

class GameSalesScraper:
    """게임 판매량 스크래핑 및 집계 클래스"""
    
    def __init__(self, data_file: str = "sales_data.json"):
        self.data_file = data_file
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.data = self.load_data()
    
    def load_data(self) -> Dict:
        """저장된 데이터 로드"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "game_name": "Black Desert",
                "platforms": {},
                "last_updated": None,
                "history": []
            }
    
    def save_data(self):
        """데이터 저장"""
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def scrape_steam_bestsellers(self) -> List[Dict]:
        """Steam 베스트셀러 차트 스크래핑"""
        print("\n🎮 Steam 베스트셀러 차트 수집 중...")
        url = "https://store.steampowered.com/charts/topselling/global"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            games = []
            # Steam 차트 구조 분석
            chart_items = soup.find_all('div', class_='Chart_ChartTable')
            
            if chart_items:
                rows = chart_items[0].find_all('a', class_='weeklytopsellers_TableRow')
                
                for i, row in enumerate(rows[:20], 1):
                    try:
                        title_elem = row.find('div', class_='weeklytopsellers_GameName')
                        title = title_elem.text.strip() if title_elem else f"Game #{i}"
                        
                        games.append({
                            'rank': i,
                            'title': title,
                            'platform': 'Steam (PC)',
                            'url': row.get('href', '')
                        })
                    except Exception as e:
                        print(f"  ⚠️  항목 파싱 오류: {e}")
                        continue
            
            print(f"✓ Steam: {len(games)}개 게임 수집 완료")
            return games
            
        except Exception as e:
            print(f"✗ Steam 스크래핑 실패: {e}")
            return []
    
    def scrape_playstation_store(self, region: str = "US") -> List[Dict]:
        """PlayStation Store 인기 차트 API 호출"""
        print(f"\n🎮 PlayStation Store ({region}) 데이터 수집 중...")
        
        # PlayStation Store GraphQL API
        url = "https://web.np.playstation.com/api/graphql/v1/op"
        
        # 인기 게임 카테고리 쿼리
        params = {
            "operationName": "categoryGridRetrieve",
            "variables": json.dumps({
                "id": "44d8bb20-653e-431e-8ad0-c0a365f68d2f",  # Popular 카테고리
                "pageArgs": {"size": 20, "offset": 0},
                "sortBy": {"name": "popularityScore", "isAscending": False},
                "filterBy": [],
                "facetOptions": []
            }),
            "extensions": json.dumps({
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "9845afc0dbaab4965f6563fffc703f588c8e76792000e8610843b8d3ee9c4c09"
                }
            })
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                games = []
                
                # API 응답 구조에 따라 데이터 추출
                if 'data' in data and 'categoryGridRetrieve' in data['data']:
                    products = data['data']['categoryGridRetrieve'].get('products', [])
                    
                    for i, product in enumerate(products[:20], 1):
                        games.append({
                            'rank': i,
                            'title': product.get('name', f'Game #{i}'),
                            'platform': 'PlayStation Store',
                            'id': product.get('id', '')
                        })
                
                print(f"✓ PlayStation Store: {len(games)}개 게임 수집 완료")
                return games
            else:
                print(f"✗ PlayStation Store API 오류: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"✗ PlayStation Store 수집 실패: {e}")
            return []
    
    def scrape_vgchartz_preorders(self) -> List[Dict]:
        """VGChartz 예약 판매 차트 스크래핑"""
        print("\n🎮 VGChartz 예약 판매 차트 수집 중...")
        url = "https://www.vgchartz.com/preorders/"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            games = []
            # VGChartz 테이블 구조 분석
            table = soup.find('table')
            
            if table:
                rows = table.find_all('tr')[1:]  # 헤더 제외
                
                for i, row in enumerate(rows[:20], 1):
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        title = cols[1].text.strip()
                        
                        games.append({
                            'rank': i,
                            'title': title,
                            'platform': 'Multi-Platform',
                            'source': 'VGChartz'
                        })
            
            print(f"✓ VGChartz: {len(games)}개 게임 수집 완료")
            return games
            
        except Exception as e:
            print(f"✗ VGChartz 스크래핑 실패: {e}")
            return []
    
    def search_game_ranking(self, game_name: str = "Black Desert") -> Dict:
        """특정 게임의 플랫폼별 순위 검색"""
        print(f"\n🔍 '{game_name}' 게임 순위 검색 중...\n")
        
        results = {
            'game_name': game_name,
            'timestamp': datetime.now().isoformat(),
            'platforms': {}
        }
        
        # Steam 검색
        steam_games = self.scrape_steam_bestsellers()
        for game in steam_games:
            if game_name.lower() in game['title'].lower():
                results['platforms']['Steam'] = {
                    'rank': game['rank'],
                    'found': True,
                    'details': game
                }
                break
        else:
            results['platforms']['Steam'] = {'found': False, 'rank': None}
        
        time.sleep(1)  # Rate limiting
        
        # PlayStation Store 검색
        ps_games = self.scrape_playstation_store()
        for game in ps_games:
            if game_name.lower() in game['title'].lower():
                results['platforms']['PlayStation'] = {
                    'rank': game['rank'],
                    'found': True,
                    'details': game
                }
                break
        else:
            results['platforms']['PlayStation'] = {'found': False, 'rank': None}
        
        # 결과 저장
        self.data['platforms'] = results['platforms']
        self.data['history'].append(results)
        self.save_data()
        
        return results
    
    def get_all_platform_rankings(self) -> Dict:
        """모든 플랫폼의 베스트셀러 차트 수집"""
        print("\n" + "="*70)
        print("전체 플랫폼 베스트셀러 차트 수집 시작")
        print("="*70)
        
        all_data = {
            'timestamp': datetime.now().isoformat(),
            'platforms': {}
        }
        
        # Steam
        steam_data = self.scrape_steam_bestsellers()
        if steam_data:
            all_data['platforms']['Steam'] = steam_data
        
        time.sleep(2)  # Rate limiting
        
        # PlayStation Store
        ps_data = self.scrape_playstation_store()
        if ps_data:
            all_data['platforms']['PlayStation'] = ps_data
        
        time.sleep(2)  # Rate limiting
        
        # VGChartz
        vgc_data = self.scrape_vgchartz_preorders()
        if vgc_data:
            all_data['platforms']['VGChartz'] = vgc_data
        
        # 결과 저장
        self.data['all_rankings'] = all_data
        self.save_data()
        
        return all_data
    
    def display_rankings(self, results: Dict):
        """순위 결과 표시"""
        print("\n" + "="*70)
        print(f"게임: {results.get('game_name', 'Unknown')}")
        print(f"검색 시간: {results.get('timestamp', 'N/A')}")
        print("="*70)
        
        for platform, data in results.get('platforms', {}).items():
            print(f"\n📊 {platform}:")
            if data.get('found'):
                print(f"  ✓ 순위: {data['rank']}위")
                if 'details' in data:
                    print(f"  제목: {data['details'].get('title', 'N/A')}")
            else:
                print(f"  ✗ Top 20 차트에 없음")
        
        print("\n" + "="*70)
    
    def display_all_rankings(self, data: Dict):
        """전체 플랫폼 순위 표시"""
        print("\n" + "="*70)
        print("전세계 플랫폼별 베스트셀러 TOP 10")
        print(f"수집 시간: {data.get('timestamp', 'N/A')}")
        print("="*70)
        
        for platform, games in data.get('platforms', {}).items():
            print(f"\n🎮 {platform}:")
            print("-" * 70)
            
            for game in games[:10]:
                rank = game.get('rank', '?')
                title = game.get('title', 'Unknown')
                print(f"  {rank:2d}위. {title}")
        
        print("\n" + "="*70)
        print(f"총 {len(data.get('platforms', {}))}개 플랫폼에서 데이터 수집 완료")
        print("="*70)
    
    def generate_report(self, filename: str = "rankings_report.txt"):
        """리포트 생성"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("게임 판매량 순위 리포트\n")
            f.write("="*70 + "\n\n")
            
            if 'all_rankings' in self.data:
                data = self.data['all_rankings']
                f.write(f"수집 시간: {data.get('timestamp', 'N/A')}\n\n")
                
                for platform, games in data.get('platforms', {}).items():
                    f.write(f"\n{platform} 베스트셀러 TOP 20\n")
                    f.write("-"*70 + "\n")
                    
                    for game in games:
                        rank = game.get('rank', '?')
                        title = game.get('title', 'Unknown')
                        f.write(f"{rank:2d}위. {title}\n")
                    
                    f.write("\n")
            
            f.write(f"\n생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        print(f"\n✓ 리포트 생성 완료: {filename}")


def main():
    """메인 실행 함수"""
    scraper = GameSalesScraper()
    
    print("\n" + "="*70)
    print("게임 판매량 순위 스크래핑 시스템")
    print("="*70)
    print("\n옵션을 선택하세요:")
    print("1. Black Desert 게임 순위 검색")
    print("2. 전체 플랫폼 베스트셀러 TOP 20 수집")
    print("3. 저장된 데이터 보기")
    print("4. 리포트 생성")
    
    choice = input("\n선택 (1-4): ").strip()
    
    if choice == "1":
        game_name = input("게임 이름 입력 (기본값: Black Desert): ").strip()
        if not game_name:
            game_name = "Black Desert"
        
        results = scraper.search_game_ranking(game_name)
        scraper.display_rankings(results)
    
    elif choice == "2":
        all_data = scraper.get_all_platform_rankings()
        scraper.display_all_rankings(all_data)
    
    elif choice == "3":
        if 'all_rankings' in scraper.data:
            scraper.display_all_rankings(scraper.data['all_rankings'])
        else:
            print("\n저장된 데이터가 없습니다.")
    
    elif choice == "4":
        scraper.generate_report()
    
    else:
        print("\n잘못된 선택입니다.")


if __name__ == "__main__":
    main()
