"""§7 delta pipeline: ts must be in the bars SELECT so delta connects.

The gateway reads bars from v9_bars_5min_woodies and delta from
v9_bars_cumulative_delta. Without ts in the bars SELECT, the delta
map lookup always returns None → shadow measured zero.

This test verifies the bars SELECT includes ts, and that
bars_from_rows can connect delta via the ts key.
"""
import inspect
import unittest


class TestDeltaPipelineTs(unittest.TestCase):

    def test_bars_select_includes_ts(self):
        """The release-gate bars SELECT must include ts."""
        from backend.v9.gateway.trading_gateway import TradingGateway
        source = inspect.getsource(TradingGateway._route_setup_inner)
        # Find the release-gate bars query
        idx = source.find("v9_bars_5min_woodies")
        # There are multiple queries; find the one near "awaiting_release"
        rg_idx = source.find("awaiting_release")
        # The bars query is right after
        bars_query_start = source.find("SELECT", rg_idx)
        if bars_query_start < 0:
            self.fail("Cannot find bars SELECT near awaiting_release")
        bars_query = source[bars_query_start:bars_query_start + 200]
        self.assertIn("ts", bars_query,
                       "Bars SELECT must include ts for delta map lookup. "
                       "Without it, r.get('ts') is always None → delta=None")

    def test_bars_from_rows_connects_delta(self):
        """bars_from_rows with delta_map connects via ts key."""
        from backend.v9.systems.release_gate import bars_from_rows
        from datetime import datetime, timezone

        ts = datetime(2026, 9, 3, 18, 0, tzinfo=timezone.utc)
        rows = [{"ts": ts, "high": 7730, "low": 7718, "close": 7730, "volume": 22284}]
        delta_map = {str(ts): 4130.0}
        bars = bars_from_rows(rows, delta_map=delta_map)
        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0].delta, 4130.0,
                          "Delta must connect through ts key")

    def test_bars_from_rows_no_ts_no_delta(self):
        """Without ts in the row, delta stays None."""
        from backend.v9.systems.release_gate import bars_from_rows

        rows = [{"high": 7730, "low": 7718, "close": 7730, "volume": 22284}]
        delta_map = {"some_ts": 4130.0}
        bars = bars_from_rows(rows, delta_map=delta_map)
        self.assertEqual(len(bars), 1)
        self.assertIsNone(bars[0].delta,
                           "Without ts, delta must be None (honest)")

    def test_mutation_removing_ts_fails(self):
        """MUTATION: removing ts from SELECT → this test fails."""
        from backend.v9.gateway.trading_gateway import TradingGateway
        source = inspect.getsource(TradingGateway._route_setup_inner)
        rg_idx = source.find("awaiting_release")
        bars_q_idx = source.find("SELECT", rg_idx)
        # Extract the SELECT clause (up to FROM)
        from_idx = source.find("FROM", bars_q_idx)
        select_clause = source[bars_q_idx:from_idx]
        self.assertIn("ts", select_clause,
                       "MUTATION: ts removed from SELECT → delta never connects")


if __name__ == "__main__":
    unittest.main()
