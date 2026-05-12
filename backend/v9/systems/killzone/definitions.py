"""Killzone definitions — 8 time zones per spec.

All times ET. Pure functions, no clock reads inside.
"""
from datetime import time, datetime, timedelta
from typing import Dict, Optional, Tuple
import pytz

ET = pytz.timezone('America/New_York')

KILLZONES = [
    # (name, start_hh_mm, end_hh_mm, edge_class)
    ("ASIA",         (18, 0),  (3, 0),   "low"),
    ("LONDON",       (3, 0),   (8, 0),   "medium"),
    ("NY_PREMARKET", (8, 0),   (9, 30),  "medium"),
    ("NY_OPEN",      (9, 30),  (11, 30), "high"),
    ("MIDDAY",       (11, 30), (13, 30), "low"),
    ("NY_PM",        (13, 30), (16, 0),  "medium"),
    ("POST_MARKET",  (16, 0),  (17, 0),  "low"),
    ("CLOSED",       (17, 0),  (18, 0),  "none"),
]


def _to_minutes(hh_mm: Tuple[int, int]) -> int:
    return hh_mm[0] * 60 + hh_mm[1]


def _now_minutes(now_et: datetime) -> int:
    return now_et.hour * 60 + now_et.minute


def _in_range(now_min: int, start_min: int, end_min: int) -> bool:
    """Check if now is in [start, end), handling midnight wraparound."""
    if start_min < end_min:
        return start_min <= now_min < end_min
    else:  # wraps midnight (e.g. ASIA 18:00 -> 03:00)
        return now_min >= start_min or now_min < end_min


def _minutes_until(now_min: int, target_min: int) -> int:
    """Minutes from now until target, wrapping at 24h."""
    diff = target_min - now_min
    if diff < 0:
        diff += 24 * 60
    return diff


def current_killzone(now_et: datetime) -> Dict:
    """Return current zone info based on ET time."""
    now_min = _now_minutes(now_et)

    # Weekend check
    wd = now_et.weekday()
    if (wd == 4 and now_min >= _to_minutes((17, 0))) or wd == 5 or (wd == 6 and now_min < _to_minutes((18, 0))):
        return {
            "name": "WEEKEND",
            "edge_class": "none",
            "started_at_et": None,
            "ends_at_et": None,
            "minutes_remaining": 0,
        }

    for name, start, end, edge in KILLZONES:
        s_min = _to_minutes(start)
        e_min = _to_minutes(end)
        if _in_range(now_min, s_min, e_min):
            remaining = _minutes_until(now_min, e_min)
            return {
                "name": name,
                "edge_class": edge,
                "started_at_et": f"{start[0]:02d}:{start[1]:02d}",
                "ends_at_et": f"{end[0]:02d}:{end[1]:02d}",
                "minutes_remaining": remaining,
            }

    return {"name": "UNKNOWN", "edge_class": "none", "started_at_et": None, "ends_at_et": None, "minutes_remaining": 0}


def next_killzone(now_et: datetime) -> Dict:
    """Return next zone and minutes until it starts."""
    now_min = _now_minutes(now_et)

    # Find current zone index
    current_idx = -1
    for i, (name, start, end, edge) in enumerate(KILLZONES):
        if _in_range(now_min, _to_minutes(start), _to_minutes(end)):
            current_idx = i
            break

    next_idx = (current_idx + 1) % len(KILLZONES) if current_idx >= 0 else 0
    next_name, next_start, _, next_edge = KILLZONES[next_idx]
    mins = _minutes_until(now_min, _to_minutes(next_start))

    return {
        "name": next_name,
        "edge_class": next_edge,
        "starts_in_minutes": mins,
    }
