"""Bike weekly volume model: anchor, <=10% build-to-build cap, ceiling, 3-up/1-down."""

ANCHOR = 170.0
CAP_PCT = 0.10
CEILING = 225.0
RECOVERY_FRAC = 0.78


def bike_weekly_volumes(num_weeks, anchor=ANCHOR, cap_pct=CAP_PCT,
                        ceiling=CEILING, recovery_frac=RECOVERY_FRAC):
    """Return a list of {week_index, target_miles, kind} for num_weeks weeks.

    kind is one of: anchor, build, ceiling, recovery.
    The <=10% cap applies build-week to build-week; recovery weeks (every 4th)
    step down and are exempt, as is the bounce-back week after them.
    """
    out = []
    prebuild = anchor
    for i in range(num_weeks):
        wk = i + 1
        if wk % 4 == 0:
            target = round(prebuild * recovery_frac)
            kind = "recovery"
        elif wk == 1:
            target = round(anchor)
            kind = "anchor"
            prebuild = target
        else:
            cand = min(prebuild * (1 + cap_pct), ceiling)
            target = round(cand)
            kind = "ceiling" if target >= ceiling else "build"
            prebuild = target
        out.append({"week_index": wk, "target_miles": target, "kind": kind})
    return out
