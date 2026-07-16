"""Regression — feed_watchdog must read the LIVE SoT table, not the dead legacy one.

2026-07-16: `_db_max_bar_age` queried `v9_bars_5min` (legacy). That table froze at
07-15 22:55 (stopped being fed after the continuous-bars rewiring), so on 07-16 the
watchdog computed a ~1060min "staleness" from a table nobody writes to and
false-halted EVERY fire (a valid ZLR SHORT was blocked at 16:35 IL while the real
feed, `v9_bars_5min_woodies`, was 1min fresh). Exactly the known SoT failure from
CLAUDE.md §Codebase-Index (2026-06-22). Fixed to `v9_bars_5min_woodies`
(docs/SOURCE_OF_TRUTH.md — the live truth) with Michael's explicit approval.

This test pins the table name so a refactor/merge can't silently revert it.
"""
from unittest import mock


def test_db_max_bar_age_queries_woodies_sot_table():
    captured = {}

    def _capture(sql, *a, **k):
        captured["sql"] = sql
        return None  # -> age None -> caller fails OPEN

    with mock.patch("backend.v9.db.read.read_scalar", side_effect=_capture):
        from backend.v9.services.feed_watchdog import _db_max_bar_age
        assert _db_max_bar_age() is None  # fail-open on None
    sql = captured.get("sql", "")
    assert "v9_bars_5min_woodies" in sql, (
        "feed_watchdog must read the live SoT table v9_bars_5min_woodies; "
        f"got: {sql!r}"
    )
    # the legacy table froze 2026-07-15 — reading it false-halts all fires
    assert "FROM v9_bars_5min " not in sql + " " or "woodies" in sql
