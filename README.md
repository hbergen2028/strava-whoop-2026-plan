# Strava Multi-Sport 2026 Plan

Data-driven training plan for three goals (sub-22 5k, swim 2x/week,
100mi-in-4hr + Davis Island pulls), Jun 9 – Dec 31 2026.

## One-time setup
- `py -3.12 auth.py`        # Strava OAuth
- `py -3.12 whoop_auth.py`  # WHOOP OAuth
- Populate WHOOP + ClickUp keys in `.env`

## Usage
- `py -3.12 fetch.py`        # pull run/swim/bike -> activities.json
- `py -3.12 whoop_fetch.py`  # pull recovery -> whoop.json
- `py -3.12 plan.py`         # scorecard + season plan + today's gated session
- `py -3.12 excel.py`        # training_plan.xlsx
- `py -3.12 grade.py`        # grade last week, post to ClickUp

A Windows scheduled task ("StravaPlan Weekly Grade") runs the grade every
Sunday at 21:00.

## Tests
- `py -3.12 -m pytest -q`
