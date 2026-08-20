"""T-10 — `pnl_sierra` reconstruction + the books-vs-broker alarm.

Fixtures are the real #749 journal lines and the real ids the backend persisted
for it, so this test fails if either side of the correlation drifts.
"""
import pytest

from backend.v9.services.sierra_pnl_reconcile import (
    divergence_summary, order_index, reconcile, sierra_pnl_by_trade,
)

# --- exactly the lines trade_fills_journal.jsonl holds for entry order 10414 --
JOURNAL_749 = [
    {"kind": "ENTRY", "ts": 1787165406, "order_id": 10414,
     "c1_target_id": 10406, "c1_stop_id": 10407,
     "c2_target_id": 10409, "c2_stop_id": 10410,
     "c3_target_id": 10412, "c3_stop_id": 10413,
     "c4_target_id": 10415, "c4_stop_id": 10416,
     "price": 7737.50, "contracts": 4, "direction": "LONG"},
    {"kind": "T1", "ts": 1787167956, "order_id": 10406, "price": 7740.75, "contracts": 1},
    {"kind": "T3", "ts": 1787167989, "order_id": 10412, "price": 7742.25, "contracts": 1},
    {"kind": "STOP", "ts": 1787168218, "order_id": 10410, "price": 7734.75, "contracts": 1, "group": 2},
    {"kind": "STOP", "ts": 1787168271, "order_id": 10416, "price": 7732.50, "contracts": 1, "group": 4},
]

# --- exactly the ids v9_trades.quality holds for #749 ------------------------
ROW_749 = {
    "id": 749, "mode": "live", "exit_reason": "STOP_FILL", "pnl_usd": -51.25,
    "quality": {"contracts": 4, "sierra_order_id": 10414,
                "c1_target_id": 10406, "c1_stop_id": 10407,
                "c2_target_id": 10409, "c2_stop_id": 10410,
                "c3_target_id": 10412, "c3_stop_id": 10413,
                "c4_target_id": 10415, "c4_stop_id": 10416},
}


class TestCorrelation:
    def test_every_child_order_id_maps_back_to_the_trade(self):
        """No DLL change needed: the books already hold every id the fills use."""
        idx = order_index([ROW_749])
        for f in JOURNAL_749:
            assert idx.get(f["order_id"]) == 749, (
                f"order {f['order_id']} does not resolve to its trade — "
                "the fill would be dropped and pnl_sierra left empty")

    def test_the_fourth_contract_is_not_lost(self):
        """c4's ids were missing from the ledger chain until T-62; that alone
        dropped #749's last stop (1 @ 7732.50 = -$25.00)."""
        idx = order_index([ROW_749])
        assert idx.get(10415) == 749 and idx.get(10416) == 749


class TestSierraPnl:
    def test_749_reconstructs_to_one_twentyfive(self):
        out = sierra_pnl_by_trade(JOURNAL_749, [ROW_749])[749]
        assert out["pnl"] == pytest.approx(1.25)
        assert out["complete"] is True
        assert out["covered"] == 4

    def test_partial_coverage_reports_none_not_a_number(self):
        """Rule 1 — a half-covered trade must NOT get a confident number."""
        partial = [f for f in JOURNAL_749 if f["kind"] in ("ENTRY", "T1")]
        out = sierra_pnl_by_trade(partial, [ROW_749])[749]
        assert out["pnl"] is None
        assert out["complete"] is False
        assert out["covered"] == 1

    def test_uncorrelated_fills_are_dropped_not_guessed(self):
        foreign = [dict(f, order_id=99999) for f in JOURNAL_749]
        assert sierra_pnl_by_trade(foreign, [ROW_749]) == {}


class TestDivergenceAlarm:
    def test_749_is_flagged_divergent_with_the_exact_error(self):
        f = reconcile([ROW_749], fills=JOURNAL_749)[0]
        assert f["status"] == "DIVERGENT"
        assert f["pnl_books"] == pytest.approx(-51.25)
        assert f["pnl_sierra"] == pytest.approx(1.25)
        assert f["delta"] == pytest.approx(-52.50)

    def test_summary_is_not_ok_when_the_books_disagree(self):
        s = divergence_summary([ROW_749], fills=JOURNAL_749)
        assert s["ok"] is False
        assert s["divergent"] == 1
        assert s["worst"]["trade_id"] == 749
        assert s["net_error"] == pytest.approx(-52.50)

    def test_correct_books_reconcile_clean(self):
        good = dict(ROW_749, pnl_usd=1.25)
        s = divergence_summary([good], fills=JOURNAL_749)
        assert s["ok"] is True
        assert s["matched"] == 1
        assert s["net_error"] == pytest.approx(0.0)

    def test_nothing_checked_is_never_reported_as_ok(self):
        """The false-green that shipped during development: db.read fell back to
        a stale SQLite file, 0 rows came back, and the summary said ok=True."""
        s = divergence_summary([], fills=JOURNAL_749)
        assert s["ok"] is None, "0 checked must be 'unknown', never 'fine'"
        assert s["checked"] == 0

        s2 = divergence_summary([ROW_749], fills=[])
        assert s2["ok"] is None and s2["checked"] == 0

    def test_incomplete_coverage_never_counts_as_a_match(self):
        """A trade we cannot verify must not be reported as verified."""
        partial = [f for f in JOURNAL_749 if f["kind"] in ("ENTRY", "T1")]
        s = divergence_summary([ROW_749], fills=partial)
        assert s["incomplete"] == 1 and s["matched"] == 0
        assert s["ok"] is True  # nothing PROVEN wrong …
        assert s["checked"] == 1  # … but it is visible that 1 went unchecked
