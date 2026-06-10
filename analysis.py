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


def analyze_swim(acts, today=None, weeks=8):
    """Sessions/week and weeks hitting the 2x/week target over a trailing window."""
    today = today or date.today()
    swims = [a for a in acts if a["sport"] == "swim"]
    start = week_start(today) - timedelta(weeks=weeks - 1)
    per_week = defaultdict(int)
    for a in swims:
        ws = week_start(a["date"])
        if ws >= start:
            per_week[ws] += 1
    weeks_hit = sum(1 for n in per_week.values() if n >= 2)
    recent = [a for a in swims if a["date"] >= start]
    return {
        "sessions_per_week": len(recent) / weeks,
        "weeks_hit_target": weeks_hit,
        "total_weeks": weeks,
        "has_data": bool(swims),
    }


def analyze_bike(acts, today=None):
    """Speed, volume, longest ride, and Tue/Thu pre-07:00 (Davis Island) detection."""
    today = today or date.today()
    rides = [a for a in acts if a["sport"] == "bike"]
    cutoff_90 = today - timedelta(days=90)
    cutoff_28 = today - timedelta(days=28)
    recent = [a for a in rides if a["date"] >= cutoff_90]

    meaningful = [a for a in recent if a["miles"] > 20]
    avg_speed = (sum(a["avg_speed_mph"] for a in meaningful) / len(meaningful)
                 if meaningful else 0)

    di = [a for a in recent if a["weekday"] in (1, 3) and a["hour"] < 7]
    di_speed = (sum(a["avg_speed_mph"] for a in di) / len(di)) if di else 0

    last_4wk = [a for a in rides if a["date"] >= cutoff_28]
    return {
        "avg_speed_20plus": avg_speed,
        "longest_miles": max((a["miles"] for a in rides), default=0),
        "weekly_avg_4wk": sum(a["miles"] for a in last_4wk) / 4,
        "di_count": len(di),
        "di_avg_speed": di_speed,
        "has_data": bool(rides),
    }
