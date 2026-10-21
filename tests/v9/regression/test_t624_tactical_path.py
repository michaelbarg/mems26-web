"""T-624 — the tactical path after a FAILED IB extension (Michael 21.10, on 19.10: "אני רוצה לתקן נתיב").

19.10 (IL): IB 7727.50–7759.75; the up-extension was accepted 18:30 and failed 19:05 (back inside the IB). The 19:00
bar — GB100 SHORT's signal bar — carried 2.1× the volume of the 20 bars before it with a 1.45-ATR bearish body (effort
and result); the 19:10 bar was the quiet pullback before TREND_STEP SHORT 19:15. test_1910_real_bars reads the real
19.10 bars from v9_bars_5min_woodies when the DB is reachable (the Mac) and skips otherwise; the other tests are
synthetic.
"""
import os
import unittest
from pathlib import Path
from unittest import mock

from backend.v9.services import decision_tree as dt
from backend.v9.services import effort_result as er

REPO = Path(__file__).resolve().parents[3]


def _bars_from_db(day="2026-10-19", upto_il="19:10"):
    """The exact bars from the DB when it is reachable (the Mac); the tests below that need them skip otherwise."""
    try:
        import subprocess
        psql = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
        q = ("select to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), open, high, low, close, volume from "
             "v9_bars_5min_woodies where symbol='MES' and (ts at time zone 'America/New_York')::date='%s' and "
             "(ts at time zone 'America/New_York')::time >= '09:30' and (ts at time zone 'America/New_York')::time < '16:00' "
             "order by ts" % day)
        out = subprocess.run([psql, "-d", "mems26", "-At", "-F", ",", "-c", q], capture_output=True, text=True,
                             timeout=20).stdout
        rows = [ln.split(",") for ln in out.split()]
        bars = [dict(t=r[0], open=float(r[1]), high=float(r[2]), low=float(r[3]), close=float(r[4]),
                     volume=float(r[5])) for r in rows]
        return [b for b in bars if b["t"] <= upto_il]
    except Exception:
        return []


def _synthetic(n=30, vol=1000.0):
    """A quiet tape: 1-pt bars, flat volume."""
    out, px = [], 7700.0
    for _ in range(n):
        out.append({"o": px, "h": px + 1.0, "l": px - 1.0, "c": px + 0.25, "v": vol})
        px += 0.25
    return out


class EffortResultTest(unittest.TestCase):

    def test_mode_is_off_unless_set(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TACTICAL_EFFORT_MODE", None)
            self.assertEqual(er.mode(), "")
        for m in ("bar", "step", "none"):
            with mock.patch.dict(os.environ, {"TACTICAL_EFFORT_MODE": m}):
                self.assertEqual(er.mode(), m)
        with mock.patch.dict(os.environ, {"TACTICAL_EFFORT_MODE": "1"}):
            self.assertEqual(er.mode(), "")

    def test_bar_strong_needs_effort_and_result(self):
        bars = _synthetic()
        # the signal bar: 2.5× volume, bearish body 3 pt (ATR ≈ 2) ⇒ strong for a SHORT, weak for a LONG
        bars.append({"o": 7708.0, "h": 7708.5, "l": 7704.5, "c": 7705.0, "v": 2500.0})
        self.assertEqual(er.label(bars, "SHORT", "bar")["label"], "strong")
        self.assertEqual(er.label(bars, "LONG", "bar")["label"], "weak")
        # effort without result (absorption): big volume, no body ⇒ weak
        bars[-1] = {"o": 7708.0, "h": 7709.5, "l": 7706.5, "c": 7708.0, "v": 2500.0}
        self.assertEqual(er.label(bars, "SHORT", "bar")["label"], "weak")
        # result without effort: big body, normal volume ⇒ weak
        bars[-1] = {"o": 7708.0, "h": 7708.5, "l": 7704.5, "c": 7705.0, "v": 1000.0}
        self.assertEqual(er.label(bars, "SHORT", "bar")["label"], "weak")

    def test_step_impulse_then_quiet_pullback(self):
        bars = _synthetic()
        bars.append({"o": 7708.0, "h": 7708.5, "l": 7704.5, "c": 7705.0, "v": 2500.0})   # the impulse (effort + result)
        bars.append({"o": 7705.0, "h": 7706.5, "l": 7704.75, "c": 7706.0, "v": 700.0})   # quiet pullback
        self.assertEqual(er.label(bars, "SHORT", "bar")["label"], "weak")                # the pullback bar itself
        r = er.label(bars, "SHORT", "step")
        self.assertEqual(r["label"], "strong")
        self.assertEqual(r["impulse"], len(bars) - 2)
        # a LOUD pullback (effort ≥ 1 against the step) ⇒ not a step
        bars[-1] = {"o": 7705.0, "h": 7707.5, "l": 7704.75, "c": 7707.0, "v": 1800.0}
        self.assertEqual(er.label(bars, "SHORT", "step")["label"], "weak")

    def test_none_and_unknown(self):
        self.assertEqual(er.label([], "SHORT", "none")["label"], "strong")
        self.assertEqual(er.label(_synthetic(5), "SHORT", "bar")["label"], "unknown")
        self.assertEqual(er.label(_synthetic(), "", "bar")["label"], "unknown")

    def test_1910_real_bars(self):
        bars = _bars_from_db(upto_il="19:10")
        if len(bars) < 30:
            self.skipTest("the 19.10 bars are not reachable here")
        at_1900 = [b for b in bars if b["t"] <= "19:00"]
        r = er.label(at_1900, "SHORT", "bar")                    # GB100 SHORT 19:05's signal bar
        self.assertEqual(r["label"], "strong")
        self.assertGreater(r["effort"], 2.0)
        self.assertGreater(r["result"], 1.4)
        r = er.label(bars, "SHORT", "bar")                       # TREND_STEP SHORT 19:15 — the 19:10 pullback bar
        self.assertEqual(r["label"], "weak")
        r = er.label(bars, "SHORT", "step")                      # … but the step (19:00 impulse, quiet pullback)
        self.assertEqual(r["label"], "strong")


class TacticalTreeVariantTest(unittest.TestCase):
    """The variant trees (harness_out/t621/decision_tree_v3.t624_tactical*.yaml) — the live tree is untouched."""

    BASE = {"opening_type": "OPEN_REJECTION_REVERSE", "phase": "C", "day_type": "Variation", "structure": "up",
            "pattern": "TREND_STEP", "kind": "PULLBACK", "direction": "SHORT", "rel_bias": "against",
            "zone": "mid_value", "edge": "none", "hour": 19, "system": 4, "ib_return": "failed_up",
            "ibr_rel": "with_failed", "effort": "strong"}

    def _walk(self, path, vec):
        t = dt.load_tree(str(path)) if path else dt.load_tree(str(REPO / "config" / "decision_tree_v3.yaml"))
        leaf, _ = dt.walk(t, vec)
        return leaf.get("leaf"), leaf.get("id"), leaf.get("promote")

    def test_live_tree_still_refuses_on_bias(self):
        self.assertEqual(self._walk(None, self.BASE)[:2], ("SKIP", "bias"))

    def test_variant_takes_the_tactical_trade(self):
        p = REPO / "harness_out" / "t621" / "decision_tree_v3.t624_tactical.yaml"
        if not p.exists():
            self.skipTest("variant tree not built")
        self.assertEqual(self._walk(p, self.BASE)[:2], ("TAKE", "tactical_failed_ext"))
        for pat in ("ZLR", "GB100", "TT", "TLB"):
            self.assertEqual(self._walk(p, dict(self.BASE, pattern=pat))[0], "TAKE", pat)
        self.assertEqual(self._walk(p, dict(self.BASE, effort="weak"))[:2], ("SKIP", "bias"))
        no_feat = {k: v for k, v in self.BASE.items() if k != "effort"}
        self.assertEqual(self._walk(p, no_feat)[:2], ("SKIP", "bias"))                    # flag off ⇒ as before
        self.assertEqual(self._walk(p, dict(self.BASE, pattern="INITIATIVE_SHORT", system=2))[:2], ("SKIP", "bias"))
        self.assertEqual(self._walk(p, dict(self.BASE, ibr_rel="none", ib_return="extended_up"))[:2], ("SKIP", "bias"))
        # T-329 is untouched: a failed-extension double with weak effort still takes take_failed_ext
        self.assertEqual(self._walk(p, dict(self.BASE, pattern="DOUBLE_TOP_AA_SHORT", system=2, effort="weak",
                                            edge="failed_extension"))[0], "TAKE")
        # phase D: the stand-down gives way to the tactical path only after a failed extension
        self.assertEqual(self._walk(p, dict(self.BASE, phase="D", hour=21, pattern="ZLR"))[:2],
                         ("TAKE", "tactical_failed_ext"))
        self.assertEqual(self._walk(p, dict(self.BASE, phase="D", hour=21, pattern="ZLR", effort="weak"))[:2],
                         ("SKIP", "stand_down"))

    def test_zlr_variant_promotes_zlr_only_there(self):
        p = REPO / "harness_out" / "t621" / "decision_tree_v3.t624_tactical_zlr.yaml"
        if not p.exists():
            self.skipTest("variant tree not built")
        self.assertEqual(self._walk(p, dict(self.BASE, pattern="ZLR"))[2], ["ZLR"])
        self.assertIsNone(self._walk(p, dict(self.BASE, effort="weak"))[2])


class StepsFilterTest(unittest.TestCase):
    """T-624b: TACTICAL_EFFORT_SCOPE=steps + decision_tree_v3.t624_steps.yaml — every TREND_STEP needs effort/result."""

    def test_scope(self):
        with mock.patch.dict(os.environ, {"TACTICAL_EFFORT_SCOPE": "steps"}):
            self.assertTrue(er.in_scope("TREND_STEP"))
            self.assertFalse(er.in_scope("ZLR"))
        with mock.patch.dict(os.environ, {"TACTICAL_EFFORT_SCOPE": "all"}):
            self.assertTrue(er.in_scope("ZLR"))
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TACTICAL_EFFORT_SCOPE", None)
            self.assertFalse(er.in_scope("TREND_STEP"))

    def test_steps_variant(self):
        p = REPO / "harness_out" / "t621" / "decision_tree_v3.t624_steps.yaml"
        if not p.exists():
            self.skipTest("variant tree not built")
        t = dt.load_tree(str(p))
        v = {"opening_type": "OPEN_REJECTION_REVERSE", "phase": "C", "day_type": "Variation", "structure": "up",
             "pattern": "TREND_STEP", "kind": "PULLBACK", "direction": "SHORT", "rel_bias": "with", "zone": "mid_value",
             "edge": "none", "hour": 19, "system": 4}
        self.assertEqual(dt.walk(t, dict(v, effort="strong"))[0]["leaf"], "TAKE")
        self.assertEqual(dt.walk(t, dict(v, effort="weak"))[0].get("id"), "step_no_effort")
        self.assertEqual(dt.walk(t, v)[0].get("id"), "step_no_effort")                     # no feature ⇒ refused
        self.assertEqual(dt.walk(t, dict(v, pattern="ZLR"))[0]["leaf"], "TAKE")            # other patterns untouched
        self.assertEqual(dt.walk(t, dict(v, hour=22, effort="strong"))[0].get("id"), "time_cutoff")


class GatewayWiringTest(unittest.TestCase):

    def test_feature_is_flag_gated_and_only_after_a_failed_extension(self):
        src = (REPO / "backend" / "v9" / "gateway" / "trading_gateway.py").read_text(encoding="utf-8")
        i = src.index("T-624 (TACTICAL_EFFORT_MODE")
        block = src[i:i + 2200]
        self.assertIn('_t624_mode and (_t3_vec.get("ibr_rel") == "with_failed"', block)
        self.assertIn('_t624.in_scope(_t3_vec.get("pattern"))', block)
        self.assertIn('_t3_vec["effort"]', block)
        self.assertLess(i, src.index("_tree_leaf, _t3_path = _dt3.walk(_dt3.load_tree(), _t3_vec)"))
        self.assertIn("effort", dt.FEATURES)


if __name__ == "__main__":
    unittest.main()
