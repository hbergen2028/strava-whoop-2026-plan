"""Season periodization: blocks, week generation, weekly template, pull progression."""

from datetime import date, timedelta

from common import week_start
from volume import bike_weekly_volumes

START = date(2026, 6, 9)
END = date(2026, 12, 31)

BLOCKS = [
    ("Base + Habit", date(2026, 6, 9), date(2026, 7, 31)),
    ("Build", date(2026, 8, 1), date(2026, 9, 30)),
    ("Sharpen", date(2026, 10, 1), date(2026, 11, 15)),
    ("Peak/Attempt", date(2026, 11, 16), date(2026, 12, 31)),
]

PULL_TARGETS = {"Base + Habit": 2, "Build": 4, "Sharpen": 6, "Peak/Attempt": 6}

# Run focus per block (Wednesday quality session).
RUN_FOCUS = {
    "Base + Habit": "Easy + 6x20s strides (heat — keep it short)",
    "Build": "Intro intervals: 5x800m @ threshold",
    "Sharpen": "5k speed: 6x400m @ VO2 pace, 90s jog",
    "Peak/Attempt": "Sub-22 5k time-trial attempt (cool morning)",
}


def block_for(d):
    for name, start, end in BLOCKS:
        if start <= d <= end:
            return name
    return BLOCKS[-1][0] if d > END else BLOCKS[0][0]


def pull_target(block):
    return PULL_TARGETS[block]


def _weekly_template(block, bike_target, long_ride):
    """7 days, bike-first. long_ride is Saturday distance; Tue/Thu ~ fixed."""
    di = "Davis Island AM ride — pull %d of 6 laps" % pull_target(block)
    return [
        {"dow": "Mon", "sport": "swim", "key": False, "desc": "Swim — technique (2x/wk habit)"},
        {"dow": "Tue", "sport": "bike", "key": True, "desc": di},
        {"dow": "Wed", "sport": "run", "key": False, "desc": RUN_FOCUS[block]},
        {"dow": "Thu", "sport": "bike", "key": True, "desc": di},
        {"dow": "Fri", "sport": "swim", "key": False, "desc": "Swim — endurance"},
        {"dow": "Sat", "sport": "bike", "key": True, "desc": "Long ride — %d mi (century build)" % long_ride},
        {"dow": "Sun", "sport": "run", "key": False, "desc": "Easy run / recovery spin / brick"},
    ]


def generate_weeks():
    """Build the full season of weeks with block, bike volume target, and template."""
    first_monday = week_start(START)
    weeks = []
    cur = first_monday
    while cur <= END:
        weeks.append(cur)
        cur += timedelta(days=7)

    vols = bike_weekly_volumes(len(weeks))
    out = []
    for i, ws in enumerate(weeks):
        block = block_for(ws)
        bike_target = vols[i]["target_miles"]
        # Saturday long ride scales with block; Tue+Thu ~66 mi, rest is long+easy.
        long_ride = {"Base + Habit": 55, "Build": 70, "Sharpen": 80, "Peak/Attempt": 50}[block]
        out.append({
            "week_index": i + 1,
            "week_start": ws,
            "block": block,
            "bike_target": bike_target,
            "bike_kind": vols[i]["kind"],
            "days": _weekly_template(block, bike_target, long_ride),
        })
    return out
