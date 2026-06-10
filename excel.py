"""Export the multi-sport plan + goal scorecard to Excel.

Usage: py -3.12 excel.py   Output: training_plan.xlsx
"""

import os
import json
from datetime import date

import xlsxwriter

from analysis import (parse_activities, analyze_run, analyze_swim,
                      analyze_bike, analyze_recovery)
from periodize import generate_weeks

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(HERE, "training_plan.xlsx")

SPORT_COLORS = {"bike": "#DCE6F1", "run": "#FDE9D9", "swim": "#E4DFEC"}


def main():
    raw = json.load(open(os.path.join(HERE, "activities.json"))) if os.path.exists(os.path.join(HERE, "activities.json")) else []
    acts = parse_activities(raw)
    whoop = json.load(open(os.path.join(HERE, "whoop.json"))) if os.path.exists(os.path.join(HERE, "whoop.json")) else {"recovery": []}
    today = date.today()
    weeks = generate_weeks()

    wb = xlsxwriter.Workbook(OUTPUT_FILE)
    hdr = wb.add_format({"bold": True, "bg_color": "#1F497D", "font_color": "white", "border": 1})
    block_fmt = wb.add_format({"bold": True, "bg_color": "#1F497D", "font_color": "white"})
    sport_fmts = {s: wb.add_format({"bg_color": c, "border": 1}) for s, c in SPORT_COLORS.items()}
    plain = wb.add_format({"border": 1})

    # --- Schedule sheet ---
    ws = wb.add_worksheet("Schedule")
    ws.set_column(0, 0, 14)
    ws.set_column(1, 1, 6)
    ws.set_column(2, 2, 8)
    ws.set_column(3, 3, 60)
    ws.set_column(4, 4, 12)
    row = 0
    cur_block = None
    for w in weeks:
        if w["block"] != cur_block:
            cur_block = w["block"]
            ws.write(row, 0, cur_block, block_fmt)
            row += 1
            for c, h in enumerate(["Week", "DOW", "Sport", "Session", "Bike target"]):
                ws.write(row, c, h, hdr)
            row += 1
        for i, d in enumerate(w["days"]):
            fmt = sport_fmts.get(d["sport"], plain)
            ws.write(row, 0, f"Wk {w['week_index']} {w['week_start']:%b %d}" if i == 0 else "", plain)
            ws.write(row, 1, d["dow"], fmt)
            ws.write(row, 2, d["sport"], fmt)
            ws.write(row, 3, d["desc"], fmt)
            ws.write(row, 4, f"{w['bike_target']} mi" if i == 0 else "", plain)
            row += 1

    # --- Scorecard sheet ---
    sc = wb.add_worksheet("Scorecard")
    sc.set_column(0, 0, 22)
    sc.set_column(1, 1, 50)
    run = analyze_run(acts, today=today)
    swim = analyze_swim(acts, today=today)
    bike = analyze_bike(acts, today=today)
    rec = analyze_recovery(whoop.get("recovery", []), today=today)
    best = run["best_5k_sec"]
    rows = [
        ("Goal", "Status"),
        ("5k sub-22:00", f"best {int(best//60)}:{int(best%60):02d}" if best else "no data"),
        ("Swim 2x/week", f"{swim['weeks_hit_target']} of {swim['total_weeks']} weeks hit"),
        ("Bike 100mi/4hr", f"{bike['weekly_avg_4wk']:.0f} mi/wk, DI {bike['di_count']} @ {bike['di_avg_speed']:.1f} mph"),
        ("Recovery", f"latest {rec['latest']['recovery']}% ({rec['latest']['band']})" if rec["has_data"] else "no WHOOP data"),
    ]
    for r, (a, b) in enumerate(rows):
        f = hdr if r == 0 else plain
        sc.write(r, 0, a, f)
        sc.write(r, 1, b, f)

    wb.close()
    print(f"Saved {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
