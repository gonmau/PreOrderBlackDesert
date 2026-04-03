#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PS Store 상세 페이지 할인 정보 DOM 구조 디버깅
"""
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(20)
    return driver

driver = setup_driver()

# 미국 NBA 2K26 (할인 확실히 있는 게임)
TEST_URL = "https://store.playstation.com/en-us/concept/10014149"
print(f"URL: {TEST_URL}")
driver.get(TEST_URL)
time.sleep(5)

print("\n=== [1] data-qa에 purchase/price/offer/discount 포함 요소 ===")
for sel in ['[data-qa*="mfe-purchase"]', '[data-qa*="price"]', '[data-qa*="offer"]', '[data-qa*="discount"]']:
    elems = driver.find_elements(By.CSS_SELECTOR, sel)
    for e in elems[:4]:
        text = e.text.strip()
        if text:
            print(f"  sel={sel}")
            print(f"    data-qa={e.get_attribute('data-qa')!r}")
            print(f"    text={text[:150]!r}")

print("\n=== [2] 'Offer ends' / 'Save' 텍스트 포함 요소 ===")
all_elems = driver.find_elements(By.CSS_SELECTOR, 'span, p, div')
found = 0
for e in all_elems:
    text = e.text.strip()
    if text and re.search(r'offer ends|save \d+%|ends \d', text, re.IGNORECASE) and len(text) < 200:
        print(f"  tag={e.tag_name}")
        print(f"    data-qa={e.get_attribute('data-qa')!r}")
        print(f"    class={e.get_attribute('class')!r}")
        print(f"    text={text!r}")
        found += 1
        if found >= 10:
            break

if found == 0:
    print("  ⚠️ 'Offer ends' 텍스트 요소 없음 - 페이지 로드 실패 가능성")
    print(f"  현재 URL: {driver.current_url}")
    print(f"  타이틀: {driver.title}")

print("\n=== [3] 전체 텍스트에 'offer' 포함 여부 확인 ===")
page_text = driver.find_element(By.TAG_NAME, 'body').text
if 'Offer' in page_text or 'offer' in page_text:
    # offer 주변 텍스트 추출
    idx = page_text.lower().find('offer')
    print(f"  'offer' 발견: ...{page_text[max(0,idx-30):idx+80]!r}...")
else:
    print("  'offer' 텍스트 없음")

if 'Save' in page_text or 'save' in page_text:
    idx = page_text.lower().find('save')
    print(f"  'save' 발견: ...{page_text[max(0,idx-30):idx+80]!r}...")

driver.quit()
print("\n디버깅 완료")
