"""
Fetch ALL cycling activities from Strava and save to activities.json.
Auto-refreshes token if expired.

Usage: python fetch.py
"""

import os
import json
import time

import requests
from dotenv import load_dotenv, set_key

ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "activities.json")

load_dotenv(ENV_FILE)

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("STRAVA_ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")
TOKEN_EXPIRES_AT = int(os.getenv("STRAVA_TOKEN_EXPIRES_AT", "0"))

CYCLING_TYPES = {"Ride", "VirtualRide", "EBikeRide"}


def refresh_if_needed():
    global ACCESS_TOKEN
    if time.time() < TOKEN_EXPIRES_AT - 60:
        return
    print("Access token expired — refreshing...")
    resp = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    })
    resp.raise_for_status()
    data = resp.json()
    ACCESS_TOKEN = data["access_token"]
    set_key(ENV_FILE, "STRAVA_ACCESS_TOKEN", data["access_token"])
    set_key(ENV_FILE, "STRAVA_REFRESH_TOKEN", data["refresh_token"])
    set_key(ENV_FILE, "STRAVA_TOKEN_EXPIRES_AT", str(data["expires_at"]))
    print("Token refreshed.")


def fetch_all_activities():
    refresh_if_needed()
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    all_activities = []
    page = 1

    while True:
        print(f"  Fetching page {page}...", end="\r")
        resp = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers=headers,
            params={"per_page": 200, "page": page},
        )
        resp.raise_for_status()
        batch = resp.json()

        if not batch:
            break

        all_activities.extend(batch)
        page += 1
        time.sleep(0.3)  # be polite to the API

    return all_activities


def main():
    if not ACCESS_TOKEN:
        print("ERROR: No access token found. Run auth.py first.")
        return

    print("Fetching all Strava activities...")
    all_activities = fetch_all_activities()

    cycling = [a for a in all_activities if a.get("type") in CYCLING_TYPES]

    print(f"\nTotal activities fetched : {len(all_activities)}")
    print(f"Cycling activities found : {len(cycling)}")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(cycling, f, indent=2)

    print(f"Saved to {OUTPUT_FILE}")
    print("Run plan.py next.")


if __name__ == "__main__":
    main()
