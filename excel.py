"""
Export the 27-day training plan to Excel with weekly totals and charts.

Usage: py -3.12 excel.py
Output: training_plan.xlsx
"""

import os
from datetime import date, timedelta
import xlsxwriter

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "training_plan.xlsx")
TODAY = date(2026, 3, 2)

# ---------------------------------------------------------------------------
# Plan data (mirrors plan.py)
# ---------------------------------------------------------------------------

SCHEDULE = [
    # Phase 1 — Base Build
    ( 0, "Assessment / easy spin",            25,  "Easy",    "Zone 2 throughout — gauge current feel and fitness"),
    ( 1, "Rest",                               0,  "Rest",    "Light stretching, mobility work"),
    ( 2, "Tempo intervals",                   35,  "Moderate","3 × 10 min at 24-25 mph, 5 min easy between"),
    ( 3, "Rest",                               0,  "Rest",    "Full recovery"),
    ( 4, "Endurance ride",                    50,  "Easy-Mod","Steady Zone 2-3; practice nutrition every 45 min"),
    ( 5, "Speed / cadence work",              20,  "Hard",    "5 × 5 min max effort; high cadence drills"),
    ( 6, "Long ride",                         65,  "Easy-Mod","Aerobic base — hold 21-23 mph, no heroics"),
    # Phase 2 — Volume Build
    ( 7, "Recovery spin",                     20,  "Easy",    "Flush legs from long ride; keep HR low"),
    ( 8, "Rest",                               0,  "Rest",    "Full recovery"),
    ( 9, "Sustained tempo",                   40,  "Moderate","2 × 20 min at 24-26 mph; 10 min easy between"),
    (10, "Rest",                               0,  "Rest",    "Full recovery"),
    (11, "Endurance + race-pace blocks",      55,  "Moderate","2 × 15 min at 25 mph embedded in Zone 2 ride"),
    (12, "Leg-speed sharpener",               25,  "Hard",    "Sprint repeats + 6 × 1 min all-out efforts"),
    (13, "Long ride — biggest of prep",       75,  "Easy-Mod","Longest training ride; practice full-race nutrition plan"),
    # Phase 3 — Sharpen
    (14, "Recovery spin",                     20,  "Easy",    "Easy legs after big week"),
    (15, "Rest",                               0,  "Rest",    "Full rest"),
    (16, "Race simulation",                   60,  "Hard",    "40+ miles at 25 mph target; test bike setup & nutrition"),
    (17, "Rest",                               0,  "Rest",    "Recovery after race sim"),
    (18, "Threshold work",                    35,  "Moderate","3 × 12 min at threshold; gauge fitness response"),
    (19, "Fast-twitch activation",            20,  "Hard",    "Short sprints; high cadence; stay sharp"),
    (20, "Confidence ride",                   50,  "Easy-Mod","Controlled, smooth effort — build mental confidence"),
    # Phase 4 — Taper
    (21, "Easy taper spin",                   20,  "Easy",    "Begin taper — keep legs fresh, don't push"),
    (22, "Rest",                               0,  "Rest",    "Full recovery"),
    (23, "Short sharpener",                   15,  "Mod-Hard","3 × 5 min at race effort to stay sharp; no fatigue"),
    (24, "Rest",                               0,  "Rest",    "Full rest"),
    (25, "Leg-opener spin",                   10,  "Easy",    "20-30 min very easy; just move the legs"),
    (26, "Rest / prep day",                    0,  "Rest",    "Check bike, lay out kit, plan nutrition, sleep early"),
    # Event
    (27, "EVENT: 100 miles in 4 hours",      100,  "Race",   "Target 25.0 mph avg — execute your plan, GO!"),
]

WEEK_LABELS = [
    "Week 1 — Base Build",
    "Week 2 — Volume Build",
    "Week 3 — Sharpen",
    "Week 4 — Taper",
    "Event Day",
]

WEEK_SLICES = [slice(0, 7), slice(7, 14), slice(14, 21), slice(21, 27), slice(27, 28)]

INTENSITY_ORDER = ["Easy", "Easy-Mod", "Moderate", "Mod-Hard", "Hard", "Race", "Rest"]

# Hex colors for each intensity (no '#')
INTENSITY_BG = {
    "Easy":     "C6EFCE",
    "Easy-Mod": "DDEBF7",
    "Moderate": "FFEB9C",
    "Mod-Hard": "FCE4D6",
    "Hard":     "FFC7CE",
    "Race":     "FFD700",
    "Rest":     "EDEDED",
}

# Chart series colors (same palette)
INTENSITY_CHART_COLOR = {
    "Easy":     "#4CAF50",
    "Easy-Mod": "#2196F3",
    "Moderate": "#FF9800",
    "Mod-Hard": "#FF5722",
    "Hard":     "#F44336",
    "Race":     "#FFD700",
}

PHASE_COLORS = ["1F4E79", "1F497D", "375623", "7B3F00"]  # dark blue tones per phase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_days():
    days = []
    for offset, desc, miles, intensity, notes in SCHEDULE:
        d = TODAY + timedelta(days=offset)
        days.append({
            "day":         offset + 1,
            "date":        d,
            "dow":         d.strftime("%A"),
            "miles":       miles,
            "intensity":   intensity,
            "description": desc,
            "notes":       notes,
        })
    return days


def build_weeks(days):
    weeks = []
    for i, (label, sl) in enumerate(zip(WEEK_LABELS, WEEK_SLICES)):
        wdays = days[sl]
        intensity_miles = {k: 0.0 for k in INTENSITY_ORDER}
        for d in wdays:
            if d["miles"] > 0:
                intensity_miles[d["intensity"]] = intensity_miles.get(d["intensity"], 0) + d["miles"]
        weeks.append({
            "label":           label,
            "days":            wdays,
            "total_miles":     sum(d["miles"] for d in wdays),
            "rides":           sum(1 for d in wdays if d["miles"] > 0),
            "rest_days":       sum(1 for d in wdays if d["miles"] == 0),
            "intensity_miles": intensity_miles,
        })
    return weeks


# ---------------------------------------------------------------------------
# Sheet 1 — Training Plan
# ---------------------------------------------------------------------------

def write_plan_sheet(wb, ws, days, weeks):
    # ── Column widths ─────────────────────────────────────────────────────
    ws.set_column("A:A", 6)   # Day #
    ws.set_column("B:B", 12)  # Date
    ws.set_column("C:C", 10)  # Day of week
    ws.set_column("D:D", 7)   # Miles
    ws.set_column("E:E", 11)  # Intensity
    ws.set_column("F:F", 34)  # Description
    ws.set_column("G:G", 48)  # Notes

    # ── Formats ───────────────────────────────────────────────────────────
    title_fmt = wb.add_format({
        "bold": True, "font_size": 16, "font_color": "FFFFFF",
        "bg_color": "1F4E79", "align": "center", "valign": "vcenter",
        "border": 0,
    })
    subtitle_fmt = wb.add_format({
        "bold": True, "font_size": 11, "font_color": "FFFFFF",
        "bg_color": "2E75B6", "align": "center", "valign": "vcenter",
    })
    header_fmt = wb.add_format({
        "bold": True, "font_size": 10, "font_color": "FFFFFF",
        "bg_color": "2F5496", "align": "center", "valign": "vcenter",
        "border": 1, "border_color": "FFFFFF",
    })
    phase_fmt = wb.add_format({
        "bold": True, "font_size": 10, "font_color": "FFFFFF",
        "bg_color": "375623", "align": "left", "valign": "vcenter",
        "left": 2, "left_color": "FFFFFF",
    })
    week_total_fmt = wb.add_format({
        "bold": True, "font_size": 10, "font_color": "FFFFFF",
        "bg_color": "1F4E79", "align": "center", "valign": "vcenter",
        "top": 2, "top_color": "9DC3E6",
    })
    week_total_label_fmt = wb.add_format({
        "bold": True, "font_size": 10, "font_color": "FFFFFF",
        "bg_color": "1F4E79", "align": "left", "valign": "vcenter",
        "top": 2, "top_color": "9DC3E6",
    })

    def row_fmt(intensity):
        bg = INTENSITY_BG.get(intensity, "FFFFFF")
        return wb.add_format({
            "font_size": 10, "bg_color": bg,
            "border": 1, "border_color": "D9D9D9",
            "valign": "vcenter",
        })

    def row_fmt_center(intensity):
        bg = INTENSITY_BG.get(intensity, "FFFFFF")
        return wb.add_format({
            "font_size": 10, "bg_color": bg,
            "border": 1, "border_color": "D9D9D9",
            "valign": "vcenter", "align": "center",
        })

    def row_fmt_bold(intensity):
        bg = INTENSITY_BG.get(intensity, "FFFFFF")
        return wb.add_format({
            "bold": True, "font_size": 10, "bg_color": bg,
            "border": 1, "border_color": "D9D9D9",
            "valign": "vcenter", "align": "center",
        })

    # ── Title rows ────────────────────────────────────────────────────────
    ws.set_row(0, 28)
    ws.merge_range("A1:G1", "27-Day Cycling Training Plan", title_fmt)
    ws.set_row(1, 18)
    ws.merge_range("A2:G2", "Goal: 100 Miles in 4 Hours on March 29, 2026  |  Target: 25.0 mph average", subtitle_fmt)
    ws.set_row(2, 6)  # spacer

    # ── Column headers ────────────────────────────────────────────────────
    ws.set_row(3, 18)
    for col, label in enumerate(["Day", "Date", "Weekday", "Miles", "Intensity", "Description", "Notes"]):
        ws.write(3, col, label, header_fmt)

    # ── Data rows ─────────────────────────────────────────────────────────
    phase_boundaries = {
        1:  "PHASE 1 — Base Build     (Mar 2–8)",
        8:  "PHASE 2 — Volume Build   (Mar 9–15)",
        15: "PHASE 3 — Sharpen        (Mar 16–22)",
        22: "PHASE 4 — Taper          (Mar 23–28)",
        28: "EVENT DAY",
    }

    row = 4
    week_idx = 0
    week_start_rows = []

    for d in days:
        # Phase header
        if d["day"] in phase_boundaries:
            ws.set_row(row, 16)
            ws.merge_range(row, 0, row, 6, phase_boundaries[d["day"]], phase_fmt)
            row += 1

        intensity = d["intensity"]
        ws.set_row(row, 18)
        ws.write(row, 0, d["day"],        row_fmt_center(intensity))
        ws.write(row, 1, d["date"].strftime("%b %d, %Y"), row_fmt_center(intensity))
        ws.write(row, 2, d["dow"],        row_fmt_center(intensity))
        ws.write(row, 3, d["miles"] if d["miles"] > 0 else "—", row_fmt_center(intensity))
        ws.write(row, 4, intensity,       row_fmt_center(intensity))
        ws.write(row, 5, d["description"], row_fmt(intensity))
        ws.write(row, 6, d["notes"],      row_fmt(intensity))

        # Track week start rows for weekly totals insertion
        if d["day"] in (1, 8, 15, 22):
            week_start_rows.append(row)

        row += 1

        # Weekly total after each phase (after day 7, 14, 21, 27)
        if d["day"] in (7, 14, 21, 27):
            w = weeks[week_idx]
            ws.set_row(row, 20)
            ws.merge_range(row, 0, row, 2,
                f"  {w['label']}  — Weekly Total",
                week_total_label_fmt)
            ws.write(row, 3, w["total_miles"], week_total_fmt)
            ws.write(row, 4, f"{w['rides']} rides / {w['rest_days']} rest", week_total_fmt)
            ws.merge_range(row, 5, row, 6,
                f"Total training miles this week: {w['total_miles']:.0f} mi",
                week_total_label_fmt)
            row += 1
            ws.set_row(row, 6)  # spacer
            row += 1
            week_idx += 1

    # Event day total
    w = weeks[4]
    ws.set_row(row, 22)
    total_all = sum(wk["total_miles"] for wk in weeks)
    ws.merge_range(row, 0, row, 2, "  TOTAL (all 27 days incl. event)", week_total_label_fmt)
    ws.write(row, 3, total_all, week_total_fmt)
    ws.merge_range(row, 4, row, 6, f"Grand total: {total_all:.0f} miles", week_total_label_fmt)

    # ── Freeze panes ──────────────────────────────────────────────────────
    ws.freeze_panes(4, 0)

    # ── Legend ────────────────────────────────────────────────────────────
    legend_title_fmt = wb.add_format({
        "bold": True, "font_size": 9, "bg_color": "2F5496", "font_color": "FFFFFF",
        "border": 1, "border_color": "D9D9D9", "align": "center",
    })
    legend_row = 6
    legend_col = 8
    ws.set_column(legend_col, legend_col, 14)
    ws.set_column(legend_col + 1, legend_col + 1, 22)
    ws.write(legend_row, legend_col, "Intensity", legend_title_fmt)
    ws.write(legend_row, legend_col + 1, "Description", legend_title_fmt)
    legend_row += 1

    legend_desc = {
        "Easy":     "Zone 2 — aerobic base",
        "Easy-Mod": "Zone 2-3 — steady endurance",
        "Moderate": "Zone 3-4 — tempo / threshold",
        "Mod-Hard": "Zone 4 — near-threshold",
        "Hard":     "Zone 5 — intervals / max effort",
        "Race":     "Race day — execute!",
        "Rest":     "Full recovery",
    }
    for intensity in INTENSITY_ORDER:
        bg = INTENSITY_BG[intensity]
        fmt_l = wb.add_format({"bold": True, "bg_color": bg, "border": 1, "border_color": "D9D9D9", "align": "center", "font_size": 9})
        fmt_r = wb.add_format({"bg_color": bg, "border": 1, "border_color": "D9D9D9", "font_size": 9})
        ws.write(legend_row, legend_col, intensity, fmt_l)
        ws.write(legend_row, legend_col + 1, legend_desc[intensity], fmt_r)
        legend_row += 1

    # ── Daily miles bar chart (stacked by intensity) ──────────────────────
    # Write hidden chart data to columns K-R (col 10+)
    chart_data_col = 11
    chart_data_row_start = 1

    # Headers
    ws.write(chart_data_row_start, chart_data_col - 1, "Date", wb.add_format({"bold": True}))
    for i, intensity in enumerate(list(INTENSITY_CHART_COLOR.keys())):
        ws.write(chart_data_row_start, chart_data_col + i, intensity, wb.add_format({"bold": True}))

    # Data rows
    intensity_keys = list(INTENSITY_CHART_COLOR.keys())
    date_labels = []
    for di, d in enumerate(days):
        dr = chart_data_row_start + 1 + di
        date_labels.append(d["date"].strftime("%b %d"))
        ws.write(dr, chart_data_col - 1, d["date"].strftime("%b %d"))
        for i, intensity in enumerate(intensity_keys):
            val = d["miles"] if d["intensity"] == intensity else 0
            ws.write(dr, chart_data_col + i, val)

    # Create stacked bar chart
    chart = wb.add_chart({"type": "bar", "subtype": "stacked"})
    chart.set_title({"name": "Daily Training Miles by Intensity"})
    chart.set_x_axis({"name": "Miles"})
    chart.set_y_axis({"name": "Date"})
    chart.set_size({"width": 520, "height": 620})
    chart.set_style(10)

    n_days = len(days)
    for i, intensity in enumerate(intensity_keys):
        col_letter = chr(ord("L") + i)
        chart.add_series({
            "name":       intensity,
            "categories": [ws.name, chart_data_row_start + 1, chart_data_col - 1,
                           chart_data_row_start + n_days, chart_data_col - 1],
            "values":     [ws.name, chart_data_row_start + 1, chart_data_col + i,
                           chart_data_row_start + n_days, chart_data_col + i],
            "fill":       {"color": INTENSITY_CHART_COLOR[intensity]},
            "gap":        50,
        })

    chart.set_legend({"position": "bottom"})
    ws.insert_chart("I6", chart, {"x_offset": 5, "y_offset": 5})


# ---------------------------------------------------------------------------
# Sheet 2 — Weekly Summary
# ---------------------------------------------------------------------------

def write_summary_sheet(wb, ws, weeks):
    ws.set_column("A:A", 26)
    ws.set_column("B:B", 10)
    ws.set_column("C:C", 8)
    ws.set_column("D:D", 10)
    ws.set_column("E:E", 10)

    title_fmt = wb.add_format({
        "bold": True, "font_size": 14, "font_color": "FFFFFF",
        "bg_color": "1F4E79", "align": "center", "valign": "vcenter",
    })
    header_fmt = wb.add_format({
        "bold": True, "font_size": 10, "font_color": "FFFFFF",
        "bg_color": "2F5496", "align": "center", "valign": "vcenter",
        "border": 1, "border_color": "FFFFFF",
    })
    week_colors = ["D6E4F0", "D5E8D4", "FFF2CC", "FCE4D6", "FFD700"]
    total_fmt = wb.add_format({
        "bold": True, "font_size": 11, "font_color": "FFFFFF",
        "bg_color": "1F4E79", "align": "center", "border": 2, "border_color": "9DC3E6",
    })
    total_label_fmt = wb.add_format({
        "bold": True, "font_size": 11, "font_color": "FFFFFF",
        "bg_color": "1F4E79", "align": "left", "border": 2, "border_color": "9DC3E6",
        "indent": 1,
    })

    # Title
    ws.set_row(0, 28)
    ws.merge_range("A1:E1", "Weekly Training Summary", title_fmt)
    ws.set_row(1, 6)

    # Headers
    ws.set_row(2, 18)
    for col, label in enumerate(["Phase / Week", "Total Miles", "Rides", "Rest Days", "Intensity Mix"]):
        ws.write(2, col, label, header_fmt)

    # Intensity bar builder (ASCII-style text)
    def intensity_mix(week):
        parts = []
        for k in ["Easy", "Easy-Mod", "Moderate", "Mod-Hard", "Hard"]:
            m = week["intensity_miles"].get(k, 0)
            if m > 0:
                parts.append(f"{k}: {m:.0f}mi")
        return "  |  ".join(parts) if parts else "—"

    row = 3
    for i, w in enumerate(weeks):
        bg = week_colors[i]
        data_fmt = wb.add_format({"bg_color": bg, "border": 1, "border_color": "D9D9D9",
                                   "align": "center", "font_size": 10})
        label_fmt = wb.add_format({"bold": True, "bg_color": bg, "border": 1,
                                    "border_color": "D9D9D9", "font_size": 10, "indent": 1})
        mix_fmt = wb.add_format({"bg_color": bg, "border": 1, "border_color": "D9D9D9",
                                  "font_size": 9})
        ws.set_row(row, 20)
        ws.write(row, 0, w["label"], label_fmt)
        ws.write(row, 1, w["total_miles"], data_fmt)
        ws.write(row, 2, w["rides"], data_fmt)
        ws.write(row, 3, w["rest_days"], data_fmt)
        ws.write(row, 4, intensity_mix(w), mix_fmt)
        row += 1

    # Total row
    total_miles = sum(w["total_miles"] for w in weeks)
    total_rides = sum(w["rides"] for w in weeks)
    total_rest = sum(w["rest_days"] for w in weeks)
    ws.set_row(row, 22)
    ws.write(row, 0, "  TOTAL", total_label_fmt)
    ws.write(row, 1, total_miles, total_fmt)
    ws.write(row, 2, total_rides, total_fmt)
    ws.write(row, 3, total_rest, total_fmt)
    ws.write(row, 4, f"{total_miles:.0f} miles across 27 days", total_label_fmt)
    row += 2

    # ── Write chart source data (hidden) ──────────────────────────────────
    # Weekly miles
    chart_row = row
    ws.write(chart_row, 0, "Week", wb.add_format({"bold": True}))
    ws.write(chart_row, 1, "Miles", wb.add_format({"bold": True}))
    for i, w in enumerate(weeks[:4]):  # training weeks only
        ws.write(chart_row + 1 + i, 0, f"Week {i+1}")
        ws.write(chart_row + 1 + i, 1, w["total_miles"])

    # Intensity breakdown per week
    ws.write(chart_row, 3, "Week", wb.add_format({"bold": True}))
    intensity_chart_keys = ["Easy", "Easy-Mod", "Moderate", "Mod-Hard", "Hard"]
    for j, k in enumerate(intensity_chart_keys):
        ws.write(chart_row, 4 + j, k, wb.add_format({"bold": True}))
    for i, w in enumerate(weeks[:4]):
        ws.write(chart_row + 1 + i, 3, f"Week {i+1}")
        for j, k in enumerate(intensity_chart_keys):
            ws.write(chart_row + 1 + i, 4 + j, w["intensity_miles"].get(k, 0))

    # ── Weekly miles column chart ─────────────────────────────────────────
    chart1 = wb.add_chart({"type": "column"})
    chart1.set_title({"name": "Weekly Training Miles"})
    chart1.set_x_axis({"name": "Training Week"})
    chart1.set_y_axis({"name": "Miles", "min": 0})
    chart1.set_style(10)
    chart1.set_size({"width": 400, "height": 280})
    chart1.add_series({
        "name":       "Miles",
        "categories": [ws.name, chart_row + 1, 0, chart_row + 4, 0],
        "values":     [ws.name, chart_row + 1, 1, chart_row + 4, 1],
        "fill":       {"color": "#2196F3"},
        "data_labels": {"value": True},
        "gap": 60,
    })
    chart1.set_legend({"none": True})
    ws.insert_chart("A10", chart1, {"x_offset": 5, "y_offset": 5})

    # ── Intensity stacked bar chart ───────────────────────────────────────
    chart2 = wb.add_chart({"type": "column", "subtype": "stacked"})
    chart2.set_title({"name": "Miles by Intensity per Week"})
    chart2.set_x_axis({"name": "Training Week"})
    chart2.set_y_axis({"name": "Miles", "min": 0})
    chart2.set_style(10)
    chart2.set_size({"width": 420, "height": 280})

    intensity_chart_colors = ["#4CAF50", "#2196F3", "#FF9800", "#FF5722", "#F44336"]
    for j, (k, color) in enumerate(zip(intensity_chart_keys, intensity_chart_colors)):
        chart2.add_series({
            "name":       k,
            "categories": [ws.name, chart_row + 1, 3, chart_row + 4, 3],
            "values":     [ws.name, chart_row + 1, 4 + j, chart_row + 4, 4 + j],
            "fill":       {"color": color},
        })
    chart2.set_legend({"position": "bottom"})
    ws.insert_chart("H10", chart2, {"x_offset": 5, "y_offset": 5})


# ---------------------------------------------------------------------------
# Sheet 3 — Race Day Checklist
# ---------------------------------------------------------------------------

def write_checklist_sheet(wb, ws):
    ws.set_column("A:A", 4)
    ws.set_column("B:B", 40)
    ws.set_column("C:C", 42)

    title_fmt = wb.add_format({
        "bold": True, "font_size": 14, "font_color": "FFFFFF",
        "bg_color": "7B2D00", "align": "center", "valign": "vcenter",
    })
    section_fmt = wb.add_format({
        "bold": True, "font_size": 11, "font_color": "FFFFFF",
        "bg_color": "C55A11", "indent": 1,
    })
    item_fmt = wb.add_format({"font_size": 10, "indent": 1, "border": 1, "border_color": "D9D9D9"})
    check_fmt = wb.add_format({"font_size": 10, "align": "center", "border": 1, "border_color": "D9D9D9"})

    ws.set_row(0, 28)
    ws.merge_range("A1:C1", "Race Day Checklist — March 29, 2026", title_fmt)
    ws.set_row(1, 6)

    sections = [
        ("Bike & Gear", [
            ("Tires pumped to correct PSI (check the day before)", ""),
            ("Chain cleaned and lubed", ""),
            ("Brakes and gears checked", ""),
            ("Bike computer charged and route loaded", ""),
            ("Helmet fit verified", ""),
            ("Kit (jersey, bibs, socks, gloves) laid out", ""),
            ("Cycling shoes + cleats checked", ""),
            ("Sunglasses / eye protection packed", ""),
        ]),
        ("Nutrition & Hydration", [
            ("Bottles filled (2 minimum)", "1 water, 1 electrolyte"),
            ("Gels / bars packed (200-300 cal/hr = 800-1200 cal total)", "Every 30-45 min"),
            ("Electrolyte tablets / salt tabs", "Prevent cramping on long rides"),
            ("Pre-ride meal planned (3-4 hrs before start)", "High carb, low fiber"),
            ("Post-ride recovery meal/shake ready", "Within 30 min of finish"),
        ]),
        ("Logistics", [
            ("Check weather — March 28 evening", "Dress 10°F warmer than temp suggests"),
            ("Route confirmed — flat course preferred for 25 mph target", ""),
            ("Start time set — avoid peak heat if warm", ""),
            ("Emergency contact notified", ""),
            ("Phone charged, emergency $ / ID", ""),
            ("CO2 cartridges or pump + spare tube packed", ""),
        ]),
        ("Strategy", [
            ("First 10 miles: hold back, settle in below target pace", "Resist going out too hard"),
            ("Miles 10-60: lock into 25 mph, check avg every 10 mi", "Adjust effort not speed"),
            ("Miles 60-90: push if feeling good, manage fatigue", "This is where races are won/lost"),
            ("Final 10 miles: everything you have left", ""),
        ]),
    ]

    row = 2
    for section_title, items in sections:
        ws.set_row(row, 20)
        ws.merge_range(row, 0, row, 2, f"  {section_title}", section_fmt)
        row += 1
        for item, note in items:
            ws.set_row(row, 18)
            ws.write(row, 0, "☐", check_fmt)
            ws.write(row, 1, item, item_fmt)
            ws.write(row, 2, note, item_fmt)
            row += 1
        row += 1  # spacer


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    days = build_days()
    weeks = build_weeks(days)

    wb = xlsxwriter.Workbook(OUTPUT_FILE)
    wb.set_properties({"title": "27-Day Cycling Plan", "subject": "100 miles on March 29, 2026"})

    ws_plan     = wb.add_worksheet("Training Plan")
    ws_summary  = wb.add_worksheet("Weekly Summary")
    ws_checklist = wb.add_worksheet("Race Day Checklist")

    write_plan_sheet(wb, ws_plan, days, weeks)
    write_summary_sheet(wb, ws_summary, weeks)
    write_checklist_sheet(wb, ws_checklist)

    wb.close()
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
