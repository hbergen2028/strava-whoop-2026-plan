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
