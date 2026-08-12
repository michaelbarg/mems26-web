"""F6b (2026-08-12) — zlr_detected must be STICKY per bar, not last-write-wins.

S4-audit Finding B: the DLL raises zlr_detected on a MID-BAR push
(Mechanism-C), but post_woodies_5min INSERT-OR-REPLACEs the row on EVERY push,
so the final push (zlr=0) erased the earlier 1 — 2026-08-10 the table said
"0 DLL-ZLR bars" while the decision log held 17 live ZLR signals.

Unit-tests the production _sticky_zlr helper with the DB read patched — NO
database writes (an endpoint-level version of this test was rejected because
without the conftest DB redirect it reaches the real Postgres; that is the
exact "pytest fixture rows" leak class the 2026-08-11 audit had to scrub).
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

import backend.v9.db.read as db_read  # noqa: E402
from backend.v9.api.v9.bars import _sticky_zlr  # noqa: E402

_TS = "2026-08-10T14:40:00+00:00"


def test_later_push_cannot_erase_stored_zlr(monkeypatch):
    calls = []

    def fake_read_one(sql, params=None):
        calls.append((sql, params))
        return {"zlr_detected": 1, "zlr_direction": "LONG"}

    monkeypatch.setattr(db_read, "read_one", fake_read_one)
    flag, direction = _sticky_zlr(_TS, 0, None)
    assert (flag, direction) == (1, "LONG"), (
        "a zlr=0 re-push of a bar whose row already holds 1 must keep the 1 "
        "(Finding B last-write-wins)")
    assert calls and calls[0][1] == {"ts": _TS}


def test_incoming_one_never_reads_db(monkeypatch):
    def boom(sql, params=None):
        raise AssertionError("must not read the DB when the push already has zlr=1")

    monkeypatch.setattr(db_read, "read_one", boom)
    assert _sticky_zlr(_TS, 1, "SHORT") == (1, "SHORT")


def test_no_prior_row_stays_zero(monkeypatch):
    monkeypatch.setattr(db_read, "read_one", lambda sql, params=None: None)
    assert _sticky_zlr(_TS, 0, None) == (0, None)


def test_prior_zero_row_stays_zero(monkeypatch):
    monkeypatch.setattr(db_read, "read_one",
                        lambda sql, params=None: {"zlr_detected": 0,
                                                  "zlr_direction": None})
    assert _sticky_zlr(_TS, 0, "NONE") == (0, "NONE")


def test_db_error_fails_open(monkeypatch):
    # read_one itself never raises in production (returns None on error);
    # garbage values must also pass through without raising.
    monkeypatch.setattr(db_read, "read_one",
                        lambda sql, params=None: {"zlr_detected": "garbage"})
    assert _sticky_zlr(_TS, 0, None) == (0, None)
