from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import requests
import os
# ================= 설정 =================

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

GAME_KEYWORD = "Crimson Desert"
MAX_PAGE = 2

URLS = {
    "🇺🇸 미국": "https://store.playstation.com/en-us/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "🇬🇧 영국": "https://store.playstation.com/en-gb/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "🇰🇷 한국": "https://store.playstation.com/ko-kr/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "FR 프랑스": "https://store.playstation.com/fr-fr/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "DE 독일": "https://store.playstation.com/de-de/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "JP 일본": "https://store.playstation.com/ja-jp/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "ES 스페인": "https://store.playstation.com/es-es/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "CA 캐나다": "https://store.playstation.com/en-ca/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "AU 호주": "https://store.playstation.com/en-au/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "IT 이탈리아": "https://store.playstation.com/it-it/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "BR 브라질": "https://store.playstation.com/pt-br/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "SA 사우디": "https://store.playstation.com/en-sa/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "AE 아랍": "https://store.playstation.com/en-ae/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "MX 멕시코": "https://store.playstation.com/es-mx/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "CN 중국": "https://store.playstation.com/zh-cn/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1",
    "NL 네덜란드": "https://store.playstation.com/nl-nl/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1"
}
# =======================================

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

def find_position(driver, base_url):
    total_count = 0

    for page in range(1, MAX_PAGE + 1):
        driver.get(f"{base_url}{page}")
        time.sleep(4)

        cards = driver.find_elements(By.CSS_SELECTOR, "a[data-telemetry-meta]")

        for card in cards:
            total_count += 1
            title = card.text.strip()

            if GAME_KEYWORD.lower() in title.lower():
                return total_count, page

    return None, None

def send_discord_message(results):
    content = "🎮 **Crimson Desert Pre-order 노출 순번 체크 결과**\n\n"

    for country, result in results.items():
        if result["position"]:
            content += f"{country} ▶ **{result['position']}번째** (페이지 {result['page']})\n"
        else:
            content += f"{country} ▶ ❌ 2페이지 내 미노출\n"

    payload = {
        "content": content
    }

    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def main():
    driver = setup_driver()
    results = {}

    for country, url in URLS.items():
        position, page = find_position(driver, url)
        results[country] = {
            "position": position,
            "page": page
        }

    driver.quit()
    send_discord_message(results)

if __name__ == "__main__":
    main()
