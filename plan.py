"""Generate the multi-sport 2026 training plan (Jun 9 - Dec 31).

Loads activities.json + whoop.json, runs analysis, prints the season schedule,
recovery-gated next session, and the goal scorecard. Saves training_plan.txt.

Usage: py -3.12 plan.py
"""

import os
import json
from datetime import date

from common import week_start
from analysis import (parse_activities, analyze_run, analyze_swim,
                      analyze_bike, analyze_recovery)
from periodize import generate_weeks
from gating import gate_session

HERE = os.path.dirname(os.path.abspath(__file__))
ACTIVITIES_FILE = os.path.join(HERE, "activities.json")
WHOOP_FILE = os.path.join(HERE, "whoop.json")
PLAN_FILE = os.path.join(HERE, "training_plan.txt")

GOAL_5K_SEC = 22 * 60  # sub-22:00


def _fmt_pace(sec):
    if not sec:
        return "n/a"
    return f"{int(sec // 60)}:{int(sec % 60):02d}"


def load_data():
    raw = json.load(open(ACTIVITIES_FILE)) if os.path.exists(ACTIVITIES_FILE) else []
    acts = parse_activities(raw)
    whoop = json.load(open(WHOOP_FILE)) if os.path.exists(WHOOP_FILE) else {"recovery": []}
    return acts, whoop.get("recovery", [])


def build_scorecard(acts, recovery_records, today):
    run = analyze_run(acts, today=today)
    swim = analyze_swim(acts, today=today)
    bike = analyze_bike(acts, today=today)
    rec = analyze_recovery(recovery_records, today=today)

    gap = run["best_5k_sec"] - GOAL_5K_SEC if run["best_5k_sec"] else None
    return {
        "run": {"best": run["best_5k_sec"], "gap": gap, "paces": run["paces"]},
        "swim": swim,
        "bike": bike,
        "recovery": rec,
    }


def print_scorecard(sc):
    print("\n" + "=" * 64)
    print("  GOAL SCORECARD")
    print("=" * 64)
    if sc["run"]["best"]:
        status = "ON TRACK" if sc["run"]["gap"] is not None and sc["run"]["gap"] <= 0 else "BUILDING"
        print(f"  5k sub-22 : best {_fmt_pace(sc['run']['best'])}  (need -{int(max(sc['run']['gap'],0))}s)  [{status}]")
    else:
        print("  5k sub-22 : insufficient run data")
    s = sc["swim"]
    print(f"  Swim 2x/wk: hit {s['weeks_hit_target']} of last {s['total_weeks']} weeks")
    b = sc["bike"]
    print(f"  Bike      : {b['weekly_avg_4wk']:.0f} mi/wk (4wk)  | longest {b['longest_miles']:.0f} mi  | DI rides {b['di_count']} @ {b['di_avg_speed']:.1f} mph")
    if sc["recovery"]["has_data"]:
        lat = sc["recovery"]["latest"]
        print(f"  Recovery  : latest {lat['recovery']}% ({lat['band']})  | 7d avg {sc['recovery']['trend_7d_avg']:.0f}%")
    else:
        print("  Recovery  : no WHOOP data")


def print_today(weeks, sc, today):
    tws = week_start(today)
    week = next((w for w in weeks if w["week_start"] == tws), weeks[0])
    dow = today.strftime("%a")
    day = next((d for d in week["days"] if d["dow"] == dow), week["days"][0])
    rec = sc["recovery"]["latest"] if sc["recovery"]["has_data"] else None
    g = gate_session(day,
                     recovery=rec["recovery"] if rec else None,
                     sleep_perf=rec.get("sleep_perf") if rec else None)
    print("\n" + "=" * 64)
    print(f"  TODAY ({today:%a %b %d}) — {week['block']}")
    print("=" * 64)
    print(f"  Prescribed : {day['desc']}")
    print(f"  Recovery   : {g['adjustment']}")
    print(f"  Do this    : {g['recommendation']}")


def save_plan(weeks, sc):
    lines = ["MULTI-SPORT TRAINING PLAN — Jun 9 to Dec 31, 2026", ""]
    cur_block = None
    for w in weeks:
        if w["block"] != cur_block:
            cur_block = w["block"]
            lines.append(f"\n=== {cur_block} ===")
        lines.append(f"\nWeek {w['week_index']} ({w['week_start']:%b %d}) — bike target {w['bike_target']} mi [{w['bike_kind']}]")
        for d in w["days"]:
            key = " *" if d.get("key") else "  "
            lines.append(f"  {d['dow']}{key} {d['sport']:<5} {d['desc']}")
    with open(PLAN_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nPlan saved to {PLAN_FILE}")


def main():
    today = date.today()
    acts, recovery = load_data()
    if not acts:
        print("No activities.json — run fetch.py first.")
        return
    weeks = generate_weeks()
    sc = build_scorecard(acts, recovery, today)
    print_scorecard(sc)
    print_today(weeks, sc, today)
    save_plan(weeks, sc)


if __name__ == "__main__":
    main()
