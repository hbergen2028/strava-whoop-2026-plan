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
