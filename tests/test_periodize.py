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
