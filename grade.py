"""Compute last week's training grade and post it to ClickUp.

Usage: py -3.12 grade.py   (also run automatically Sunday nights — see scheduler)
"""

import os
import json
from datetime import date, timedelta

from dotenv import load_dotenv

from common import week_start
from analysis import parse_activities, recovery_band
from periodize import generate_weeks, pull_target
from grading import grade_week
import clickup

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, ".env"))
ACTIVITIES_FILE = os.path.join(HERE, "activities.json")
WHOOP_FILE = os.path.join(HERE, "whoop.json")
GRADES_FILE = os.path.join(HERE, "grades.json")


def _completed_week_start(today):
    """Monday of the most recently completed week (the week before this one)."""
    return week_start(today) - timedelta(days=7)


def summarize_week(acts, recovery, ws):
    """Build the grade_week input dict from actuals for the week starting ws."""
    we = ws + timedelta(days=6)
    wk_acts = [a for a in acts if ws <= a["date"] <= we]

    bikes = [a for a in wk_acts if a["sport"] == "bike"]
    key_bikes = [a for a in bikes if (a["weekday"] in (1, 3) and a["hour"] < 7) or a["weekday"] == 5]
    swims = [a for a in wk_acts if a["sport"] == "swim"]
    runs = [a for a in wk_acts if a["sport"] == "run"]

    week_meta = next((w for w in generate_weeks() if w["week_start"] == ws), None)
    bike_target = week_meta["bike_target"] if week_meta else 170
    pulls_target = pull_target(week_meta["block"]) if week_meta else 6

    recs = {r["date"]: r for r in recovery}
    overreached = False
    for a in key_bikes:
        r = recs.get(a["date"].isoformat())
        if r and recovery_band(r.get("recovery")) == "red":
            overreached = True

    return {
        "bike": {
            "key_rides_done": min(len(key_bikes), 3),
            "key_rides_planned": 3,
            "volume_actual": sum(a["miles"] for a in bikes),
            "volume_target": bike_target,
            "pulls_done": pulls_target if len(key_bikes) >= 2 else 0,
            "pulls_target": pulls_target,
        },
        "swim": {"sessions": len(swims)},
        "run": {"quality_done": len(runs) >= 1, "hit_pace": len(runs) >= 2},
        "recovery": {"respected": not overreached, "overreached": overreached},
    }


def build_description(ws, summary, grade):
    we = ws + timedelta(days=6)
    c = grade["components"]
    b = summary["bike"]
    return (
        f"**Week of {ws:%b %d} – {we:%b %d}, 2026**\n\n"
        f"**Grade: {grade['letter']}** (GPA {grade['gpa']})\n\n"
        f"- Bike (40%): {c['bike']:.1f}/4 — {b['key_rides_done']}/3 key rides, "
        f"{b['volume_actual']:.0f}/{b['volume_target']} mi, pulls {b['pulls_done']}/{b['pulls_target']}\n"
        f"- Swim (20%): {c['swim']:.1f}/4 — {summary['swim']['sessions']} sessions\n"
        f"- Run (20%): {c['run']:.1f}/4\n"
        f"- Recovery (20%): {c['recovery']:.1f}/4\n"
    )


def main():
    today = date.today()
    ws = _completed_week_start(today)

    acts = parse_activities(json.load(open(ACTIVITIES_FILE))) if os.path.exists(ACTIVITIES_FILE) else []
    whoop = json.load(open(WHOOP_FILE)) if os.path.exists(WHOOP_FILE) else {"recovery": []}
    recovery = whoop.get("recovery", [])

    summary = summarize_week(acts, recovery, ws)
    grade = grade_week(summary)
    name = f"Week of {ws:%b %d} — Grade: {grade['letter']}"
    desc = build_description(ws, summary, grade)

    log = json.load(open(GRADES_FILE)) if os.path.exists(GRADES_FILE) else []
    log = [g for g in log if g["week_start"] != ws.isoformat()]
    log.append({"week_start": ws.isoformat(), "letter": grade["letter"], "gpa": grade["gpa"]})
    json.dump(log, open(GRADES_FILE, "w"), indent=2)

    res = clickup.post_or_update_week_task(
        token=os.getenv("CLICKUP_API_TOKEN", ""),
        list_id=os.getenv("CLICKUP_LIST_ID", ""),
        name=name, description=desc)

    print(f"{name}  (GPA {grade['gpa']})")
    if res.get("skipped"):
        print(f"ClickUp post skipped: {res.get('reason')}")
    elif res.get("error"):
        print(f"ClickUp error (grade saved locally): {res['error']}")
    else:
        print(f"Posted to ClickUp: {res.get('url')}")


if __name__ == "__main__":
    main()
