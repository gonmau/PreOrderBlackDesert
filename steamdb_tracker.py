#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SteamDB Tracker - RSS 방식 (GitHub Actions 최적화)
Selenium 없이 RSS 피드만 사용하여 빠르고 안정적으로 동작
"""

import os
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re

# =============================================================================
# 설정
# =============================================================================

STEAMDB_RSS_URL = "https://steamdb.info/app/3321460/history/?rss=1"
STEAMDB_HISTORY_URL = "https://steamdb.info/app/3321460/history/"
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# =============================================================================
# 함수들
# =============================================================================

def parse_rfc822_date(date_str):
    """RFC 822 날짜 형식 파싱 (예: Mon, 15 Jan 2026 12:34:56 +0000)"""
    try:
        # 간단한 RFC 822 파싱
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str)
    except:
        # 수동 파싱
        try:
            # "Mon, 15 Jan 2026 12:34:56 +0000" 형식
            date_str = date_str.strip()
            # 요일 제거
            if ',' in date_str:
                date_str = date_str.split(',', 1)[1].strip()
            
            # timezone 정보 분리
            parts = date_str.rsplit(' ', 1)
            date_part = parts[0]
            
            # 날짜 파싱 시도
            formats = [
                "%d %b %Y %H:%M:%S",
                "%d %B %Y %H:%M:%S",
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_part, fmt)
                except:
                    continue
            
            return None
        except:
            return None

def check_steamdb_rss():
    """SteamDB RSS 피드에서 오늘 업데이트 확인"""
    print("🔍 SteamDB RSS 피드 확인 중...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        }
        
        print(f"  📥 RSS 피드 가져오는 중: {STEAMDB_RSS_URL}")
        response = requests.get(STEAMDB_RSS_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"  ✅ RSS 피드 가져오기 성공 (크기: {len(response.content)} bytes)")
        
        # 디버깅: RSS 내용 일부 저장
        with open("steamdb_rss_debug.xml", "w", encoding="utf-8") as f:
            f.write(response.text[:2000])
        print("  📄 RSS 샘플 저장: steamdb_rss_debug.xml")
        
        # XML 파싱
        root = ET.fromstring(response.content)
        
        # RSS 2.0 형식의 아이템 찾기
        items = root.findall('.//item')
        
        if not items:
            # Atom 형식 시도
            namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
            items = root.findall('.//atom:entry', namespaces)
        
        print(f"  📊 총 {len(items)}개 RSS 항목 발견")
        
        if len(items) == 0:
            print("  ⚠️  RSS 항목이 없습니다. RSS 피드 형식을 확인하세요.")
            return None
        
        # 오늘 날짜 기준 (UTC)
        now_utc = datetime.utcnow()
        today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        
        print(f"  📅 오늘 날짜 (UTC): {today_start.strftime('%Y-%m-%d')}")
        
        today_updates = []
        
        for idx, item in enumerate(items):
            try:
                # RSS 2.0 필드 찾기
                title = item.find('title')
                pub_date = item.find('pubDate')
                description = item.find('description')
                link = item.find('link')
                
                # Atom 형식 필드 찾기 (폴백)
                if title is None:
                    title = item.find('{http://www.w3.org/2005/Atom}title')
                if pub_date is None:
                    pub_date = item.find('{http://www.w3.org/2005/Atom}updated')
                    if pub_date is None:
                        pub_date = item.find('{http://www.w3.org/2005/Atom}published')
                if description is None:
                    description = item.find('{http://www.w3.org/2005/Atom}summary')
                    if description is None:
                        description = item.find('{http://www.w3.org/2005/Atom}content')
                if link is None:
                    link_elem = item.find('{http://www.w3.org/2005/Atom}link')
                    if link_elem is not None:
                        link_text = link_elem.get('href')
                    else:
                        link_text = None
                else:
                    link_text = link.text if link is not None else None
                
                if title is None:
                    continue
                
                title_text = title.text
                description_text = description.text if description is not None else ""
                
                # 디버깅: 처음 3개 항목 출력
                if idx < 3:
                    print(f"\n  🔍 항목 {idx}:")
                    print(f"     제목: {title_text}")
                    if pub_date is not None:
                        print(f"     날짜: {pub_date.text}")
                
                if pub_date is None:
                    print(f"  ⚠️  날짜 정보 없음: {title_text}")
                    continue
                
                pub_date_text = pub_date.text
                
                # 날짜 파싱
                item_date = parse_rfc822_date(pub_date_text)
                
                if item_date is None:
                    print(f"  ⚠️  날짜 파싱 실패: {pub_date_text}")
                    continue
                
                # timezone-naive로 변환 (UTC 기준)
                if item_date.tzinfo is not None:
                    # UTC로 변환
                    item_date = item_date.replace(tzinfo=None)
                
                # 오늘 날짜인지 확인
                if item_date >= today_start:
                    update_info = {
                        "timestamp": item_date.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "title": title_text,
                        "info": description_text[:200] if description_text else title_text,
                        "link": link_text
                    }
                    
                    today_updates.append(update_info)
                    print(f"  ✅ 오늘 업데이트 발견: [{update_info['timestamp']}] {title_text[:60]}")
                else:
                    # 디버깅: 오늘이 아닌 항목
                    if idx < 3:
                        print(f"     → 오늘이 아님: {item_date.strftime('%Y-%m-%d %H:%M:%S')}")
                
            except Exception as e:
                print(f"  ⚠️  항목 {idx} 처리 오류: {e}")
                continue
        
        if today_updates:
            print(f"\n  ✅ 총 {len(today_updates)}건의 오늘 업데이트 발견")
            return today_updates
        else:
            print("  ℹ️  오늘 업데이트 없음")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"  ❌ RSS 피드 가져오기 실패: {e}")
        return None
    except ET.ParseError as e:
        print(f"  ❌ XML 파싱 오류: {e}")
        print(f"     RSS 응답 미리보기: {response.text[:500]}")
        return None
    except Exception as e:
        print(f"  ❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

def load_history():
    """기존 히스토리 로드"""
    history_file = "steamdb_history.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(updates):
    """히스토리 저장"""
    history = load_history()
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "updates": updates if updates else [],
        "found_updates": len(updates) if updates else 0
    }
    
    history.append(entry)
    
    if len(history) > 100:
        history = history[-100:]
    
    with open("steamdb_history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    print("✅ steamdb_history.json 저장 완료")

def send_discord(updates):
    """Discord로 결과 전송"""
    if not DISCORD_WEBHOOK:
        print("⚠️  DISCORD_WEBHOOK 환경변수 없음")
        return
    
    if updates:
        desc = f"**오늘 발견된 업데이트: {len(updates)}건**\n\n"
        
        for idx, update in enumerate(updates[:10], 1):
            timestamp = update.get("timestamp", "")
            title = update.get("title", "")
            info = update.get("info", "")
            link = update.get("link", "")
            
            # 제목이 길면 자르기
            display_title = title[:80] + "..." if len(title) > 80 else title
            
            if link:
                desc += f"{idx}. `{timestamp}`\n   [{display_title}]({link})\n"
            else:
                desc += f"{idx}. `{timestamp}` {display_title}\n"
        
        if len(updates) > 10:
            desc += f"\n... 외 {len(updates) - 10}건 더"
        
        color = 0x00FF00  # 초록색
    else:
        desc = "오늘은 업데이트가 없습니다."
        color = 0x808080  # 회색
    
    embed = {
        "title": "🔔 Crimson Desert - SteamDB 업데이트",
        "description": desc,
        "color": color,
        "url": STEAMDB_HISTORY_URL,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "SteamDB RSS Tracker"}
    }
    
    payload = {"embeds": [embed]}
    
    try:
        response = requests.post(DISCORD_WEBHOOK, json=payload)
        if response.status_code in [204, 200]:
            print("✅ Discord 전송 성공!")
        else:
            print(f"⚠️  Discord 전송 실패: {response.status_code}")
            print(f"   응답: {response.text}")
    except Exception as e:
        print(f"❌ Discord 오류: {e}")

# =============================================================================
# 메인
# =============================================================================

def main():
    print("=" * 60)
    print("🔍 Crimson Desert SteamDB 업데이트 체크")
    print("   (RSS 피드 모드 - GitHub Actions 최적화)")
    print("=" * 60)
    
    updates = check_steamdb_rss()
    
    print("\n" + "=" * 60)
    print("📊 결과 요약")
    print("=" * 60)
    
    if updates:
        print(f"오늘의 업데이트: {len(updates)}건\n")
        for idx, update in enumerate(updates, 1):
            print(f"{idx}. [{update['timestamp']}] {update['title'][:80]}")
    else:
        print("오늘 업데이트 없음")
    
    save_history(updates)
    send_discord(updates)
    
    print("\n" + "=" * 60)
    print("✅ 완료! SteamDB URL:")
    print(f"   {STEAMDB_HISTORY_URL}")
    print("=" * 60)

if __name__ == "__main__":
    main()
