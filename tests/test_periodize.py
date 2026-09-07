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


# --- FTP test scheduling (every 6 weeks from Tue 2026-09-15) ---

def test_ftp_test_dates_every_six_weeks_within_season():
    from periodize import ftp_test_dates, END
    dates = ftp_test_dates()
    assert dates == [date(2026, 9, 15), date(2026, 10, 27), date(2026, 12, 8)]
    assert all(d <= END for d in dates)


def test_ftp_test_dates_are_all_tuesdays():
    """The test occupies the Tuesday Zwift slot, which counts as a key ride."""
    from periodize import ftp_test_dates
    assert all(d.weekday() == 1 for d in ftp_test_dates())


def _week(ws):
    return next(w for w in generate_weeks() if w["week_start"] == ws)


def _tuesday(week):
    return next(d for d in week["days"] if d["dow"] == "Tue")


def test_ftp_test_week_replaces_the_tuesday_session():
    """Week of Mon Sep 14 contains the Tue Sep 15 test."""
    tue = _tuesday(_week(date(2026, 9, 14)))
    assert tue["ftp_test"] is True
    assert "FTP" in tue["desc"]
    assert tue["sport"] == "bike" and tue["key"] is True


def test_non_test_week_keeps_davis_island_tuesday():
    tue = _tuesday(_week(date(2026, 9, 21)))
    assert not tue.get("ftp_test")
    assert "Davis Island" in tue["desc"]


def test_ftp_test_week_still_has_three_key_bikes():
    """The test occupies a key slot rather than adding a fourth."""
    days = _week(date(2026, 9, 14))["days"]
    assert sum(1 for d in days if d["sport"] == "bike" and d["key"]) == 3


def test_every_scheduled_ftp_date_appears_in_its_week():
    from periodize import ftp_test_dates
    from common import week_start
    for d in ftp_test_dates():
        tue = _tuesday(_week(week_start(d)))
        assert tue["ftp_test"] is True, f"no FTP session scheduled for {d}"
