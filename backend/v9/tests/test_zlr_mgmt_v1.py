"""ZLR_MGMT_V1 (Michael ruling 2026-07-14) — ZLR / System-4 ONLY.

Proves, flag ON vs OFF, the four spec axes:
  (a) allocation — ZLR bracket sends 2 contracts to T1 + 1 to T2 when ON
      (per-contract targets [T1, T1, T2]); the classic 1/1/1 ladder when OFF.
  (b) scope — a NON-ZLR setup is byte-identical (1/1/1) even with the flag ON.
  (c) pre-T1 hard rule — a ZLR per-bar stop-move is BLOCKED when ON, and runs
      exactly as today when OFF.
  (d) post-T1 BE — after T1 the ZLR runner's stop goes to PLAIN entry (BE),
      overriding STOP_STRUCTURE_TRAIL_V1 and the BE+1T fallback, ZLR only.

Flag OFF (default, no env var) is the code default → every assertion below shows
the OFF branch is unchanged from today. Enabling ZLR_MGMT_V1 is Michael's call.

Anti-tautological: each ON assertion differs from the OFF/pre-change value
(allocation t2/t3 swap; blocked vs moved stop; plain-BE 7500.0 vs BE+1T 7500.25 /
struct 7497.5). Run: python3 -m pytest backend/v9/tests/test_zlr_mgmt_v1.py -v
"""
import os
import sys
import types

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from backend.v9.services.sierra_command import command_from_setup, _is_zlr_setup  # noqa: E402
from backend.v9.services.trade_manager.manager import (  # noqa: E402
    TradeManager,
    is_zlr_trade,
)


# ── shared fixtures ────────────────────────────────────────────────────────

def _zlr_setup(**over):
    """A System-4 woodies ZLR fire as it reaches command_from_setup
    (classification == metadata.pattern == 'ZLR', firing_system == 4)."""
    s = {
        "firing_system": 4,
        "direction": "LONG",
        "classification": "ZLR",
        "confidence": 0.7,
        "metadata": {"pattern": "ZLR", "sizing": 3},
        "contracts": 3,
        "entry_price": 7500.0,
        "stop": 7492.0,
        "t1": 7503.0,
        "t2": 7506.0,
        "t3": 7509.0,
    }
    s.update(over)
    return s


def _reactive_setup():
    """A System-2 REACTIVE fire — NOT ZLR — same price geometry."""
    return _zlr_setup(
        firing_system=2,
        classification="REACTIVE_LONG",
        metadata={"pattern": "REACTIVE_LONG", "sizing": 3},
    )


def _run_command(setup, monkeypatch, tmp_path, zlr_on):
    """Call command_from_setup under an isolated flag/dir environment and return
    the written PLACE payload."""
    monkeypatch.setenv("MEMS26_SIGNALS_DIR", str(tmp_path))
    for _f in ("FIXED_CONTRACTS_2", "FIXED_CONTRACTS_3", "SIZE_CAP_OVER_FIXED_V1"):
        monkeypatch.delenv(_f, raising=False)
    if zlr_on:
        monkeypatch.setenv("ZLR_MGMT_V1", "1")
    else:
        monkeypatch.delenv("ZLR_MGMT_V1", raising=False)
    return command_from_setup(setup, trade_id="T-ZLR", account="SIM", mode="demo")


def _mk_tm():
    """A TradeManager with no DB (skip __init__); log/emit are captured."""
    tm = TradeManager.__new__(TradeManager)
    tm._mgmt_log = []
    tm._log_management = lambda tid, kind, payload: tm._mgmt_log.append((tid, kind, payload))
    tm._emits = []
    tm._emit_modify_stop = lambda trade, stop: tm._emits.append((trade.id, stop))
    return tm


def _mk_trade(direction, entry, stop, pattern, t1_hit=False, initial=None):
    t = types.SimpleNamespace()
    t.id = 366
    t.direction = direction
    t.entry_price = entry
    t.stop = stop
    q = {"contracts": 3}
    if pattern is not None:
        q["pattern_name"] = pattern
    if initial is not None:
        q["initial_stop"] = initial
    t.quality = q
    t.cross_context = []
    t.t1_hit_ts = "2026-07-14T15:00:00+00:00" if t1_hit else None
    return t


# ── identity helpers ───────────────────────────────────────────────────────

def test_identity_helpers():
    assert _is_zlr_setup(_zlr_setup()) is True
    assert _is_zlr_setup(_reactive_setup()) is False
    assert is_zlr_trade(_mk_trade("LONG", 7500, 7492, pattern="ZLR")) is True
    assert is_zlr_trade(_mk_trade("LONG", 7500, 7492, pattern="REACTIVE_LONG")) is False


# ── (a) allocation: 2×T1 + 1×T2 when ON, 1/1/1 when OFF ────────────────────

def test_a_zlr_allocation_2xT1_1xT2_when_on(monkeypatch, tmp_path):
    p = _run_command(_zlr_setup(), monkeypatch, tmp_path, zlr_on=True)
    assert p["contracts"] == 3
    assert p["target_price"] == 7503.0        # C1 → T1
    assert p["context"]["t2"] == 7503.0       # C2 → T1  → 2 contracts at T1
    assert p["context"]["t3"] == 7506.0       # C3 → T2  → 1 contract at T2 (no T3 runner)


def test_a_zlr_allocation_1_1_1_when_off(monkeypatch, tmp_path):
    p = _run_command(_zlr_setup(), monkeypatch, tmp_path, zlr_on=False)
    assert p["contracts"] == 3
    assert p["target_price"] == 7503.0        # C1 → T1
    assert p["context"]["t2"] == 7506.0       # C2 → T2   (classic ladder)
    assert p["context"]["t3"] == 7509.0       # C3 → T3   (runner)


# ── (b) a non-ZLR setup is unchanged even with the flag ON ─────────────────

def test_b_non_zlr_unchanged_when_on(monkeypatch, tmp_path):
    p_on = _run_command(_reactive_setup(), monkeypatch, tmp_path, zlr_on=True)
    assert p_on["target_price"] == 7503.0
    assert p_on["context"]["t2"] == 7506.0    # 1/1/1 preserved
    assert p_on["context"]["t3"] == 7509.0
    # …and identical to the flag-OFF run.
    p_off = _run_command(_reactive_setup(), monkeypatch, tmp_path, zlr_on=False)
    assert (p_on["target_price"], p_on["context"]["t2"], p_on["context"]["t3"]) == \
           (p_off["target_price"], p_off["context"]["t2"], p_off["context"]["t3"])


# ── (c) pre-T1 stop-move: blocked when ON, allowed-as-today when OFF ────────

def test_c_zlr_pre_t1_stop_move_blocked_when_on(monkeypatch):
    monkeypatch.setenv("ZLR_MGMT_V1", "1")
    tm = _mk_tm()
    t = _mk_trade("LONG", 7500.0, 7492.0, pattern="ZLR", t1_hit=False, initial=7492.0)
    tm.apply_trail_after_t1(t, bar_high=7520.0, bar_low=7495.0)
    assert t.t1_hit_ts is None                 # still pre-T1
    assert t.stop == 7492.0                    # BLOCKED — no stop modification at all
    assert tm._emits == []                     # nothing sent to Sierra


def test_c_zlr_pre_t1_stop_move_allowed_when_off(monkeypatch):
    monkeypatch.delenv("ZLR_MGMT_V1", raising=False)
    tm = _mk_tm()
    t = _mk_trade("LONG", 7500.0, 7492.0, pattern="ZLR", t1_hit=False, initial=7492.0)
    tm.apply_trail_after_t1(t, bar_high=7520.0, bar_low=7495.0)
    assert t.stop > 7492.0                     # trailed up exactly as today
    assert t.stop >= 7500.25                   # at/above the BE+1T floor
    assert tm._emits and tm._emits[0][1] == t.stop


# ── (d) post-T1 → stop == entry (plain BE) when ON, overriding structure ────

def test_d_zlr_post_t1_stop_to_entry_be_when_on(monkeypatch):
    monkeypatch.setenv("ZLR_MGMT_V1", "1")
    monkeypatch.setenv("STOP_STRUCTURE_TRAIL_V1", "1")   # structure-trail ON …
    tm = _mk_tm()
    tm._structure_stop_after_t1 = lambda direction: 7497.5   # … with an anchor available
    t = _mk_trade("LONG", 7500.0, 7492.0, pattern="ZLR", t1_hit=True, initial=7492.0)
    tm._apply_smart_be_after_t1(t)
    assert t.stop == 7500.0                    # PLAIN entry (BE) — not 7497.5 struct, not 7500.25 BE+1T
    assert tm._emits and tm._emits[0][1] == pytest.approx(7500.0)
    assert t.cross_context[-1]["reason"] == "ZLR BE (entry) after T1"


def test_d_zlr_post_t1_short_mirror_when_on(monkeypatch):
    monkeypatch.setenv("ZLR_MGMT_V1", "1")
    tm = _mk_tm()
    t = _mk_trade("SHORT", 7500.0, 7508.0, pattern="ZLR", t1_hit=True, initial=7508.0)
    tm._apply_smart_be_after_t1(t)
    assert t.stop == 7500.0                    # SHORT BE == entry


def test_d_zlr_post_t1_flag_off_is_be_plus_1t(monkeypatch):
    """Flag OFF → a ZLR trade still gets the classic BE+1T (byte-identical today)."""
    monkeypatch.delenv("ZLR_MGMT_V1", raising=False)
    monkeypatch.delenv("STOP_STRUCTURE_TRAIL_V1", raising=False)
    tm = _mk_tm()
    t = _mk_trade("LONG", 7500.0, 7492.0, pattern="ZLR", t1_hit=True, initial=7492.0)
    tm._apply_smart_be_after_t1(t)
    assert t.stop == 7500.25                   # entry + 1 tick — unchanged


def test_d_non_zlr_post_t1_unchanged_when_on(monkeypatch):
    """Flag ON but trade is NOT ZLR → classic BE+1T (structure flag off). ZLR-scoped."""
    monkeypatch.setenv("ZLR_MGMT_V1", "1")
    monkeypatch.delenv("STOP_STRUCTURE_TRAIL_V1", raising=False)
    tm = _mk_tm()
    tm._structure_stop_after_t1 = lambda direction: 7497.5
    t = _mk_trade("LONG", 7500.0, 7492.0, pattern="REACTIVE_LONG", t1_hit=True, initial=7492.0)
    tm._apply_smart_be_after_t1(t)
    assert t.stop == 7500.25                   # BE+1T — ZLR override did NOT fire
