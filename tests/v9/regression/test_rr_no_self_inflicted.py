"""A gate may reject a setup — never rewrite it and then reject its own rewrite.

Law 1 of the fix plan (Michael, 08.09 18:45, approving item 2).

Measured live the same evening, 18:20:04:

    [FiveMin] FIRE: DOUBLE_BOTTOM_EE LONG (conf=0.85, size=half)
    [S2] T1Setup emitted: entry=7701.25 stop=7676.00 tier=HIGH contracts=5
    [Gateway] STOP ARBITRATION: STEP_SCALED_LADDER OVERRODE StopResolver
              (7676.00 -> 7693.75)
    [Gateway] §3 STRUCT_TARGETS_WIN: t1/t2/t3 7707.50/7713.75/7719.75
              -> 7703.25/7704.75/7717.75 (structural)
    [Gateway] BLOCKED rr_hard_floor: R:R 0.27 < 0.30 (un-rescuable,
              T1=7703.25 entry=7701.25 stop=7693.75)

Ten points of reward became two, and the chain then refused the trade for the
ratio it had just manufactured. The highest-confidence signal of the session.

Two halves are guarded here: the producer's target must be PRESERVED when the
structural override replaces it, and the R:R floor must CONSULT it before
blocking. Break either and a self-inflicted rejection returns.
"""
import unittest


class TestNoSelfInflictedRejection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import inspect
        from backend.v9.gateway import trading_gateway as tg
        cls.SRC = inspect.getsource(tg)

    # ── half 1: the producer's target survives the structural override ──
    def test_struct_override_preserves_the_producers_target(self):
        i = self.SRC.find("§3 STRUCT_TARGETS_WIN")
        self.assertNotEqual(i, -1, "the structural-targets override was not found")
        window = self.SRC[max(0, i - 3000):i + 500]
        self.assertIn(
            't1_pre_struct', window,
            "STRUCT_TARGETS_WIN replaces t1 without keeping what the producer "
            "shipped — the R:R floor then has nothing to compare against and a "
            "cut target becomes an unappealable rejection (08.09 18:20)")

    # ── half 2: the floor consults it before blocking ──
    def test_rr_floor_consults_the_original_before_blocking(self):
        i = self.SRC.find('result["blocked_by"] = "rr_hard_floor"')
        self.assertNotEqual(i, -1, "the rr_hard_floor block was not found")
        window = self.SRC[max(0, i - 2600):i]
        self.assertIn(
            "RR_NO_SELF_INFLICTED_V1", window,
            "rr_hard_floor blocks without asking what the ratio was on the "
            "target the producer shipped — that is the 18:20 case verbatim")
        i_flag = window.find("RR_NO_SELF_INFLICTED_V1")
        i_restore = window.find('setup["t1"] = _orig')
        self.assertNotEqual(i_restore, -1, "the restore path is missing")
        self.assertLess(i_flag, i_restore, "the flag must gate the restore")

    def test_it_is_a_restore_not_a_bypass(self):
        """The floor must still block a setup that fails on its OWN economics."""
        i = self.SRC.find('result["blocked_by"] = "rr_hard_floor"')
        window = self.SRC[max(0, i - 2600):i]
        self.assertIn(
            ">= _rr_hard_floor", window,
            "the restored target must itself clear the floor — otherwise this "
            "is a bypass of the floor rather than a repair of our own damage")
        # and the block must still be reachable: a second check after the restore
        after = self.SRC[max(0, i - 400):i]
        self.assertIn("_rr_actual < _rr_hard_floor", after,
                      "the floor must be re-evaluated after the restore")

    def test_default_off_is_byte_identical(self):
        i = self.SRC.find('result["blocked_by"] = "rr_hard_floor"')
        window = self.SRC[max(0, i - 2600):i].replace("'", '"')
        self.assertIn('"RR_NO_SELF_INFLICTED_V1", "0"', window,
                      "the flag must default OFF")

    def test_ruling_recorded(self):
        from pathlib import Path
        p = Path(__file__).resolve().parents[3] / "config" / "RULED_FLAGS.yaml"
        self.assertIn("RR_NO_SELF_INFLICTED_V1", p.read_text(encoding="utf-8"),
                      "flag_guard cannot hold a flag that is not in RULED_FLAGS")


if __name__ == "__main__":
    unittest.main()
