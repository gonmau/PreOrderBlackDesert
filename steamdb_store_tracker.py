#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
from datetime import datetime

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
STEAMDB_URL = "https://steamdb.info/app/3321460/charts/"

def main():
    today = datetime.now().strftime("%Y-%m-%d")

    message = (
        f"📊 **SteamDB Store Tracker**\n"
        f"🗓 {today}\n\n"
        f"🔗 SteamDB Charts 바로가기\n"
        f"{STEAMDB_URL}\n\n"
        f"✅ Top Sellers / Wishlists / Activity / Followers 확인"
    )

    requests.post(
        DISCORD_WEBHOOK,
        json={"content": message},
        timeout=20
    )

if __name__ == "__main__":
    main()
