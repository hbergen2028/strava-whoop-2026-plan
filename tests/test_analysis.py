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
    # best 5k-equivalent seconds should be near 22:45 (1365s), within 25s
    assert abs(r["best_5k_sec"] - 1365) < 25
    # derived paces: vo2 faster than threshold faster than easy
    assert r["paces"]["vo2_sec_per_mi"] < r["paces"]["threshold_sec_per_mi"] < r["paces"]["easy_sec_per_mi"]


from analysis import analyze_swim, analyze_bike


def _act(typ, d, miles, minutes, hour=6, speed_ms=8.9):
    return {"type": typ, "start_date_local": f"{d}T{hour:02d}:00:00",
            "distance": miles * 1609.34, "moving_time": int(minutes * 60),
            "average_speed": speed_ms}


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
