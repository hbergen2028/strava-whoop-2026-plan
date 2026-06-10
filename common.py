"""Shared constants and date helpers for the multi-sport training tool."""

from datetime import datetime, date, timedelta

M_TO_MILES = 1 / 1609.34
MS_TO_MPH = 2.23694
M_TO_FEET = 3.28084


def parse_dt(raw: str) -> datetime:
    """Parse an ISO-8601 timestamp (with optional trailing Z) to naive datetime."""
    return datetime.strptime(raw[:19], "%Y-%m-%dT%H:%M:%S")


def week_start(d: date) -> date:
    """Monday of the week containing d."""
    return d - timedelta(days=d.weekday())
