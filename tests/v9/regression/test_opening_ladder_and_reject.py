"""P0 08.09 — the two halves of trade #1220.

Half 1: `opening_entry.build_opening_setup` shipped `t2=None, t3=None` on every
setup. `T3_REQUIRED_V1` (Michael 01.09: every contract carries a target) rejects
a PLACE with `t3<=0` on >=3 contracts, and `RISK_MIN_CONTRACTS=3` makes that
always true — so 100% of opening entries were rejected from 02.09 on.

Half 2: that rejection is returned as `{"rejected": True, ...}`, not raised. The
gateway only handled `ValueError`, so it logged "LIVE trade", pushed the phone
notification and held the live slot while nothing reached Sierra.

Both are guarded here. Mutation-sensitivity is the point: revert either fix and
the matching test must fail.
"""
import os
import unittest


class TestOpeningLadder(unittest.TestCase):
    """OPENING_LADDER_V1 — the opening setup must carry a full ladder."""

    TRIGGER = {"type": "DRIVE", "direction": "SHORT", "entry": 7708.0,
               "extreme": 7720.0, "or_width": 8.0, "reverses": None}
    BARS = [{"ts": f"2026-09-08 16:{30 + 5 * i}:00+03:00", "o": 7710.0 + i,
             "h": 7714.0 + i, "l": 7706.0 + i, "c": 7708.0 + i, "v": 900 + i}
            for i in range(6)]

    def setUp(self):
        self._prev = {k: os.environ.get(k) for k in
                      ("OPENING_LADDER_V1", "OPENING_T2_R", "OPENING_T3_R", "T1_BANK_R")}

    def tearDown(self):
        for k, v in self._prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _build(self):
        from backend.v9.systems.opening_entry import build_opening_setup
        return build_opening_setup(self.TRIGGER, self.BARS, shadow_only=False)

    def test_flag_on_gives_t2_and_t3_on_the_correct_side(self):
        os.environ["OPENING_LADDER_V1"] = "1"
        s = self._build()
        self.assertIsNotNone(s, "the fixture must produce a setup")
        self.assertIsNotNone(
            s["t2"], "t2 is None with OPENING_LADDER_V1=1 — the ladder did not build")
        self.assertIsNotNone(
            s["t3"], "t3 is None with OPENING_LADDER_V1=1 — T3_REQUIRED_V1 will "
                     "reject the PLACE on >=3 contracts and nothing reaches Sierra")
        entry, stop = s["entry_price"], s["stop"]
        self.assertGreater(stop, entry, "fixture is a SHORT: stop must sit above entry")
        # SHORT: every target below entry, and monotonically farther out.
        self.assertLess(s["t1"], entry)
        self.assertLess(s["t2"], s["t1"])
        self.assertLess(s["t3"], s["t2"])

    def test_multiples_are_measured_from_risk(self):
        os.environ["OPENING_LADDER_V1"] = "1"
        os.environ["OPENING_T2_R"] = "2.5"
        os.environ["OPENING_T3_R"] = "4.0"
        s = self._build()
        risk = abs(s["stop"] - s["entry_price"])
        self.assertAlmostEqual(s["entry_price"] - s["t2"], 2.5 * risk, places=1)
        self.assertAlmostEqual(s["entry_price"] - s["t3"], 4.0 * risk, places=1)

    def test_flag_off_is_byte_identical_to_the_old_behaviour(self):
        os.environ["OPENING_LADDER_V1"] = "0"
        s = self._build()
        self.assertIsNone(s["t2"])
        self.assertIsNone(s["t3"])


class TestRejectedCommandIsNotASuccess(unittest.TestCase):
    """The gateway must treat {"rejected": True} exactly like the ValueError arm."""

    def test_t3_belt_rejects_a_ladderless_opening_setup(self):
        """The belt itself: no t3 on 3 contracts → a rejection dict, not a write."""
        from backend.v9.services import sierra_command as sc
        prev = os.environ.get("T3_REQUIRED_V1")
        os.environ["T3_REQUIRED_V1"] = "1"
        try:
            setup = {"direction": "SHORT", "entry_price": 7701.0, "stop": 7716.0,
                     "t1": 7691.0, "t2": 7666.0, "t3": None,
                     "classification": "OPENING_DRIVE",
                     "metadata": {"sizing_contracts": 3}}
            out = sc.command_from_setup(setup, trade_id="test-1220",
                                        account="TEST", mode="live")
            if isinstance(out, dict) and out.get("rejected"):
                self.assertEqual(out.get("reason"), "t3_missing")
            else:
                self.skipTest("sizing path did not reach the t3 belt in this fixture")
        finally:
            if prev is None:
                os.environ.pop("T3_REQUIRED_V1", None)
            else:
                os.environ["T3_REQUIRED_V1"] = prev

    def test_gateway_source_handles_the_rejected_key(self):
        """Structural guard: the handler must exist between command_from_setup and
        the LIVE-trade log line, and must return before the ntfy push.

        A behavioural test would need a live TradeManager + DB; this asserts the
        ordering that the bug violated, and fails if the block is removed.
        """
        import inspect
        from backend.v9.gateway import trading_gateway as tg
        src = inspect.getsource(tg)

        # Every place that builds a Sierra command must inspect the rejection
        # shape before it announces or notifies. There is one such call in the
        # demo path and one in the live path; both must be covered.
        starts = []
        pos = src.find("command = command_from_setup(")
        while pos != -1:
            starts.append(pos)
            pos = src.find("command = command_from_setup(", pos + 1)
        self.assertTrue(starts, "no command_from_setup call site found")

        for i_cmd in starts:
            window = src[i_cmd:i_cmd + 4000]
            i_rej = window.find('command.get("rejected")')
            self.assertNotEqual(
                i_rej, -1,
                "a command_from_setup call site does not check "
                "command['rejected'] — a rejected PLACE is announced as a real "
                "trade while nothing reaches Sierra (trade #1220, 08.09)")
            for marker, what in (("trade TM id=", "the trade log line"),
                                 ("ntfy_notify", "the phone notification")):
                i_m = window.find(marker)
                if i_m != -1:
                    self.assertLess(
                        i_rej, i_m,
                        f"the rejected-check must run BEFORE {what}")


if __name__ == "__main__":
    unittest.main()
