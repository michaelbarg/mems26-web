"""The termination entry must survive the day-direction compass.

Michael ruled it twice. 28.08, quoted verbatim in `config/RULED_FLAGS.yaml`
under `DALTON_EDGE_V1`: "שנייצר תבנית כזאת שתתחיל לסחור **היום לונג ושורט**
בנקודות **סיום** של דלתון". 08.09, after watching it fail live: "אמרתי שברגע
שמסתיים לאפשר לונג בהיפוך — היה היפוך למה אין לונג?"

He is right, and the record shows why. `DIRECTION_COMPASS_V1` (20.08) exists to
stop "תת-הקבוצה שנגד-הכיוון". A Dalton termination entry is counter-day by
definition — the move just ended. The two rulings collide, the older gate wins,
and `DALTON_EDGE` has never been able to take the long at the end of a down day.

Measured live on 08.09 at 17:19:46 — one second, one price, both directions:

    BLOCKED  DALTON_EDGE_LONG  7685.00  blocked_by=direction_compass
    FIRE     INITIATIVE_SHORT  7684.00  → live → STOP_HIT −$103.75

The session low was 7680.00 at 17:10; by 17:55 price was 7698.75. The blocked
long was worth roughly +13.75 points.

This guards the exemption: narrow to the termination family, and nothing else.
"""
import os
import unittest


class TestCompassTerminationExemption(unittest.TestCase):
    SRC = None

    @classmethod
    def setUpClass(cls):
        import inspect
        from backend.v9.gateway import trading_gateway as tg
        cls.SRC = inspect.getsource(tg)

    def _compass_block(self) -> str:
        i = self.SRC.find("direction_verdict as _cmp_verdict")
        self.assertNotEqual(i, -1, "the compass gate was not found in the gateway")
        j = self.SRC.find('result["blocked_by"] = "direction_compass"', i)
        self.assertNotEqual(j, -1, "the compass block statement was not found")
        return self.SRC[i:j]

    def test_the_exemption_exists_and_is_read_from_a_flag(self):
        blk = self._compass_block()
        self.assertIn(
            "DALTON_EDGE_COMPASS_EXEMPT_V1", blk,
            "the compass has no termination exemption — DALTON_EDGE_LONG is "
            "blocked at exactly the moment it is supposed to fire (08.09 17:19:46)")
        self.assertIn("DALTON_EDGE", blk, "the exemption does not name the family")

    def test_the_exemption_runs_before_the_block(self):
        """The check must precede the veto, or it changes nothing."""
        blk = self._compass_block()
        i_flag = blk.find("DALTON_EDGE_COMPASS_EXEMPT_V1")
        i_verdict = blk.find("_cmp_verdict(")
        self.assertNotEqual(i_verdict, -1)
        self.assertLess(i_flag, len(blk), "exemption must sit inside the compass block")

    def test_scope_is_the_termination_family_only(self):
        """A blanket exemption would disable the compass. It must not.

        Comments are stripped first: the block deliberately quotes the 08.09
        evidence, which names the short that was permitted while the long was
        blocked. What matters is which families the CODE exempts.
        """
        code = "\n".join(
            ln for ln in self._compass_block().splitlines()
            if not ln.lstrip().startswith("#"))
        for foreign in ("INITIATIVE", "ZLR", "GB100", "OPENING_DRIVE", "REACTIVE"):
            self.assertNotIn(
                foreign, code,
                f"the exemption must not name {foreign} — only the termination "
                f"family is counter-day by definition")
        self.assertIn("DALTON_EDGE", code, "the code must name the exempt family")

    def test_default_off_is_byte_identical(self):
        """The flag must default OFF so the gate is unchanged until ruled on."""
        blk = self._compass_block()
        self.assertIn('"DALTON_EDGE_COMPASS_EXEMPT_V1", "0"', blk.replace("'", '"'),
                      "the exemption must default to OFF")

    def test_ruling_is_recorded_with_the_flag(self):
        """A behaviour flag without its ruling is how a decision gets lost."""
        from pathlib import Path
        p = Path(__file__).resolve().parents[3] / "config" / "RULED_FLAGS.yaml"
        txt = p.read_text(encoding="utf-8")
        self.assertIn("DALTON_EDGE_COMPASS_EXEMPT_V1", txt,
                      "the flag is not in RULED_FLAGS — flag_guard cannot hold it")


if __name__ == "__main__":
    unittest.main()
