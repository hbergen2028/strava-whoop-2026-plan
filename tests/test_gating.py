from gating import gate_session


def _hard():
    return {"sport": "bike", "key": True, "desc": "Davis Island AM ride — pull 6 of 6 laps"}


def test_green_passes_through():
    g = gate_session(_hard(), recovery=85, sleep_perf=80)
    assert g["adjustment"] == "as_prescribed"


def test_yellow_trims_volume():
    g = gate_session(_hard(), recovery=50, sleep_perf=70)
    assert g["adjustment"] == "trim"
    assert "trim" in g["recommendation"].lower() or "reduce" in g["recommendation"].lower()


def test_red_downgrades_to_easy():
    g = gate_session(_hard(), recovery=25, sleep_perf=70)
    assert g["adjustment"] == "downgrade"
    assert "zone 2" in g["recommendation"].lower() or "easy" in g["recommendation"].lower()


def test_red_plus_poor_sleep_recommends_rest():
    g = gate_session(_hard(), recovery=25, sleep_perf=40)
    assert g["adjustment"] == "rest"


def test_no_recovery_data_is_noop():
    g = gate_session(_hard(), recovery=None, sleep_perf=None)
    assert g["adjustment"] == "no_data"


def _ftp_test():
    return {"sport": "bike", "key": True, "ftp_test": True,
            "desc": "Zwift FTP test — maximal effort, sets zones for the next 6 weeks"}


def test_ftp_test_on_yellow_postpones_rather_than_trims():
    """A trimmed test is invalid — a sub-maximal number would set wrong zones."""
    g = gate_session(_ftp_test(), recovery=50, sleep_perf=70)
    assert g["adjustment"] == "postpone"
    assert "postpone" in g["recommendation"].lower()


def test_ftp_test_on_red_postpones():
    g = gate_session(_ftp_test(), recovery=25, sleep_perf=70)
    assert g["adjustment"] == "postpone"


def test_ftp_test_on_red_plus_poor_sleep_postpones_not_rest():
    g = gate_session(_ftp_test(), recovery=25, sleep_perf=40)
    assert g["adjustment"] == "postpone"


def test_ftp_test_on_green_proceeds_as_prescribed():
    g = gate_session(_ftp_test(), recovery=85, sleep_perf=80)
    assert g["adjustment"] == "as_prescribed"


def test_ordinary_key_bike_on_yellow_still_trims():
    """The postpone branch must not swallow normal key-ride gating."""
    g = gate_session(_hard(), recovery=50, sleep_perf=70)
    assert g["adjustment"] == "trim"
