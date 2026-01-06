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
        
        # 추적할 국가/지역
        self.regions = {
            'US': {'name': '미국', 'steam_cc': 'us', 'psn_region': 'en/us', 'amazon': 'com'},
            'KR': {'name': '한국', 'steam_cc': 'kr', 'psn_region': 'ko/kr', 'amazon': None},
            'JP': {'name': '일본', 'steam_cc': 'jp', 'psn_region': 'ja/jp', 'amazon': 'co.jp'},
            'GB': {'name': '영국', 'steam_cc': 'gb', 'psn_region': 'en/gb', 'amazon': 'co.uk'},
            'DE': {'name': '독일', 'steam_cc': 'de', 'psn_region': 'de/de', 'amazon': 'de'},
            'FR': {'name': '프랑스', 'steam_cc': 'fr', 'psn_region': 'fr/fr', 'amazon': 'fr'}
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
    
    def get_ggdeals_wishlist_rank(self, platform: str = 'playstation', preorder_only: bool = True) -> Optional[Dict]:
        """GG.deals에서 Wishlist 순위 확인 - 실제 순위 제공!"""
        print(f"\n🔍 GG.deals ({platform}) Wishlist 순위 확인 중...")
        
        try:
            # GG.deals 예약 판매 게임 순위 페이지
            if preorder_only:
                url = f"https://gg.deals/ranking/{platform}/most-wishlisted/pre-orders/"
            else:
                url = f"https://gg.deals/ranking/{platform}/most-wishlisted/"
            
            response = requests.get(url, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 게임 리스트 찾기
                game_items = soup.find_all('div', class_='game-item')
                if not game_items:
                    # 다른 클래스 시도
                    game_items = soup.find_all('a', href=re.compile(r'/game/'))
                
                for rank, item in enumerate(game_items[:100], 1):
                    # 제목 찾기
                    title_elem = item.find('span', class_='game-info-title')
                    if not title_elem:
                        title_elem = item.find('div', class_='title')
                    
                    if title_elem:
                        title = title_elem.text.strip().lower()
                        
                        if 'crimson desert' in title:
                            print(f"  ✅ GG.deals ({platform}): {rank}위 발견!")
                            return {
                                'platform': platform.capitalize(),
                                'source': 'GG.deals',
                                'type': 'Wishlist Ranking',
                                'rank': rank,
                                'found': True,
                                'title': title_elem.text.strip()
                            }
                
                print(f"  ❌ GG.deals ({platform}) TOP 100에서 찾을 수 없음")
                return {
                    'platform': platform.capitalize(),
                    'source': 'GG.deals',
                    'found': False,
                    'message': 'TOP 100 위시리스트에 없음'
                }
            
        except Exception as e:
            print(f"  ⚠️  GG.deals ({platform}) 조회 실패: {e}")
            return {
                'platform': platform.capitalize(),
                'source': 'GG.deals',
                'found': False,
                'message': '조회 오류'
            }
    
    def get_steam_wishlist_rank(self, region_code: str = 'us') -> Optional[Dict]:
        """Steam Wishlist 순위 확인 (국가별)"""
        region_name = self.regions.get(region_code.upper(), {}).get('name', region_code)
        print(f"\n🔍 Steam ({region_name}) Wishlist 순위 확인 중...")
        
        try:
            # Steam Top Wishlist 페이지 (국가별)
            url = "https://store.steampowered.com/search/"
            params = {
                'filter': 'popularwishlist',
                'category1': 998,  # Games
                'cc': region_code.lower()  # 국가 코드
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 검색 결과에서 Crimson Desert 찾기
                search_results = soup.find_all('a', class_='search_result_row')
                
                for rank, result in enumerate(search_results, 1):
                    title_elem = result.find('span', class_='title')
                    
                    if title_elem and 'crimson desert' in title_elem.text.lower():
                        print(f"  ✅ Steam ({region_name}) Wishlist: {rank}위 발견!")
                        return {
                            'platform': 'Steam',
                            'region': region_name,
                            'type': 'Wishlist Ranking',
                            'rank': rank,
                            'found': True,
                            'title': title_elem.text.strip()
                        }
                
                print(f"  ❌ Steam ({region_name}) Wishlist TOP 100에서 찾을 수 없음")
                return {
                    'platform': 'Steam',
                    'region': region_name,
                    'type': 'Wishlist Ranking',
                    'found': False,
                    'message': 'TOP 100 위시리스트에 없음'
                }
                
        except Exception as e:
            print(f"  ⚠️  Steam ({region_name}) 조회 실패: {e}")
            return {
                'platform': 'Steam',
                'region': region_name,
                'found': False,
                'message': f'조회 오류'
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
    
    def get_playstation_preorder_rank(self, region_code: str = 'US') -> Optional[Dict]:
        """PlayStation Store 예약 순위 확인 (국가별)"""
        region_name = self.regions.get(region_code.upper(), {}).get('name', region_code)
        psn_region = self.regions.get(region_code.upper(), {}).get('psn_region', 'en/us')
        
        print(f"\n🔍 PlayStation Store ({region_name}) 예약 순위 확인 중...")
        
        try:
            # PlayStation Store 직접 검색
            search_url = f"https://store.playstation.com/{psn_region}/search/crimson%20desert"
            
            response = requests.get(search_url, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                if 'crimson' in response.text.lower() and 'desert' in response.text.lower():
                    print(f"  ✅ PlayStation Store ({region_name}): 예약 가능 페이지 발견")
                    return {
                        'platform': 'PlayStation',
                        'region': region_name,
                        'type': 'Pre-order Available',
                        'found': True,
                        'status': '예약 가능',
                        'url': search_url
                    }
            
            print(f"  ❌ PlayStation Store ({region_name}): 찾을 수 없음")
            return {
                'platform': 'PlayStation',
                'region': region_name,
                'found': False,
                'message': '예약 정보 없음'
            }
            
        except Exception as e:
            print(f"  ⚠️  PlayStation Store ({region_name}) 조회 실패: {e}")
            return {
                'platform': 'PlayStation',
                'region': region_name,
                'found': False,
                'message': '조회 오류'
            }
    
    def get_xbox_preorder_rank(self, region_code: str = 'US') -> Optional[Dict]:
        """Xbox Store 예약 순위 확인 (국가별)"""
        region_name = self.regions.get(region_code.upper(), {}).get('name', region_code)
        
        print(f"\n🔍 Xbox Store ({region_name}) 예약 순위 확인 중...")
        
        try:
            # Microsoft Store 검색
            search_url = f"https://www.microsoft.com/{region_code.lower()}-{region_code.lower()}/search/shop/games"
            params = {'q': 'crimson desert'}
            
            response = requests.get(search_url, params=params, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                if 'crimson' in response.text.lower() and 'desert' in response.text.lower():
                    print(f"  ✅ Xbox Store ({region_name}): 예약 가능 페이지 발견")
                    return {
                        'platform': 'Xbox',
                        'region': region_name,
                        'type': 'Pre-order Available',
                        'found': True,
                        'status': '예약 가능'
                    }
            
            print(f"  ❌ Xbox Store ({region_name}): 찾을 수 없음")
            return {
                'platform': 'Xbox',
                'region': region_name,
                'found': False,
                'message': '예약 정보 없음'
            }
            
        except Exception as e:
            print(f"  ⚠️  Xbox Store ({region_name}) 조회 실패: {e}")
            return {
                'platform': 'Xbox',
                'region': region_name,
                'found': False,
                'message': '조회 오류'
            }
    
    def get_amazon_preorder_rank(self, region_code: str = 'US') -> Optional[Dict]:
        """Amazon 예약 판매 순위 확인 (국가별)"""
        region_name = self.regions.get(region_code.upper(), {}).get('name', region_code)
        amazon_domain = self.regions.get(region_code.upper(), {}).get('amazon')
        
        if not amazon_domain:
            print(f"  ⚠️  Amazon ({region_name}): 해당 국가 미지원")
            return {
                'platform': 'Amazon',
                'region': region_name,
                'found': False,
                'message': 'Amazon 미지원 국가'
            }
        
        print(f"\n🔍 Amazon ({region_name}) 예약 판매 순위 확인 중...")
        
        try:
            # Amazon 검색
            url = f"https://www.amazon.{amazon_domain}/s"
            params = {
                'k': 'crimson desert',
                'i': 'videogames'
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 검색 결과에서 Crimson Desert 찾기
                results = soup.find_all('div', {'data-component-type': 's-search-result'})
                
                for rank, result in enumerate(results[:20], 1):
                    title_elem = result.find('h2')
                    
                    if title_elem and 'crimson desert' in title_elem.text.lower():
                        print(f"  ✅ Amazon ({region_name}): {rank}위 발견")
                        return {
                            'platform': 'Amazon',
                            'region': region_name,
                            'rank': rank,
                            'found': True
                        }
                
                print(f"  ❌ Amazon ({region_name}): 검색 결과 없음")
                return {
                    'platform': 'Amazon',
                    'region': region_name,
                    'found': False,
                    'message': '검색 결과 없음'
                }
            
        except Exception as e:
            print(f"  ⚠️  Amazon ({region_name}) 조회 실패: {e}")
            return {
                'platform': 'Amazon',
                'region': region_name,
                'found': False,
                'message': '조회 오류'
            }
    
    def track_all_platforms(self) -> Dict:
        """모든 국가 × 모든 플랫폼 예약 순위 추적"""
        print("\n" + "="*70)
        print("🌍 Crimson Desert 전세계 예약 판매 순위 추적 시작")
        print(f"📅 출시일: {self.game_info['release_date']}")
        print(f"🗺️  추적 국가: {len(self.regions)}개")
        print("="*70)
        
        timestamp = datetime.now().isoformat()
        results = {
            'timestamp': timestamp,
            'game': 'Crimson Desert',
            'regions': {}
        }
        
        # 각 국가별로 플랫폼 조회
        for region_code, region_info in self.regions.items():
            region_name = region_info['name']
            print(f"\n{'='*70}")
            print(f"🌏 {region_name} ({region_code}) 조회 중...")
            print(f"{'='*70}")
            
            region_results = {
                'name': region_name,
                'code': region_code,
                'platforms': {}
            }
            
            # Steam
            steam_result = self.get_steam_wishlist_rank(region_code)
            if steam_result:
                region_results['platforms']['Steam'] = steam_result
            time.sleep(2)
            
            # PlayStation (GG.deals에서 실제 순위 확인)
            ps_gg_result = self.get_ggdeals_wishlist_rank('playstation', preorder_only=True)
            if ps_gg_result and ps_gg_result.get('found'):
                region_results['platforms']['PlayStation'] = ps_gg_result
            else:
                # 실패 시 기존 방법 시도
                ps_result = self.get_playstation_preorder_rank(region_code)
                if ps_result:
                    region_results['platforms']['PlayStation'] = ps_result
            time.sleep(2)
            
            # Xbox (GG.deals에서 실제 순위 확인 시도)
            # 참고: GG.deals는 주로 Steam과 PlayStation 중심
            xbox_result = self.get_xbox_preorder_rank(region_code)
            if xbox_result:
                region_results['platforms']['Xbox'] = xbox_result
            time.sleep(2)
            
            # Amazon (지원 국가만)
            if region_info.get('amazon'):
                amazon_result = self.get_amazon_preorder_rank(region_code)
                if amazon_result:
                    region_results['platforms']['Amazon'] = amazon_result
                time.sleep(2)
            
            results['regions'][region_code] = region_results
        
        # 결과 저장
        self.data['rankings'] = results
        self.data['history'].append(results)
        self.save_data()
        
        return results
    
    def display_results(self, results: Dict):
        """결과 출력 - 국가별 정리"""
        print("\n" + "="*70)
        print("🎮 Crimson Desert 전세계 예약 판매 순위 추적 결과")
        print(f"⏰ 수집 시간: {datetime.fromisoformat(results['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        total_found = 0
        total_platforms = 0
        
        for region_code, region_data in results.get('regions', {}).items():
            region_name = region_data.get('name', region_code)
            
            print(f"\n🌏 {region_name} ({region_code})")
            print("-" * 70)
            
            for platform_name, platform_data in region_data.get('platforms', {}).items():
                total_platforms += 1
                
                if platform_data.get('found'):
                    total_found += 1
                    rank = platform_data.get('rank', '예약 가능')
                    status = platform_data.get('status', '')
                    
                    print(f"   ✅ {platform_name}: ", end='')
                    if isinstance(rank, int):
                        print(f"{rank}위")
                    else:
                        print(f"{status or rank}")
                else:
                    message = platform_data.get('message', '정보 없음')
                    print(f"   ❌ {platform_name}: {message}")
        
        print("\n" + "="*70)
        print(f"📊 요약:")
        print(f"   🗺️  조사 국가: {len(results.get('regions', {}))}개")
        print(f"   🎮 총 플랫폼: {total_platforms}개")
        print(f"   ✅ 정보 확인: {total_found}개")
        print(f"   📈 발견율: {total_found}/{total_platforms} ({int(total_found/total_platforms*100) if total_platforms > 0 else 0}%)")
        print("="*70)
    
    def send_to_discord(self, results: Dict):
        """Discord로 결과 전송 - 국가별 정리"""
        if not self.discord_webhook:
            print("\n❌ Discord Webhook URL이 설정되지 않았습니다.")
            return False
        
        try:
            timestamp = results.get('timestamp', '')
            
            # 발견된 정보 카운트
            total_found = 0
            total_platforms = 0
            for region_data in results.get('regions', {}).values():
                for platform_data in region_data.get('platforms', {}).values():
                    total_platforms += 1
                    if platform_data.get('found'):
                        total_found += 1
            
            # Embed 색상
            if total_found >= total_platforms * 0.7:
                color = 3066993  # 초록
            elif total_found >= total_platforms * 0.4:
                color = 16776960  # 노랑
            else:
                color = 15158332  # 빨강
            
            # 메인 Embed
            embed = {
                "title": "🌍 Crimson Desert 전세계 예약 순위",
                "description": f"출시일: 2026년 3월 19일\n{total_found}/{total_platforms} 플랫폼에서 정보 확인",
                "color": color,
                "timestamp": timestamp,
                "fields": [],
                "footer": {"text": "Crimson Desert Global Pre-order Tracker"}
            }
            
            # 국가별로 필드 추가
            for region_code, region_data in results.get('regions', {}).items():
                region_name = region_data.get('name', region_code)
                field_value = []
                
                for platform_name, platform_data in region_data.get('platforms', {}).items():
                    if platform_data.get('found'):
                        rank = platform_data.get('rank', '예약 가능')
                        if isinstance(rank, int):
                            field_value.append(f"✅ {platform_name}: **{rank}위**")
                        else:
                            field_value.append(f"✅ {platform_name}: {rank}")
                    else:
                        field_value.append(f"❌ {platform_name}")
                
                # 각 국가를 하나의 필드로
                embed["fields"].append({
                    "name": f"🌏 {region_name}",
                    "value": "\n".join(field_value) if field_value else "데이터 없음",
                    "inline": True
                })
            
            # Discord 전송
            payload = {"embeds": [embed]}
            response = requests.post(self.discord_webhook, json=payload)
            
            if response.status_code == 204:
                print("\n✅ Discord로 전세계 순위 전송 완료!")
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
