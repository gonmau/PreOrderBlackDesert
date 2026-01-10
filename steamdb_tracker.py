#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import os
import json
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# =============================================================================
# 설정
# =============================================================================

STEAMDB_HISTORY_URL = "https://steamdb.info/app/3321460/history/"
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# =============================================================================
# 함수들
# =============================================================================

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def check_steamdb_updates(driver):
    """SteamDB에서 오늘 날짜 업데이트 확인"""
    print("🔍 SteamDB 업데이트 히스토리 확인 중...")
    
    try:
        driver.get(STEAMDB_HISTORY_URL)
        time.sleep(5)
        
        # 페이지 스크롤 (테이블 로딩 대기)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # 오늘 날짜 (여러 형식 시도)
        now = datetime.now()
        today_formats = [
            now.strftime("%d %B %Y"),      # "10 January 2026"
            now.strftime("%d %b %Y"),       # "10 Jan 2026"
            now.strftime("%Y-%m-%d"),       # "2026-01-10"
            now.strftime("%d/%m/%Y"),       # "10/01/2026"
        ]
        
        print(f"  📅 오늘 날짜: {today_formats[0]}")
        
        # 테이블에서 업데이트 찾기
        try:
            # SteamDB 히스토리 테이블
            rows = driver.find_elements(By.CSS_SELECTOR, "table.table-products tbody tr")
            
            if not rows:
                # 다른 선택자 시도
                rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
            
            print(f"  📊 테이블 행 수: {len(rows)}")
            
            today_updates = []
            
            for row in rows[:20]:  # 최근 20개만 확인
                try:
                    row_text = row.text
                    
                    # 오늘 날짜가 포함된 행 찾기
                    is_today = any(date_format in row_text for date_format in today_formats)
                    
                    if is_today:
                        # 셀 데이터 추출
                        cells = row.find_elements(By.TAG_NAME, "td")
                        
                        if len(cells) >= 3:
                            # 일반적으로: [시간] [변경항목] [변경값] [...]
                            timestamp = cells[0].text.strip() if len(cells) > 0 else ""
                            change_key = cells[1].text.strip() if len(cells) > 1 else ""
                            change_old = cells[2].text.strip() if len(cells) > 2 else ""
                            change_new = cells[3].text.strip() if len(cells) > 3 else ""
                            
                            # 업데이트 정보 구성
                            if change_new and change_new != change_old:
                                update_info = f"{change_key}: {change_old} → {change_new}"
                            elif change_key and change_old:
                                update_info = f"{change_key}: {change_old}"
                            else:
                                update_info = row_text[:100]  # 전체 텍스트 일부
                            
                            today_updates.append({
                                "timestamp": timestamp,
                                "info": update_info
                            })
                            
                            print(f"  ✅ 업데이트 발견: {update_info[:80]}")
                except Exception as e:
                    continue
            
            if today_updates:
                print(f"  ✅ 총 {len(today_updates)}건의 오늘 업데이트 발견")
                return today_updates
            else:
                print("  ℹ️  오늘 업데이트 없음")
                return None
                
        except Exception as e:
            print(f"  ⚠️  테이블 파싱 오류: {e}")
            
            # 폴백: 페이지 전체 텍스트에서 오늘 날짜 찾기
            page_text = driver.find_element(By.TAG_NAME, "body").text
            
            for date_format in today_formats:
                if date_format in page_text:
                    print(f"  ⚠️  오늘 날짜 '{date_format}' 발견했지만 상세 파싱 실패")
                    return [{"timestamp": "오늘", "info": "업데이트 있음 (상세 확인 필요)"}]
            
            return None
            
    except Exception as e:
        print(f"  ❌ 크롤링 오류: {e}")
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
        "updates": updates if updates else []
    }
    
    history.append(entry)
    
    # 최근 100개만 유지
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
    
    # Discord 메시지 구성
    if updates:
        desc = f"**오늘 발견된 업데이트: {len(updates)}건**\n\n"
        
        for idx, update in enumerate(updates[:10], 1):  # 최대 10개만
            timestamp = update.get("timestamp", "")
            info = update.get("info", "")
            desc += f"{idx}. `{timestamp}` {info}\n"
        
        if len(updates) > 10:
            desc += f"\n... 외 {len(updates) - 10}건 더"
        
        color = 0x00FF00  # 초록색 (업데이트 있음)
    else:
        desc = "오늘은 업데이트가 없습니다."
        color = 0x808080  # 회색 (업데이트 없음)
    
    embed = {
        "title": "🔔 Crimson Desert - SteamDB 업데이트",
        "description": desc,
        "color": color,
        "url": STEAMDB_HISTORY_URL,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "SteamDB History Tracker"}
    }
    
    payload = {"embeds": [embed]}
    
    try:
        response = requests.post(DISCORD_WEBHOOK, json=payload)
        if response.status_code in [204, 200]:
            print("✅ Discord 전송 성공!")
        else:
            print(f"⚠️  Discord 전송 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ Discord 오류: {e}")

# =============================================================================
# 메인
# =============================================================================

def main():
    print("=" * 60)
    print("🔍 Crimson Desert SteamDB 업데이트 체크")
    print("=" * 60)
    
    start_time = time.time()
    driver = setup_driver()
    
    try:
        updates = check_steamdb_updates(driver)
    finally:
        driver.quit()
    
    elapsed = (time.time() - start_time) / 60
    print(f"\n⏱️  소요 시간: {elapsed:.1f}분")
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("📊 결과 요약")
    print("=" * 60)
    
    if updates:
        print(f"오늘의 업데이트: {len(updates)}건\n")
        for idx, update in enumerate(updates, 1):
            print(f"{idx}. [{update['timestamp']}] {update['info']}")
    else:
        print("오늘 업데이트 없음")
    
    # 히스토리 저장
    save_history(updates)
    
    # Discord 전송
    send_discord(updates)

if __name__ == "__main__":
    main()
