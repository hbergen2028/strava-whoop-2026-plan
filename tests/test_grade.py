from datetime import date, timedelta

import grade


def _label(y, m, d):
    ws = date(y, m, d)
    return grade._week_label(ws, ws + timedelta(days=6))


def test_label_within_one_month():
    assert _label(2026, 7, 13) == "Jul 13 to 19"


def test_label_spanning_two_months():
    assert _label(2026, 6, 29) == "Jun 29 to Jul 05"


def test_label_end_is_sunday_not_next_monday():
    """The graded week is Mon-Sun; the label must not run to the next Monday."""
    ws = date(2026, 7, 13)
    we = ws + timedelta(days=6)
    assert we.weekday() == 6 and we.day == 19
    assert "20" not in grade._week_label(ws, we)


def test_label_days_are_zero_padded():
    """Padding keeps 'Week of Jul 01' from prefix-matching 'Week of Jul 13'."""
    assert _label(2026, 6, 1) == "Jun 01 to 07"


# --- key-ride detection (week of Mon 2026-08-31: Tue=09-01, Thu=09-03, Sat=09-05) ---

WS = date(2026, 8, 31)


def _ride(day, hour, virtual=False, miles=20):
    return {"type": "VirtualRide" if virtual else "Ride",
            "start_date_local": f"{day}T{hour:02d}:00:00",
            "distance": miles * 1609.34, "moving_time": 3600, "name": "ride"}


def _key_rides(*raw):
    from analysis import parse_activities
    return grade.summarize_week(parse_activities(list(raw)), [], WS)["bike"]["key_rides_done"]


def test_tuesday_zwift_after_7am_counts_as_key_ride():
    """Zwift has no dawn group-ride constraint, so the hour cutoff shouldn't apply."""
    assert _key_rides(_ride("2026-09-01", 9, virtual=True)) == 1


def test_thursday_zwift_after_7am_counts_as_key_ride():
    assert _key_rides(_ride("2026-09-03", 14, virtual=True)) == 1


def test_tuesday_outdoor_after_7am_is_still_not_a_key_ride():
    """Outdoor rides keep the pre-07:00 Davis Island cutoff."""
    assert _key_rides(_ride("2026-09-01", 9)) == 0


def test_tuesday_outdoor_before_7am_still_counts():
    assert _key_rides(_ride("2026-09-01", 5)) == 1


def test_monday_zwift_is_not_a_key_ride():
    """Monday is a swim day — no bike slot exists to fill."""
    assert _key_rides(_ride("2026-08-31", 9, virtual=True)) == 0


def test_saturday_ride_counts_at_any_hour_as_before():
    assert _key_rides(_ride("2026-09-05", 10)) == 1
