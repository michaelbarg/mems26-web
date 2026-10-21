# -*- coding: utf-8 -*-
"""CC_ORDER 2026-10-05 17:11 · נתב-דלתון שלב 1 — the automatic supervision.

The §0 lock table was measured 05.10 17:10 on harness_out/t466/t529b_*.json
(65 sessions, the live-config replay, 1 contract). If any lock moves — a day
changes opening/structure, a trade re-buckets, a cent of Σ — this test fails.
Read-only: it calls the pure functions, writes no report, touches no DB.
"""
import glob
import importlib.util
import os

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SCRIPT = os.path.join(ROOT, "scripts", "daily_dalton.py")


def _mod():
    spec = importlib.util.spec_from_file_location("daily_dalton", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def result():
    m = _mod()
    files = glob.glob(m.HARNESS_GLOB)
    assert len(files) == 65, "expected the 65 t529b harness files, found %d at %s" % (len(files), m.HARNESS_GLOB)
    return m, m.compute(m.load_sessions())


def test_all_locks_identical(result):
    m, res = result
    assert m.check_locks(res) == []


def test_headline_lines_verbatim(result):
    m, res = result
    out = m.render(res, []).splitlines()
    assert out[0] == "sessions=65 pnl=2502.40 pos=35 neg=30"
    assert out[1] == "OPEN_REJECTION_REVERSE days=14 pnl=990.0 pos=10"
    assert out[2] == "OPEN_AUCTION_IN days=41 pnl=790.6 pos=19"
    assert out[3] == "OPEN_DRIVE days=10 pnl=721.9 pos=6"


def test_every_trade_matched_a_route(result):
    # 192 harness trades; phase/kind/hour buckets must not contain 'unmatched'
    m, res = result
    for name in ("phase", "kind", "hour"):
        assert "unmatched" not in res[name], (name, res[name].get("unmatched"))
    assert sum(b["n"] for b in res["phase"].values()) == 192


def test_a_moved_lock_is_caught():
    m = _mod()
    res = m.compute(m.load_sessions())
    res["opening"]["OPEN_DRIVE"]["pnl"] += 0.1  # one dime
    assert any(b.startswith("opening OPEN_DRIVE") for b in m.check_locks(res))
