# -*- coding: utf-8 -*-
"""T-498 (27.09): the entry-confirm gate (S4_ENTRY_CONFIRM_V1) must test the CLOSED signal bar.

It read "ORDER BY ts DESC LIMIT 15" — the last row of v9_bars_5min_woodies. Live routes run 2–6 s after the bar
boundary while the new bar's row is created 0.8–11 s after it, so the gate sometimes tested a bar that had opened
seconds earlier (open≈close ⇒ within the ATR tolerance ⇒ pass). 25.09 19:25:06: the 19:25 row was created at
19:25:04 ⇒ #2408 passed; the closed 19:20 bar (7800.75 → 7795.00) was bearish ⇒ the replay blocked the same
candidate. Measured value of the gate on closed bars (the harness): OFF ⇒ −197.50$ gross / −218.30$ net over 60
sessions (harness_out/t494, t498ec0 vs live0927)."""
import os
import unittest

SRC = os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend", "v9", "gateway", "trading_gateway.py")


class TestEntryConfirmReadsClosedBars(unittest.TestCase):
    def setUp(self):
        self.src = open(SRC, encoding="utf-8").read()

    def test_query_excludes_the_forming_bar(self):
        i = self.src.index('if os.getenv("S4_ENTRY_CONFIRM_V1", "0")')
        block = self.src[i:i + 2500]
        self.assertIn("WHERE ts + interval '5 minutes' <= now()", block)
        self.assertIn("ORDER BY ts DESC LIMIT 15", block)

    def test_no_unbounded_last_row_read_left_in_the_gate(self):
        i = self.src.index('if os.getenv("S4_ENTRY_CONFIRM_V1", "0")')
        block = self.src[i:i + 2500]
        self.assertNotIn('"SELECT open, close, high, low FROM v9_bars_5min_woodies "\n'
                         '                                    "ORDER BY ts DESC LIMIT 15"', block)


if __name__ == "__main__":
    unittest.main()
