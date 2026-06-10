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
