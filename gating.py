"""Adaptive recovery gating: WHOOP recovery score adjusts today's prescribed session."""

from analysis import recovery_band

POOR_SLEEP = 50


def gate_session(day, recovery, sleep_perf=None):
    """Return the session with a recovery-adjusted recommendation.

    day: a template-day dict with 'sport', 'key', 'desc'.
    recovery: latest WHOOP recovery score (0-100) or None.
    """
    band = recovery_band(recovery)
    hard = day.get("key") or day.get("sport") == "run"  # key bikes + quality runs

    if band == "unknown":
        return {**day, "adjustment": "no_data",
                "recommendation": day["desc"] + " (no recent WHOOP data — gating off)"}

    if band == "green":
        return {**day, "adjustment": "as_prescribed", "recommendation": day["desc"]}

    if not hard:
        # easy day stays easy regardless of yellow/red
        return {**day, "adjustment": "as_prescribed", "recommendation": day["desc"]}

    if band == "yellow":
        return {**day, "adjustment": "trim",
                "recommendation": "Hold intensity but TRIM volume ~25% (fewer intervals / shorter pulls): " + day["desc"]}

    # red
    if sleep_perf is not None and sleep_perf < POOR_SLEEP:
        return {**day, "adjustment": "rest",
                "recommendation": "Red recovery + poor sleep — REST or mobility only."}
    return {**day, "adjustment": "downgrade",
            "recommendation": "Red recovery — DOWNGRADE to easy Zone 2 (sit in, no pulls / no intervals)."}
