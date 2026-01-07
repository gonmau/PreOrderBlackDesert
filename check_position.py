from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

GAME_KEYWORD = "Crimson Desert"

URLS = {
    "US": "https://store.playstation.com/en-us/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/",
    "UK": "https://store.playstation.com/en-gb/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/",
    "KR": "https://store.playstation.com/ko-kr/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/",
}

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

def find_game_position(driver, base_url, max_page=2):
    count = 0

    for page in range(1, max_page + 1):
        url = f"{base_url}{page}"
        driver.get(url)
        time.sleep(4)

        cards = driver.find_elements(By.CSS_SELECTOR, "a[data-telemetry-meta]")

        for idx, card in enumerate(cards, start=1):
            title = card.text.strip()
            count += 1

            if GAME_KEYWORD.lower() in title.lower():
                return count, page

    return None, None

def main():
    driver = setup_driver()

    for country, url in URLS.items():
        position, page = find_game_position(driver, url)

        if position:
            print(f"[{country}] Crimson Desert ▶ {position}번째 (페이지 {page})")
        else:
            print(f"[{country}] Crimson Desert ▶ 2페이지 내 미노출")

    driver.quit()

if __name__ == "__main__":
    main()
