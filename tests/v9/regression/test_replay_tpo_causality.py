"""Regression: historical replay may use TPO only after row availability."""
from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "maximized_replay_tpo_test",
    ROOT / "scripts" / "replay_maximized_opportunity.py")
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def test_tpo_level_not_visible_before_created_at():
    day = dt.date(2026, 7, 7)
    nominal = dt.datetime(2026, 7, 7, 9, 30)
    available = dt.datetime(2026, 7, 7, 12, 30)
    snapshots = {
        day: [(nominal, available, 100.0, 110.0, 90.0)]
    }
    prior = (105.0, 95.0)

    before = MOD.tpo_levels_at(
        day, dt.datetime(2026, 7, 7, 10, 0), snapshots, prior)
    after = MOD.tpo_levels_at(
        day, dt.datetime(2026, 7, 7, 13, 0), snapshots, prior)

    assert before == (105.0, 95.0, "prior_value")
    assert after == (110.0, 90.0, "developing_tpo")
