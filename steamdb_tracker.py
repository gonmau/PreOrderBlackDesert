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
        time.sleep(5)
        
        # 페이지 스크롤 (테이블 로딩 대기)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        # 오늘 날짜 (여러 형식 시도)
        now = datetime.now()
        today_formats = [
            now.strftime("%d %B %Y"),      # "15 January 2026"
            now.strftime("%d %b %Y"),       # "15 Jan 2026"
            now.strftime("%-d %B %Y"),      # "15 January 2026" (선행 0 제거)
            now.strftime("%-d %b %Y"),      # "15 Jan 2026" (선행 0 제거)
            now.strftime("%Y-%m-%d"),       # "2026-01-15"
            now.strftime("%d/%m/%Y"),       # "15/01/2026"
        ]
        
        # 상대 시간도 체크 (SteamDB는 "2 hours ago" 같은 형식 사용)
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
            # 여러 선택자 시도
            selectors = [
                "table.table-products tbody tr",
                "table.history-table tbody tr",
                "#table-history tbody tr",
                "table tbody tr",
                ".history-row",
                "tr[data-time]",  # 시간 속성이 있는 행
            ]
            
            rows = []
            for selector in selectors:
                try:
                    rows = driver.find_elements(By.CSS_SELECTOR, selector)
                    if rows and len(rows) > 0:
                        print(f"  ✓ '{selector}' 선택자로 {len(rows)}개 행 발견")
                        break
                except:
                    continue
            
            if not rows:
                print("  ❌ 테이블 행을 찾을 수 없음")
                # 페이지 HTML 샘플 저장 (디버깅용)
                if DEBUG_MODE:
                    with open("steamdb_debug.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source[:5000])
                    print("  📄 디버그 HTML 저장: steamdb_debug.html")
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
                    is_today = any(date_format in row_text for date_format in today_formats)
                    is_recent = any(rel_time in row_text.lower() for rel_time in relative_times)
                    
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
