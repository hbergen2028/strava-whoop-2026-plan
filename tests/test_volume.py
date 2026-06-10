from volume import bike_weekly_volumes


def test_anchor_and_length():
    vols = bike_weekly_volumes(29)
    assert len(vols) == 29
    assert vols[0]["target_miles"] == 170


def test_build_to_build_cap_10pct():
    vols = bike_weekly_volumes(29)
    builds = [w for w in vols if w["kind"] in ("anchor", "build", "ceiling")]
    for prev, cur in zip(builds, builds[1:]):
        assert cur["target_miles"] <= round(prev["target_miles"] * 1.10) + 0.001


def test_recovery_every_fourth_week_and_lower():
    vols = bike_weekly_volumes(29)
    for i, w in enumerate(vols, start=1):
        if i % 4 == 0:
            assert w["kind"] == "recovery"
            assert w["target_miles"] < vols[i - 2]["target_miles"]


def test_ceiling_not_exceeded():
    vols = bike_weekly_volumes(29)
    assert max(w["target_miles"] for w in vols) <= 225
