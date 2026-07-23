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
