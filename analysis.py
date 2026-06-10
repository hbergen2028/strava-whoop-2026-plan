"""Pure analysis functions over parsed Strava activities and WHOOP records."""

from datetime import date, timedelta
from collections import defaultdict

from common import parse_dt, week_start, M_TO_MILES, MS_TO_MPH

SPORT_MAP = {
    "Run": "run",
    "Swim": "swim",
    "Ride": "bike", "VirtualRide": "bike", "EBikeRide": "bike",
}

FIVE_K_MILES = 3.10686  # 5000 m in miles


def parse_activities(raw):
    """Normalize raw Strava activities into typed dicts. Unknown types dropped."""
    out = []
    for a in raw:
        sport = SPORT_MAP.get(a.get("type"))
        if not sport:
            continue
        dist_m = a.get("distance", 0) or 0
        moving_s = a.get("moving_time", 0) or 0
        dt = parse_dt(a.get("start_date_local") or a.get("start_date", ""))
        miles = dist_m * M_TO_MILES
        out.append({
            "sport": sport,
            "date": dt.date(),
            "hour": dt.hour,
            "weekday": dt.weekday(),
            "miles": miles,
            "meters": dist_m,
            "moving_hrs": moving_s / 3600,
            "moving_s": moving_s,
            "avg_speed_mph": (a.get("average_speed", 0) or 0) * MS_TO_MPH,
            "pace_sec_per_mi": (moving_s / miles) if miles > 0 else 0,
            "name": a.get("name", ""),
        })
    return out


def analyze_run(acts, today=None):
    """Best ~5k-equivalent pace and derived workout paces from current fitness."""
    today = today or date.today()
    runs = [a for a in acts if a["sport"] == "run"]
    fives = [a for a in runs if 2.8 <= a["miles"] <= 3.6 and a["pace_sec_per_mi"] > 0]
    cutoff = today - timedelta(days=90)
    recent_runs = [a for a in runs if a["date"] >= cutoff]

    if fives:
        best = min(fives, key=lambda a: a["pace_sec_per_mi"])
        best_pace = best["pace_sec_per_mi"]
        best_5k_sec = best_pace * FIVE_K_MILES
    else:
        best_pace = 0
        best_5k_sec = 0

    # Derived paces relative to current 5k pace per mile.
    paces = {
        "vo2_sec_per_mi": best_pace - 20 if best_pace else 0,
        "threshold_sec_per_mi": best_pace + 20 if best_pace else 0,
        "easy_sec_per_mi": best_pace + 105 if best_pace else 0,
    }
    return {
        "best_5k_sec": best_5k_sec,
        "best_5k_pace_sec_per_mi": best_pace,
        "paces": paces,
        "runs_per_week_90d": len(recent_runs) / 13 if recent_runs else 0,
        "has_data": bool(fives),
    }
