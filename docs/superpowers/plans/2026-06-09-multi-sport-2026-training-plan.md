# Multi-Sport 2026 Training Plan — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the cycling-only, single-event tool with a data-driven multi-sport training system (run + swim + bike) for Jun 9 – Dec 31, 2026, with WHOOP recovery gating and an automatic weekly grade posted to ClickUp.

**Architecture:** Pure-logic modules (`analysis.py`, `volume.py`, `periodize.py`, `gating.py`, `grading.py`) hold all testable business logic as functions over plain dicts/lists. Thin IO scripts (`fetch.py`, `whoop_fetch.py`, `clickup.py`, `plan.py`, `grade.py`, `excel.py`) handle network, files, and orchestration. This keeps every rule unit-testable in isolation and each file focused on one responsibility.

**Tech Stack:** Python 3.12, `requests`, `python-dotenv`, `xlsxwriter`, `pytest`. Strava API v3, WHOOP API v2, ClickUp API v2. Auth tokens live in `.env` (already populated and verified for all three services).

---

## File Structure

**New pure-logic modules (importable, no network/IO):**
- `common.py` — unit constants, `parse_dt`, date/week helpers.
- `analysis.py` — `parse_activities`, `analyze_run`, `analyze_swim`, `analyze_bike`, `analyze_recovery`.
- `volume.py` — `bike_weekly_volumes` (anchor / ≤10% build-to-build cap / 225 ceiling / 3-up-1-down).
- `periodize.py` — `BLOCKS`, `block_for`, `generate_weeks`, `WEEKLY_TEMPLATE`, Davis Island pull progression.
- `gating.py` — `gate_session` (WHOOP recovery → session adjustment).
- `grading.py` — `grade_week` (bike-first GPA → letter ±).

**New IO scripts:**
- `whoop_fetch.py` — pull WHOOP v2 recovery/sleep/cycle → `whoop.json` (token auto-refresh).
- `clickup.py` — `post_or_update_week_task` (ClickUp v2 client).
- `grade.py` — orchestrator: load data → `grade_week` → ClickUp post.

**Modified:**
- `fetch.py` — widen activity type filter to include `Run` and `Swim`.
- `plan.py` — replaced: orchestrator that loads data, calls the pure modules, prints analysis + 29-week schedule + scorecard, saves `training_plan.txt`.
- `excel.py` — replaced body: render multi-sport weekly schedule + scorecard with `xlsxwriter`.
- `requirements.txt` — add `pytest`.

**Tests:** `tests/test_common.py`, `tests/test_analysis.py`, `tests/test_volume.py`, `tests/test_periodize.py`, `tests/test_gating.py`, `tests/test_grading.py`, `tests/test_clickup.py`.

**Data files (generated):** `activities.json` (multi-sport), `whoop.json`, `grades.json` (local grade log).

**Note on the ≤10% rule:** "≤10% week-over-week" is enforced **build-week to build-week**. The deload (recovery) week intentionally drops ~22%, and the week after a deload returns toward the prior *build* level — that bounce-back is exempt. Tests assert the cap on consecutive build weeks, not across deload boundaries.

---

## Task 0: Project scaffolding (pytest + data dirs)

**Files:**
- Modify: `requirements.txt`
- Create: `tests/__init__.py`
- Create: `pytest.ini`

- [ ] **Step 1: Add pytest to requirements**

Append to `requirements.txt`:
```
pytest
xlsxwriter
```
(`xlsxwriter` is already present; ensure `pytest` is added on its own line.)

- [ ] **Step 2: Install deps**

Run: `py -3.12 -m pip install -r requirements.txt`
Expected: pytest installs without error.

- [ ] **Step 3: Create pytest config**

Create `pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
```

- [ ] **Step 4: Create tests package marker**

Create empty `tests/__init__.py` (no content).

- [ ] **Step 5: Verify pytest runs**

Run: `py -3.12 -m pytest -q`
Expected: "no tests ran" (exit 5) — confirms pytest is wired.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt pytest.ini tests/__init__.py
git commit -m "chore: add pytest scaffolding for multi-sport plan"
```

---

## Task 1: common.py — constants and date helpers

**Files:**
- Create: `common.py`
- Test: `tests/test_common.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_common.py`:
```python
from datetime import date, datetime
from common import parse_dt, week_start, M_TO_MILES, MS_TO_MPH


def test_parse_dt_handles_local_and_z():
    assert parse_dt("2026-06-09T05:25:00") == datetime(2026, 6, 9, 5, 25, 0)
    assert parse_dt("2026-06-09T05:25:00Z") == datetime(2026, 6, 9, 5, 25, 0)


def test_week_start_is_monday():
    # 2026-06-10 is a Wednesday; Monday of that week is 2026-06-08
    assert week_start(date(2026, 6, 10)) == date(2026, 6, 8)


def test_unit_constants():
    assert abs(1609.34 * M_TO_MILES - 1.0) < 1e-6
    assert abs(MS_TO_MPH - 2.23694) < 1e-6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.12 -m pytest tests/test_common.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'common'`.

- [ ] **Step 3: Write minimal implementation**

Create `common.py`:
```python
"""Shared constants and date helpers for the multi-sport training tool."""

from datetime import datetime, date, timedelta

M_TO_MILES = 1 / 1609.34
MS_TO_MPH = 2.23694
M_TO_FEET = 3.28084


def parse_dt(raw: str) -> datetime:
    """Parse an ISO-8601 timestamp (with optional trailing Z) to naive datetime."""
    return datetime.strptime(raw[:19], "%Y-%m-%dT%H:%M:%S")


def week_start(d: date) -> date:
    """Monday of the week containing d."""
    return d - timedelta(days=d.weekday())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.12 -m pytest tests/test_common.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add common.py tests/test_common.py
git commit -m "feat: add common constants and date helpers"
```

---

## Task 2: analysis.py — activity parsing + run analysis

**Files:**
- Create: `analysis.py`
- Test: `tests/test_analysis.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_analysis.py`:
```python
from datetime import date
from analysis import parse_activities, analyze_run


def _run(d, miles, minutes):
    return {"type": "Run", "start_date_local": d + "T06:00:00",
            "distance": miles * 1609.34, "moving_time": int(minutes * 60)}


def test_parse_activities_maps_sport_and_units():
    raw = [
        {"type": "Run", "start_date_local": "2026-06-09T06:00:00",
         "distance": 5000, "moving_time": 1500},
        {"type": "Swim", "start_date_local": "2026-06-08T06:00:00",
         "distance": 1372, "moving_time": 1260},
        {"type": "VirtualRide", "start_date_local": "2026-06-07T06:00:00",
         "distance": 32186, "moving_time": 3600},
    ]
    acts = parse_activities(raw)
    sports = {a["sport"] for a in acts}
    assert sports == {"run", "swim", "bike"}
    run = next(a for a in acts if a["sport"] == "run")
    assert abs(run["miles"] - 3.107) < 0.01
    assert run["date"] == date(2026, 6, 9)


def test_analyze_run_best_5k_and_paces():
    runs = [
        _run("2026-05-01", 3.11, 22.78),  # ~7:19/mi -> ~22:45 5k
        _run("2026-05-08", 3.10, 24.0),   # slower
    ]
    acts = parse_activities(runs)
    r = analyze_run(acts, today=date(2026, 6, 9))
    # best 5k-equivalent seconds should be near 22:45 (1365s), within 20s
    assert abs(r["best_5k_sec"] - 1365) < 25
    # derived paces: vo2 faster than threshold faster than easy
    assert r["paces"]["vo2_sec_per_mi"] < r["paces"]["threshold_sec_per_mi"] < r["paces"]["easy_sec_per_mi"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.12 -m pytest tests/test_analysis.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'analysis'`.

- [ ] **Step 3: Write minimal implementation**

Create `analysis.py` with parsing + run analysis (other analyzers added in Tasks 3–4):
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.12 -m pytest tests/test_analysis.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add analysis.py tests/test_analysis.py
git commit -m "feat: add activity parsing and run analysis"
```

---

## Task 3: analysis.py — swim and bike analysis

**Files:**
- Modify: `analysis.py`
- Test: `tests/test_analysis.py`

- [ ] **Step 1: Write the failing test (append)**

Append to `tests/test_analysis.py`:
```python
from analysis import analyze_swim, analyze_bike


def _act(typ, d, miles, minutes, hour=6):
    return {"type": typ, "start_date_local": f"{d}T{hour:02d}:00:00",
            "distance": miles * 1609.34, "moving_time": int(minutes * 60)}


def test_analyze_swim_sessions_per_week():
    raw = [
        {"type": "Swim", "start_date_local": "2026-06-01T06:00:00", "distance": 1372, "moving_time": 1260},
        {"type": "Swim", "start_date_local": "2026-06-04T06:00:00", "distance": 1372, "moving_time": 1260},
        {"type": "Swim", "start_date_local": "2026-06-08T06:00:00", "distance": 1372, "moving_time": 1260},
    ]
    acts = parse_activities(raw)
    s = analyze_swim(acts, today=date(2026, 6, 9), weeks=8)
    assert s["weeks_hit_target"] >= 1  # week of Jun 1 had 2 swims
    assert s["total_weeks"] == 8


def test_analyze_bike_detects_davis_island():
    raw = [
        _act("Ride", "2026-06-02", 33, 90, hour=5),   # Tue 05:00 -> Davis Island
        _act("Ride", "2026-06-04", 34, 92, hour=5),   # Thu 05:00 -> Davis Island
        _act("Ride", "2026-06-06", 60, 180, hour=8),  # Sat long, not DI
    ]
    acts = parse_activities(raw)
    b = analyze_bike(acts, today=date(2026, 6, 9))
    assert b["di_count"] == 2
    assert b["longest_miles"] >= 59
    assert b["avg_speed_20plus"] > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.12 -m pytest tests/test_analysis.py -k "swim or davis" -v`
Expected: FAIL — `ImportError: cannot import name 'analyze_swim'`.

- [ ] **Step 3: Write minimal implementation (append to analysis.py)**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.12 -m pytest tests/test_analysis.py -v`
Expected: PASS (4 tests total).

- [ ] **Step 5: Commit**

```bash
git add analysis.py tests/test_analysis.py
git commit -m "feat: add swim and bike analysis with Davis Island detection"
```

---

## Task 4: analysis.py — WHOOP recovery analysis

**Files:**
- Modify: `analysis.py`
- Test: `tests/test_analysis.py`

- [ ] **Step 1: Write the failing test (append)**

```python
from analysis import analyze_recovery


def test_analyze_recovery_latest_and_trend():
    records = [
        {"date": "2026-06-10", "recovery": 80, "rhr": 47, "hrv": 80.7, "sleep_perf": 82},
        {"date": "2026-06-09", "recovery": 91, "rhr": 46, "hrv": 97.2, "sleep_perf": 78},
        {"date": "2026-06-08", "recovery": 30, "rhr": 55, "hrv": 50.0, "sleep_perf": 60},
    ]
    r = analyze_recovery(records, today=date(2026, 6, 10))
    assert r["latest"]["recovery"] == 80
    assert r["latest"]["band"] == "green"
    assert 30 <= r["trend_7d_avg"] <= 91
    assert r["has_data"] is True


def test_analyze_recovery_empty():
    r = analyze_recovery([], today=date(2026, 6, 10))
    assert r["has_data"] is False
    assert r["latest"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.12 -m pytest tests/test_analysis.py -k recovery -v`
Expected: FAIL — `ImportError: cannot import name 'analyze_recovery'`.

- [ ] **Step 3: Write minimal implementation (append to analysis.py)**

```python
GREEN_MIN = 67
RED_MAX = 33


def recovery_band(score):
    if score is None:
        return "unknown"
    if score >= GREEN_MIN:
        return "green"
    if score <= RED_MAX:
        return "red"
    return "yellow"


def analyze_recovery(records, today=None):
    """Latest recovery + 7-day trend from normalized WHOOP records (date strings)."""
    today = today or date.today()
    norm = []
    for r in records:
        d = r["date"] if isinstance(r["date"], date) else date.fromisoformat(str(r["date"])[:10])
        norm.append({**r, "date": d, "band": recovery_band(r.get("recovery"))})
    norm.sort(key=lambda r: r["date"], reverse=True)
    if not norm:
        return {"has_data": False, "latest": None, "trend_7d_avg": 0}

    cutoff = today - timedelta(days=7)
    last7 = [r["recovery"] for r in norm if r["date"] >= cutoff and r.get("recovery") is not None]
    return {
        "has_data": True,
        "latest": norm[0],
        "trend_7d_avg": sum(last7) / len(last7) if last7 else norm[0]["recovery"],
        "records": norm,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.12 -m pytest tests/test_analysis.py -v`
Expected: PASS (6 tests total).

- [ ] **Step 5: Commit**

```bash
git add analysis.py tests/test_analysis.py
git commit -m "feat: add WHOOP recovery analysis with bands"
```

---

## Task 5: volume.py — bike weekly volume model

**Files:**
- Create: `volume.py`
- Test: `tests/test_volume.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_volume.py`:
```python
from volume import bike_weekly_volumes


def test_anchor_and_length():
    vols = bike_weekly_volumes(29)
    assert len(vols) == 29
    assert vols[0]["target_miles"] == 170


def test_build_to_build_cap_10pct():
    vols = bike_weekly_volumes(29)
    builds = [w for w in vols if w["kind"] in ("anchor", "build", "ceiling")]
    for prev, cur in zip(builds, builds[1:]):
        assert cur["target_miles"] <= round(prev["target_miles"] * 1.10) + 0.001


def test_recovery_every_fourth_week_and_lower():
    vols = bike_weekly_volumes(29)
    for i, w in enumerate(vols, start=1):
        if i % 4 == 0:
            assert w["kind"] == "recovery"
            assert w["target_miles"] < vols[i - 2]["target_miles"]


def test_ceiling_not_exceeded():
    vols = bike_weekly_volumes(29)
    assert max(w["target_miles"] for w in vols) <= 225
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.12 -m pytest tests/test_volume.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'volume'`.

- [ ] **Step 3: Write minimal implementation**

Create `volume.py`:
```python
"""Bike weekly volume model: anchor, <=10% build-to-build cap, ceiling, 3-up/1-down."""

ANCHOR = 170.0
CAP_PCT = 0.10
CEILING = 225.0
RECOVERY_FRAC = 0.78


def bike_weekly_volumes(num_weeks, anchor=ANCHOR, cap_pct=CAP_PCT,
                        ceiling=CEILING, recovery_frac=RECOVERY_FRAC):
    """Return a list of {week_index, target_miles, kind} for num_weeks weeks.

    kind is one of: anchor, build, ceiling, recovery.
    The <=10% cap applies build-week to build-week; recovery weeks (every 4th)
    step down and are exempt, as is the bounce-back week after them.
    """
    out = []
    prebuild = anchor
    for i in range(num_weeks):
        wk = i + 1
        if wk % 4 == 0:
            target = round(prebuild * recovery_frac)
            kind = "recovery"
        elif wk == 1:
            target = round(anchor)
            kind = "anchor"
            prebuild = target
        else:
            cand = min(prebuild * (1 + cap_pct), ceiling)
            target = round(cand)
            kind = "ceiling" if target >= ceiling else "build"
            prebuild = target
        out.append({"week_index": wk, "target_miles": target, "kind": kind})
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.12 -m pytest tests/test_volume.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add volume.py tests/test_volume.py
git commit -m "feat: add bike weekly volume model with 10pct cap and ceiling"
```

---

## Task 6: periodize.py — blocks, weeks, weekly template

**Files:**
- Create: `periodize.py`
- Test: `tests/test_periodize.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_periodize.py`:
```python
from datetime import date
from periodize import block_for, generate_weeks, pull_target


def test_block_boundaries():
    assert block_for(date(2026, 6, 9)) == "Base + Habit"
    assert block_for(date(2026, 8, 15)) == "Build"
    assert block_for(date(2026, 10, 20)) == "Sharpen"
    assert block_for(date(2026, 12, 1)) == "Peak/Attempt"


def test_generate_weeks_spans_season():
    weeks = generate_weeks()
    assert weeks[0]["week_start"] == date(2026, 6, 8)   # Monday on/before Jun 9
    assert weeks[-1]["week_start"] <= date(2026, 12, 31)
    assert all("block" in w and "bike_target" in w for w in weeks)
    # every week has a 7-day template with 2 swims, 2 runs, 3 key bikes
    days = weeks[0]["days"]
    assert sum(1 for d in days if d["sport"] == "swim") == 2
    assert sum(1 for d in days if d["sport"] == "run") == 2
    assert sum(1 for d in days if d["sport"] == "bike" and d["key"]) == 3


def test_pull_target_progresses():
    assert pull_target("Base + Habit") < pull_target("Sharpen") <= 6
    assert pull_target("Peak/Attempt") == 6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.12 -m pytest tests/test_periodize.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'periodize'`.

- [ ] **Step 3: Write minimal implementation**

Create `periodize.py`:
```python
"""Season periodization: blocks, week generation, weekly template, pull progression."""

from datetime import date, timedelta

from common import week_start
from volume import bike_weekly_volumes

START = date(2026, 6, 9)
END = date(2026, 12, 31)

BLOCKS = [
    ("Base + Habit", date(2026, 6, 9), date(2026, 7, 31)),
    ("Build", date(2026, 8, 1), date(2026, 9, 30)),
    ("Sharpen", date(2026, 10, 1), date(2026, 11, 15)),
    ("Peak/Attempt", date(2026, 11, 16), date(2026, 12, 31)),
]

PULL_TARGETS = {"Base + Habit": 2, "Build": 4, "Sharpen": 6, "Peak/Attempt": 6}

# Run focus per block (Wednesday quality session).
RUN_FOCUS = {
    "Base + Habit": "Easy + 6x20s strides (heat — keep it short)",
    "Build": "Intro intervals: 5x800m @ threshold",
    "Sharpen": "5k speed: 6x400m @ VO2 pace, 90s jog",
    "Peak/Attempt": "Sub-22 5k time-trial attempt (cool morning)",
}


def block_for(d):
    for name, start, end in BLOCKS:
        if start <= d <= end:
            return name
    return BLOCKS[-1][0] if d > END else BLOCKS[0][0]


def pull_target(block):
    return PULL_TARGETS[block]


def _weekly_template(block, bike_target, long_ride):
    """7 days, bike-first. long_ride is Saturday distance; Tue/Thu ~ fixed."""
    di = "Davis Island AM ride — pull %d of 6 laps" % pull_target(block)
    return [
        {"dow": "Mon", "sport": "swim", "key": False, "desc": "Swim — technique (2x/wk habit)"},
        {"dow": "Tue", "sport": "bike", "key": True, "desc": di},
        {"dow": "Wed", "sport": "run", "key": False, "desc": RUN_FOCUS[block]},
        {"dow": "Thu", "sport": "bike", "key": True, "desc": di},
        {"dow": "Fri", "sport": "swim", "key": False, "desc": "Swim — endurance"},
        {"dow": "Sat", "sport": "bike", "key": True, "desc": "Long ride — %d mi (century build)" % long_ride},
        {"dow": "Sun", "sport": "run", "key": False, "desc": "Easy run / recovery spin / brick"},
    ]


def generate_weeks():
    """Build the full season of weeks with block, bike volume target, and template."""
    first_monday = week_start(START)
    weeks = []
    cur = first_monday
    while cur <= END:
        weeks.append(cur)
        cur += timedelta(days=7)

    vols = bike_weekly_volumes(len(weeks))
    out = []
    for i, ws in enumerate(weeks):
        block = block_for(ws)
        bike_target = vols[i]["target_miles"]
        # Saturday long ride scales with block; Tue+Thu ~66 mi, rest is long+easy.
        long_ride = {"Base + Habit": 55, "Build": 70, "Sharpen": 80, "Peak/Attempt": 50}[block]
        out.append({
            "week_index": i + 1,
            "week_start": ws,
            "block": block,
            "bike_target": bike_target,
            "bike_kind": vols[i]["kind"],
            "days": _weekly_template(block, bike_target, long_ride),
        })
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.12 -m pytest tests/test_periodize.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add periodize.py tests/test_periodize.py
git commit -m "feat: add season periodization and weekly template"
```

---

## Task 7: gating.py — WHOOP recovery gating

**Files:**
- Create: `gating.py`
- Test: `tests/test_gating.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_gating.py`:
```python
from gating import gate_session


def _hard():
    return {"sport": "bike", "key": True, "desc": "Davis Island AM ride — pull 6 of 6 laps"}


def test_green_passes_through():
    g = gate_session(_hard(), recovery=85, sleep_perf=80)
    assert g["adjustment"] == "as_prescribed"


def test_yellow_trims_volume():
    g = gate_session(_hard(), recovery=50, sleep_perf=70)
    assert g["adjustment"] == "trim"
    assert "trim" in g["recommendation"].lower() or "reduce" in g["recommendation"].lower()


def test_red_downgrades_to_easy():
    g = gate_session(_hard(), recovery=25, sleep_perf=70)
    assert g["adjustment"] == "downgrade"
    assert "zone 2" in g["recommendation"].lower() or "easy" in g["recommendation"].lower()


def test_red_plus_poor_sleep_recommends_rest():
    g = gate_session(_hard(), recovery=25, sleep_perf=40)
    assert g["adjustment"] == "rest"


def test_no_recovery_data_is_noop():
    g = gate_session(_hard(), recovery=None, sleep_perf=None)
    assert g["adjustment"] == "no_data"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.12 -m pytest tests/test_gating.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gating'`.

- [ ] **Step 3: Write minimal implementation**

Create `gating.py`:
```python
"""Adaptive recovery gating: WHOOP recovery score adjusts today's prescribed session."""

from analysis import recovery_band

POOR_SLEEP = 50


def gate_session(day, recovery, sleep_perf=None):
    """Return the session with a recovery-adjusted recommendation.

    day: a template-day dict with 'sport', 'key', 'desc'.
    recovery: latest WHOOP recovery score (0-100) or None.
    """
    band = recovery_band(recovery)
    hard = day.get("key") or day.get("sport") == "run"  # key bikes + quality runs

    if band == "unknown":
        return {**day, "adjustment": "no_data",
                "recommendation": day["desc"] + " (no recent WHOOP data — gating off)"}

    if band == "green":
        return {**day, "adjustment": "as_prescribed", "recommendation": day["desc"]}

    if not hard:
        # easy day stays easy regardless of yellow/red
        return {**day, "adjustment": "as_prescribed", "recommendation": day["desc"]}

    if band == "yellow":
        return {**day, "adjustment": "trim",
                "recommendation": "Hold intensity but TRIM volume ~25% (fewer intervals / shorter pulls): " + day["desc"]}

    # red
    if sleep_perf is not None and sleep_perf < POOR_SLEEP:
        return {**day, "adjustment": "rest",
                "recommendation": "Red recovery + poor sleep — REST or mobility only."}
    return {**day, "adjustment": "downgrade",
            "recommendation": "Red recovery — DOWNGRADE to easy Zone 2 (sit in, no pulls / no intervals)."}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.12 -m pytest tests/test_gating.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add gating.py tests/test_gating.py
git commit -m "feat: add WHOOP recovery session gating"
```

---

## Task 8: grading.py — weekly bike-first GPA grade

**Files:**
- Create: `grading.py`
- Test: `tests/test_grading.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_grading.py`:
```python
from grading import grade_week, gpa_to_letter


def test_gpa_to_letter_bands():
    assert gpa_to_letter(4.0) == "A"
    assert gpa_to_letter(3.7) == "A-"
    assert gpa_to_letter(3.3) == "B+"
    assert gpa_to_letter(2.3) == "C+"
    assert gpa_to_letter(0.5) == "F"


def test_perfect_week_is_A():
    week = {
        "bike": {"key_rides_done": 3, "key_rides_planned": 3, "volume_actual": 170, "volume_target": 170, "pulls_done": 6, "pulls_target": 6},
        "swim": {"sessions": 2},
        "run": {"quality_done": True, "hit_pace": True},
        "recovery": {"respected": True, "overreached": False},
    }
    g = grade_week(week)
    assert g["letter"].startswith("A")
    assert g["gpa"] >= 3.85


def test_missed_everything_is_low():
    week = {
        "bike": {"key_rides_done": 0, "key_rides_planned": 3, "volume_actual": 40, "volume_target": 170, "pulls_done": 0, "pulls_target": 6},
        "swim": {"sessions": 0},
        "run": {"quality_done": False, "hit_pace": False},
        "recovery": {"respected": False, "overreached": True},
    }
    g = grade_week(week)
    assert g["gpa"] < 1.5
    assert g["letter"] in ("D", "D-", "F")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.12 -m pytest tests/test_grading.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'grading'`.

- [ ] **Step 3: Write minimal implementation**

Create `grading.py`:
```python
"""Weekly training grade: bike-first GPA composite -> letter with +/-."""

WEIGHTS = {"bike": 0.40, "swim": 0.20, "run": 0.20, "recovery": 0.20}


def _bike_score(b):
    rides = (b["key_rides_done"] / b["key_rides_planned"]) if b["key_rides_planned"] else 0
    vol = min(b["volume_actual"] / b["volume_target"], 1.0) if b["volume_target"] else 0
    pulls = min(b["pulls_done"] / b["pulls_target"], 1.0) if b["pulls_target"] else 0
    # weighted within bike: rides 0.5, volume 0.3, pulls 0.2
    return 4.0 * (0.5 * rides + 0.3 * vol + 0.2 * pulls)


def _swim_score(s):
    return 4.0 * min(s["sessions"] / 2, 1.0)


def _run_score(r):
    if r["quality_done"] and r["hit_pace"]:
        return 4.0
    if r["quality_done"]:
        return 3.0
    return 0.0


def _recovery_score(rec):
    if rec["overreached"]:
        return 1.0
    return 4.0 if rec["respected"] else 2.5


def grade_week(week):
    scores = {
        "bike": _bike_score(week["bike"]),
        "swim": _swim_score(week["swim"]),
        "run": _run_score(week["run"]),
        "recovery": _recovery_score(week["recovery"]),
    }
    gpa = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    return {"gpa": round(gpa, 2), "letter": gpa_to_letter(gpa), "components": scores}


def gpa_to_letter(gpa):
    bands = [
        (3.85, "A"), (3.5, "A-"), (3.15, "B+"), (2.85, "B"), (2.5, "B-"),
        (2.15, "C+"), (1.85, "C"), (1.5, "C-"), (1.15, "D+"), (0.85, "D"),
        (0.5, "D-"),
    ]
    for thresh, letter in bands:
        if gpa >= thresh:
            return letter
    return "F"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.12 -m pytest tests/test_grading.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add grading.py tests/test_grading.py
git commit -m "feat: add weekly bike-first GPA grading"
```

---

## Task 9: clickup.py — ClickUp v2 client with idempotent upsert

**Files:**
- Create: `clickup.py`
- Test: `tests/test_clickup.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_clickup.py` (mocks the network; no real API calls):
```python
import clickup


class FakeResp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.ok = 200 <= status < 300
        self.text = str(payload)

    def json(self):
        return self._payload


def test_creates_task_when_none_exists(monkeypatch):
    calls = {}

    def fake_get(url, headers=None, params=None):
        return FakeResp(200, {"tasks": []})

    def fake_post(url, headers=None, data=None):
        calls["post_url"] = url
        calls["data"] = data
        return FakeResp(200, {"id": "abc", "url": "https://app.clickup.com/t/abc"})

    monkeypatch.setattr(clickup.requests, "get", fake_get)
    monkeypatch.setattr(clickup.requests, "post", fake_post)

    res = clickup.post_or_update_week_task(
        token="pk_x", list_id="123",
        name="Week of Jun 8 — Grade: A-", description="body")
    assert "/list/123/task" in calls["post_url"]
    assert res["url"].endswith("/t/abc")


def test_updates_existing_same_week(monkeypatch):
    calls = {}

    def fake_get(url, headers=None, params=None):
        return FakeResp(200, {"tasks": [{"id": "old", "name": "Week of Jun 8 — Grade: B"}]})

    def fake_put(url, headers=None, data=None):
        calls["put_url"] = url
        return FakeResp(200, {"id": "old", "url": "https://app.clickup.com/t/old"})

    monkeypatch.setattr(clickup.requests, "get", fake_get)
    monkeypatch.setattr(clickup.requests, "put", fake_put)

    res = clickup.post_or_update_week_task(
        token="pk_x", list_id="123",
        name="Week of Jun 8 — Grade: A-", description="body")
    assert "/task/old" in calls["put_url"]


def test_missing_token_skips(monkeypatch):
    res = clickup.post_or_update_week_task(token="", list_id="123",
                                           name="x", description="y")
    assert res["skipped"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.12 -m pytest tests/test_clickup.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'clickup'`.

- [ ] **Step 3: Write minimal implementation**

Create `clickup.py`:
```python
"""Minimal ClickUp v2 client for posting the weekly grade task (idempotent)."""

import json
import requests

API = "https://api.clickup.com/api/v2"


def _week_prefix(name):
    """'Week of Jun 8' — used to match an existing task for the same week."""
    return name.split("—")[0].strip()


def post_or_update_week_task(token, list_id, name, description):
    """Create the weekly grade task, or update it if one for the same week exists."""
    if not token or not list_id:
        return {"skipped": True, "reason": "missing CLICKUP_API_TOKEN or CLICKUP_LIST_ID"}

    headers = {"Authorization": token, "Content-Type": "application/json"}
    prefix = _week_prefix(name)

    existing = requests.get(f"{API}/list/{list_id}/task", headers=headers,
                            params={"archived": "false"})
    if existing.ok:
        for t in existing.json().get("tasks", []):
            if t.get("name", "").startswith(prefix):
                put = requests.put(f"{API}/task/{t['id']}", headers=headers,
                                   data=json.dumps({"name": name, "description": description}))
                if put.ok:
                    return {"skipped": False, "updated": True, **put.json()}
                return {"skipped": False, "error": put.text}

    post = requests.post(f"{API}/list/{list_id}/task", headers=headers,
                         data=json.dumps({"name": name, "description": description}))
    if post.ok:
        return {"skipped": False, "updated": False, **post.json()}
    return {"skipped": False, "error": post.text}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.12 -m pytest tests/test_clickup.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add clickup.py tests/test_clickup.py
git commit -m "feat: add idempotent ClickUp weekly task client"
```

---

## Task 10: fetch.py — widen to multi-sport

**Files:**
- Modify: `fetch.py:26` (the `CYCLING_TYPES` set and the filter)

- [ ] **Step 1: Update the type set**

In `fetch.py`, replace:
```python
CYCLING_TYPES = {"Ride", "VirtualRide", "EBikeRide"}
```
with:
```python
ACTIVITY_TYPES = {"Ride", "VirtualRide", "EBikeRide", "Run", "Swim"}
```

- [ ] **Step 2: Update the filter and messages in `main()`**

Replace the filtering block in `main()`:
```python
    cycling = [a for a in all_activities if a.get("type") in CYCLING_TYPES]

    print(f"\nTotal activities fetched : {len(all_activities)}")
    print(f"Cycling activities found : {len(cycling)}")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(cycling, f, indent=2)
```
with:
```python
    kept = [a for a in all_activities if a.get("type") in ACTIVITY_TYPES]

    print(f"\nTotal activities fetched : {len(all_activities)}")
    print(f"Run/Swim/Bike kept       : {len(kept)}")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(kept, f, indent=2)
```

- [ ] **Step 3: Run it against the live API**

Run: `py -3.12 fetch.py`
Expected: prints a total and a "Run/Swim/Bike kept" count > the old cycling-only count; `activities.json` rewritten.

- [ ] **Step 4: Sanity-check the output contains all three sports**

Run: `py -3.12 -c "import json,collections; print(collections.Counter(a['type'] for a in json.load(open('activities.json'))))"`
Expected: a Counter showing Ride/VirtualRide plus Run and Swim entries.

- [ ] **Step 5: Commit**

```bash
git add fetch.py
git commit -m "feat: fetch runs and swims, not just cycling"
```

---

## Task 11: whoop_fetch.py — pull WHOOP v2 data

**Files:**
- Create: `whoop_fetch.py`

- [ ] **Step 1: Write the module**

Create `whoop_fetch.py`:
```python
"""Fetch WHOOP recovery, sleep, and cycle (strain) data via the v2 API -> whoop.json.

Auto-refreshes the WHOOP token if expired. Usage: py -3.12 whoop_fetch.py
"""

import os
import json
import time

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


def main():
    if not ACCESS_TOKEN:
        print("ERROR: no WHOOP token. Run whoop_auth.py first.")
        return
    refresh_if_needed()

    recovery = _get("/v2/recovery", limit=30)
    sleep = _get("/v2/activity/sleep", limit=30)
    cycles = _get("/v2/cycle", limit=30)

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

    out = {"recovery": norm, "cycles": cycles, "fetched_at": int(time.time())}
    with open(OUTPUT_FILE, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Saved {len(norm)} recovery records to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it against the live API**

Run: `py -3.12 whoop_fetch.py`
Expected: "Saved N recovery records to ...whoop.json"; `whoop.json` created.

- [ ] **Step 3: Verify normalized shape**

Run: `py -3.12 -c "import json; d=json.load(open('whoop.json')); print(d['recovery'][0])"`
Expected: a dict with `date`, `recovery`, `rhr`, `hrv`, `sleep_perf`.

- [ ] **Step 4: Commit**

```bash
git add whoop_fetch.py
git commit -m "feat: fetch WHOOP v2 recovery/sleep/strain to whoop.json"
```

---

## Task 12: plan.py — replace with multi-sport orchestrator

**Files:**
- Replace: `plan.py`

- [ ] **Step 1: Replace plan.py**

Overwrite `plan.py` entirely:
```python
"""Generate the multi-sport 2026 training plan (Jun 9 - Dec 31).

Loads activities.json + whoop.json, runs analysis, prints the season schedule,
recovery-gated next session, and the goal scorecard. Saves training_plan.txt.

Usage: py -3.12 plan.py
"""

import os
import json
from datetime import date

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
    # Run
    if sc["run"]["best"]:
        status = "ON TRACK" if sc["run"]["gap"] is not None and sc["run"]["gap"] <= 0 else "BUILDING"
        print(f"  5k sub-22 : best {_fmt_pace(sc['run']['best'])}  (need -{int(max(sc['run']['gap'],0))}s)  [{status}]")
    else:
        print("  5k sub-22 : insufficient run data")
    # Swim
    s = sc["swim"]
    print(f"  Swim 2x/wk: hit {s['weeks_hit_target']} of last {s['total_weeks']} weeks")
    # Bike
    b = sc["bike"]
    print(f"  Bike      : {b['weekly_avg_4wk']:.0f} mi/wk (4wk)  | longest {b['longest_miles']:.0f} mi  | DI rides {b['di_count']} @ {b['di_avg_speed']:.1f} mph")
    # Recovery
    if sc["recovery"]["has_data"]:
        lat = sc["recovery"]["latest"]
        print(f"  Recovery  : latest {lat['recovery']}% ({lat['band']})  | 7d avg {sc['recovery']['trend_7d_avg']:.0f}%")
    else:
        print("  Recovery  : no WHOOP data")


def print_today(weeks, sc, today):
    week = next((w for w in weeks if w["week_start"] <= today < w["week_start"].replace()
                 or (w["week_start"] <= today)), weeks[0])
    # find the day matching today's weekday
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
```

- [ ] **Step 2: Fix the `print_today` week selection (simplify)**

Replace the `week` selection line in `print_today` with a clean version:
```python
    from common import week_start
    tws = week_start(today)
    week = next((w for w in weeks if w["week_start"] == tws), weeks[0])
```

- [ ] **Step 3: Run it end-to-end**

Run: `py -3.12 plan.py`
Expected: prints GOAL SCORECARD (5k best ~22:47, swim weeks hit, bike DI rides ~2, recovery ~latest %), a TODAY section with a recovery-gated recommendation, and "Plan saved to ...training_plan.txt".

- [ ] **Step 4: Verify the saved plan spans the season**

Run: `py -3.12 -c "t=open('training_plan.txt',encoding='utf-8').read(); print('Peak/Attempt' in t, t.count('Week '))"`
Expected: `True 29` (29 weeks, all four blocks present).

- [ ] **Step 5: Commit**

```bash
git add plan.py
git commit -m "feat: replace plan.py with multi-sport orchestrator"
```

---

## Task 13: grade.py — compute weekly grade and post to ClickUp

**Files:**
- Create: `grade.py`

- [ ] **Step 1: Write the module**

Create `grade.py`:
```python
"""Compute last week's training grade and post it to ClickUp.

Usage: py -3.12 grade.py   (also run automatically Sunday nights — see Task 15)
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

    # recovery: did any red day get followed by a hard effort? (overreach proxy)
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
            "pulls_done": pulls_target if len(key_bikes) >= 2 else 0,  # proxy: did the DI rides
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

    # Save locally first so the grade is never lost.
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
```

- [ ] **Step 2: Run it (posts the most recent completed week to ClickUp)**

Run: `py -3.12 grade.py`
Expected: prints `Week of <date> — Grade: <letter> (GPA x.xx)` and `Posted to ClickUp: https://app.clickup.com/t/...`.

- [ ] **Step 3: Verify the task in ClickUp**

Run: `py -3.12 -c "import os,requests; from dotenv import load_dotenv; load_dotenv(); h={'Authorization':os.getenv('CLICKUP_API_TOKEN')}; r=requests.get(f\"https://api.clickup.com/api/v2/list/{os.getenv('CLICKUP_LIST_ID')}/task\",headers=h); print([t['name'] for t in r.json()['tasks']])"`
Expected: list includes a `Week of ... — Grade: ...` task.

- [ ] **Step 4: Commit**

```bash
git add grade.py
git commit -m "feat: compute weekly grade and post to ClickUp"
```

---

## Task 14: excel.py — multi-sport workbook

**Files:**
- Replace: `excel.py`

- [ ] **Step 1: Replace excel.py**

Overwrite `excel.py`:
```python
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
    ws.set_column(0, 0, 10)
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
```

- [ ] **Step 2: Run it**

Run: `py -3.12 excel.py`
Expected: "Saved ...training_plan.xlsx".

- [ ] **Step 3: Verify the workbook opens and has both sheets**

Run: `py -3.12 -c "import zipfile; z=zipfile.ZipFile('training_plan.xlsx'); print('xl/worksheets/sheet1.xml' in z.namelist(), 'xl/worksheets/sheet2.xml' in z.namelist())"`
Expected: `True True`.

- [ ] **Step 4: Commit**

```bash
git add excel.py
git commit -m "feat: replace excel export with multi-sport schedule and scorecard"
```

---

## Task 15: Sunday-night scheduled grade post (Windows Task Scheduler)

**Files:**
- Create: `run_grade.cmd`

- [ ] **Step 1: Create the launcher script**

Create `run_grade.cmd`:
```bat
@echo off
cd /d "%~dp0"
py -3.12 fetch.py
py -3.12 whoop_fetch.py
py -3.12 grade.py
```

- [ ] **Step 2: Register the scheduled task (Sunday 21:00)**

Run (PowerShell):
```powershell
schtasks /Create /TN "StravaPlan Weekly Grade" /TR "\"c:\Users\hrber\kvi_archive_apps\strava-plan\run_grade.cmd\"" /SC WEEKLY /D SUN /ST 21:00 /F
```
Expected: "SUCCESS: The scheduled task ... has successfully been created."

- [ ] **Step 3: Test the task end-to-end immediately**

Run: `schtasks /Run /TN "StravaPlan Weekly Grade"`
Expected: the task runs; within ~30s a fresh `Week of ... — Grade: ...` task appears/updates in the ClickUp "Weekly Grades" list.

- [ ] **Step 4: Confirm registration**

Run: `schtasks /Query /TN "StravaPlan Weekly Grade" /V /FO LIST`
Expected: shows Schedule Type Weekly, Day Sunday, Start Time 21:00.

- [ ] **Step 5: Commit**

```bash
git add run_grade.cmd
git commit -m "chore: add Sunday-night scheduled weekly grade runner"
```

---

## Task 16: Full regression + README note

**Files:**
- Modify: `README.md` (create if absent)

- [ ] **Step 1: Run the full test suite**

Run: `py -3.12 -m pytest -q`
Expected: all tests pass (common, analysis, volume, periodize, gating, grading, clickup).

- [ ] **Step 2: Run the full data pipeline**

Run: `py -3.12 fetch.py; py -3.12 whoop_fetch.py; py -3.12 plan.py; py -3.12 excel.py`
Expected: each completes; `activities.json`, `whoop.json`, `training_plan.txt`, `training_plan.xlsx` all refreshed.

- [ ] **Step 3: Write a short README**

Create/replace `README.md`:
```markdown
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
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add README for multi-sport plan"
```

---

## Self-Review Notes

- **Spec coverage:** fetch multi-sport (T10), WHOOP v2 fetch (T11), per-sport + recovery analysis (T2–4), bike volume model 170/≤10%/225/3-up-1-down (T5), periodization + weekly template + pull progression (T6), adaptive gating green/yellow/red + rest (T7), bike-first GPA grade (T8), ClickUp idempotent post (T9), grade orchestrator with local-save fallback (T13), Sunday-night schedule (T15), excel scorecard (T14). All spec sections map to a task.
- **Graceful degradation:** missing `whoop.json` → gating no-ops (T7 `no_data` + plan handles empty); missing ClickUp creds → grade saved locally, post skipped (T9/T13).
- **The ≤10% rule** is enforced build-week-to-build-week with deload bounce-back exempt — encoded in `volume.py` and asserted in `tests/test_volume.py`.
