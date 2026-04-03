#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PS Store DOM 구조 디버깅 - 미국 1페이지만 확인
"""
import time
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
driver.get("https://store.playstation.com/en-us/pages/browse/1")
time.sleep(5)

print("=== [1] data-qa에 'productTile' 포함 요소 ===")
elems = driver.find_elements(By.CSS_SELECTOR, '[data-qa*="productTile"]')
print(f"총 {len(elems)}개 발견")
for e in elems[:5]:
    print(f"  tag={e.tag_name}, data-qa={e.get_attribute('data-qa')}, href={e.get_attribute('href')}, text={e.text[:60]!r}")

print("\n=== [2] /concept/ href 포함 <a> 태그 ===")
links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/concept/"]')
print(f"총 {len(links)}개 발견")
for a in links[:8]:
    print(f"  href={a.get_attribute('href')}, data-qa={a.get_attribute('data-qa')}, text={a.text[:60]!r}")

print("\n=== [3] 페이지 내 data-qa 속성 샘플 (앞 30개) ===")
all_qa = driver.find_elements(By.CSS_SELECTOR, '[data-qa]')
print(f"총 {len(all_qa)}개 data-qa 요소")
seen = set()
for e in all_qa:
    qa = e.get_attribute('data-qa') or ''
    # productTile 또는 game 관련만
    if any(kw in qa.lower() for kw in ['tile', 'game', 'product', 'item', 'card']):
        if qa not in seen:
            seen.add(qa)
            print(f"  {qa}")
        if len(seen) >= 20:
            break

print("\n=== [4] 할인 뱃지(-X%) 포함 요소 ===")
import re
badge_elems = driver.find_elements(By.CSS_SELECTOR, '[class*="discount"], [class*="badge"], [class*="sale"]')
print(f"class 기반 {len(badge_elems)}개")
for e in badge_elems[:5]:
    print(f"  class={e.get_attribute('class')}, text={e.text[:40]!r}")

# 텍스트로 찾기
all_spans = driver.find_elements(By.CSS_SELECTOR, 'span')
discount_spans = [s for s in all_spans if re.search(r'-\d+%', s.text or '')]
print(f"텍스트 -X% 포함 span {len(discount_spans)}개")
for s in discount_spans[:5]:
    print(f"  text={s.text!r}, class={s.get_attribute('class')}")

driver.quit()
print("\n디버깅 완료")
