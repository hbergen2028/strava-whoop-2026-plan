from grading import grade_week, gpa_to_letter


def test_gpa_to_letter_bands():
    assert gpa_to_letter(4.0) == "A"
    assert gpa_to_letter(3.7) == "A-"
    assert gpa_to_letter(3.3) == "B+"
    assert gpa_to_letter(2.3) == "C+"
    assert gpa_to_letter(0.5) == "D-"


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
