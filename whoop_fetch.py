"""Fetch WHOOP recovery, sleep, and cycle (strain) data via the v2 API -> whoop.json.

Auto-refreshes the WHOOP token if expired. Usage: py -3.12 whoop_fetch.py
"""

import os
import json
import time
from datetime import datetime, timezone

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

# Monday of the season's opening week (the plan runs Jun 9 - Dec 31 2026).
SEASON_START = "2026-06-08T00:00:00.000Z"


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


def _get_paged(path, start, end, limit=25):
    """Every record in [start, end], following nextToken pagination.

    The plain limit=N call only reaches back ~3 weeks of workouts, which is far
    short of the season, so swims need an explicit date range plus paging.
    """
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    out, token = [], None
    while True:
        params = {"limit": limit, "start": start, "end": end}
        if token:
            params["nextToken"] = token
        r = requests.get(f"{BASE}{path}", headers=headers, params=params)
        r.raise_for_status()
        body = r.json()
        out += body.get("records", [])
        token = body.get("next_token")
        if not token:
            return out


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

    # Workouts are where swims live — most never reach Strava, so this is the
    # source of truth for the swim count. Full season so past weeks can regrade.
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    raw_workouts = _get_paged("/v2/activity/workout", SEASON_START, now_iso)
    workouts = [{
        "date": (w.get("start") or "")[:10],
        "sport": w.get("sport_name"),
        "start": w.get("start"),
        "strain": (w.get("score") or {}).get("strain"),
    } for w in raw_workouts if w.get("start")]

    out = {"recovery": norm, "cycles": cycles, "workouts": workouts,
           "fetched_at": int(time.time())}
    with open(OUTPUT_FILE, "w") as f:
        json.dump(out, f, indent=2)
    swims = sum(1 for w in workouts if w["sport"] == "swimming")
    print(f"Saved {len(norm)} recovery records, {len(workouts)} workouts "
          f"({swims} swims) to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
