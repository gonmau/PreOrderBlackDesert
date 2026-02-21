
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime, timezone, timedelta

# ==============================
# KST 고정 설정
# ==============================
KST = timezone(timedelta(hours=9))

HISTORY_FILE = "trends_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def record_trend(data):
    history = load_history()

    timestamp = datetime.now(KST).isoformat()

    history.append({
        "timestamp": timestamp,
        "data": data
    })

    save_history(history)

if __name__ == "__main__":
    # 예시 데이터 기록 (실제 크롤링 결과로 교체)
    sample_data = {"example_metric": 100}
    record_trend(sample_data)
    print("KST 기준으로 기록 완료")
