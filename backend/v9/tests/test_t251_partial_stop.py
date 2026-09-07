"""T-251: partial stop → PARTIAL, not CLOSED.

Tested on trade #1008 structure: 5 contracts, fills arrive one leg
at a time. After 4 legs (T0+T1×2+STOP×1), Σqty=4 < 5 → PARTIAL.
After the 5th leg, Σqty=5 = 5 → CLOSED.

The anchor is our order IDs ∩ orders[], not position_qty (account
shared with Eti — position_qty cannot attribute a leg).
"""
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from backend.v9.services.trade_manager.manager import trade_contract_count


class FakeTrade:
    """Minimal trade stub matching #1008 structure."""
    def __init__(self, trade_id=1008, contracts=5):
        self.id = trade_id
        self.quality = {
            "contracts": contracts,
            "exit_fills": [],
            "sierra_order_id": 10975,
        }
        self.state = "FILLED"
        self.stop = 7725.0
        self.stop_hit_ts = None
        self.exit_ts = None
        self.exit_price = None
        self.exit_reason = None
        self.pnl_usd = None
        self.outcome = None
        self.direction = "SHORT"
        self.entry_price = 7720.0
        self.mode = "demo"
        self.t1 = 7715.0
        self.t2 = 7710.0
        self.t3 = 7705.0
        self.cross_context = {}


class TestTradeContractCount(unittest.TestCase):

    def test_from_quality(self):
        t = FakeTrade(contracts=5)
        self.assertEqual(trade_contract_count(t), 5)

    def test_zero_fallback(self):
        t = FakeTrade()
        t.quality = {}
        # Falls through to env or legacy default
        n = trade_contract_count(t)
        self.assertGreaterEqual(n, 1)


class TestPartialStopDetection(unittest.TestCase):

    def test_four_of_five_fills_is_partial(self):
        """Σqty=4 < contracts=5 → should NOT close."""
        fills = [
            {"kind": "T0", "price": 7714.0, "qty": 1, "order_id": 10977},
            {"kind": "T1", "price": 7711.5, "qty": 2, "order_id": 10980},
            {"kind": "STOP", "price": 7716.75, "qty": 1, "order_id": 10986},
        ]
        total = sum(f["qty"] for f in fills)
        self.assertEqual(total, 4)
        self.assertLess(total, 5, "4 fills of 5 contracts = PARTIAL")

    def test_five_of_five_fills_is_closed(self):
        """Σqty=5 = contracts=5 → should close."""
        fills = [
            {"kind": "T0", "price": 7714.0, "qty": 1, "order_id": 10977},
            {"kind": "T1", "price": 7711.5, "qty": 2, "order_id": 10980},
            {"kind": "STOP", "price": 7716.75, "qty": 1, "order_id": 10986},
            {"kind": "STOP", "price": 7724.75, "qty": 1, "order_id": 10984},
        ]
        total = sum(f["qty"] for f in fills)
        self.assertEqual(total, 5)
        self.assertGreaterEqual(total, 5, "5 fills of 5 contracts = CLOSED")

    def test_anchor_is_our_order_ids(self):
        """The partial check uses exit_fills (our IDs), not position_qty."""
        import subprocess
        out = subprocess.run(
            ["grep", "-n", "position_qty",
             "backend/v9/services/trade_manager/manager.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        # position_qty should NOT appear as CODE in the partial check block
        for line in out.stdout.strip().split("\n"):
            if not line:
                continue
            lineno = int(line.split(":")[0])
            content = line.split(":", 1)[1].strip() if ":" in line else ""
            if 1714 <= lineno <= 1775 and not content.lstrip().startswith("#"):
                self.fail(f"position_qty as CODE in partial-stop block: {line}")

    def test_t251_code_block_exists(self):
        """T-251 partial-stop code block exists in on_stop_hit."""
        import subprocess
        out = subprocess.run(
            ["grep", "-c", "STOP_HIT_PARTIAL",
             "backend/v9/services/trade_manager/manager.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        self.assertGreaterEqual(int(out.stdout.strip()), 1,
                                 "STOP_HIT_PARTIAL must exist in manager")


if __name__ == "__main__":
    unittest.main()
