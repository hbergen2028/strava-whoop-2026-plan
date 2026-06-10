"""Fetch WHOOP recovery, sleep, and cycle (strain) data via the v2 API -> whoop.json.

Auto-refreshes the WHOOP token if expired. Usage: py -3.12 whoop_fetch.py
"""

import os
import json
import time

import requests
from dotenv import load_dotenv, set_key

ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whoop.json")
load_dotenv(ENV_FILE)

CLIENT_ID = os.getenv("WHOOP_CLIENT_ID")
CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("WHOOP_ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("WHOOP_REFRESH_TOKEN")
EXPIRES_AT = int(os.getenv("WHOOP_TOKEN_EXPIRES_AT", "0"))

BASE = "https://api.prod.whoop.com/developer"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"


def refresh_if_needed():
    global ACCESS_TOKEN
    if time.time() < EXPIRES_AT - 60:
        return
    print("WHOOP token expired — refreshing...")
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    resp.raise_for_status()
    data = resp.json()
    ACCESS_TOKEN = data["access_token"]
    set_key(ENV_FILE, "WHOOP_ACCESS_TOKEN", data["access_token"])
    set_key(ENV_FILE, "WHOOP_REFRESH_TOKEN", data.get("refresh_token", REFRESH_TOKEN))
    set_key(ENV_FILE, "WHOOP_TOKEN_EXPIRES_AT", str(int(time.time()) + int(data.get("expires_in", 3600))))
    print("WHOOP token refreshed.")


def _get(path, limit=30):
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    r = requests.get(f"{BASE}{path}", headers=headers, params={"limit": limit})
    r.raise_for_status()
    return r.json().get("records", [])


def main():
    if not ACCESS_TOKEN:
        print("ERROR: no WHOOP token. Run whoop_auth.py first.")
        return
    refresh_if_needed()

    recovery = _get("/v2/recovery", limit=25)
    sleep = _get("/v2/activity/sleep", limit=25)
    cycles = _get("/v2/cycle", limit=25)

    # Normalize recovery into flat day records the analysis layer expects.
    sleep_by_day = {}
    for s in sleep:
        day = (s.get("start") or "")[:10]
        score = (s.get("score") or {}).get("sleep_performance_percentage")
        if day:
            sleep_by_day[day] = score

    norm = []
    for rec in recovery:
        sc = rec.get("score") or {}
        day = (rec.get("created_at") or "")[:10]
        norm.append({
            "date": day,
            "recovery": sc.get("recovery_score"),
            "rhr": sc.get("resting_heart_rate"),
            "hrv": sc.get("hrv_rmssd_milli"),
            "sleep_perf": sleep_by_day.get(day),
        })

    out = {"recovery": norm, "cycles": cycles, "fetched_at": int(time.time())}
    with open(OUTPUT_FILE, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Saved {len(norm)} recovery records to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
