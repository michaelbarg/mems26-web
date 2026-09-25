# -*- coding: utf-8 -*-
"""T-478 (Michael 25.09 17:00 "לחבר את מערכת 3 לשדואו כי צריך לדייק אותה"): S3 returns in SHADOW.

Three guarantees:
  1. the SCID tick file resolves to the LIVE contract (the dead-feed root: MESM26 hard-coded after the roll);
  2. S2 does not read footprint state unless S2_READ_FOOTPRINT_V1=1 — with data present belly/COT/AMT would
     VETO S2 fires, so the default keeps S2 exactly as it trades today;
  3. the value-migration / POC-side profile features are pure and never raise.
"""
import importlib.util
import os
import tempfile
import time
import unittest
from unittest import mock

from backend.v9.services import decision_tree as dt3


def _load_vap():
    spec = importlib.util.spec_from_file_location(
        "vap_recompute_t478", os.path.join(os.path.dirname(__file__), "..", "..", "..", "bridge", "v9_streams", "vap_recompute.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestScidPathResolution(unittest.TestCase):
    def test_env_override_wins(self):
        vap = _load_vap()
        with mock.patch.dict(os.environ, {"MES_SCID_PATH": "~/x/MESZ26_FUT_CME.scid"}):
            self.assertTrue(vap.resolve_mes_scid_path().endswith("/x/MESZ26_FUT_CME.scid"))

    def test_newest_contract_by_mtime(self):
        vap = _load_vap()
        with tempfile.TemporaryDirectory() as d:
            old = os.path.join(d, "MESM26_FUT_CME.scid"); new = os.path.join(d, "MESZ26_FUT_CME.scid")
            for p, age in ((old, 3600), (new, 0)):
                open(p, "wb").write(b"\0" * 8); os.utime(p, (time.time() - age, time.time() - age))
            with mock.patch.dict(os.environ, {"MES_SCID_PATH": ""}), \
                    mock.patch.object(vap.os.path, "expanduser", lambda s: d if s == "~/SierraChart/Data" else s):
                self.assertEqual(vap.resolve_mes_scid_path(), new)


class TestS2FootprintIsolation(unittest.TestCase):
    def _fms(self):
        from backend.v9.systems.five_min.five_min_system import FiveMinSystem
        fms = FiveMinSystem.__new__(FiveMinSystem)      # no __init__: only the read path is exercised
        fms._footprint_system = mock.Mock()
        fms._footprint_system.get_current.return_value = {"belly_ratio_dominant": False, "cot": 1.0, "amt": 2.0}
        return fms

    def test_default_reads_nothing(self):
        fms = self._fms()
        with mock.patch.dict(os.environ, {"S2_READ_FOOTPRINT_V1": ""}):
            self.assertEqual(fms._footprint_state(), {})
        with mock.patch.dict(os.environ, {"S2_READ_FOOTPRINT_V1": "0"}):
            self.assertEqual(fms._footprint_state(), {})

    def test_flag_on_reads_the_system(self):
        fms = self._fms()
        with mock.patch.dict(os.environ, {"S2_READ_FOOTPRINT_V1": "1"}):
            self.assertEqual(fms._footprint_state().get("belly_ratio_dominant"), False)


class TestProfileFeatures(unittest.TestCase):
    def test_value_migration(self):
        self.assertEqual(dt3.value_migration(7790, 7771, 7775, 7734), "overlap_high")
        self.assertEqual(dt3.value_migration(7800, 7780, 7775, 7734), "higher")
        self.assertEqual(dt3.value_migration(7730, 7710, 7775, 7734), "lower")
        self.assertEqual(dt3.value_migration(7770, 7740, 7775, 7734), "inside")
        self.assertEqual(dt3.value_migration(7780, 7730, 7775, 7734), "outside")
        self.assertEqual(dt3.value_migration(None, 0, 7775, 7734), "unknown")

    def test_poc_side(self):
        self.assertEqual(dt3.poc_side(7790, 7780.75, 1.0), "above")
        self.assertEqual(dt3.poc_side(7780.5, 7780.75, 1.0), "at")
        self.assertEqual(dt3.poc_side(7770, 7780.75, 1.0), "below")
        self.assertEqual(dt3.poc_side(0, 7780.75, 1.0), "unknown")

    def test_features_carry_profile_and_seed_ignores_them(self):
        setup = {"direction": "LONG", "classification": "INITIATIVE_LONG", "entry_price": 7790.0, "stop": 7785.0}
        vec = dt3.features_of_setup(setup, opening_type="OPEN_AUCTION_IN", phase="B", day_type="", structure="forming",
                                    dir_hint=None, zone="unknown", kind="BREAK", atr=None, hour=17,
                                    prior_zone="above_value", poc_side_="above", migration="higher")
        self.assertEqual((vec["prior_zone"], vec["poc_side"], vec["value_migration"]), ("above_value", "above", "higher"))
        tree = dt3.load_tree()
        a, _ = dt3.walk(tree, vec)
        vec2 = dict(vec, prior_zone="below_value", poc_side="below", value_migration="lower")
        b, _ = dt3.walk(tree, vec2)
        self.assertEqual(a.get("leaf"), b.get("leaf"))      # no seed branch splits on the profile yet (parity)


if __name__ == "__main__":
    unittest.main()
