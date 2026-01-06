"""
Crimson Desert Pre-Order Rankings Tracker
전세계 플랫폼별 Crimson Desert 예약 판매 순위 추적
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from typing import Dict, List, Optional
import time
import os
import re

class CrimsonDesertTracker:
    """Crimson Desert 예약 판매 순위 추적 클래스"""
    
    def __init__(self, data_file: str = "crimson_desert_preorders.json", discord_webhook: str = None):
        self.data_file = data_file
        self.discord_webhook = discord_webhook or os.getenv('DISCORD_WEBHOOK_URL')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.data = self.load_data()
        
        # Crimson Desert 정보
        self.game_info = {
            'name': 'Crimson Desert',
            'release_date': '2026-03-19',
            'steam_id': '3321460',
            'platforms': ['Steam (PC)', 'PlayStation 5', 'Xbox Series X/S']
        }
    
    def load_data(self) -> Dict:
        """저장된 데이터 로드"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "game": "Crimson Desert",
                "rankings": {},
                "history": [],
                "last_updated": None
            }
    
    def save_data(self):
        """데이터 저장"""
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def get_steam_wishlist_rank(self) -> Optional[Dict]:
        """Steam Wishlist 순위 확인"""
        print("\n🔍 Steam Wishlist 순위 확인 중...")
        
        try:
            # Steam Top Wishlist 페이지
            url = "https://store.steampowered.com/search/"
            params = {
                'filter': 'popularwishlist',
                'category1': 998  # Games
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 검색 결과에서 Crimson Desert 찾기
                search_results = soup.find_all('a', class_='search_result_row')
                
                for rank, result in enumerate(search_results, 1):
                    app_id = result.get('data-ds-appid', '')
                    title = result.find('span', class_='title')
                    
                    if title and 'crimson desert' in title.text.lower():
                        print(f"  ✅ Steam Wishlist: {rank}위 발견!")
                        return {
                            'platform': 'Steam (PC)',
                            'type': 'Wishlist Ranking',
                            'rank': rank,
                            'found': True,
                            'title': title.text.strip(),
                            'note': f'Steam 가장 많이 위시리스트에 추가된 게임 {rank}위'
                        }
                
                print(f"  ❌ Steam Wishlist TOP 100에서 찾을 수 없음")
                return {
                    'platform': 'Steam (PC)',
                    'type': 'Wishlist Ranking',
                    'found': False,
                    'message': 'TOP 100 위시리스트에 없음'
                }
                
        except Exception as e:
            print(f"  ⚠️  Steam 조회 실패: {e}")
            return {
                'platform': 'Steam (PC)',
                'found': False,
                'message': f'조회 오류: {str(e)}'
            }
    
    def get_steam_preorder_info(self) -> Optional[Dict]:
        """Steam 예약 구매 정보 확인"""
        print("\n🔍 Steam 예약 구매 정보 확인 중...")
        
        try:
            url = f"https://store.steampowered.com/app/{self.game_info['steam_id']}/Crimson_Desert/"
            
            response = requests.get(url, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 예약 구매 가능 여부 확인
                purchase_area = soup.find('div', class_='game_purchase_action')
                
                if purchase_area:
                    btn_text = purchase_area.text.lower()
                    
                    if 'pre-purchase' in btn_text or 'pre-order' in btn_text:
                        print(f"  ✅ Steam에서 예약 구매 가능!")
                        return {
                            'platform': 'Steam (PC)',
                            'type': 'Pre-order Available',
                            'found': True,
                            'status': '예약 구매 가능',
                            'url': url
                        }
                
                print(f"  ℹ️  Steam 페이지 존재하나 예약 구매 정보 확인 필요")
                return {
                    'platform': 'Steam (PC)',
                    'found': True,
                    'status': '페이지 존재',
                    'url': url
                }
                
        except Exception as e:
            print(f"  ⚠️  Steam 페이지 조회 실패: {e}")
            return None
    
    def get_playstation_preorder_rank(self, region: str = 'US') -> Optional[Dict]:
        """PlayStation Store 예약 순위 확인"""
        print(f"\n🔍 PlayStation Store ({region}) 예약 순위 확인 중...")
        
        try:
            # PlayStation Store 검색 API
            search_url = "https://web.np.playstation.com/api/graphql/v1/op"
            
            # 예약 가능 게임 카테고리 쿼리
            params = {
                "operationName": "categoryGridRetrieve",
                "variables": json.dumps({
                    "id": "upcoming-games",  # 출시 예정 게임
                    "pageArgs": {"size": 50, "offset": 0},
                    "sortBy": {"name": "releaseDate", "isAscending": True}
                }),
                "extensions": json.dumps({
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "9845afc0dbaab4965f6563fffc703f588c8e76792000e8610843b8d3ee9c4c09"
                    }
                })
            }
            
            response = requests.get(search_url, params=params, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data:
                    products = data.get('data', {}).get('categoryGridRetrieve', {}).get('products', [])
                    
                    for rank, product in enumerate(products, 1):
                        name = product.get('name', '').lower()
                        
                        if 'crimson desert' in name:
                            print(f"  ✅ PlayStation Store: 출시 예정 {rank}번째 게임")
                            return {
                                'platform': 'PlayStation 5',
                                'region': region,
                                'type': 'Upcoming Games',
                                'rank': rank,
                                'found': True,
                                'title': product.get('name'),
                                'note': f'출시 예정 게임 {rank}번째'
                            }
            
            print(f"  ℹ️  PlayStation Store API 응답 제한")
            return {
                'platform': 'PlayStation 5',
                'found': False,
                'message': 'API 데이터 제한으로 순위 확인 불가'
            }
            
        except Exception as e:
            print(f"  ⚠️  PlayStation Store 조회 실패: {e}")
            return {
                'platform': 'PlayStation 5',
                'found': False,
                'message': f'조회 오류: {str(e)}'
            }
    
    def get_amazon_preorder_rank(self, region: str = 'US') -> Optional[Dict]:
        """Amazon 예약 판매 순위 확인"""
        print(f"\n🔍 Amazon ({region}) 예약 판매 순위 확인 중...")
        
        try:
            # Amazon 비디오 게임 베스트셀러
            if region == 'US':
                url = "https://www.amazon.com/bestsellers/videogames"
            elif region == 'JP':
                url = "https://www.amazon.co.jp/gp/bestsellers/videogames"
            else:
                url = f"https://www.amazon.{region.lower()}/bestsellers/videogames"
            
            response = requests.get(url, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 베스트셀러 아이템 찾기
                items = soup.find_all('div', {'class': re.compile('zg-grid-general-faceout')})
                
                for rank_elem in items:
                    title_elem = rank_elem.find('div', class_='p13n-sc-truncate')
                    
                    if title_elem and 'crimson desert' in title_elem.text.lower():
                        rank_badge = rank_elem.find('span', class_='zg-bdg-text')
                        rank = rank_badge.text.strip('#') if rank_badge else '?'
                        
                        print(f"  ✅ Amazon 베스트셀러: {rank}위")
                        return {
                            'platform': f'Amazon ({region})',
                            'type': 'Bestseller Rank',
                            'rank': rank,
                            'found': True,
                            'note': 'Amazon 비디오 게임 베스트셀러'
                        }
            
            print(f"  ❌ Amazon 베스트셀러에서 찾을 수 없음")
            return {
                'platform': f'Amazon ({region})',
                'found': False,
                'message': '베스트셀러 차트에 없음'
            }
            
        except Exception as e:
            print(f"  ⚠️  Amazon 조회 실패: {e}")
            return {
                'platform': f'Amazon ({region})',
                'found': False,
                'message': f'조회 오류: {str(e)}'
            }
    
    def track_all_platforms(self) -> Dict:
        """모든 플랫폼 예약 순위 추적"""
        print("\n" + "="*70)
        print("🎮 Crimson Desert 예약 판매 순위 추적 시작")
        print(f"📅 출시일: {self.game_info['release_date']}")
        print("="*70)
        
        timestamp = datetime.now().isoformat()
        results = {
            'timestamp': timestamp,
            'game': 'Crimson Desert',
            'platforms': {}
        }
        
        # Steam Wishlist 순위
        steam_wishlist = self.get_steam_wishlist_rank()
        if steam_wishlist:
            results['platforms']['Steam_Wishlist'] = steam_wishlist
        
        time.sleep(3)
        
        # Steam 예약 구매 정보
        steam_preorder = self.get_steam_preorder_info()
        if steam_preorder:
            results['platforms']['Steam_Preorder'] = steam_preorder
        
        time.sleep(3)
        
        # PlayStation Store
        ps_rank = self.get_playstation_preorder_rank('US')
        if ps_rank:
            results['platforms']['PlayStation_US'] = ps_rank
        
        time.sleep(3)
        
        # Amazon 순위
        amazon_rank = self.get_amazon_preorder_rank('US')
        if amazon_rank:
            results['platforms']['Amazon_US'] = amazon_rank
        
        # 결과 저장
        self.data['rankings'] = results
        self.data['history'].append(results)
        self.save_data()
        
        return results
    
    def display_results(self, results: Dict):
        """결과 출력"""
        print("\n" + "="*70)
        print("🎮 Crimson Desert 예약 판매 순위 추적 결과")
        print(f"⏰ 수집 시간: {datetime.fromisoformat(results['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        found_count = 0
        
        for platform_key, platform_data in results.get('platforms', {}).items():
            platform_name = platform_data.get('platform', platform_key)
            platform_type = platform_data.get('type', '')
            
            if platform_data.get('found'):
                found_count += 1
                rank = platform_data.get('rank', '?')
                note = platform_data.get('note', platform_data.get('status', ''))
                
                print(f"\n✅ {platform_name}")
                if platform_type:
                    print(f"   📊 유형: {platform_type}")
                print(f"   🏆 순위: {rank}위")
                if note:
                    print(f"   💡 {note}")
            else:
                message = platform_data.get('message', '정보 없음')
                print(f"\n❌ {platform_name}")
                print(f"   {message}")
        
        print("\n" + "="*70)
        print(f"📊 요약: {len(results.get('platforms', {}))}개 플랫폼 조사")
        print(f"✅ {found_count}개 플랫폼에서 정보 확인")
        print("="*70)
    
    def send_to_discord(self, results: Dict):
        """Discord로 결과 전송"""
        if not self.discord_webhook:
            print("\n❌ Discord Webhook URL이 설정되지 않았습니다.")
            return False
        
        try:
            timestamp = results.get('timestamp', '')
            found_count = sum(1 for p in results.get('platforms', {}).values() if p.get('found'))
            
            # Embed 색상
            if found_count >= 3:
                color = 3066993  # 초록
            elif found_count >= 1:
                color = 16776960  # 노랑
            else:
                color = 15158332  # 빨강
            
            embed = {
                "title": "🎮 Crimson Desert 예약 판매 순위",
                "description": f"출시일: 2026년 3월 19일\n{found_count}개 플랫폼에서 정보 확인",
                "color": color,
                "timestamp": timestamp,
                "fields": [],
                "footer": {"text": "Crimson Desert Pre-order Tracker"}
            }
            
            # 플랫폼별 정보
            for platform_key, platform_data in results.get('platforms', {}).items():
                platform_name = platform_data.get('platform', platform_key)
                
                if platform_data.get('found'):
                    rank = platform_data.get('rank', '?')
                    note = platform_data.get('note', platform_data.get('status', ''))
                    value = f"**{rank}위**\n{note}" if note else f"**{rank}위**"
                    
                    embed["fields"].append({
                        "name": f"✅ {platform_name}",
                        "value": value,
                        "inline": True
                    })
                else:
                    message = platform_data.get('message', '정보 없음')
                    embed["fields"].append({
                        "name": f"❌ {platform_name}",
                        "value": message,
                        "inline": True
                    })
            
            # Discord 전송
            payload = {"embeds": [embed]}
            response = requests.post(self.discord_webhook, json=payload)
            
            if response.status_code == 204:
                print("\n✅ Discord로 결과 전송 완료!")
                return True
            else:
                print(f"\n❌ Discord 전송 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"\n❌ Discord 전송 오류: {e}")
            return False
    
    def generate_report(self, filename: str = None):
        """리포트 생성"""
        if filename is None:
            filename = f"crimson_desert_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("Crimson Desert 예약 판매 순위 리포트\n")
            f.write("="*70 + "\n\n")
            f.write(f"게임명: Crimson Desert\n")
            f.write(f"출시일: 2026년 3월 19일\n")
            f.write(f"플랫폼: PC (Steam), PlayStation 5, Xbox Series X/S\n\n")
            
            if self.data.get('history'):
                latest = self.data['history'][-1]
                
                f.write(f"수집 시간: {latest.get('timestamp', 'N/A')}\n\n")
                f.write("-"*70 + "\n\n")
                
                for platform_key, platform_data in latest.get('platforms', {}).items():
                    platform_name = platform_data.get('platform', platform_key)
                    f.write(f"{platform_name}\n")
                    
                    if platform_data.get('found'):
                        rank = platform_data.get('rank', '?')
                        note = platform_data.get('note', platform_data.get('status', ''))
                        f.write(f"  순위: {rank}위\n")
                        if note:
                            f.write(f"  비고: {note}\n")
                    else:
                        message = platform_data.get('message', '정보 없음')
                        f.write(f"  상태: {message}\n")
                    
                    f.write("\n")
            
            f.write(f"\n생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        print(f"\n✅ 리포트 생성 완료: {filename}")


def auto_run():
    """GitHub Actions 자동 실행"""
    print("\n" + "="*70)
    print("🤖 Crimson Desert 예약 순위 자동 추적")
    print("="*70)
    
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print("\n❌ Discord Webhook URL이 설정되지 않았습니다.")
        return
    
    tracker = CrimsonDesertTracker(discord_webhook=webhook_url)
    
    # 순위 추적
    results = tracker.track_all_platforms()
    
    # 결과 출력
    tracker.display_results(results)
    
    # Discord 전송
    tracker.send_to_discord(results)
    
    # 리포트 생성
    tracker.generate_report()
    
    print("\n✅ 자동 추적 완료!")


def main():
    """대화형 메뉴"""
    print("\n" + "="*70)
    print("🎮 Crimson Desert 예약 판매 순위 추적 시스템")
    print("="*70)
    
    webhook_url = input("\nDiscord Webhook URL (선택, 엔터로 건너뛰기): ").strip()
    tracker = CrimsonDesertTracker(discord_webhook=webhook_url if webhook_url else None)
    
    print("\n옵션 선택:")
    print("1. 예약 순위 추적")
    print("2. 저장된 데이터 보기")
    print("3. Discord로 전송")
    print("4. 리포트 생성")
    
    choice = input("\n선택 (1-4): ").strip()
    
    if choice == "1":
        results = tracker.track_all_platforms()
        tracker.display_results(results)
        
        if tracker.discord_webhook:
            send = input("\nDiscord로 전송? (y/n): ").lower()
            if send == 'y':
                tracker.send_to_discord(results)
    
    elif choice == "2":
        if tracker.data.get('history'):
            latest = tracker.data['history'][-1]
            tracker.display_results(latest)
        else:
            print("\n저장된 데이터가 없습니다.")
    
    elif choice == "3":
        if tracker.data.get('history'):
            latest = tracker.data['history'][-1]
            tracker.send_to_discord(latest)
        else:
            print("\n전송할 데이터가 없습니다.")
    
    elif choice == "4":
        tracker.generate_report()


if __name__ == "__main__":
    if os.getenv('GITHUB_ACTIONS') == 'true':
        auto_run()
    else:
        main()
