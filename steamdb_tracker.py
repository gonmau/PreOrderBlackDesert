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
DEBUG_MODE = True  # 디버깅 모드

# =============================================================================
# 함수들
# =============================================================================

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def check_steamdb_updates(driver):
    """SteamDB에서 오늘 날짜 업데이트 확인"""
    print("🔍 SteamDB 업데이트 히스토리 확인 중...")
    
    try:
        driver.get(STEAMDB_HISTORY_URL)
        print("  ⏳ 페이지 로딩 대기 중... (10초)")
        time.sleep(10)  # 더 긴 대기 시간
        
        # 페이지 스크롤 (테이블 로딩 대기)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        # JavaScript 실행 완료 대기
        driver.execute_script("return document.readyState") 
        time.sleep(2)
        
        # 오늘 날짜 (여러 형식 시도) - 영어 로케일 강제
        import locale
        try:
            locale.setlocale(locale.LC_TIME, 'en_US.UTF-8')
        except:
            try:
                locale.setlocale(locale.LC_TIME, 'C')
            except:
                pass
        
        now = datetime.now()
        
        # SteamDB는 "15 January 2026" 형식 사용 (일에 선행 0 없음)
        today_day = now.day  # 15
        today_month = now.strftime("%B")  # "January"
        today_year = now.year  # 2026
        
        today_formats = [
            f"{today_day} {today_month} {today_year}",  # "15 January 2026"
            f"{today_day:02d} {today_month} {today_year}",  # "15 January 2026"
            now.strftime("%d %B %Y"),      # 폴백
            now.strftime("%d %b %Y"),       # "15 Jan 2026"
        ]
        
        # 상대 시간도 체크 (SteamDB는 "5 hours ago" 같은 형식 사용)
        # 24시간 이내면 오늘 업데이트로 간주
        relative_times = [
            "hour ago", "hours ago", 
            "minute ago", "minutes ago", 
            "just now", "a moment ago",
            "second ago", "seconds ago"
        ]
        
        print(f"  📅 오늘 날짜: {today_formats[0]}")
        
        # 디버깅: 페이지 스크린샷 저장
        if DEBUG_MODE:
            try:
                driver.save_screenshot("steamdb_page.png")
                print("  📸 스크린샷 저장: steamdb_page.png")
            except:
                pass
        
        # 테이블에서 업데이트 찾기
        try:
            # 먼저 페이지 전체 텍스트로 오늘 날짜 확인
            page_text = driver.find_element(By.TAG_NAME, "body").text
            print(f"  📄 페이지 텍스트 길이: {len(page_text)} 문자")
            
            # 오늘 날짜 또는 최근 시간이 있는지 확인
            has_today = any(date_format.lower() in page_text.lower() for date_format in today_formats)
            has_recent = any(rel_time in page_text.lower() for rel_time in relative_times)
            
            if has_today:
                print(f"  ✅ 페이지에 오늘 날짜 발견!")
            if has_recent:
                print(f"  ✅ 페이지에 최근 업데이트 시간 발견!")
            
            if not has_today and not has_recent:
                print("  ℹ️  페이지에 오늘 날짜나 최근 시간이 없음")
                return None
            
            # 여러 선택자 시도 - SteamDB는 특수한 구조 사용
            selectors = [
                "*",  # 모든 요소 (폴백)
                "div",  # 모든 div
                ".history-change",  # SteamDB의 실제 히스토리 항목 클래스
                "div[class*='change']",
                "div[class*='history']",
                "table.table-products tbody tr",
                "table tbody tr",
                "tr",
            ]
            
            rows = []
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and len(elements) > 0:
                        # 텍스트가 있는 요소만 필터링
                        rows = [el for el in elements if el.text.strip() and len(el.text.strip()) > 10]
                        if len(rows) > 0:
                            print(f"  ✓ '{selector}' 선택자로 {len(rows)}개 유효한 요소 발견")
                            break
                except:
                    continue
            
            if not rows:
                print("  ⚠️  구조화된 요소를 찾을 수 없음 - 페이지 전체 텍스트 사용")
                
                # 최후의 수단: 페이지 전체에서 날짜가 포함된 줄 찾기
                lines = page_text.split('\n')
                today_updates = []
                
                for line in lines:
                    line = line.strip()
                    if not line or len(line) < 10:
                        continue
                    
                    # 오늘 날짜 또는 최근 시간 포함 여부
                    has_date = any(date_format.lower() in line.lower() for date_format in today_formats)
                    has_time = any(rel_time in line.lower() for rel_time in relative_times)
                    
                    if has_date or has_time:
                        # 시간 정보 필터링 (24시간 이내만)
                        if "hour" in line.lower():
                            import re
                            match = re.search(r'(\d+)\s+hours?\s+ago', line.lower())
                            if match and int(match.group(1)) >= 24:
                                continue  # 24시간 이상은 제외
                        
                        today_updates.append({
                            "timestamp": "오늘",
                            "info": line[:200]
                        })
                        print(f"  ✅ 업데이트 발견: {line[:80]}")
                
                if today_updates:
                    print(f"  ✅ 총 {len(today_updates)}건의 오늘 업데이트 발견")
                    return today_updates
                else:
                    print("  ℹ️  업데이트를 파싱하지 못함")
                    return None
            
            today_updates = []
            
            print(f"  🔍 {len(rows)}개 행 검사 중...")
            
            for idx, row in enumerate(rows[:50]):  # 최근 50개 확인
                try:
                    row_text = row.text.strip()
                    
                    if not row_text or len(row_text) < 3:  # 빈 행 스킵
                        continue
                    
                    # 디버깅: 처음 5개 행 출력
                    if DEBUG_MODE and idx < 5:
                        print(f"  🔍 행 {idx}: {row_text[:120]}")
                    
                    # 오늘 날짜 또는 상대 시간이 포함된 행 찾기
                    # "5 hours ago · 15 January 2026" 형식 체크
                    is_today = False
                    is_recent = False
                    
                    # 1. 오늘 날짜가 정확히 포함되어 있는지 확인
                    for date_format in today_formats:
                        if date_format.lower() in row_text.lower():
                            is_today = True
                            if DEBUG_MODE:
                                print(f"    ✓ 날짜 매칭: '{date_format}'")
                            break
                    
                    # 2. 상대 시간 확인 (24시간 이내)
                    text_lower = row_text.lower()
                    for rel_time in relative_times:
                        if rel_time in text_lower:
                            # "X hours ago" 형식에서 숫자 추출
                            if "hour" in rel_time:
                                try:
                                    # "20 hours ago"에서 20 추출
                                    import re
                                    match = re.search(r'(\d+)\s+hours?\s+ago', text_lower)
                                    if match:
                                        hours = int(match.group(1))
                                        if hours < 24:  # 24시간 이내만
                                            is_recent = True
                                            if DEBUG_MODE:
                                                print(f"    ✓ 시간 매칭: {hours} hours ago")
                                            break
                                except:
                                    is_recent = True
                                    break
                            else:
                                is_recent = True
                                if DEBUG_MODE:
                                    print(f"    ✓ 시간 매칭: '{rel_time}'")
                                break
                    
                    if is_today or is_recent:
                        # 셀 데이터 추출
                        cells = row.find_elements(By.TAG_NAME, "td")
                        
                        if len(cells) >= 2:
                            # 모든 셀 텍스트 수집
                            cell_texts = [cell.text.strip() for cell in cells if cell.text.strip()]
                            
                            # 일반적으로: [시간] [변경항목] [이전값] [새값]
                            timestamp = cell_texts[0] if len(cell_texts) > 0 else "오늘"
                            
                            # 나머지 정보 결합
                            if len(cell_texts) > 1:
                                change_info = " | ".join(cell_texts[1:])
                            else:
                                change_info = row_text
                            
                            # 너무 긴 정보는 자르기
                            if len(change_info) > 200:
                                change_info = change_info[:200] + "..."
                            
                            update_entry = {
                                "timestamp": timestamp,
                                "info": change_info
                            }
                            
                            # 중복 체크
                            if update_entry not in today_updates:
                                today_updates.append(update_entry)
                                print(f"  ✅ 업데이트 발견: [{timestamp}] {change_info[:70]}")
                        else:
                            # 셀이 적으면 전체 텍스트 사용
                            update_entry = {
                                "timestamp": "오늘",
                                "info": row_text[:200]
                            }
                            if update_entry not in today_updates:
                                today_updates.append(update_entry)
                                print(f"  ✅ 업데이트 발견 (단순): {row_text[:70]}")
                            
                except Exception as e:
                    if DEBUG_MODE and idx < 5:  # 처음 몇 개만 에러 출력
                        print(f"  ⚠️  행 {idx} 처리 오류: {e}")
                    continue
            
            if today_updates:
                print(f"  ✅ 총 {len(today_updates)}건의 오늘 업데이트 발견")
                return today_updates
            else:
                print("  ℹ️  테이블에서 오늘 업데이트를 찾지 못함")
                
                # 폴백: 페이지 전체 텍스트 검사
                try:
                    page_text = driver.find_element(By.TAG_NAME, "body").text
                    print(f"  📄 페이지 전체 텍스트 길이: {len(page_text)} 문자")
                    
                    # 오늘 날짜 검색
                    for date_format in today_formats:
                        if date_format in page_text:
                            print(f"  ⚠️  페이지에 '{date_format}' 발견 - 파싱 로직 확인 필요")
                            return [{"timestamp": "오늘", "info": "업데이트 감지됨 (파싱 실패, 수동 확인 필요)"}]
                    
                    # 상대 시간 검색
                    for rel_time in relative_times:
                        if rel_time in page_text.lower():
                            print(f"  ⚠️  페이지에 '{rel_time}' 발견 - 파싱 로직 확인 필요")
                            return [{"timestamp": "최근", "info": "최근 업데이트 감지됨 (파싱 실패, 수동 확인 필요)"}]
                    
                    print("  ℹ️  페이지 전체에서도 오늘 날짜/최근 시간을 찾지 못함")
                except Exception as e:
                    print(f"  ⚠️  페이지 텍스트 검사 실패: {e}")
                
                return None
                
        except Exception as e:
            print(f"  ⚠️  테이블 파싱 오류: {e}")
            import traceback
            traceback.print_exc()
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
        "updates": updates if updates else [],
        "found_updates": len(updates) if updates else 0
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
    
    print("\n" + "=" * 60)
    print("완료! SteamDB URL을 직접 확인하려면:")
    print(f"{STEAMDB_HISTORY_URL}")
    print("=" * 60)

if __name__ == "__main__":
    main()
