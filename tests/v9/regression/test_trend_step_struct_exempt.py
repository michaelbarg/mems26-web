"""F4 / G2 — the staircase must not be killed for standing where it is born.

A1 (`structural_targets_wrong_side`, live since 08-11) blocks a setup when EVERY
structural objective — IB edges, POC, VAH/VAL — lands behind the entry. Its
premise is "market structure offers no target in this direction".

That premise is false for a stair. A TREND_STEP entry happens AT the session
extreme by construction, so every structural level necessarily sits behind it —
A1 therefore kills EVERY stair-long at a high, for a reason that is a property
of the pattern and not of the location. And the stair never asked structure for
its objectives: it arrives carrying its own measured ladder (stop = pause
extreme + 10% of the impulse, targets 0.45/0.80/1.30 x impulse), marked by
`stop_source == TREND_STEP_LEG`.

Retro-audit (RETRO_BACKTEST_2026-08-20 §G2) over every session since A1 went
live: exactly two verdicts.
  KILLER  08-19 10:50 ET  TREND_STEP LONG @7747.0  MFE +17.75pt, replay +$150
  SAVER   08-14 11:50 ET  ZLR SHORT @7800.75       ~-$93 avoided
Exempting ONLY stairs keeps the save — which is what the ZLR test below pins.

n=2. The evidence is thin and one-directional, so the exemption is one flag,
default OFF in code, loud on every firing, and reversible. These tests pin all
four corners: OFF is byte-identical, a stair is exempted, a NON-stair is still
vetoed, and a setup with no `stop_source` is NOT exempted.
"""
from __future__ import annotations

import zoneinfo

import pytest

from backend.v9.gateway import trading_gateway as tg


# ── ground truth, straight out of the decisions archive ──────────────────────
# ~/SierraChart_Data/v9_export/gateway_decisions.jsonl, the ONLY TREND_STEP the
# gate ever killed:
#   {"ts": "2026-08-19T14:50:04+00:00", "system": 4, "pattern": "TREND_STEP",
#    "direction": "LONG", "entry": 7747.0,
#    "blocked_by": "structural_targets_wrong_side",
#    "reason": "ALL structural targets on wrong side of LONG entry=7747.0
#               (c1=7754.25, c2=7761.5, c3=7768.75, day_type=Normal)"}
# The printed c1/c2/c3 are POST-fallback: `_build_result` flags all_wrong_side
# first, then replaces the wrong-side levels with 1R/2R/3R. 7754.25 = entry+1R
# => the risk that reached A1 was 7.25pt. That is what LIVE_RISK reproduces.
STAIR_ENTRY = 7747.0
STAIR_DAY_TYPE = "Normal"
STAIR_LIVE_RISK = 7.25
STAIR_LIVE_STOP = STAIR_ENTRY - STAIR_LIVE_RISK              # 7739.75
STAIR_LIVE_REASON = (
    "ALL structural targets on wrong side of LONG entry=7747.0 "
    "(c1=7754.25, c2=7761.5, c3=7768.75, day_type=Normal)")

# On a Normal day `_resolve_normal` gives LONG c1=IB-center, c2=VAH, c3=IBH.
# A stair long stands ABOVE all of them by construction — that IS the geometry.
TPO_NORMAL = {
    "ib_high": 7742.0, "ib_low": 7702.0, "poc": 7727.0,
    "vah": 7738.0, "val": 7712.0, "ib_width": 40.0,
}

# The 08-19 10:45 ET staircase as the detector models it: impulse 21.5pt,
# leg-relative stop, targets 0.45/0.80/1.30 x impulse.
STAIR_STOP = 7744.25
STAIR_IMPULSE = 21.5
STAIR_T1 = round(STAIR_ENTRY + 0.45 * STAIR_IMPULSE, 2)   # 7756.68
STAIR_T2 = round(STAIR_ENTRY + 0.80 * STAIR_IMPULSE, 2)   # 7764.20
STAIR_T3 = round(STAIR_ENTRY + 1.30 * STAIR_IMPULSE, 2)   # 7774.95

# The SAVER, same archive:
#   {"ts": "2026-08-14T15:50:03+00:00", "pattern": "ZLR", "direction": "SHORT",
#    "entry": 7800.75, "blocked_by": "structural_targets_wrong_side",
#    "reason": "... (c1=7796.25, c2=7791.75, c3=7787.25, day_type=Variation)"}
# c1 = entry-1R => risk 4.5pt.
ZLR_ENTRY = 7800.75
ZLR_STOP = ZLR_ENTRY + 4.5                                   # 7805.25
# T-249 (2026-09-04): this constant used to pin the OLD sentence,
#   "... (c1=7796.25, c2=7791.75, c3=7787.25, day_type=Variation)"
# which named three levels BELOW a SHORT entry of 7800.75 — i.e. on the CORRECT
# side — as the reason for a wrong-side veto. Those were the R-fallbacks
# `structural_targets` writes AFTER the verdict, not the levels it judged. The
# veto was right; the sentence was not, and this test had frozen it.
ZLR_REASON = (
    "ALL structural targets on wrong side of SHORT entry=7800.75 "
    "— rejected levels c1=7810.0, c2=7810.0, c3=7825.0 "
    "(day_type=Variation); the R-fallbacks that replaced them were "
    "7796.25/7791.75/7787.25")

# Variation SHORT: c1 = IBL - IBwidth/2, c3 = VAL. A short at the session low
# has all of them ABOVE it — the mirror image of the stair's geometry.
TPO_VARIATION = {
    "ib_high": 7840.0, "ib_low": 7820.0, "poc": 7830.0,
    "vah": 7835.0, "val": 7825.0, "ib_width": 20.0,
}


class _TZBoom:
    """Force the IB-lock check to fail-open, so the structural stage runs
    regardless of the wall clock the suite happens to run at."""

    def __init__(self, *a, **k):
        raise RuntimeError("test: force IB-locked fail-open")


# Gates whose flag is read inside a helper module rather than in the gateway
# body, so the source scan below cannot see them.
_EXTERNAL_GATE_FLAGS = (
    "RELEASE_ENTRY_GATE_V1",      # backend/v9/systems/release_gate.py
    "NEWS_BLACKOUT_V1",           # backend/v9/services/news_blackout.py
    "S2_ADAPTIVE_THRESHOLDS_V1",
    "OPENING_WINDOW_FIRE_V1",
    "PATTERN_LOSS_BREAKER_V1",
    "EXTREME_CHASE_GUARD",
    "DIRECTION_COMPASS_V1",
    "LIVE_EXECUTION_V1",
    "LIVE_TRADING_ARMED",
)

# The three flags this file exercises; the blanket isolation must not touch them.
_UNDER_TEST = (
    "TREND_STEP_STRUCT_EXEMPT_V1",
    "DAYTYPE_TARGETS_STRUCTURAL",
    "STRUCTURAL_TARGETS_WRONG_SIDE_VETO_V1",
)


def _isolate_gates(monkeypatch):
    """Silence every gate that is not under test, so a block can only come from
    A1 itself.

    The list is DERIVED from the gateway source (every `os.getenv("X", "0")` —
    i.e. every default-OFF boolean gate) instead of hand-maintained, so a gate
    added tomorrow cannot quietly start blocking this suite and turn its
    assertions into accidents. The three flags this file actually exercises are
    re-enabled by the caller afterwards.
    """
    import inspect
    import re
    src = inspect.getsource(tg)
    found = set(re.findall(r'os\.getenv\(\s*"([A-Z0-9_]+)"\s*,\s*"0"\s*\)', src))
    for flag in sorted(found | set(_EXTERNAL_GATE_FLAGS)) :
        if flag in _UNDER_TEST:
            continue          # the caller owns these three
        monkeypatch.setenv(flag, "0")

    # Not env-gated: a stale feed or an engaged kill-switch would block before
    # the structural stage and make the whole file vacuous.
    from backend.v9.services import feed_watchdog as _fw
    from backend.v9.services import kill_switch as _ks
    monkeypatch.setattr(_fw, "is_feed_alive", lambda *a, **k: (True, "test"))
    monkeypatch.setattr(_ks, "is_engaged", lambda *a, **k: (False, None))


def _gw(monkeypatch, day_type=STAIR_DAY_TYPE, pattern="TREND_STEP", tpo=None):
    _isolate_gates(monkeypatch)
    monkeypatch.setenv("DAYTYPE_TARGETS_STRUCTURAL", "1")
    monkeypatch.setenv("STRUCTURAL_TARGETS_WRONG_SIDE_VETO_V1", "1")
    monkeypatch.setattr(zoneinfo, "ZoneInfo", _TZBoom)
    monkeypatch.setattr(tg, "is_within_firing_window", lambda: True)
    monkeypatch.setattr(
        tg, "extract_g1_entry_context", lambda cc: {"day_type_at_entry": day_type})
    monkeypatch.setattr(tg, "resolve_pattern_id", lambda setup, g1: pattern)
    gw = tg.TradingGateway()
    monkeypatch.setattr(gw, "_execute_shadow", lambda *a, **k: {"trade_id": "t"})
    monkeypatch.setattr(
        gw, "_capture_cross_context",
        lambda: {
            "day_type_machine": {"day_type": day_type},
            "woodies_system": {"trend_state": "GREEN"},
            "tpo_system": dict(tpo if tpo is not None else TPO_NORMAL),
        },
    )
    return gw


def _stair_setup(stop=STAIR_STOP, t1=STAIR_T1, t2=STAIR_T2, t3=STAIR_T3):
    """The 08-19 stair, carrying the leg model exactly as the detector ships it."""
    return {
        "firing_system": 4,
        "direction": "LONG",
        "classification": "TREND_STEP",
        "entry_price": STAIR_ENTRY,
        "stop": stop,
        "t1": t1, "t2": t2, "t3": t3,
        "stop_source": "TREND_STEP_LEG",
        "metadata": {
            "pattern": "TREND_STEP", "trend_step": True,
            "impulse_pts": STAIR_IMPULSE, "stop_source": "TREND_STEP_LEG",
            "step_id": "2026-08-19T10:45|LONG|7747.00",
        },
    }


def _zlr_setup():
    """The 08-14 11:50 ET ZLR SHORT @7800.75 — the SAVER. Same all-wrong-side
    geometry (a short at the session low: every structural level ABOVE it), but
    NO leg model. It must stay blocked, flag or no flag."""
    return {
        "firing_system": 4,
        "direction": "SHORT",
        "classification": "ZLR",
        "entry_price": ZLR_ENTRY,
        "stop": ZLR_STOP,
        "t1": ZLR_ENTRY - 6.0,
        "metadata": {"pattern": "ZLR"},
    }


def _zlr_gw(monkeypatch):
    return _gw(monkeypatch, day_type="Variation", pattern="ZLR", tpo=TPO_VARIATION)


def _route(gw, setup):
    return gw.route_setup(setup, 4)


# ───────────────────────── the veto is real to begin with ─────────────────────

def test_the_harness_reproduces_the_archived_0819_block_verbatim(monkeypatch):
    """Anti-tautology, at the strongest setting available: with the flag off the
    harness must not merely block — it must emit the EXACT reason string the
    live gateway wrote to the decisions archive at 2026-08-19T14:50:04Z. If this
    drifts, every other assertion in this file is about a scenario that never
    happened."""
    monkeypatch.delenv("TREND_STEP_STRUCT_EXEMPT_V1", raising=False)
    gw = _gw(monkeypatch)
    res = _route(gw, _stair_setup(stop=STAIR_LIVE_STOP))
    assert res.get("blocked_by") == "structural_targets_wrong_side"
    assert res.get("reason") == STAIR_LIVE_REASON, (
        "no longer byte-identical to the archived live block:\n  live: %s\n  now:  %s"
        % (STAIR_LIVE_REASON, res.get("reason")))


def test_the_stair_is_blocked_today_anti_tautology(monkeypatch):
    """Same, for the leg-model stop the detector actually ships."""
    monkeypatch.delenv("TREND_STEP_STRUCT_EXEMPT_V1", raising=False)
    gw = _gw(monkeypatch)
    res = _route(gw, _stair_setup())
    assert res.get("blocked_by") == "structural_targets_wrong_side", (
        "A1 no longer blocks the stair — the harness stopped reproducing "
        "the 08-19 KILLER, so the exemption tests are vacuous: %s" % res)


def test_flag_off_is_byte_identical(monkeypatch):
    """OFF must be indistinguishable from before the change: same block, same
    reason string, and no exemption marker anywhere in the result."""
    monkeypatch.setenv("TREND_STEP_STRUCT_EXEMPT_V1", "0")
    gw = _gw(monkeypatch)
    res = _route(gw, _stair_setup(stop=STAIR_LIVE_STOP))
    assert res.get("blocked_by") == "structural_targets_wrong_side"
    assert res.get("reason") == STAIR_LIVE_REASON
    assert "trend_step_struct_exempt" not in res


def test_unset_flag_is_off(monkeypatch):
    """Code default OFF — a clone/restart with no .env line keeps A1 intact."""
    monkeypatch.delenv("TREND_STEP_STRUCT_EXEMPT_V1", raising=False)
    gw = _gw(monkeypatch)
    assert _route(gw, _stair_setup()).get("blocked_by") == \
        "structural_targets_wrong_side"


@pytest.mark.parametrize("junk", ["", "no", "true-ish", "2", "off"])
def test_only_an_explicit_truthy_value_enables(monkeypatch, junk):
    monkeypatch.setenv("TREND_STEP_STRUCT_EXEMPT_V1", junk)
    gw = _gw(monkeypatch)
    assert _route(gw, _stair_setup()).get("blocked_by") == \
        "structural_targets_wrong_side"


# ───────────────────────────── the exemption itself ───────────────────────────

def test_the_stair_is_exempted_when_the_flag_is_on(monkeypatch):
    """THE test: the 08-19 KILLER routes."""
    monkeypatch.setenv("TREND_STEP_STRUCT_EXEMPT_V1", "1")
    gw = _gw(monkeypatch)
    res = _route(gw, _stair_setup())
    assert res.get("blocked_by") is None, (
        "the stair is still blocked: %s / %s"
        % (res.get("blocked_by"), res.get("reason")))


@pytest.mark.parametrize("truthy", ["1", "true", "yes", "TRUE", "Yes"])
def test_the_documented_truthy_spellings_all_work(monkeypatch, truthy):
    monkeypatch.setenv("TREND_STEP_STRUCT_EXEMPT_V1", truthy)
    gw = _gw(monkeypatch)
    assert _route(gw, _stair_setup()).get("blocked_by") is None


def test_the_leg_ladder_survives_the_exemption(monkeypatch):
    """The exemption's own premise is that the stair's targets come from the
    measured leg model. Structure's 'targets' in the all-wrong-side case are
    pure R-fallbacks (1R/2R/3R off the 2.75pt stop) — letting them overwrite
    the ladder would both defeat that premise and INVERT it: 2R = 7752.5 sits
    inside the kept t1 of 7756.68."""
    monkeypatch.setenv("TREND_STEP_STRUCT_EXEMPT_V1", "1")
    gw = _gw(monkeypatch)
    setup = _stair_setup()
    assert _route(gw, setup).get("blocked_by") is None
    assert setup["stop"] == STAIR_STOP
    assert setup["t1"] == STAIR_T1
    assert setup["t2"] == STAIR_T2, "structural R-fallback stomped the leg t2"
    assert setup["t3"] == STAIR_T3, "structural R-fallback stomped the leg t3"
    # ladder still strictly increasing away from entry
    e = setup["entry_price"]
    assert abs(setup["t1"] - e) < abs(setup["t2"] - e) < abs(setup["t3"] - e)


def test_the_firing_is_loud_and_countable(monkeypatch, caplog):
    """n=2 evidence => the live count must be measurable from day one, from
    the log alone."""
    import logging
    monkeypatch.setenv("TREND_STEP_STRUCT_EXEMPT_V1", "1")
    gw = _gw(monkeypatch)
    with caplog.at_level(logging.WARNING, logger="backend.v9.gateway.trading_gateway"):
        res = _route(gw, _stair_setup())
    assert res.get("blocked_by") is None
    hits = [r for r in caplog.records if "TREND_STEP_STRUCT_EXEMPT" in r.getMessage()]
    assert len(hits) == 1, "expected exactly one countable WARNING, got %d" % len(hits)
    assert hits[0].levelno == logging.WARNING
    msg = hits[0].getMessage()
    for token in ("7747.0", "LONG", "TREND_STEP_LEG"):
        assert token in msg, "log line cannot be audited — %r missing: %s" % (token, msg)


def test_the_result_carries_a_machine_readable_marker(monkeypatch):
    monkeypatch.setenv("TREND_STEP_STRUCT_EXEMPT_V1", "1")
    gw = _gw(monkeypatch)
    res = _route(gw, _stair_setup())
    mark = res.get("trend_step_struct_exempt")
    assert isinstance(mark, dict)
    assert mark["entry"] == STAIR_ENTRY
    assert mark["direction"] == "LONG"
    assert mark["stop_source"] == "TREND_STEP_LEG"


# ─────────────────────── the SAVER must stay saved (scope) ────────────────────

def test_a_non_stair_wrong_side_setup_is_still_vetoed(monkeypatch):
    """The 08-14 ZLR — the gate's only SAVER. Flag ON must not touch it, and
    the block must still read exactly as the archive recorded it."""
    monkeypatch.setenv("TREND_STEP_STRUCT_EXEMPT_V1", "1")
    gw = _zlr_gw(monkeypatch)
    res = _route(gw, _zlr_setup())
    assert res.get("blocked_by") == "structural_targets_wrong_side", (
        "the ZLR SAVER (~-$93 avoided) lost its protection: %s" % res)
    assert res.get("reason") == ZLR_REASON
    assert "trend_step_struct_exempt" not in res


def test_a_missing_stop_source_is_not_exempted(monkeypatch):
    """Fail-closed on identity: no marker => no exemption. A stair that lost
    its `stop_source` is not provably carrying the leg model."""
    monkeypatch.setenv("TREND_STEP_STRUCT_EXEMPT_V1", "1")
    gw = _gw(monkeypatch)
    setup = _stair_setup()
    setup.pop("stop_source")
    assert _route(gw, setup).get("blocked_by") == "structural_targets_wrong_side"


@pytest.mark.parametrize("src", [None, "", "StopResolver", "STEP_SCALED_LADDER",
                                 "TREND_STEP", "TREND_STEP_LEG_X"])
def test_only_the_exact_leg_marker_exempts(monkeypatch, src):
    """Classification alone must not exempt — a stair whose ladder was resized
    by another writer no longer carries the measured model."""
    monkeypatch.setenv("TREND_STEP_STRUCT_EXEMPT_V1", "1")
    gw = _gw(monkeypatch)
    setup = _stair_setup()
    setup["stop_source"] = src
    assert _route(gw, setup).get("blocked_by") == "structural_targets_wrong_side"


def test_the_marker_is_case_insensitive(monkeypatch):
    monkeypatch.setenv("TREND_STEP_STRUCT_EXEMPT_V1", "1")
    gw = _gw(monkeypatch)
    setup = _stair_setup()
    setup["stop_source"] = "trend_step_leg"
    assert _route(gw, setup).get("blocked_by") is None


def test_the_exemption_does_not_disable_a1_for_the_next_setup(monkeypatch):
    """Reversibility/scope: the exemption is per-setup state, not a latch."""
    monkeypatch.setenv("TREND_STEP_STRUCT_EXEMPT_V1", "1")
    gw = _gw(monkeypatch)
    assert _route(gw, _stair_setup()).get("blocked_by") is None
    gw2 = _zlr_gw(monkeypatch)
    assert _route(gw2, _zlr_setup()).get("blocked_by") == \
        "structural_targets_wrong_side"


# ───────────────────────────── scope: one branch only ─────────────────────────

def test_the_exemption_lives_only_inside_the_all_wrong_side_branch(monkeypatch):
    """Source-level scope proof: `TREND_STEP_STRUCT_EXEMPT_V1` is read exactly
    once, and inside the `all_wrong_side` branch — so no other path through
    the gateway can change shape."""
    import inspect
    import re
    src = inspect.getsource(tg)
    reads = [m.start() for m in re.finditer(
        r'os\.getenv\(\s*"TREND_STEP_STRUCT_EXEMPT_V1"', src)]
    assert len(reads) == 1, (
        "the flag is read %d times — one gate, one read" % len(reads))
    i = reads[0]
    j = src.rindex("all_wrong_side", 0, i)
    assert i - j < 3000, (
        "the flag drifted out of the all_wrong_side branch — byte-identity "
        "for every other path is no longer guaranteed by construction")


def test_the_ruling_is_recorded_in_ruled_flags():
    """A ruled flag with no RULED_FLAGS row is a flag that will silently drift."""
    import os
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    txt = open(os.path.join(root, "config", "RULED_FLAGS.yaml"),
               encoding="utf-8").read()
    assert "TREND_STEP_STRUCT_EXEMPT_V1" in txt
    line = [l for l in txt.splitlines() if "TREND_STEP_STRUCT_EXEMPT_V1" in l][0]
    assert 'expected: "1"' in line
    assert "2026-08-20" in line
