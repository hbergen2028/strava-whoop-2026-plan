"""
Analyze all cycling activities and generate a 27-day training plan.
Goal: 100 miles in 4 hours on March 29, 2026 (25.0 mph average).

Usage: python plan.py
"""

import os
import json
from datetime import datetime, timedelta, date
from collections import defaultdict

ACTIVITIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "activities.json")
PLAN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "training_plan.txt")

M_TO_MILES = 1 / 1609.34
MS_TO_MPH = 2.23694
M_TO_FEET = 3.28084

TODAY = date(2026, 3, 2)
EVENT_DATE = date(2026, 3, 29)
TARGET_MILES = 100.0
TARGET_HOURS = 4.0
TARGET_SPEED = TARGET_MILES / TARGET_HOURS  # 25.0 mph


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_activity(a):
    raw_date = a.get("start_date_local") or a.get("start_date", "")
    try:
        activity_date = datetime.strptime(raw_date[:19], "%Y-%m-%dT%H:%M:%S").date()
    except ValueError:
        activity_date = TODAY

    dist_m = a.get("distance", 0) or 0
    moving_s = a.get("moving_time", 0) or 0
    miles = dist_m * M_TO_MILES
    hrs = moving_s / 3600

    return {
        "date": activity_date,
        "name": a.get("name", ""),
        "miles": miles,
        "moving_hrs": hrs,
        "avg_speed_mph": a.get("average_speed", 0) * MS_TO_MPH,
        "max_speed_mph": a.get("max_speed", 0) * MS_TO_MPH,
        "elevation_ft": (a.get("total_elevation_gain") or 0) * M_TO_FEET,
        "watts": a.get("average_watts"),
        "suffer_score": a.get("suffer_score"),
        "kudos": a.get("kudos_count", 0),
    }


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze(raw_activities):
    rides = sorted([parse_activity(a) for a in raw_activities], key=lambda x: x["date"])

    if not rides:
        return {}

    total_miles = sum(r["miles"] for r in rides)
    total_hrs = sum(r["moving_hrs"] for r in rides)

    # Weekly buckets (Monday-based)
    weekly = defaultdict(list)
    for r in rides:
        week_start = r["date"] - timedelta(days=r["date"].weekday())
        weekly[week_start].append(r)

    weekly_miles = {w: sum(r["miles"] for r in rs) for w, rs in weekly.items()}

    # Meaningful rides (>20 mi) — better speed sample
    meaningful = [r for r in rides if r["miles"] > 20]
    meaningful_speed = (
        sum(r["avg_speed_mph"] for r in meaningful) / len(meaningful)
        if meaningful else 0
    )

    # Recent windows
    cutoff_30 = TODAY - timedelta(days=30)
    cutoff_90 = TODAY - timedelta(days=90)
    last_30 = [r for r in rides if r["date"] >= cutoff_30]
    last_90 = [r for r in rides if r["date"] >= cutoff_90]

    miles_30 = sum(r["miles"] for r in last_30)
    hrs_30 = sum(r["moving_hrs"] for r in last_30)
    miles_90 = sum(r["miles"] for r in last_90)
    hrs_90 = sum(r["moving_hrs"] for r in last_90)
    speed_90 = miles_90 / hrs_90 if hrs_90 > 0 else 0

    # Longest rides ever
    top5 = sorted(rides, key=lambda x: x["miles"], reverse=True)[:5]

    # Last 8 weeks of volume
    recent_weeks = sorted(weekly_miles.items())[-8:]

    return {
        "total_rides": len(rides),
        "total_miles": total_miles,
        "total_hrs": total_hrs,
        "overall_avg_speed": total_miles / total_hrs if total_hrs > 0 else 0,
        "meaningful_avg_speed": meaningful_speed,
        "speed_90d": speed_90,
        "miles_30d": miles_30,
        "hrs_30d": hrs_30,
        "rides_30d": len(last_30),
        "miles_90d": miles_90,
        "weekly_miles_per_week_30d": miles_30 / 4 if miles_30 else 0,
        "top5": top5,
        "recent_weeks": recent_weeks,
    }


# ---------------------------------------------------------------------------
# Plan generation
# ---------------------------------------------------------------------------

def generate_plan(stats):
    """
    27-day periodized plan:
      Phase 1 (Mar 2-8)  : Base build
      Phase 2 (Mar 9-15) : Volume build
      Phase 3 (Mar 16-22): Sharpen / race simulation
      Phase 4 (Mar 23-28): Taper
      Day 27  (Mar 29)   : Event
    """
    # fmt: (day_offset, description, miles, intensity, notes)
    schedule = [
        # ── Phase 1: Base Build (Week 1) ────────────────────────────────────
        ( 0, "Assessment / easy spin",        25,  "Easy",    "Zone 2 throughout — gauge current feel and fitness"),
        ( 1, "Rest",                            0,  "Rest",    "Light stretching, mobility work"),
        ( 2, "Tempo intervals",                35,  "Moderate","3 × 10 min at 24-25 mph, 5 min easy between"),
        ( 3, "Rest",                            0,  "Rest",    "Full recovery"),
        ( 4, "Endurance ride",                 50,  "Easy-Mod","Steady Zone 2-3; practice nutrition every 45 min"),
        ( 5, "Speed / cadence work",           20,  "Hard",    "5 × 5 min max effort; high cadence drills"),
        ( 6, "Long ride",                      65,  "Easy-Mod","Aerobic base — hold 21-23 mph, no heroics"),

        # ── Phase 2: Volume Build (Week 2) ───────────────────────────────────
        ( 7, "Recovery spin",                  20,  "Easy",    "Flush legs from long ride; keep HR low"),
        ( 8, "Rest",                            0,  "Rest",    "Full recovery"),
        ( 9, "Sustained tempo",                40,  "Moderate","2 × 20 min at 24-26 mph; 10 min easy between"),
        (10, "Rest",                            0,  "Rest",    "Full recovery"),
        (11, "Endurance + race-pace blocks",   55,  "Moderate","2 × 15 min at 25 mph embedded in Zone 2 ride"),
        (12, "Leg-speed sharpener",            25,  "Hard",    "Sprint repeats + 6 × 1 min all-out efforts"),
        (13, "Long ride — biggest of prep",    75,  "Easy-Mod","Longest training ride; practice full-race nutrition plan"),

        # ── Phase 3: Sharpen (Week 3) ────────────────────────────────────────
        (14, "Recovery spin",                  20,  "Easy",    "Easy legs after big week"),
        (15, "Rest",                            0,  "Rest",    "Full rest"),
        (16, "Race simulation",                60,  "Hard",    "40+ miles at 25 mph target; test bike setup & nutrition"),
        (17, "Rest",                            0,  "Rest",    "Recovery after race sim"),
        (18, "Threshold work",                 35,  "Moderate","3 × 12 min at threshold; gauge fitness response"),
        (19, "Fast-twitch activation",         20,  "Hard",    "Short sprints; high cadence; stay sharp"),
        (20, "Confidence ride",                50,  "Easy-Mod","Controlled, smooth effort — build mental confidence"),

        # ── Phase 4: Taper (Week 4) ──────────────────────────────────────────
        (21, "Easy taper spin",                20,  "Easy",    "Begin taper — keep legs fresh, don't push"),
        (22, "Rest",                            0,  "Rest",    "Full recovery"),
        (23, "Short sharpener",                15,  "Mod-Hard","3 × 5 min at race effort to stay sharp; no fatigue"),
        (24, "Rest",                            0,  "Rest",    "Full rest"),
        (25, "Leg-opener spin",                10,  "Easy",    "20-30 min very easy; just move the legs"),
        (26, "Rest / prep day",                 0,  "Rest",    "Check bike, lay out kit, plan nutrition, sleep early"),

        # ── Event ─────────────────────────────────────────────────────────────
        (27, "EVENT: 100 miles in 4 hours",   100,  "Race",   "Target 25.0 mph avg — execute your plan, GO!"),
    ]

    plan = []
    for offset, desc, miles, intensity, notes in schedule:
        plan.append({
            "day": offset + 1,
            "date": TODAY + timedelta(days=offset),
            "description": desc,
            "miles": miles,
            "intensity": intensity,
            "notes": notes,
        })
    return plan


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_analysis(stats):
    sep = "=" * 62
    print(f"\n{sep}")
    print("  STRAVA CYCLING ANALYSIS")
    print(sep)
    print(f"  Total rides          : {stats['total_rides']}")
    print(f"  All-time miles       : {stats['total_miles']:>8,.0f} mi")
    print(f"  All-time hours       : {stats['total_hrs']:>8,.0f} hr")
    print(f"  Overall avg speed    : {stats['overall_avg_speed']:>8.1f} mph")
    print(f"  Avg speed (>20 mi)   : {stats['meaningful_avg_speed']:>8.1f} mph")
    print(f"  Avg speed (last 90d) : {stats['speed_90d']:>8.1f} mph")
    print()
    print(f"  Last 30 days         : {stats['rides_30d']} rides  /  {stats['miles_30d']:.0f} mi  /  {stats['hrs_30d']:.0f} hr")
    print(f"  Avg weekly miles     : {stats['weekly_miles_per_week_30d']:.0f} mi/wk (last 30d)")

    print(f"\n  Top 5 longest rides:")
    for r in stats["top5"]:
        print(f"    {r['date']}  {r['miles']:>5.1f} mi  {r['avg_speed_mph']:>5.1f} mph  {r['elevation_ft']:>5.0f} ft gain")

    print(f"\n  Recent weekly mileage (last 8 weeks):")
    max_w = max((m for _, m in stats["recent_weeks"]), default=1)
    for week, miles in stats["recent_weeks"]:
        bar = "█" * int(miles / max_w * 20)
        print(f"    {week}  {miles:>5.0f} mi  {bar}")

    current_speed = stats["meaningful_avg_speed"] or stats["speed_90d"] or 18.0
    gap = TARGET_SPEED - current_speed
    print(f"\n{sep}")
    print(f"  GOAL: {TARGET_MILES:.0f} miles in {TARGET_HOURS:.0f} hours  =  {TARGET_SPEED:.1f} mph average")
    print(f"  Your current pace (meaningful rides): {current_speed:.1f} mph")
    if gap > 0:
        print(f"  Speed gap to close: +{gap:.1f} mph")
        if gap > 5:
            print("  NOTE: 25 mph avg is elite/competitive — plan accordingly.")
            print("        Strong drafting, flat/tailwind course, and peak fitness required.")
        elif gap > 2:
            print("  NOTE: Aggressive but achievable — focused training + good conditions.")
        else:
            print("  NOTE: You're close — tune-up and race-day execution are key.")
    else:
        print(f"  You're already at or above goal pace — execute the plan and peak on race day!")
    print(sep)


def print_plan(plan, stats):
    sep = "=" * 62
    current_speed = stats.get("meaningful_avg_speed") or stats.get("speed_90d") or 18.0

    print(f"\n{sep}")
    print(f"  27-DAY PLAN: 100 Miles on March 29, 2026")
    print(f"  Current fitness: ~{current_speed:.1f} mph  |  Target: {TARGET_SPEED:.1f} mph")
    print(sep)

    phases = [
        ("PHASE 1 — Base Build",     range(1,  8)),
        ("PHASE 2 — Volume Build",   range(8,  15)),
        ("PHASE 3 — Sharpen",        range(15, 22)),
        ("PHASE 4 — Taper",          range(22, 28)),
        ("EVENT DAY",                range(28, 29)),
    ]

    def phase_for(day):
        for label, r in phases:
            if day in r:
                return label
        return ""

    current_phase = ""
    total_training = 0

    for d in plan:
        phase = phase_for(d["day"])
        if phase != current_phase:
            current_phase = phase
            print(f"\n  {phase}")
            print("  " + "-" * 50)

        dow = d["date"].strftime("%a")
        date_str = d["date"].strftime("%b %d")
        miles = d["miles"]
        intensity = d["intensity"]
        desc = d["description"]
        notes = d["notes"]

        if miles > 0 and intensity != "Race":
            total_training += miles
            print(f"  {dow} {date_str} | {miles:>3} mi | {intensity:<9} | {desc}")
            print(f"             |        |           | → {notes}")
        elif intensity == "Race":
            print(f"  {dow} {date_str} | {miles:>3} mi | {intensity:<9} | {desc}")
            print(f"             |        |           | → {notes}")
        else:
            print(f"  {dow} {date_str} |  ---   | {intensity:<9} | {desc}")

    print(f"\n{sep}")
    print(f"  Training miles (excl. event) : {total_training:.0f} mi")
    print(f"  Total including event        : {total_training + 100:.0f} mi")
    print(f"\n  RACE DAY CHECKLIST:")
    print("    □  Bike fully tuned — chain lubed, tires at correct PSI")
    print("    □  Nutrition: 200-300 cal/hr (gels, bars, or liquid)")
    print("    □  Hydration: 1 bottle per hour minimum")
    print("    □  Start conservative — bank time after mile 60")
    print("    □  Avg power / speed check every 10 miles")
    print("    □  Weather checked March 28 — dress accordingly")
    print(sep)


def save_plan(plan, stats):
    current_speed = stats.get("meaningful_avg_speed") or stats.get("speed_90d") or 0
    lines = [
        "27-DAY CYCLING TRAINING PLAN",
        f"Goal: 100 miles in 4 hours on March 29, 2026 (25.0 mph avg)",
        f"Generated: {TODAY}",
        f"Current fitness: ~{current_speed:.1f} mph avg (meaningful rides)",
        "",
    ]
    for d in plan:
        prefix = f"Day {d['day']:>2} ({d['date'].strftime('%a %b %d')}) | {d['miles']:>3} mi | {d['intensity']:<9}"
        lines.append(f"{prefix} | {d['description']}")
        if d["notes"]:
            lines.append(f"{'':>36}  → {d['notes']}")
    lines.append("")
    with open(PLAN_FILE, "w") as f:
        f.write("\n".join(lines))
    print(f"\n  Plan saved to {PLAN_FILE}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not os.path.exists(ACTIVITIES_FILE):
        print(f"ERROR: {ACTIVITIES_FILE} not found. Run fetch.py first.")
        return

    with open(ACTIVITIES_FILE) as f:
        raw = json.load(f)

    if not raw:
        print("No cycling activities found in activities.json.")
        return

    print(f"Loaded {len(raw)} cycling activities.")
    stats = analyze(raw)
    print_analysis(stats)

    plan = generate_plan(stats)
    print_plan(plan, stats)
    save_plan(plan, stats)


if __name__ == "__main__":
    main()
