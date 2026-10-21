"""T-629 — the step detector (מדרגה: impulse → pause → test) on the 21.10.2026 RTH bars.

Mechanics only (the parameters k/m/n/r/tol are the measurement's business): the detector finds the 18:15–18:45
up-step of the accepted extension and the 16:55–17:15 down-step of the opening rotation, a test is recognised
only on a closed bar that probed the base and closed back on the step's side, and nothing here looks ahead.
"""
import unittest

from backend.v9.systems.steps import detect_steps, entry_from_step, last_step, step_test


def _b(o, h, l, c):
    return {"open": o, "high": h, "low": l, "close": c}


# 21.10.2026 RTH 5-min bars, 16:30 → 19:45 IL (v9_bars_5min), index 0 = 16:30
BARS = [
    _b(7779.25, 7780.00, 7764.50, 7769.50),  # 0  16:30
    _b(7769.50, 7777.25, 7767.50, 7777.00),  # 1  16:35
    _b(7777.00, 7778.75, 7764.75, 7768.75),  # 2  16:40
    _b(7768.75, 7780.75, 7767.75, 7778.50),  # 3  16:45
    _b(7778.75, 7779.50, 7769.75, 7772.50),  # 4  16:50
    _b(7772.75, 7779.50, 7772.25, 7773.75),  # 5  16:55
    _b(7773.75, 7777.00, 7765.75, 7766.50),  # 6  17:00
    _b(7766.25, 7766.75, 7755.00, 7755.50),  # 7  17:05
    _b(7755.25, 7757.75, 7751.00, 7754.75),  # 8  17:10
    _b(7754.75, 7758.50, 7752.50, 7755.75),  # 9  17:15
    _b(7755.75, 7761.75, 7752.25, 7758.25),  # 10 17:20
    _b(7758.50, 7764.00, 7755.50, 7761.00),  # 11 17:25
    _b(7760.75, 7768.50, 7760.00, 7766.25),  # 12 17:30
    _b(7766.75, 7768.00, 7761.25, 7762.50),  # 13 17:35
    _b(7762.50, 7771.75, 7762.00, 7769.25),  # 14 17:40
    _b(7769.25, 7778.50, 7769.00, 7776.75),  # 15 17:45
    _b(7777.00, 7779.50, 7774.25, 7775.00),  # 16 17:50
    _b(7775.00, 7778.50, 7772.75, 7776.25),  # 17 17:55
    _b(7776.25, 7778.75, 7774.25, 7777.75),  # 18 18:00
    _b(7777.75, 7779.75, 7775.50, 7777.50),  # 19 18:05
    _b(7777.75, 7782.75, 7777.75, 7782.00),  # 20 18:10
    _b(7782.00, 7784.50, 7777.00, 7777.50),  # 21 18:15
    _b(7777.75, 7783.75, 7776.25, 7780.75),  # 22 18:20
    _b(7780.50, 7789.25, 7779.75, 7787.50),  # 23 18:25
    _b(7787.50, 7790.00, 7786.75, 7788.50),  # 24 18:30
    _b(7788.50, 7795.75, 7788.00, 7794.00),  # 25 18:35
    _b(7794.00, 7794.50, 7791.50, 7793.00),  # 26 18:40
    _b(7793.00, 7796.25, 7793.00, 7796.00),  # 27 18:45
    _b(7796.00, 7796.75, 7793.25, 7793.75),  # 28 18:50
    _b(7793.75, 7795.50, 7793.00, 7794.00),  # 29 18:55
    _b(7794.00, 7795.00, 7791.00, 7792.75),  # 30 19:00
    _b(7792.50, 7794.00, 7789.75, 7791.25),  # 31 19:05
    _b(7791.25, 7793.75, 7790.25, 7793.25),  # 32 19:10
    _b(7793.25, 7794.25, 7791.75, 7792.75),  # 33 19:15
    _b(7793.00, 7794.25, 7791.00, 7792.25),  # 34 19:20
    _b(7792.00, 7792.25, 7787.75, 7790.25),  # 35 19:25
    _b(7790.25, 7791.75, 7788.75, 7790.00),  # 36 19:30
    _b(7790.00, 7805.75, 7789.25, 7804.00),  # 37 19:35
    _b(7804.25, 7806.50, 7795.00, 7798.00),  # 38 19:40
    _b(7798.00, 7799.25, 7794.75, 7797.50),  # 39 19:45
]
ATR = 9.0
KW = dict(k_impulse=1.5, m_bars=4, n_pause=2, r_pause=0.7)


class TestStepsOn2110(unittest.TestCase):
    def test_finds_the_rotation_down_step_and_the_extension_up_step(self):
        steps = detect_steps(BARS, ATR, **KW)
        dirs = [(s["dir"], s["i1"]) for s in steps]
        self.assertIn(("DOWN", 7), dirs, "16:55→17:05 drop (−18.25 in 2 closes) is a DOWN impulse")
        up = [s for s in steps if s["dir"] == "UP" and s["i1"] == 25]
        self.assertTrue(up, "18:15→18:35 (+16.5 over 4 closes) is the extension's UP impulse: %s" % dirs)
        s = up[0]
        self.assertEqual(s["extreme"], 7795.75)
        self.assertEqual(s["base"], 7791.50, "the pause low (18:40) is the base")
        self.assertEqual((s["p0"], s["p1"], s["confirm_i"]), (26, 27, 27), "confirmed when the 2-bar pause closed (18:45)")

    def test_down_step_base_is_the_pause_high(self):
        s = [x for x in detect_steps(BARS, ATR, **KW) if x["dir"] == "DOWN" and x["i1"] == 7][0]
        self.assertEqual(s["extreme"], 7755.00)
        self.assertEqual(s["base"], 7758.50, "17:10/17:15 pause high")
        t = step_test(BARS, s, tol=0.5)
        self.assertIsNotNone(t)
        self.assertEqual((t["i"], t["held"]), (10, True), "17:20 probed 7761.75 and closed 7758.25 under the base")

    def test_up_step_test_is_the_first_probe_that_closes_back_above_base(self):
        s = last_step(BARS, ATR, "LONG", **KW)
        self.assertEqual(s["i1"], 37, "the latest confirmed UP step is the 19:35 impulse")
        s = [x for x in detect_steps(BARS, ATR, **KW) if x["dir"] == "UP" and x["i1"] == 25][0]
        t = step_test(BARS, s, tol=0.5)
        self.assertEqual((t["i"], t["held"]), (30, True),
                         "18:50/18:55 never reached base+tol; 19:00 probed 7791.00 and closed 7792.75 > base → held "
                         "(and the market then broke it at 19:05 — the parameters are the measurement's business)")
        e = entry_from_step(s, t, stop_offset_ticks=1, t1_r=1.5)
        self.assertEqual((e["direction"], e["entry"], e["stop"], e["t1"]), ("LONG", 7792.75, 7791.25, 7795.00))

    def test_no_test_means_no_entry(self):
        s = last_step(BARS, ATR, "LONG", **KW)      # the 19:35 step: pause 19:40–19:45, base 7794.75
        self.assertEqual(s["base"], 7794.75)
        self.assertIsNone(step_test(BARS, s, tol=0.5), "no bar after the pause has printed yet")
        self.assertIsNone(entry_from_step(s, None))

    def test_invalidation_is_a_close_through_the_base(self):
        s = {"dir": "UP", "base": 7791.50, "extreme": 7795.75, "impulse_pts": 19.5, "i0": 21, "i1": 25,
             "p0": 26, "p1": 27, "confirm_i": 27}
        bars = BARS[:30] + [_b(7792.50, 7794.00, 7788.00, 7790.00)]   # 18:50/18:55 untested, then a close 1.5 under the base
        t = step_test(bars, s, tol=0.5)
        self.assertEqual((t["held"], t.get("invalidated")), (False, True))

    def test_lookahead_free_prefix_property(self):
        full = detect_steps(BARS, ATR, **KW)
        for k in range(10, len(BARS) + 1):
            part = detect_steps(BARS[:k], ATR, **KW)
            self.assertEqual(part, full[:len(part)], "a step confirmed on a prefix must be identical on the full series (k=%d)" % k)
            self.assertTrue(all(s["confirm_i"] < k for s in part))

    def test_honest_empty_without_atr(self):
        self.assertEqual(detect_steps(BARS, None, **KW), [])
        self.assertEqual(detect_steps(BARS[:3], ATR, **KW), [])


if __name__ == "__main__":
    unittest.main()
