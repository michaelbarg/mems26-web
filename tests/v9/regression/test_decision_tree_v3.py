# -*- coding: utf-8 -*-
"""DECISION_TREE_V3 — the nested tree (config/decision_tree_v3.yaml) walked by
backend/v9/services/decision_tree.py.

Parity milestone (docs/plans/DECISION_TREE_V3_PLAN_2026-09-25.md §3): the seed tree must give the
SAME verdict as the legacy chain — dalton_playbook.intent + evaluate_gate (kinds_apply_to =
counter_bias_only) + the T-319b location pre-check + the T-329 failed-extension exemption — on the
exhaustive grid of circumstances. Then the gateway hook: DECISION_TREE_V3=1 ⇒ `tree:*` blocks;
unset ⇒ byte-identical.
"""
import itertools
import os
import unittest

from backend.v9.services import decision_tree as dt3
from backend.v9.services.dalton_playbook import intent as pb_intent, evaluate_gate as pb_eval

OPENINGS = ["OPEN_DRIVE", "OPEN_TEST_DRIVE", "OPEN_REJECTION_REVERSE", "OPEN_AUCTION_IN", "OPEN_AUCTION_OUT", "UNKNOWN"]
PHASES = {"A": "16:35", "B": "17:00", "C": "18:00", "D": "21:30"}
DAY_TYPES = ["", "Trend_Normal", "Trend_DD", "Variation", "Normal_Variation", "Normal", "Neutral_Center",
             "Neutral_Extreme", "Nontrend", "Nonconviction", "FORMING"]
KINDS = {"OPENING_DRIVE": "WITH_DRIVE", "OPENING_ORR": "REVERSAL", "REACTIVE_LONG": "EDGE_FADE",
         "PULLBACK_CONT": "PULLBACK", "INITIATIVE_LONG": "BREAK", "RE_ACCEPTANCE": "VALUE_RETURN",
         "CEILING_FLIP_LONG": "REVERSAL"}
ZONES = ["unknown", "above_value", "near_vah", "mid_value", "near_val", "below_value"]
NN = ("Normal", "Neutral_Center", "Neutral_Extreme")


def legacy_verdict(*, opening, phase, day_type, direction, hint, pattern, zone, edge):
    """What the gateway's legacy chain decides for this circumstance (the code path under
    DALTON_PLAYBOOK_V1 with DECISION_TREE_V3 unset), reduced to TAKE / SKIP:<kind>."""
    it = pb_intent(opening_type=opening, day_type=day_type, now_il_hhmm=PHASES[phase], direction_hint=hint)
    location_checked = False
    if day_type in NN and phase != "D" and zone != "unknown":
        ok = (direction == "LONG" and zone in ("near_val", "below_value")) or \
             (direction == "SHORT" and zone in ("near_vah", "above_value"))
        if not ok:
            return "SKIP:location"
        location_checked = True
    setup = {"direction": direction, "classification": pattern, "entry_price": 7700.0, "stop": 7695.0}
    block = pb_eval(setup, it)
    if block and location_checked and block["blocked_by"] == "dalton_intent:kind":
        block = None
    if block and block["blocked_by"] in ("dalton_intent:bias", "dalton_intent:kind") \
            and pattern.startswith("CEILING_FLIP") and edge == "failed_extension":
        block = None
    if block:
        return "SKIP:" + block["blocked_by"].split(":", 1)[1]
    return "TAKE"


def tree_verdict(tree, *, opening, phase, day_type, direction, hint, pattern, zone, edge):
    t_hint = hint
    if opening == "OPEN_REJECTION_REVERSE" and phase in ("A", "B") and hint in ("LONG", "SHORT"):
        t_hint = "SHORT" if hint == "LONG" else "LONG"     # the gateway hands the reversal direction to the tree
    setup = {"direction": direction, "classification": pattern, "entry_price": 7700.0, "stop": 7695.0}
    vec = dt3.features_of_setup(setup, opening_type=opening, phase=phase, day_type=day_type,
                                structure="forming" if phase in ("A", "B") else "none",
                                dir_hint=t_hint, zone=zone, kind=KINDS[pattern], atr=None, hour=17)
    vec["edge"] = edge
    leaf, path = dt3.walk(tree, vec)
    act = str(leaf.get("leaf")).upper()
    tree_verdict.last_leaf = leaf
    return ("SKIP:" + str(leaf.get("id"))) if act == "SKIP" else act, path


LEGACY_IDS = ("stand_down", "bias", "kind", "location")


def live_equivalent(exp, got, leaf=None):
    """Parity of the LIVE path: a SHADOW leaf never fires live (it records only), so it is equivalent to
    the legacy refusal; a seed SKIP leaf must carry the legacy reason; a measured split may refine the
    reason id (e.g. a branch under a legacy `kind` cell). A TAKE where the legacy chain refused is allowed
    ONLY on a leaf that carries an explicit `ruling:` (Michael's written word) AND `measured:` — a silent
    divergence is a bug."""
    if got == "TAKE" and exp != "TAKE":
        return bool(leaf and leaf.get("ruling") and leaf.get("measured"))
    if exp == "TAKE" or got == "TAKE":
        return exp == got
    if got == "SHADOW":
        return True
    gid = got.split(":", 1)[1]
    return gid not in LEGACY_IDS or exp == got


class TestTreeShape(unittest.TestCase):
    def setUp(self):
        dt3.invalidate_cache()
        self.tree = dt3.load_tree()

    def test_root_order_is_michaels(self):
        self.assertEqual(self.tree["split"], "opening_type")
        for child in self.tree["branches"].values():
            self.assertEqual(child["split"], "phase")
            self.assertEqual(child["branches"]["C"]["split"], "day_type")

    def test_every_leaf_is_an_action(self):
        leaves = dt3.leaves(self.tree)
        self.assertGreater(len(leaves), 50)
        for lf in leaves:
            self.assertIn(lf["leaf"], ("TAKE", "SHADOW", "SKIP"), lf)

    def test_walk_never_falls_through(self):
        leaf, path = dt3.walk(self.tree, {})
        self.assertEqual(leaf["leaf"], "SKIP")
        self.assertTrue(path)

    def test_numeric_and_list_keys(self):
        self.assertTrue(dt3._match("LONG|SHORT", "short"))
        self.assertTrue(dt3._match("<=0.5", 0.4))
        self.assertFalse(dt3._match("<=0.5", 0.6))
        self.assertTrue(dt3._match(">2", 3))
        self.assertFalse(dt3._match(">2", None))


class TestParityWithLegacyChain(unittest.TestCase):
    """The seed tree == the legacy chain on every circumstance (parity milestone 1)."""

    def setUp(self):
        dt3.invalidate_cache()
        self.tree = dt3.load_tree()
        for k in ("DALTON_KINDS_APPLY_TO", "DALTON_KINDS_ADVISORY_PHASES"):
            os.environ.pop(k, None)

    def test_exhaustive_grid(self):
        grid = itertools.product(OPENINGS, PHASES.keys(), DAY_TYPES, ("LONG", "SHORT"),
                                 (None, "LONG", "SHORT"), KINDS.keys(), ZONES, ("none", "failed_extension"))
        n = 0
        mismatches = []
        for opening, phase, day_type, direction, hint, pattern, zone, edge in grid:
            if edge == "failed_extension" and not pattern.startswith("CEILING_FLIP"):
                continue   # the gateway computes the edge for CEILING_FLIP patterns only
            exp = legacy_verdict(opening=opening, phase=phase, day_type=day_type, direction=direction,
                                 hint=hint, pattern=pattern, zone=zone, edge=edge)
            got, path = tree_verdict(self.tree, opening=opening, phase=phase, day_type=day_type,
                                     direction=direction, hint=hint, pattern=pattern, zone=zone, edge=edge)
            n += 1
            if not live_equivalent(exp, got, getattr(tree_verdict, "last_leaf", None)):
                mismatches.append((opening, phase, day_type, direction, hint, pattern, zone, edge, exp, got, path))
        self.assertGreater(n, 20000)
        self.assertEqual(mismatches, [], f"{len(mismatches)} of {n} circumstances differ; first: {mismatches[:5]}")

    def test_shadow_leaves_are_measured_branches_only(self):
        """Every SHADOW leaf in the seed is a measured split (carries `measured:`), never a bare row."""
        for lf in dt3.leaves(self.tree):
            if lf["leaf"] == "SHADOW":
                self.assertTrue(lf.get("measured"), f"SHADOW leaf without measured: {lf.get('path')}")

    def test_ruled_branches_carry_ruling_and_number(self):
        """A branch that diverges from the legacy chain (T-484 auction_B_trend_break) carries Michael's ruling
        quote and its day-total number — the tree never takes on its own."""
        ruled = [lf for lf in dt3.leaves(self.tree) if lf.get("ruling")]
        self.assertTrue(ruled)
        for lf in ruled:
            self.assertEqual(lf["leaf"], "TAKE")
            self.assertIn("Michael", str(lf["ruling"]))
            self.assertTrue(lf.get("measured") and lf["measured"].get("sessions"))
        got, _ = tree_verdict(self.tree, opening="OPEN_AUCTION_IN", phase="B", day_type="Trend_Normal", direction="LONG",
                              hint=None, pattern="INITIATIVE_LONG", zone="unknown", edge="none")
        self.assertEqual(got, "TAKE")

    def test_23_09_opening_drive_short_is_taken(self):
        got, path = tree_verdict(self.tree, opening="OPEN_DRIVE", phase="B", day_type="", direction="SHORT",
                                 hint="SHORT", pattern="OPENING_DRIVE", zone="unknown", edge="none")
        self.assertEqual(got, "TAKE", path)

    def test_24_09_initiative_long_under_open_auction_is_refused_by_kind(self):
        got, path = tree_verdict(self.tree, opening="OPEN_AUCTION_IN", phase="B", day_type="", direction="LONG",
                                 hint=None, pattern="INITIATIVE_LONG", zone="unknown", edge="none")
        self.assertEqual(got, "SKIP:kind", path)
        self.assertEqual([f for f, _ in path][:3], ["opening_type", "phase", "day_type"])

    def test_phase_d_variation_is_manage_only(self):
        got, _ = tree_verdict(self.tree, opening="OPEN_DRIVE", phase="D", day_type="Variation", direction="LONG",
                              hint="LONG", pattern="PULLBACK_CONT", zone="unknown", edge="none")
        self.assertEqual(got, "SKIP:stand_down")

    def test_responsive_day_location_decides(self):
        kw = dict(opening="OPEN_AUCTION_IN", phase="C", day_type="Normal", hint=None, pattern="INITIATIVE_LONG", edge="none")
        self.assertEqual(tree_verdict(self.tree, direction="LONG", zone="near_val", **kw)[0], "TAKE")
        self.assertEqual(tree_verdict(self.tree, direction="LONG", zone="mid_value", **kw)[0], "SKIP:location")
        self.assertEqual(tree_verdict(self.tree, direction="SHORT", zone="near_val", **kw)[0], "SKIP:location")
        self.assertEqual(tree_verdict(self.tree, direction="SHORT", zone="above_value", **kw)[0], "TAKE")


class TestStructureBeforeLabel(unittest.TestCase):
    """25.09 19:05 (Michael: "בכלל זה כבר לא יום נורמלי"): under a Normal label the tree asks what the price
    did to the IB first. 25.09: IB 7752.75–7793.75, price to 7805.75 on +3,752 delta — every long refused by
    `location` because the label stayed Normal."""

    def setUp(self):
        dt3.invalidate_cache()
        self.tree = dt3.load_tree()

    def _walk(self, **kw):
        vec = {"opening_type": "OPEN_AUCTION_IN", "phase": "C", "day_type": "Normal", "structure": "none",
               "pattern": "DOUBLE_BOTTOM_EE_LONG", "kind": "BREAK", "direction": "LONG", "rel_bias": "none",
               "zone": "mid_value", "edge": "none"}
        vec.update(kw)
        return dt3.walk(self.tree, vec)

    def test_extension_up_with_the_extension_is_taken_and_skips_elq(self):
        leaf, path = self._walk(structure="up", rel_bias="with", zone="above_value")
        self.assertEqual((leaf["leaf"], leaf["id"]), ("TAKE", "take_with_extension"), path)
        self.assertIn("entry_location_quality", leaf.get("skip_gates") or [])
        self.assertTrue(leaf.get("ruling") and leaf.get("measured"))

    def test_extension_up_against_is_refused_unless_failed_extension(self):
        leaf, _ = self._walk(structure="up", rel_bias="against", direction="SHORT", zone="near_vah",
                             pattern="REACTIVE_SHORT", kind="EDGE_FADE")
        self.assertEqual((leaf["leaf"], leaf["id"]), ("SKIP", "bias"))
        leaf, _ = self._walk(structure="up", rel_bias="against", direction="SHORT", zone="near_vah",
                             pattern="CEILING_FLIP_SHORT", kind="REVERSAL", edge="failed_extension")
        self.assertEqual(leaf["leaf"], "TAKE")

    def test_no_extension_keeps_the_normal_template(self):
        self.assertEqual(self._walk(structure="none", zone="mid_value")[0]["id"], "location")
        self.assertEqual(self._walk(structure="none", zone="near_val")[0]["id"], "take_location")
        self.assertEqual(self._walk(structure="none", direction="SHORT", zone="near_vah")[0]["id"], "take_location")

    def test_two_sided_is_the_neutral_template(self):
        self.assertEqual(self._walk(structure="two_sided", zone="below_value")[0]["id"], "take_location")
        self.assertEqual(self._walk(structure="two_sided", zone="mid_value")[0]["id"], "location")

    def test_the_25_09_1900_long_is_now_taken(self):
        # 19:00:08 DOUBLE_BOTTOM_EE_LONG @7790.25 — IB high 7793.75 broken (session high 7805.75), hint LONG
        leaf, path = self._walk(structure=dt3.structure_of(7793.75, 7752.75, 7805.75, 7752.75, "C"),
                                rel_bias="with", zone="near_vah")
        self.assertEqual(leaf["id"], "take_with_extension", path)


class TestGatewayHook(unittest.TestCase):
    """The gateway source carries the hook and its parity guarantees."""

    def setUp(self):
        import backend.v9.gateway.trading_gateway as gw
        self.src = open(gw.__file__, encoding="utf-8").read()

    def test_hook_present_and_legacy_gated(self):
        self.assertIn("from backend.v9.services import decision_tree as _dt3", self.src)
        self.assertIn("_dp_block = _tree_block if _tree_used else _dp_eval(setup, _dalton_intent)", self.src)
        self.assertIn("and _dp_phase_now != \"D\" and not _vc_branch and not _tree_used", self.src)
        self.assertIn("[TREE-V3 DIFF]", self.src)

    def test_flag_default_off(self):
        os.environ.pop("DECISION_TREE_V3", None)
        self.assertFalse(dt3.enabled())
        os.environ["DECISION_TREE_V3"] = "shadow"
        self.assertTrue(dt3.enabled()); self.assertTrue(dt3.is_shadow())
        os.environ["DECISION_TREE_V3"] = "1"
        self.assertTrue(dt3.enabled()); self.assertFalse(dt3.is_shadow())
        os.environ.pop("DECISION_TREE_V3", None)


if __name__ == "__main__":
    unittest.main()
