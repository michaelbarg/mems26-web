"""T-242 (session maturity) + T-236/T-235 (has_pullback wire) — 03.09.

These tests EXECUTE THE REAL GATEWAY BLOCK, not a replica. The ELQ block is
extracted from `TradingGateway._route_setup_inner` source, compiled against the
gateway module globals, and run with `_load_sierra_tpo` / `current_atr14` /
`read_all` patched. A refactor of the block breaks these tests loudly — which is
the point: T-219 shipped with five static source tests that all passed while the
feature produced zero rows.

RAW EVIDENCE the tests replay (backend.err.log, 2026-09-03, log clock = IDT):

  16:30:04  BLOCKED by entry_location_quality: chaser: pos=1.27 > 0.66
            (top 34% of leg, no pullback); beyond_value: ex=1.27 > 0.25
  16:30:04  BLOCKED system=4 pattern=ZLR dir=LONG entry=7704.25

  21:35:07  BLOCKED by entry_location_quality: chaser: pos=0.98 > 0.66
  21:35:07  BLOCKED system=4 pattern=ZLR dir=LONG entry=7764.75

DB facts (local PG, verified):
  first RTH bar 09:30 ET: open=7704.25 high=7718.00 low=7704.25 close=7715.00
    -> the CLOSED bar's high is ABOVE the 7704.25 entry, so leg_extreme<entry
       at 09:30:04 could only come from an intermediate (4-second) state.
  session through 14:35 ET: 62 bars, max(high)=7766.25, min(low)=7698.25
    -> (7764.75-7698.25)/68.00 = 0.978 -> "pos=0.98", matching the log exactly.
  bars 14:25 / 14:30 / 14:35 ET lows: 7762.25 / 7761.25 / 7763.50
    -> 7766.25 - 7762.25 = 4.00pt dip >= PULLBACK_MIN_PTS(3.0) -> a REAL pullback.
"""
import inspect
import textwrap

import pytest

# ── real 03.09 numbers ───────────────────────────────────────────────────────
ATR14 = 8.36            # [Woodies] ATR14=8.36 (03.09 17:34:38 MAE-scratch line)
SESSION_HIGH = 7766.25
SESSION_LOW = 7698.25
ENTRY_1435 = 7764.75    # the 21:35:07Z ZLR LONG
ENTRY_0930 = 7704.25    # the 16:30:04 ZLR LONG — VAL == POC == opening-bar low


def _elq_runner():
    """Extract + compile the REAL ELQ block into a callable."""
    from backend.v9.gateway import trading_gateway as tg
    lines = textwrap.dedent(
        inspect.getsource(tg.TradingGateway._route_setup_inner)).split("\n")
    i0 = next(i for i, l in enumerate(lines)
              if "_elq_mode = os.getenv(" in l and "ENTRY_LOCATION_QUALITY_V1" in l)
    i1 = next(i for i, l in enumerate(lines)
              if i > i0 and l.strip().startswith("# --- SA-3 fix"))
    block = textwrap.dedent("\n".join(lines[i0:i1]))
    src = ("def _elq_run(setup, direction, result):\n"
           + textwrap.indent(block, "    ")
           + "\n    return result\n")
    ns = dict(vars(tg))
    exec(compile(src, "<elq-block>", "exec"), ns)
    return ns["_elq_run"]


def _bar(high, low, closed=True):
    return {"high": high, "low": low, "closed": closed}


def _patch(monkeypatch, *, rows, tpo, atr=None, mode="1", min_bars=None):
    """atr defaults to None — that is PRODUCTION REALITY, not a shortcut.

    The gate does `from backend.v9.shared.atr import current_atr14`, but that
    module defines only _wilder_atr / atr_5min / atr_daily — there is no
    current_atr14 (it lives in systems/target_spacing.py and systems/
    mae_scratch.py). The import raises, the bare `except: pass` swallows it, and
    _elq_atr is None on every candidate. Corroborated: `grep -c expensive_stop
    /tmp/backend.err.log` -> 0 across the whole 91MB log. So the expensive-stop
    third of the 28.08 ruling has never fired either (recorded as a separate
    finding; NOT fixed here — fixing it ADDS a blocking condition, which is a
    trading-risk change and out of tonight's scope).
    With atr None the leg floor is max(1.0, ...) -> 1.0.
    """
    import backend.v9.api.v9.tpo_routes as tpo_routes
    import backend.v9.shared.atr as atr_mod
    import backend.v9.db.read as db_read

    monkeypatch.setenv("ENTRY_LOCATION_QUALITY_V1", mode)
    monkeypatch.setenv("PULLBACK_MIN_PTS", "3.0")
    if min_bars is None:
        monkeypatch.delenv("ELQ_MIN_SESSION_BARS", raising=False)
    else:
        monkeypatch.setenv("ELQ_MIN_SESSION_BARS", str(min_bars))
    monkeypatch.setattr(tpo_routes, "_load_sierra_tpo", lambda *a, **k: dict(tpo))
    if atr is not None:
        monkeypatch.setattr(atr_mod, "current_atr14", lambda *a, **k: atr,
                            raising=False)
    monkeypatch.setattr(db_read, "read_all", lambda *a, **k: list(rows))
    monkeypatch.setattr(db_read, "read_one", lambda *a, **k: None)


def _run(monkeypatch, *, entry, direction, stop, rows, tpo, **kw):
    _patch(monkeypatch, rows=rows, tpo=tpo, **kw)
    run = _elq_runner()
    result = {"shadow": None, "demo": None, "live": None, "blocked_by": None}
    setup = {"entry_price": entry, "stop": stop, "direction": direction}
    return run(setup, direction, result)


# ═════════════════════════════════════════════════════════════════════════════
# T-242 — session maturity at the opening bell
# ═════════════════════════════════════════════════════════════════════════════
class TestT242OpeningBell:
    """A 4-second building bar is not a leg (Rule 1: honest missing)."""

    # 09:30:04 replay. The exact intermediate leg is unrecoverable; what IS
    # proven is leg_extreme < entry with ZERO closed bars. The leg below is
    # 1.25pt wide — above the 1.00 floor, so the FLOOR is deliberately not what
    # fires here (the closed-bar count is) — and yields pos=1.60, the same
    # mathematically-impossible class as the observed 1.27, plus a beyond_value
    # hit off the same 4-second-old developing VA.
    ROWS = [_bar(7703.50, 7702.25, closed=False)]
    TPO = {"vah": 7703.50, "val": 7702.75,
           "session_high": 7703.50, "session_low": 7702.25}

    def test_regression_A_opening_bell_not_blocked(self, monkeypatch):
        """09:30:04, single building bar → position tests skipped → NOT blocked."""
        r = _run(monkeypatch, entry=ENTRY_0930, direction="LONG", stop=7698.0,
                 rows=self.ROWS, tpo=self.TPO)
        assert r["blocked_by"] is None, (
            f"still blocked at the opening bell: {r.get('reason')}")

    def test_mutation_guard_disabled_restores_the_block(self, monkeypatch):
        """MUTATION: ELQ_MIN_SESSION_BARS=0 → the same candidate is blocked again.

        Single-variable proof that the maturity guard — and nothing else — is
        what changed the outcome.
        """
        r = _run(monkeypatch, entry=ENTRY_0930, direction="LONG", stop=7698.0,
                 rows=self.ROWS, tpo=self.TPO, min_bars=0)
        assert r["blocked_by"] == "entry_location_quality"
        assert "pos=1.60" in r["reason"], r["reason"]
        assert "beyond_value" in r["reason"], r["reason"]

    def test_one_closed_bar_still_immature(self, monkeypatch):
        """09:36 ET: 1 closed bar < 2 → still skipped."""
        rows = [_bar(7718.0, 7704.25, closed=True), _bar(7716.0, 7714.0, closed=False)]
        r = _run(monkeypatch, entry=ENTRY_0930, direction="LONG", stop=7698.0,
                 rows=rows, tpo=self.TPO)
        assert r["blocked_by"] is None

    def test_leg_floor_skips_a_degenerate_leg(self, monkeypatch):
        """L below max(1.0, 0.5*ATR) is noise, not a leg → skipped.

        ATR is None in production → floor = 1.0. L here is 0.75.
        """
        rows = [_bar(7704.75, 7704.0, closed=True)] * 4        # 4 closed bars
        tpo = {"vah": 7704.75, "val": 7704.25,
               "session_high": 7704.75, "session_low": 7704.0}  # L = 0.75 < 1.0
        r = _run(monkeypatch, entry=7704.5, direction="LONG", stop=7701.0,
                 rows=rows, tpo=tpo)
        assert r["blocked_by"] is None

    def test_leg_floor_uses_half_atr_when_atr_is_available(self, monkeypatch):
        """If current_atr14 ever starts resolving, the floor becomes 0.5*ATR."""
        rows = [_bar(7705.0, 7703.0, closed=True)] * 4
        tpo = {"vah": 7705.0, "val": 7703.5,
               "session_high": 7705.0, "session_low": 7703.0}   # L = 2.00
        # 2.00 > 1.0 (would be measured) but < 0.5*8.36 = 4.18 (skipped)
        r = _run(monkeypatch, entry=7704.75, direction="LONG", stop=7704.0,
                 rows=rows, tpo=tpo, atr=ATR14)
        assert r["blocked_by"] is None

    def test_db_read_failure_does_not_widen_the_gate(self, monkeypatch):
        """A DB error must NOT be read as 'immature' — no free pass on a bug."""
        import backend.v9.db.read as db_read
        _patch(monkeypatch, rows=[], tpo=self.TPO)

        def _boom(*a, **k):
            raise RuntimeError("simulated DB outage")

        monkeypatch.setattr(db_read, "read_all", _boom)
        run = _elq_runner()
        result = {"shadow": None, "demo": None, "live": None, "blocked_by": None}
        r = run({"entry_price": ENTRY_0930, "stop": 7698.0}, "LONG", result)
        assert r["blocked_by"] == "entry_location_quality", (
            "a failed session-bar read silently opened the gate")


# ═════════════════════════════════════════════════════════════════════════════
# T-242 — a MATURE session must still be measured (no loosening)
# ═════════════════════════════════════════════════════════════════════════════
class TestT242MatureSessionStillMeasured:

    @staticmethod
    def _mature_rows(recent_lows):
        """62 closed bars carrying the real session extremes."""
        rows = [_bar(SESSION_HIGH, SESSION_LOW, closed=True)]
        rows += [_bar(7764.0, 7763.0, closed=True) for _ in range(58)]
        rows += [_bar(7764.5, low, closed=True) for low in recent_lows]
        return rows

    TPO = {"vah": 7766.25, "val": 7719.5,
           "session_high": SESSION_HIGH, "session_low": SESSION_LOW}

    def test_regression_B_true_chaser_still_blocked(self, monkeypatch):
        """62 bars, genuine 68pt leg, NO pullback in the last 3 → still blocked.

        pos = (7764.75-7698.25)/68.00 = 0.978 → the production "pos=0.98".
        """
        rows = self._mature_rows([7763.75, 7764.00, 7763.50])  # dips < 3.0pt
        r = _run(monkeypatch, entry=ENTRY_1435, direction="LONG", stop=7758.0,
                 rows=rows, tpo=self.TPO)
        assert r["blocked_by"] == "entry_location_quality", "gate was loosened"
        assert "pos=0.98" in r["reason"], r["reason"]

    def test_mature_session_is_never_skipped(self, monkeypatch):
        """The maturity guard must not fire on 62 closed bars (proof by outcome:
        the leg WAS measured — pos appears in the reason)."""
        rows = self._mature_rows([7763.75, 7764.00, 7763.50])
        r = _run(monkeypatch, entry=ENTRY_1435, direction="LONG", stop=7758.0,
                 rows=rows, tpo=self.TPO)
        assert "pos=" in (r.get("reason") or ""), (
            "position test was skipped on a mature session")


# ═════════════════════════════════════════════════════════════════════════════
# T-236 / T-235 — has_pullback wire (Michael 28.08 18:50, literal)
# ═════════════════════════════════════════════════════════════════════════════
class TestT236PullbackWire:

    TPO = TestT242MatureSessionStillMeasured.TPO

    def _rows(self, recent_lows):
        return TestT242MatureSessionStillMeasured._mature_rows(recent_lows)

    def test_real_pullback_now_passes(self, monkeypatch):
        """pos>0.66 WITH a real >=3.0pt pullback → passes (the 28.08 exemption).

        These are the REAL 14:25/14:30/14:35 ET lows; 7766.25-7762.25 = 4.00pt.
        """
        rows = self._rows([7762.25, 7761.25, 7763.50])
        r = _run(monkeypatch, entry=ENTRY_1435, direction="LONG", stop=7758.0,
                 rows=rows, tpo=self.TPO)
        assert r["blocked_by"] is None, (
            f"the ruled pullback exemption did not fire: {r.get('reason')}")

    def test_mutation_unwiring_has_pullback_restores_the_block(self, monkeypatch):
        """MUTATION: drop `has_pullback=_elq_has_pb` → the same entry is blocked.

        Proves the wire is live and not decorative.
        """
        from backend.v9.gateway import trading_gateway as tg
        lines = textwrap.dedent(
            inspect.getsource(tg.TradingGateway._route_setup_inner)).split("\n")
        i0 = next(i for i, l in enumerate(lines)
                  if "_elq_mode = os.getenv(" in l and "ENTRY_LOCATION_QUALITY_V1" in l)
        i1 = next(i for i, l in enumerate(lines)
                  if i > i0 and l.strip().startswith("# --- SA-3 fix"))
        block = textwrap.dedent("\n".join(lines[i0:i1]))
        mutant = block.replace("has_pullback=_elq_has_pb,", "")
        assert mutant != block, "mutation target not found — the wire moved?"
        src = ("def _elq_run(setup, direction, result):\n"
               + textwrap.indent(mutant, "    ") + "\n    return result\n")
        ns = dict(vars(tg))
        exec(compile(src, "<elq-mutant>", "exec"), ns)

        _patch(monkeypatch, rows=self._rows([7762.25, 7761.25, 7763.50]),
               tpo=self.TPO)
        result = {"shadow": None, "demo": None, "live": None, "blocked_by": None}
        r = ns["_elq_run"]({"entry_price": ENTRY_1435, "stop": 7758.0},
                           "LONG", result)
        assert r["blocked_by"] == "entry_location_quality", (
            "MUTATION FAILED TO KILL — has_pullback is not actually reaching "
            "assess_entry_quality")

    def test_pullback_just_under_threshold_still_blocks(self, monkeypatch):
        """2.75pt dip < PULLBACK_MIN_PTS(3.0) → not a pullback → still blocked."""
        rows = self._rows([7763.50, 7763.75, 7764.00])   # 7766.25-7763.50 = 2.75
        r = _run(monkeypatch, entry=ENTRY_1435, direction="LONG", stop=7758.0,
                 rows=rows, tpo=self.TPO)
        assert r["blocked_by"] == "entry_location_quality"
        assert "no pullback" in r["reason"]

    def test_pullback_only_outside_last_3_bars_does_not_count(self, monkeypatch):
        """The ECG window is the last 3 bars — an older dip must not exempt."""
        rows = TestT242MatureSessionStillMeasured._mature_rows(
            [7763.75, 7764.00, 7763.50])
        rows[30] = _bar(7764.0, 7755.0, closed=True)   # big dip, 30 bars ago
        r = _run(monkeypatch, entry=ENTRY_1435, direction="LONG", stop=7758.0,
                 rows=rows, tpo=self.TPO)
        assert r["blocked_by"] == "entry_location_quality"

    def test_short_mirror_pullback(self, monkeypatch):
        """SHORT: bounce >= 3.0pt off the session low exempts, identical to ECG."""
        # entry 7710.00 sits INSIDE the value area (ex=0.20 < 0.25) so the only
        # live disqualifier is the chaser test: pos=(7766.25-7710.00)/68 = 0.83.
        rows = [_bar(SESSION_HIGH, SESSION_LOW, closed=True)]
        rows += [_bar(7712.0, 7709.0, closed=True) for _ in range(58)]
        rows += [_bar(7712.0, 7709.0, closed=True),   # 7712.0-7698.25 = 13.75 bounce
                 _bar(7711.0, 7709.5, closed=True),
                 _bar(7710.5, 7709.75, closed=True)]
        tpo = {"vah": 7766.25, "val": 7719.5,
               "session_high": SESSION_HIGH, "session_low": SESSION_LOW}
        r = _run(monkeypatch, entry=7710.0, direction="SHORT", stop=7716.0,
                 rows=rows, tpo=tpo)
        assert r["blocked_by"] is None, r.get("reason")

    def test_short_no_pullback_still_blocked(self, monkeypatch):
        """SHORT with no bounce >= 3.0pt in the last 3 bars → still blocked."""
        rows = [_bar(SESSION_HIGH, SESSION_LOW, closed=True)]
        rows += [_bar(7700.0, 7699.0, closed=True) for _ in range(58)]
        rows += [_bar(7700.5, 7699.0, closed=True),
                 _bar(7700.75, 7699.0, closed=True),
                 _bar(7700.5, 7698.75, closed=True)]
        tpo = {"vah": 7766.25, "val": 7719.5,
               "session_high": SESSION_HIGH, "session_low": SESSION_LOW}
        r = _run(monkeypatch, entry=7699.75, direction="SHORT", stop=7706.0,
                 rows=rows, tpo=tpo)
        assert r["blocked_by"] == "entry_location_quality"
        assert "no pullback" in r["reason"]


# ═════════════════════════════════════════════════════════════════════════════
# Thresholds are untouched (T-225 discipline: no sizing/threshold drift)
# ═════════════════════════════════════════════════════════════════════════════
def test_thresholds_unchanged():
    from backend.v9.systems.entry_location_quality import DEFAULTS
    assert DEFAULTS["pos_max"] == 0.66
    assert DEFAULTS["rr_max"] == 1.5
    assert DEFAULTS["ex_max"] == 0.25


def test_elq_does_not_reuse_chase_min_session_bars():
    """CHASE_MIN_SESSION_BARS is 8 in .env — reusing it would blank the position
    tests for the first 40 minutes. The ELQ guard has its OWN var."""
    from backend.v9.gateway import trading_gateway as tg
    lines = textwrap.dedent(
        inspect.getsource(tg.TradingGateway._route_setup_inner)).split("\n")
    i0 = next(i for i, l in enumerate(lines)
              if "_elq_mode = os.getenv(" in l and "ENTRY_LOCATION_QUALITY_V1" in l)
    i1 = next(i for i, l in enumerate(lines)
              if i > i0 and l.strip().startswith("# --- SA-3 fix"))
    block = "\n".join(lines[i0:i1])
    code = "\n".join(l for l in block.split("\n") if not l.strip().startswith("#"))
    assert 'os.getenv("ELQ_MIN_SESSION_BARS"' in code
    assert "CHASE_MIN_SESSION_BARS" not in code
