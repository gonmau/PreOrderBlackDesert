#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

STEAMDB_RSS_URL = "https://steamdb.info/app/3321460/history/?rss=1"
STEAMDB_HISTORY_URL = "https://steamdb.info/app/3321460/history/"
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

def parse_rfc822_date(date_str):
    """RFC 822 날짜 파싱"""
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str)
    except:
        try:
            date_str = date_str.strip()
            if ',' in date_str:
                date_str = date_str.split(',', 1)[1].strip()
            parts = date_str.rsplit(' ', 1)
            date_part = parts[0]
            formats = ["%d %b %Y %H:%M:%S", "%d %B %Y %H:%M:%S"]
            for fmt in formats:
                try:
                    return datetime.strptime(date_part, fmt)
                except:
                    continue
            return None
        except:
            return None

def check_steamdb_rss():
    """SteamDB RSS 확인"""
    print("🔍 SteamDB RSS 피드 확인 중...")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        print(f"  📥 RSS 가져오는 중...")
        response = requests.get(STEAMDB_RSS_URL, headers=headers, timeout=30)
        response.raise_for_status()
        print(f"  ✅ RSS 피드 성공 ({len(response.content)} bytes)")
        
        root = ET.fromstring(response.content)
        items = root.findall('.//item')
        print(f"  📊 {len(items)}개 항목 발견")
        
        if len(items) == 0:
            print("  ⚠️  RSS 항목 없음")
            return None
        
        now_utc = datetime.utcnow()
        today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        print(f"  📅 오늘 날짜 (UTC): {today_start.strftime('%Y-%m-%d')}")
        
        today_updates = []
        
        for idx, item in enumerate(items):
            try:
                title = item.find('title')
                pub_date = item.find('pubDate')
                description = item.find('description')
                link = item.find('link')
                
                if title is None or pub_date is None:
                    continue
                
                title_text = title.text
                pub_date_text = pub_date.text
                description_text = description.text if description is not None else ""
                link_text = link.text if link is not None else None
                
                if idx < 3:
                    print(f"\n  🔍 항목 {idx}: {title_text[:60]}")
                    print(f"     날짜: {pub_date_text}")
                
                item_date = parse_rfc822_date(pub_date_text)
                
                if item_date is None:
                    print(f"  ⚠️  날짜 파싱 실패: {pub_date_text}")
                    continue
                
                if item_date.tzinfo is not None:
                    item_date = item_date.replace(tzinfo=None)
                
                if item_date >= today_start:
                    update_info = {
                        "timestamp": item_date.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "title": title_text,
                        "info": description_text[:200] if description_text else title_text,
                        "link": link_text
                    }
                    today_updates.append(update_info)
                    print(f"  ✅ 오늘 업데이트: [{update_info['timestamp']}] {title_text[:50]}")
                else:
                    if idx < 3:
                        print(f"     → 과거: {item_date.strftime('%Y-%m-%d %H:%M:%S')}")
                
            except Exception as e:
                print(f"  ⚠️  항목 {idx} 오류: {e}")
                continue
        
        if today_updates:
            print(f"\n  ✅ 총 {len(today_updates)}건 발견")
            return today_updates
        else:
            print("  ℹ️  오늘 업데이트 없음")
            return None
            
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

def load_history():
    history_file = "steamdb_history.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(updates):
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
    print("✅ steamdb_history.json 저장")

def send_discord(updates):
    if not DISCORD_WEBHOOK:
        print("⚠️  DISCORD_WEBHOOK 없음")
        return
    
    if updates:
        desc = f"**오늘 발견된 업데이트: {len(updates)}건**\n\n"
        for idx, update in enumerate(updates[:10], 1):
            timestamp = update.get("timestamp", "")
            title = update.get("title", "")
            link = update.get("link", "")
            display_title = title[:80] + "..." if len(title) > 80 else title
            if link:
                desc += f"{idx}. `{timestamp}`\n   [{display_title}]({link})\n"
            else:
                desc += f"{idx}. `{timestamp}` {display_title}\n"
        if len(updates) > 10:
            desc += f"\n... 외 {len(updates) - 10}건"
        color = 0x00FF00
    else:
        desc = "오늘은 업데이트가 없습니다."
        color = 0x808080
    
    embed = {
        "title": "🔔 Crimson Desert - SteamDB 업데이트",
        "description": desc,
        "color": color,
        "url": STEAMDB_HISTORY_URL,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "SteamDB RSS Tracker"}
    }
    
    try:
        response = requests.post(DISCORD_WEBHOOK, json={"embeds": [embed]})
        if response.status_code in [204, 200]:
            print("✅ Discord 전송 성공!")
        else:
            print(f"⚠️  Discord 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ Discord 오류: {e}")

def main():
    print("=" * 60)
    print("🔍 Crimson Desert SteamDB 업데이트 체크")
    print("=" * 60)
    
    updates = check_steamdb_rss()
    
    print("\n" + "=" * 60)
    print("📊 결과")
    print("=" * 60)
    
    if updates:
        print(f"오늘의 업데이트: {len(updates)}건\n")
        for idx, update in enumerate(updates, 1):
            print(f"{idx}. [{update['timestamp']}] {update['title'][:80]}")
    else:
        print("오늘 업데이트 없음")
    
    save_history(updates)
    send_discord(updates)
    
    print("\n✅ 완료!")

if __name__ == "__main__":
    main()
