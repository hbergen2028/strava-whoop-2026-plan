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


# --- swim count comes from WHOOP, not Strava ---

def _swim_raw(day):
    return {"type": "Swim", "start_date_local": f"{day}T13:00:00",
            "distance": 1372, "moving_time": 1260, "name": "swim"}


def _whoop_swim(day):
    return {"date": day, "sport": "swimming", "start": day + "T13:00:00.000Z", "strain": 7.7}


def _summary(raw_acts, workouts):
    from analysis import parse_activities
    return grade.summarize_week(parse_activities(raw_acts), [], WS, workouts=workouts)


def test_swims_are_counted_from_whoop_workouts():
    s = _summary([], [_whoop_swim("2026-09-01"), _whoop_swim("2026-09-04")])
    assert s["swim"]["sessions"] == 2


def test_strava_swim_without_whoop_record_does_not_count():
    """WHOOP is the source of truth, so a Strava-only swim is not a second session."""
    s = _summary([_swim_raw("2026-09-01")], [_whoop_swim("2026-09-01")])
    assert s["swim"]["sessions"] == 1


def test_whoop_swims_outside_the_graded_week_are_ignored():
    s = _summary([], [_whoop_swim("2026-08-30"), _whoop_swim("2026-09-02")])
    assert s["swim"]["sessions"] == 1


def test_missing_workout_data_falls_back_to_strava_rather_than_scoring_zero():
    """An absent workouts key must not silently zero the swim score."""
    s = _summary([_swim_raw("2026-09-01"), _swim_raw("2026-09-03")], None)
    assert s["swim"]["sessions"] == 2


# --- choosing which week to grade ---

def test_target_week_defaults_to_last_completed_week():
    assert grade._target_week(date(2026, 10, 4)) == date(2026, 9, 21)


def test_target_week_accepts_an_explicit_monday():
    """Lets a finished week be graded before the scheduler would reach it."""
    assert grade._target_week(date(2026, 10, 4), "2026-09-28") == date(2026, 9, 28)


def test_target_week_rejects_a_non_monday():
    """Weeks run Mon-Sun; a mid-week start would silently grade a shifted window."""
    try:
        grade._target_week(date(2026, 10, 4), "2026-09-30")
    except ValueError as e:
        assert "Monday" in str(e)
    else:
        raise AssertionError("expected ValueError for a non-Monday week start")
