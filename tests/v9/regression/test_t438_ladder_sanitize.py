"""T-438 — the live fire of 2026-09-21 18:30:03 that was rejected and lost.

The incident, from the raw evidence (not from memory):

    [Gateway] §3 STRUCT_TARGETS_WIN: ... 7782.50 / 7768.50 / 7754.50
    [TargetSpacing] SHADOW would-be: t2 7786.00 dropped
    [SierraCmd] T-335 LADDER INVALID: SHORT targets [7782.5, 7786.0, 7779.0]
                are not monotonic in trade direction — PLACE blocked

`v9_trades` #2038 (live, SHORT, entry 7796.50, stop 7800.00) carries exactly
that ladder and `exit_reason='ladder_invalid'`. No order ever reached Sierra.

The producer is arithmetic, not mystery — `_clamp_targets_to_max_r` caps t2/t3
at T2_MAX_R/T3_MAX_R multiples of RISK, while t1 came from STRUCT_TARGETS_WIN
and is NOT subject to that cap. With risk 3.50 and a structural t1 14.00 out
(4R), the cap pulled t2 to 3R = 7786.00 and t3 to 5R = 7779.00 — *inside* t1.
The ladder inverted. Note the ladder is NOT "wrong side of entry": every leg
is below the SHORT entry and in profit. The defect is ORDER, and a fix that
only checked the side of entry would not have saved this fire.

Same class as T-428 (`OPENING_STOP_STRUCTURAL_V1`, RULED_FLAGS 20.09): one
stage anchors t1, another recomputes t2/t3 off a smaller risk → inversion →
T-335 blocks the whole PLACE.

Learning doctrine 09.09: an incident becomes a REPLAY CASE, not a flag. This
file is that case, and it is wired into `scripts/guard_tests.sh` so `T-335=0`
stays a gate condition.

Mutation-sensitivity is the point: revert the sanitizer and
`test_golden_2038_places_with_t1_only` fails.
"""
import os
import unittest


# The #2038 row, verbatim from v9_trades (see module docstring).
ENTRY = 7796.5
STOP = 7800.0
T1 = 7782.5           # structural — STRUCT_TARGETS_WIN, survives every clamp
T2_CLAMPED = 7786.0   # 3R — inside T1 → the inversion
T3_CLAMPED = 7779.0   # 5R — also inside T1
STRUCT_T2 = 7768.5    # what STRUCT_TARGETS_WIN actually produced
STRUCT_T3 = 7754.5


def _setup(**over):
    s = {
        "direction": "SHORT",
        "entry_price": ENTRY,
        "stop": STOP,
        "t1": T1,
        "t2": T2_CLAMPED,
        "t3": T3_CLAMPED,
        "contracts": 1,          # FIXED_CONTRACTS_1 — Michael 18.09
        "classification": "CEILING_FLIP_SHORT",
        "firing_system": 2,
        "confidence": 0.7,
        "metadata": {},
    }
    s.update(over)
    return s


class _EnvPinned(unittest.TestCase):
    """T-432 lesson: a test pins its own environment, it never assumes .env."""

    PIN = {
        "T2_MAX_R": "3.0",
        "T3_MAX_R": "5.0",
        "T3_REQUIRED_V1": "1",
        "ZLR_MGMT_V1": "0",
        "T0_TARGET_PTS": "0",
        "RUNNER_TRAIL_V2": "0",
        "RUNNER_BY_DAYTYPE_V1": "0",
        "C4_RULING6_V1": "0",
        "TARGET_MIN_SPACING_V1": "shadow",
        "SITUATION_VECTOR_LOG_V1": "0",
    }

    def setUp(self):
        self._prev = {k: os.environ.get(k)
                      for k in list(self.PIN) + ["LADDER_SANITIZE_V1",
                                                 "MEMS26_SIGNALS_DIR"]}
        os.environ.update(self.PIN)
        import tempfile
        self._tmp = tempfile.mkdtemp(prefix="t438_signals_")
        os.environ["MEMS26_SIGNALS_DIR"] = self._tmp

    def tearDown(self):
        for k, v in self._prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class TestInversionProducer(_EnvPinned):
    """Section 2 evidence, pinned as a test: WHO wrote t2=7786.00.

    Not a guess — the exact call with the exact #2038 numbers.
    """

    def test_r_clamp_is_the_writer_of_7786_and_7779(self):
        from backend.v9.gateway.trading_gateway import TradingGateway
        out = TradingGateway._clamp_targets_to_max_r(
            "SHORT", ENTRY, STOP, T1, STRUCT_T2, STRUCT_T3)
        self.assertEqual(
            out, (T1, T2_CLAMPED, T3_CLAMPED),
            "the R-clamp no longer reproduces #2038 — if this is intentional, "
            "the T-438 finding must be re-derived before relaxing the fix")

    def test_the_clamp_leaves_t1_beyond_t2_ie_inverted(self):
        from backend.v9.gateway.trading_gateway import TradingGateway
        t1, t2, t3 = TradingGateway._clamp_targets_to_max_r(
            "SHORT", ENTRY, STOP, T1, STRUCT_T2, STRUCT_T3)
        # SHORT: farther out = lower. t2 ABOVE t1 is the inversion.
        self.assertGreater(t2, t1, "no inversion — the fixture has drifted")
        # And every leg is still on the PROFIT side of a SHORT entry, which is
        # why a wrong-side-only check cannot catch this.
        for leg in (t1, t2, t3):
            self.assertLess(leg, ENTRY)


class TestGoldenReplay2038(_EnvPinned):
    """Section 1: replay the ladder that reached sierra_command.py:920."""

    def test_golden_2038_places_with_t1_only(self):
        from backend.v9.services.sierra_command import command_from_setup
        cmd = command_from_setup(_setup(), trade_id="t438-golden",
                                 account="SIM", mode="demo")
        self.assertFalse(
            cmd.get("rejected"),
            "PLACE still rejected (%s) — the fire of 21.09 18:30:03 is still "
            "lost" % cmd.get("reason"))
        self.assertEqual(cmd.get("op"), "PLACE")
        self.assertEqual(cmd.get("action"), "SELL")
        self.assertEqual(
            cmd.get("target_price"), T1,
            "T1 must survive untouched — it is the leg the R:R gate and "
            "TARGET_REALISM already ruled on")
        ctx = cmd.get("context") or {}
        self.assertIn(ctx.get("t2"), (None, 0, 0.0),
                      "the inverted t2 must be DROPPED, never sent")
        self.assertIn(ctx.get("t3"), (None, 0, 0.0),
                      "t3 sat inside t1 too — it must be dropped with t2")

    def test_t335_gate_is_never_reached_for_this_ladder(self):
        """`T-335=0` stays a gate condition: the sanitizer runs BEFORE it, so a
        producible ladder can no longer trip it."""
        from backend.v9.services import sierra_command as sc
        seen = []
        real = sc.logger.error

        def spy(msg, *a, **kw):
            seen.append(str(msg) % a if a else str(msg))
            return real(msg, *a, **kw)

        sc.logger.error = spy
        try:
            sc.command_from_setup(_setup(), trade_id="t438-gate",
                                  account="SIM", mode="demo")
        finally:
            sc.logger.error = real
        self.assertFalse([s for s in seen if "LADDER INVALID" in s],
                         "T-335 fired — the sanitizer did not run before it")


class TestWrongSideIsDropped(_EnvPinned):
    """The literal ask in the order: a target on the LOSING side of entry is
    thrown away, never sent."""

    def test_short_target_above_entry_is_dropped(self):
        from backend.v9.services.sierra_command import command_from_setup
        cmd = command_from_setup(
            _setup(t2=ENTRY + 5.0, t3=None), trade_id="t438-wrongside",
            account="SIM", mode="demo")
        self.assertFalse(cmd.get("rejected"), cmd.get("reason"))
        self.assertEqual(cmd.get("target_price"), T1)
        self.assertIn((cmd.get("context") or {}).get("t2"), (None, 0, 0.0))

    def test_long_target_below_entry_is_dropped(self):
        from backend.v9.services.sierra_command import command_from_setup
        cmd = command_from_setup(
            _setup(direction="LONG", entry_price=7796.5, stop=7793.0,
                   t1=7810.5, t2=7790.0, t3=None),
            trade_id="t438-wrongside-long", account="SIM", mode="demo")
        self.assertFalse(cmd.get("rejected"), cmd.get("reason"))
        self.assertEqual(cmd.get("target_price"), 7810.5)
        self.assertIn((cmd.get("context") or {}).get("t2"), (None, 0, 0.0))


class TestValidLadderUntouched(_EnvPinned):
    """No 'while I'm here': a healthy ladder must be byte-identical."""

    def test_monotonic_short_ladder_passes_through(self):
        from backend.v9.services.sierra_command import command_from_setup
        cmd = command_from_setup(
            _setup(t2=STRUCT_T2, t3=STRUCT_T3), trade_id="t438-ok",
            account="SIM", mode="demo")
        self.assertFalse(cmd.get("rejected"), cmd.get("reason"))
        ctx = cmd.get("context") or {}
        self.assertEqual(cmd.get("target_price"), T1)
        self.assertEqual(ctx.get("t2"), STRUCT_T2)
        self.assertEqual(ctx.get("t3"), STRUCT_T3)

    def test_monotonic_long_ladder_passes_through(self):
        from backend.v9.services.sierra_command import command_from_setup
        cmd = command_from_setup(
            _setup(direction="LONG", entry_price=7700.0, stop=7696.0,
                   t1=7706.0, t2=7712.0, t3=7718.0),
            trade_id="t438-ok-long", account="SIM", mode="demo")
        self.assertFalse(cmd.get("rejected"), cmd.get("reason"))
        ctx = cmd.get("context") or {}
        self.assertEqual(cmd.get("target_price"), 7706.0)
        self.assertEqual(ctx.get("t2"), 7712.0)
        self.assertEqual(ctx.get("t3"), 7718.0)


class TestNoUnprotectedContract(_EnvPinned):
    """Dropping a leg must never ship a contract with no target.

    The sanitizer runs BEFORE the T-214 t3 belt precisely so that a dropped t3
    on >=3 contracts is still a rejection — "PLACE continues with T1 only" is
    correct at the ruled 1-contract size (ladder (1,0,0,0)), not at three.
    """

    def test_three_contracts_with_dropped_t3_is_still_rejected(self):
        from backend.v9.services.sierra_command import command_from_setup
        cmd = command_from_setup(_setup(contracts=3),
                                 trade_id="t438-3c", account="SIM", mode="demo")
        self.assertTrue(
            cmd.get("rejected"),
            "3 contracts with t2/t3 dropped would leave two contracts without "
            "a target — T3_REQUIRED_V1 must still reject")
        self.assertEqual(cmd.get("reason"), "t3_missing")


class TestKillSwitch(_EnvPinned):
    """LADDER_SANITIZE_V1=0 restores the pre-fix behaviour exactly."""

    def test_flag_off_reproduces_the_21_09_rejection(self):
        os.environ["LADDER_SANITIZE_V1"] = "0"
        from backend.v9.services.sierra_command import command_from_setup
        cmd = command_from_setup(_setup(), trade_id="t438-off",
                                 account="SIM", mode="demo")
        self.assertTrue(cmd.get("rejected"))
        self.assertEqual(cmd.get("reason"), "ladder_invalid")


if __name__ == "__main__":
    unittest.main()
