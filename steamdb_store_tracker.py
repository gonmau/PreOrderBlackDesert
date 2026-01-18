#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import matplotlib.pyplot as plt

STEAMDB_URL = "https://steamdb.info/app/3321460/charts/"
DATA_FILE = "steamdb_store_history.json"
GRAPH_FILE = "steamdb_store_trend.png"
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://steamdb.info/"
}


def fetch_store_numbers():
    r = requests.get(STEAMDB_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    store_data = {
        "top_sellers": None,
        "top_wishlists": None,
        "wishlist_activity": None,
        "followers": None,
    }

    for item in soup.select("div.app-chart-numbers div"):
        text = item.get_text(strip=True)

        if "in top sellers" in text:
            store_data["top_sellers"] = int(text.split("#")[1].split()[0])
        elif "in top wishlists" in text:
            store_data["top_wishlists"] = int(text.split("#")[1].split()[0])
        elif "in wishlist activity" in text:
            store_data["wishlist_activity"] = int(text.split("#")[1].split()[0])
        elif "followers" in text:
            store_data["followers"] = int(text.replace(",", "").split()[0])

    return store_data


def load_history():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_history(history):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def draw_graph(history):
    dates = [h["date"] for h in history]
    sellers = [h["top_sellers"] for h in history]
    wishlists = [h["top_wishlists"] for h in history]
    activity = [h["wishlist_activity"] for h in history]
    followers = [h["followers"] for h in history]

    plt.figure(figsize=(10, 6))
    plt.plot(dates, sellers, label="Top Sellers Rank")
    plt.plot(dates, wishlists, label="Top Wishlists Rank")
    plt.plot(dates, activity, label="Wishlist Activity Rank")
    plt.plot(dates, followers, label="Followers")

    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.savefig(GRAPH_FILE)
    plt.close()


def send_to_discord(today_data):
    message = (
        f"📊 **SteamDB Store Tracker (Daily)**\n"
        f"🗓 {today_data['date']}\n\n"
        f"🏆 Top Sellers: #{today_data['top_sellers']}\n"
        f"💖 Top Wishlists: #{today_data['top_wishlists']}\n"
        f"🔥 Wishlist Activity: #{today_data['wishlist_activity']}\n"
        f"👥 Followers: {today_data['followers']:,}"
    )

    with open(GRAPH_FILE, "rb") as f:
        requests.post(
            DISCORD_WEBHOOK,
            data={"content": message},
            files={"file": f},
            timeout=30
        )


def main():
    today = datetime.utcnow().strftime("%Y-%m-%d")

    store_numbers = fetch_store_numbers()
    store_numbers["date"] = today

    history = load_history()

    if history and history[-1]["date"] == today:
        print("Already updated today.")
        return

    history.append(store_numbers)
    save_history(history)
    draw_graph(history)
    send_to_discord(store_numbers)


if __name__ == "__main__":
    main()
