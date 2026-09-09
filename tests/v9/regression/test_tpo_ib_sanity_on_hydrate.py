"""IB sanity at the TPO layer — the G-71 class, at the layer that serves it.

Incident (2026-09-09 16:54:52, 24 minutes after the cash open):

    [TPO] Hydrated IB from DB: H=7717.75 L=7680.00 locked=True W=37.75

That is **yesterday's** initial balance — 2026-09-08's true first-12-bar
extremes were exactly 7680.00 / 7717.75, while 09-09's were 7644.25 /
7663.75. A backend restart landed while today's `v9_tpo_sessions` row still
carried the previous session's values with `ib_locked=1`, and `locked`
short-circuits every re-computation, so the stale range would have stood for
the remainder of the session. It was corrected only by accident: a *later*
restart (18:32:50) re-hydrated after the real IB had locked.

`S1_IB_SANITY_V1` already fixes this class — but only inside the day-type
classifier (`classifier_core.py:64-93`). Every other IB consumer
(`BEYOND_IB_EDGE` stops, `rib`, the StopResolver's "35% of IB" floor) kept
reading the stale value. One truthful IB is the standing ruling; these tests
pin the same check at the hydration layer.

Rule-1 note: the fallback validates ALREADY-INGESTED bars against the stored
row. It never invents an IB — with fewer than 12 RTH bars it returns None and
the stored value stands untouched.
"""

import os
import unittest
from unittest import mock

if not os.getenv("BRIDGE_TOKEN"):
    os.environ["BRIDGE_TOKEN"] = "test-token-for-isolation"

from backend.v9.systems.tpo.tpo_system import TPOSystem


# 2026-09-09 ground truth, straight from v9_bars_5min_woodies.
TODAY_IB = (7644.25, 7663.75)      # (low, high) — first 12 RTH bars
YESTERDAY_IB = (7680.00, 7717.75)  # what hydrate() actually restored at 16:54


def _tpo():
    try:
        return TPOSystem()
    except TypeError:
        return TPOSystem.__new__(TPOSystem)


class TestTPOIBSanityOnHydrate(unittest.TestCase):

    def _hydrate_with(self, stored_high, stored_low, bars_extremes, locked=1):
        """Run hydrate() against a stored row and a bars answer we control."""
        sys_ = _tpo()
        row = {
            "ib_high": stored_high, "ib_low": stored_low,
            "ib_locked": locked, "ib_locked_ts": "2026-09-09T10:18:58+00:00",
            "poc_price": None, "vah_price": None, "val_price": None,
        }
        with mock.patch("backend.v9.db.read.read_one", return_value=row), \
             mock.patch.object(TPOSystem, "_first12_rth_extremes",
                               return_value=bars_extremes):
            sys_.hydrate()
        return sys_

    def test_stale_locked_row_is_rebased_to_todays_bars(self):
        """THE regression: yesterday's locked IB must not survive hydration."""
        sys_ = self._hydrate_with(
            stored_high=YESTERDAY_IB[1], stored_low=YESTERDAY_IB[0],
            bars_extremes=TODAY_IB)

        self.assertEqual(
            (sys_.ib_low, sys_.ib_high), TODAY_IB,
            "hydrate() kept yesterday's IB (7680.00/7717.75) instead of "
            "re-basing to today's first 12 RTH bars (7644.25/7663.75) — this "
            "is the exact 2026-09-09 16:54:52 incident")
        self.assertAlmostEqual(
            sys_.ib_high - sys_.ib_low, 19.5, places=2,
            msg="IB width must be today's 19.50, not yesterday's 37.75")
        self.assertEqual(
            sys_.current_state.get("ib_source"),
            "bars_fallback_stored_inconsistent",
            "the substitution must be visible to callers/UI, not silent")

    def test_a_correct_stored_ib_is_left_alone(self):
        """No false positives: a truthful row must pass through untouched."""
        sys_ = self._hydrate_with(
            stored_high=TODAY_IB[1], stored_low=TODAY_IB[0],
            bars_extremes=TODAY_IB)

        self.assertEqual((sys_.ib_low, sys_.ib_high), TODAY_IB)
        self.assertIsNone(
            sys_.current_state.get("ib_source"),
            "a consistent IB must not be tagged as substituted")

    def test_incomplete_ib_window_leaves_the_stored_value_untouched(self):
        """Rule 1: fewer than 12 RTH bars => no bars answer => no invention."""
        sys_ = self._hydrate_with(
            stored_high=YESTERDAY_IB[1], stored_low=YESTERDAY_IB[0],
            bars_extremes=None)

        self.assertEqual(
            (sys_.ib_low, sys_.ib_high), YESTERDAY_IB,
            "with no complete bar window there is nothing to sanity against; "
            "hydrate() must leave the stored value alone rather than guess")
        self.assertIsNone(sys_.current_state.get("ib_source"))

    def test_bars_poking_outside_the_claimed_ib_trigger_the_rebase(self):
        """Detector (a): nothing in the first hour can exceed its own extremes."""
        # Stored IB is NARROWER than the bars — impossible if it were the
        # real first hour, so it must be a different window.
        sys_ = self._hydrate_with(
            stored_high=7650.00, stored_low=7648.00, bars_extremes=TODAY_IB)
        self.assertEqual((sys_.ib_low, sys_.ib_high), TODAY_IB)

    def test_helper_returns_none_when_a_bar_has_no_high_or_low(self):
        """A null OHLC field must yield None, never a partial IB."""
        rows = [{"high": 1.0, "low": 0.5}] * 11 + [{"high": None, "low": 0.5}]
        sys_ = _tpo()
        with mock.patch("backend.v9.db.read.read_all", return_value=rows):
            self.assertIsNone(sys_._first12_rth_extremes())


if __name__ == "__main__":
    unittest.main()
