"""T-627 (21.10.2026) — the swing trail must never hand the runner a stop on the
wrong side of the market.

Golden: 21.10 #3687 (SHORT 7792.75, 19:20) and #3702 (SHORT 7807.75, 20:25).
Both banked T1, SMART_BE moved the stop to BE, and then F5 SWING_TRAIL wrote
stop 7781.00 — the IB high 7780.75 (16:45) + 1 tick, the last CONFIRMED swing
high of the session — while the price sat at 7789 / 7803 inside an up-leg whose
own high had not yet been confirmed (no 7.5-pt close retrace). A buy-stop under
the market is a market order: Sierra filled the runner within 4 seconds.

With `last_close` (SWING_TRAIL_SIDE_GUARD_V1 in the manager) a confirmed pivot
the market has traded through is not "the structure that must hold": the pure
function answers None (= HOLD). Without it the legacy answer is byte-identical.
"""
import unittest

from backend.v9.services.trade_manager.swing_trail import (
    last_confirmed_swing, swing_trail_stop)


def _bar(h, l, c):
    return {"high": h, "low": l, "close": c}


# The 21.10 shape, 5-min closes: IB high confirmed (close retrace >= 7.5 to the
# 7751 low), the low confirmed by the rally, then a rally to 7796.75 with no
# 7.5-pt close retrace -> the up-leg's high is NOT a confirmed pivot yet.
BARS_2110 = [
    _bar(7780.00, 7764.50, 7769.50),   # 16:30
    _bar(7777.25, 7767.50, 7777.00),
    _bar(7778.75, 7764.75, 7768.75),
    _bar(7780.75, 7767.75, 7778.50),   # 16:45 -> the pivot HIGH (bar high 7780.75)
    _bar(7779.50, 7769.75, 7772.50),
    _bar(7779.50, 7772.25, 7773.75),
    _bar(7777.00, 7765.75, 7766.50),   # 17:00 close 7766.50 -> 7778.50-7766.50 = 12 >= 7.5: H confirmed
    _bar(7766.75, 7755.00, 7755.50),
    _bar(7757.75, 7751.00, 7754.75),   # 17:10 -> the pivot LOW (bar low 7751.00)
    _bar(7758.50, 7752.50, 7755.75),
    _bar(7761.75, 7752.25, 7758.25),
    _bar(7764.00, 7755.50, 7761.00),
    _bar(7768.50, 7760.00, 7766.25),   # 17:30 close 7766.25 -> L confirmed (>= 7.5 off 7754.75)
    _bar(7768.00, 7761.25, 7762.50),
    _bar(7771.75, 7762.00, 7769.25),
    _bar(7778.50, 7769.00, 7776.75),
    _bar(7779.50, 7774.25, 7775.00),
    _bar(7778.50, 7772.75, 7776.25),
    _bar(7778.75, 7774.25, 7777.75),
    _bar(7779.75, 7775.50, 7777.50),
    _bar(7782.75, 7777.75, 7782.00),   # 18:10 break of the IB high
    _bar(7784.50, 7777.00, 7777.50),
    _bar(7783.75, 7776.25, 7780.75),
    _bar(7789.25, 7779.75, 7787.50),
    _bar(7790.00, 7786.75, 7788.50),
    _bar(7795.75, 7788.00, 7794.00),
    _bar(7794.50, 7791.50, 7793.00),
    _bar(7796.25, 7793.00, 7796.00),   # 18:45 -> the up-leg's running high (unconfirmed)
    _bar(7796.75, 7793.25, 7793.75),
    _bar(7795.50, 7793.00, 7794.00),
    _bar(7795.00, 7791.00, 7792.75),
    _bar(7794.00, 7789.75, 7791.25),
    _bar(7793.75, 7790.25, 7793.25),
    _bar(7794.25, 7791.75, 7792.75),
    _bar(7794.25, 7791.00, 7792.25),
    _bar(7792.25, 7787.75, 7790.25),   # 19:25 — the bar the 19:28 trail acted on (close 7790.25)
]
REV = 7.5


class TestLegacyIsByteIdentical(unittest.TestCase):
    def test_short_legacy_answer_is_the_stale_ib_high(self):
        self.assertEqual(swing_trail_stop(BARS_2110, "SHORT", rev=REV), 7781.0,
                         "the 21.10 answer: IB high 7780.75 + 1 tick, 9 pt UNDER the market")

    def test_no_last_close_means_no_filter(self):
        sw = last_confirmed_swing(BARS_2110, "SHORT", REV)
        self.assertIsNotNone(sw)
        self.assertEqual(sw["kind"], "H")
        self.assertEqual(sw["price"], 7780.75)


class TestSideGuard(unittest.TestCase):
    def test_short_pivot_behind_the_price_is_refused(self):
        self.assertIsNone(swing_trail_stop(BARS_2110, "SHORT", rev=REV, last_close=7790.25),
                          "a confirmed swing high below the close is behind a SHORT — HOLD")
        self.assertIsNone(last_confirmed_swing(BARS_2110, "SHORT", REV, last_close=7790.25))

    def test_short_pivot_in_front_of_the_price_still_trails(self):
        # Same session seen from 17:05 (price 7755.50 under the confirmed high): the trail is valid.
        bars = BARS_2110[:8]
        self.assertEqual(swing_trail_stop(bars, "SHORT", rev=REV, last_close=7755.50), 7781.0)

    def test_long_is_symmetric(self):
        # A LONG runner at 17:30 trails under the confirmed low 7751.00 (close 7766.25 above it).
        bars = BARS_2110[:13]
        self.assertEqual(swing_trail_stop(bars, "LONG", rev=REV, last_close=7766.25), 7750.75)
        # ...and if the market had fallen through that low, the pivot is no protection.
        self.assertIsNone(swing_trail_stop(bars, "LONG", rev=REV, last_close=7749.00))

    def test_garbage_last_close_falls_back_to_legacy(self):
        self.assertEqual(swing_trail_stop(BARS_2110, "SHORT", rev=REV, last_close="n/a"), 7781.0)


if __name__ == "__main__":
    unittest.main()
