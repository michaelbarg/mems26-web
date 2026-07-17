"""CONFLUENCE_RI_ZLR (spec docs/handoff/CONFLUENCE_PATTERN_SPEC_2026-07-17.md).

Anti-tautological: every test drives the REAL TradingGateway.route_setup /
confluence_ri_zlr.observe_route / sierra_command.effective_contracts code —
only the executors (_execute_shadow/_execute_demo/_execute_live), the
cross-context snapshot, the firing window and the canonical-bars loader are
stubbed (same pattern as tests/v9/regression/test_rr_graded_rotation.py).

Covers (task list a-g + spec §4.3 regression):
  a. flag OFF → registering both parents produces NO combined setup
  b. flag ON + both parents same bar/direction/Δ≤1pt + G-fresh pass → ONE
     combined setup: contracts=2, C1/C2=±4/±8, stop≤7pt correct side,
     fixed_contracts_exempt honored by effective_contracts under
     FIXED_CONTRACTS_4=1 while a regular ZLR-style setup still ships 4
  c. Δentry > 1pt → no setup
  d. opposite directions → no setup
  e. G-fresh fail (close not beyond prior-3-bar extreme) → no setup;
     missing bars → honest reject (no setup)
  f. combined setup routes SHADOW-only even when MEMS26_MODE=live with demo+
     live enabled; CONFLUENCE_RI_ZLR_LIVE=1 → guarded stub still refuses
  g. detector raising → parents still fire (hook can never break the parents)
  +  route-window >5s → no join · bar_ts canonical mismatch → no join ·
     one emission per bar+direction · 7pt stop cap · per-pattern R:R at the
     rr_entry_gate (parents blocked, confluence judged on (C1+C2)/2).
"""
import pytest

import backend.v9.systems.confluence.confluence_ri_zlr as conf
from backend.v9.gateway import trading_gateway as tg
from backend.v9.services.sierra_command import effective_contracts


# ── canonical-series bars (oldest-first; bars[-1] = signal bar) ──────────────
# SHORT G-fresh PASS: signal close 7589.5 < min(prior lows 7595, 7593, 7592) = 7592
BARS_SHORT_FRESH = [
    {"ts": "2026-07-16 17:05:00", "open": 7597.0, "high": 7599.0, "low": 7595.0, "close": 7596.0},
    {"ts": "2026-07-16 17:10:00", "open": 7596.0, "high": 7597.5, "low": 7593.0, "close": 7594.0},
    {"ts": "2026-07-16 17:15:00", "open": 7594.0, "high": 7595.5, "low": 7592.0, "close": 7593.0},
    {"ts": "2026-07-16 17:20:00", "open": 7591.0, "high": 7591.5, "low": 7589.0, "close": 7589.5},
]
# SHORT G-fresh FAIL: signal close 7591.0 NOT below min(prior lows) = 7590.0
BARS_SHORT_STALE = [
    {"ts": "2026-07-16 17:05:00", "open": 7594.0, "high": 7596.0, "low": 7590.0, "close": 7592.0},
    {"ts": "2026-07-16 17:10:00", "open": 7592.0, "high": 7594.0, "low": 7592.0, "close": 7593.0},
    {"ts": "2026-07-16 17:15:00", "open": 7593.0, "high": 7595.0, "low": 7593.0, "close": 7594.0},
    {"ts": "2026-07-16 17:20:00", "open": 7592.0, "high": 7592.5, "low": 7590.5, "close": 7591.0},
]
# LONG G-fresh PASS: signal close 7600.0 > max(prior highs 7594, 7596, 7597) = 7597
BARS_LONG_FRESH = [
    {"ts": "2026-07-16 17:05:00", "open": 7592.0, "high": 7594.0, "low": 7590.0, "close": 7593.0},
    {"ts": "2026-07-16 17:10:00", "open": 7593.0, "high": 7596.0, "low": 7592.0, "close": 7595.0},
    {"ts": "2026-07-16 17:15:00", "open": 7595.0, "high": 7597.0, "low": 7594.0, "close": 7596.0},
    {"ts": "2026-07-16 17:20:00", "open": 7597.5, "high": 7600.5, "low": 7597.5, "close": 7600.0},
]


def _s4(entry=7589.5, stop=7594.0, direction="SHORT", **over):
    s = {"firing_system": 4, "direction": direction, "classification": "ZLR",
         "confidence": 0.8, "entry_price": entry, "stop": stop,
         "t1": entry - 4.5 if direction == "SHORT" else entry + 4.5,
         "t2": None, "t3": None,
         "metadata": {"pattern": "ZLR", "sizing": "full"}}
    s.update(over)
    return s


def _s2(entry=7589.5, direction="SHORT", pattern="REACTIVE_SHORT", **over):
    sign = -1.0 if direction == "SHORT" else 1.0
    s = {"firing_system": 2, "direction": direction, "classification": pattern,
         "confidence": 0.7, "entry_price": entry, "stop": entry - sign * 6.0,
         "t1": entry + sign * 4.0, "t2": entry + sign * 8.0, "t3": None,
         "metadata": {"pattern": pattern, "sizing": 3}}
    s.update(over)
    return s


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    """Fresh registry + known-off env for every test (no ambient leakage)."""
    conf.reset_registry()
    for var in ("CONFLUENCE_RI_ZLR_V1", "CONFLUENCE_RI_ZLR_LIVE", "CONFLUENCE_RR_MIN",
                "FIXED_CONTRACTS_2", "FIXED_CONTRACTS_3", "FIXED_CONTRACTS_4",
                "SIZE_CAP_OVER_FIXED_V1", "RR_ENTRY_GATE_V1", "RR_MIN_ROTATION",
                "DEMO_EXECUTION_ENABLED", "MEMS26_MODE", "DEDUP_FIRE_GUARD"):
        monkeypatch.delenv(var, raising=False)
    yield
    conf.reset_registry()


def _gw(monkeypatch):
    """Real gateway; only executors/context/window stubbed (rr-graded pattern)."""
    monkeypatch.setattr(tg, "is_within_firing_window", lambda: True)
    gw = tg.TradingGateway()
    shadow_calls = []

    def _shadow(setup, system_id, ctx):
        shadow_calls.append(dict(setup))
        return {"trade_id": f"t{len(shadow_calls)}", "mode": "shadow",
                "firing_system": system_id, "direction": setup.get("direction"),
                "state": "FILLED", "entry_price": setup.get("entry_price"),
                "entry_ts": "x"}

    monkeypatch.setattr(gw, "_execute_shadow", _shadow)
    monkeypatch.setattr(gw, "_capture_cross_context",
                        lambda: {"day_type_machine": {}, "woodies_system": {}, "tpo_system": {}})
    return gw, shadow_calls


def _conf_calls(shadow_calls):
    return [s for s in shadow_calls if s.get("classification") == "CONFLUENCE_RI_ZLR"]


# ── a. flag OFF → nothing ────────────────────────────────────────────────────
def test_flag_off_no_combined_setup(monkeypatch):
    monkeypatch.setattr(conf, "load_signal_bars", lambda limit=4: list(BARS_SHORT_FRESH))
    gw, calls = _gw(monkeypatch)
    gw.route_setup(_s4(), 4)
    gw.route_setup(_s2(), 2)
    assert len(calls) == 2                      # both parents shadow-recorded
    assert _conf_calls(calls) == []             # no combined setup


# ── b. happy path: ONE combined setup with the definitional numbers ─────────
def test_join_emits_one_combined_setup_short(monkeypatch):
    monkeypatch.setenv("CONFLUENCE_RI_ZLR_V1", "1")
    monkeypatch.setattr(conf, "load_signal_bars", lambda limit=4: list(BARS_SHORT_FRESH))
    gw, calls = _gw(monkeypatch)
    gw.route_setup(_s4(), 4)                    # ZLR routes first (live ordering)
    gw.route_setup(_s2(), 2)
    cc = _conf_calls(calls)
    assert len(cc) == 1
    c = cc[0]
    assert c["direction"] == "SHORT"
    assert c["entry_price"] == 7589.5           # midpoint of equal closes
    assert c["t1"] == 7585.5 and c["t2"] == 7581.5   # entry −4 / −8 (SHORT)
    assert c["t3"] is None
    assert c["stop"] == 7594.0                  # S4 structural stop, 4.5pt ≤ 7 cap
    assert 0.0 < c["stop"] - c["entry_price"] <= 7.0  # correct side + cap
    assert c["contracts"] == 2
    m = c["metadata"]
    assert m["fixed_contracts_exempt"] == 1
    assert m["confluence"]["g_fresh"]["pass"] is True
    assert len(m["confluence"]["parents"]) == 2
    # decisions panel records the combined route as shadow_only
    d = [x for x in gw.decisions if x["pattern"] == "CONFLUENCE_RI_ZLR"]
    assert d and d[-1]["outcome"] == "shadow_only"
    # one emission per bar+direction: re-routing the parents cannot double-emit
    gw.route_setup(_s2(), 2)
    gw.route_setup(_s4(), 4)
    assert len(_conf_calls(calls)) == 1


def test_join_long_mirror_and_7pt_stop_cap(monkeypatch):
    monkeypatch.setenv("CONFLUENCE_RI_ZLR_V1", "1")
    monkeypatch.setattr(conf, "load_signal_bars", lambda limit=4: list(BARS_LONG_FRESH))
    gw, calls = _gw(monkeypatch)
    # S4 stop 12pt away → must be CAPPED to 7.0 from entry
    gw.route_setup(_s4(entry=7600.0, stop=7588.0, direction="LONG"), 4)
    gw.route_setup(_s2(entry=7600.0, direction="LONG", pattern="INITIATIVE_LONG"), 2)
    cc = _conf_calls(calls)
    assert len(cc) == 1
    c = cc[0]
    assert c["t1"] == 7604.0 and c["t2"] == 7608.0   # entry +4 / +8 (LONG)
    assert c["stop"] == 7593.0                       # 7600 − 7.0 cap (not 7588)
    assert 0.0 < c["entry_price"] - c["stop"] <= 7.0


# ── sizing chokepoint: FIXED_CONTRACTS_4 exemption is scoped ────────────────
def test_effective_contracts_exemption_scoped(monkeypatch):
    monkeypatch.setenv("FIXED_CONTRACTS_4", "1")
    exempt = {"contracts": 2, "metadata": {"fixed_contracts_exempt": 1}}
    assert effective_contracts(exempt) == 2          # confluence ships exactly 2
    assert effective_contracts({"contracts": 2}) == 4            # non-exempt forced (unchanged)
    assert effective_contracts({"metadata": {"sizing": "full"}}) == 4  # regular ZLR-style → 4
    monkeypatch.setenv("SIZE_CAP_OVER_FIXED_V1", "1")
    assert effective_contracts(exempt) == 2          # exemption precedes the cap-over-fixed path
    monkeypatch.delenv("SIZE_CAP_OVER_FIXED_V1", raising=False)
    monkeypatch.delenv("FIXED_CONTRACTS_4", raising=False)
    assert effective_contracts(exempt) == 2          # flag off → still its own count


def test_routed_combined_setup_survives_fixed_contracts_4(monkeypatch):
    """End-to-end: the setup the gateway shadow-executed resolves to 2 contracts."""
    monkeypatch.setenv("CONFLUENCE_RI_ZLR_V1", "1")
    monkeypatch.setenv("FIXED_CONTRACTS_4", "1")
    monkeypatch.setattr(conf, "load_signal_bars", lambda limit=4: list(BARS_SHORT_FRESH))
    gw, calls = _gw(monkeypatch)
    gw.route_setup(_s4(), 4)
    gw.route_setup(_s2(), 2)
    c = _conf_calls(calls)[0]
    assert effective_contracts(c) == 2
    # and the ZLR parent in the SAME env still resolves to 4 (spec §4.3 regression)
    zlr = [s for s in calls if s.get("classification") == "ZLR"][0]
    assert effective_contracts(zlr) == 4


# ── c. entry delta > 1pt → no join ───────────────────────────────────────────
def test_entry_delta_over_1pt_no_join(monkeypatch):
    monkeypatch.setenv("CONFLUENCE_RI_ZLR_V1", "1")
    monkeypatch.setattr(conf, "load_signal_bars", lambda limit=4: list(BARS_SHORT_FRESH))
    gw, calls = _gw(monkeypatch)
    gw.route_setup(_s4(entry=7589.5), 4)
    gw.route_setup(_s2(entry=7591.0), 2)        # Δ = 1.5pt > 1.0 → bar-source-split suspicion
    assert _conf_calls(calls) == []


# ── d. opposite directions → no join ─────────────────────────────────────────
def test_opposite_directions_no_join(monkeypatch):
    monkeypatch.setenv("CONFLUENCE_RI_ZLR_V1", "1")
    monkeypatch.setattr(conf, "load_signal_bars", lambda limit=4: list(BARS_SHORT_FRESH))
    gw, calls = _gw(monkeypatch)
    gw.route_setup(_s4(direction="SHORT"), 4)
    gw.route_setup(_s2(direction="LONG", pattern="REACTIVE_LONG",
                       entry=7589.5), 2)
    assert _conf_calls(calls) == []


# ── e. G-fresh fail / missing bars → honest reject ───────────────────────────
def test_g_fresh_fail_no_setup(monkeypatch):
    monkeypatch.setenv("CONFLUENCE_RI_ZLR_V1", "1")
    monkeypatch.setattr(conf, "load_signal_bars", lambda limit=4: list(BARS_SHORT_STALE))
    gw, calls = _gw(monkeypatch)
    gw.route_setup(_s4(entry=7591.0, stop=7594.5), 4)
    gw.route_setup(_s2(entry=7591.0), 2)
    assert _conf_calls(calls) == []             # stale signal rejected
    assert len(calls) == 2                      # parents untouched


def test_missing_bars_honest_reject(monkeypatch):
    monkeypatch.setenv("CONFLUENCE_RI_ZLR_V1", "1")
    monkeypatch.setattr(conf, "load_signal_bars", lambda limit=4: [])  # DB silent
    gw, calls = _gw(monkeypatch)
    gw.route_setup(_s4(), 4)
    gw.route_setup(_s2(), 2)
    assert _conf_calls(calls) == []             # no synthetic pass (Rule 1)


# ── f. SHADOW-only routing even in live mode; LIVE flag stub refuses ─────────
def test_shadow_only_even_when_mode_live(monkeypatch):
    monkeypatch.setenv("CONFLUENCE_RI_ZLR_V1", "1")
    monkeypatch.setenv("MEMS26_MODE", "live")
    monkeypatch.setenv("DEMO_EXECUTION_ENABLED", "1")
    monkeypatch.setattr(conf, "load_signal_bars", lambda limit=4: list(BARS_SHORT_FRESH))
    monkeypatch.setattr(tg, "passes_strict_checks", lambda *a, **k: True)
    gw, shadow_calls = _gw(monkeypatch)
    live_calls, demo_calls = [], []
    monkeypatch.setattr(
        gw, "_execute_live",
        lambda s, sid, ctx: (live_calls.append(dict(s)) or
                             {"trade_id": "L1", "firing_system": sid}))
    monkeypatch.setattr(
        gw, "_execute_demo",
        lambda s, sid, ctx: (demo_calls.append(dict(s)) or
                             {"trade_id": "D1", "firing_system": sid}))
    gw.enable_live(2); gw.enable_live(4)
    gw.enable_demo(2); gw.enable_demo(4)
    gw.route_setup(_s4(), 4)
    gw.route_setup(_s2(), 2)
    # combined setup exists — but ONLY as shadow
    assert len(_conf_calls(shadow_calls)) == 1
    assert all(s.get("classification") != "CONFLUENCE_RI_ZLR"
               for s in live_calls + demo_calls)
    d = [x for x in gw.decisions if x["pattern"] == "CONFLUENCE_RI_ZLR"]
    assert d and d[-1]["outcome"] == "shadow_only"


def test_live_flag_routes_to_live(monkeypatch):
    """Michael ruling 2026-07-17 ~11:15 IL: 'לגבי התבנית החדשה מאושר להפעיל על
    לייב' — with CONFLUENCE_RI_ZLR_LIVE=1 the combined setup must reach the
    NORMAL demo/live routing (was: refusing stub). LIVE flag unset stays
    shadow-only (pinned by test_shadow_only_even_in_live_mode above)."""
    monkeypatch.setenv("CONFLUENCE_RI_ZLR_V1", "1")
    monkeypatch.setenv("CONFLUENCE_RI_ZLR_LIVE", "1")
    monkeypatch.setenv("MEMS26_MODE", "live")
    monkeypatch.setattr(conf, "load_signal_bars", lambda limit=4: list(BARS_SHORT_FRESH))
    monkeypatch.setattr(tg, "passes_strict_checks", lambda *a, **k: True)
    gw, shadow_calls = _gw(monkeypatch)
    live_calls, demo_calls = [], []
    monkeypatch.setattr(gw, "_execute_live",
                        lambda s, sid, ctx: (live_calls.append(dict(s)) or {"trade_id": "L1"}))
    monkeypatch.setattr(gw, "_execute_demo",
                        lambda s, sid, ctx: (demo_calls.append(dict(s)) or {"trade_id": "D1"}))
    gw.enable_live(4)
    gw.route_setup(_s4(), 4)
    # Single-slot reality: the parent ZLR just took the live slot (first-wins) —
    # the confluence must NOT double-fire alongside it. Free the slot (as when
    # the parent was gate-blocked or already closed) before the join completes:
    gw.live_slot = None
    gw.route_setup(_s2(), 2)
    assert len(_conf_calls(shadow_calls)) == 1          # shadow always recorded
    conf_live = [s for s in live_calls
                 if s.get("classification") == "CONFLUENCE_RI_ZLR"]
    assert len(conf_live) == 1, (
        f"confluence must route LIVE per ruling; live={len(conf_live)} "
        f"demo={len(demo_calls)}")
    # sizing stays the definitional 2 contracts on the live-routed setup
    assert (conf_live[0].get("metadata") or {}).get("fixed_contracts_exempt") == 1


def test_live_flag_no_double_fire_when_slot_taken(monkeypatch):
    """Slot competition (spec §4.4-V1): when the parent holds the live slot the
    confluence must NOT fire a second live trade — one trade at a time."""
    monkeypatch.setenv("CONFLUENCE_RI_ZLR_V1", "1")
    monkeypatch.setenv("CONFLUENCE_RI_ZLR_LIVE", "1")
    monkeypatch.setenv("MEMS26_MODE", "live")
    monkeypatch.setattr(conf, "load_signal_bars", lambda limit=4: list(BARS_SHORT_FRESH))
    monkeypatch.setattr(tg, "passes_strict_checks", lambda *a, **k: True)
    gw, shadow_calls = _gw(monkeypatch)
    live_calls = []
    monkeypatch.setattr(gw, "_execute_live",
                        lambda s, sid, ctx: (live_calls.append(dict(s)) or {"trade_id": "L1"}))
    gw.enable_live(4)
    gw.route_setup(_s4(), 4)   # parent takes the single live slot
    gw.route_setup(_s2(), 2)   # join completes — slot still occupied
    conf_live = [s for s in live_calls
                 if s.get("classification") == "CONFLUENCE_RI_ZLR"]
    assert len(conf_live) == 0, "confluence double-fired alongside its parent"
    assert len(_conf_calls(shadow_calls)) == 1          # still shadow-recorded


# ── g. detector errors can never break the parents ───────────────────────────
def test_detector_error_never_breaks_parents(monkeypatch):
    monkeypatch.setenv("CONFLUENCE_RI_ZLR_V1", "1")

    def _boom(*a, **k):
        raise RuntimeError("registry boom")

    monkeypatch.setattr(conf, "observe_route", _boom)
    gw, calls = _gw(monkeypatch)
    r4 = gw.route_setup(_s4(), 4)
    r2 = gw.route_setup(_s2(), 2)
    assert r4["shadow"] and r2["shadow"]        # both parents still fired
    assert len(calls) == 2
    assert r4["blocked_by"] is None and r2["blocked_by"] is None


# ── join keying: 5s route window + canonical bar_ts ──────────────────────────
def test_route_window_5s_enforced(monkeypatch):
    monkeypatch.setenv("CONFLUENCE_RI_ZLR_V1", "1")
    clock = {"t": 0.0}
    conf.reset_registry(now_fn=lambda: clock["t"])
    monkeypatch.setattr(conf, "load_signal_bars", lambda limit=4: list(BARS_SHORT_FRESH))
    gw, calls = _gw(monkeypatch)
    gw.route_setup(_s4(), 4)
    clock["t"] = 6.0                            # 6s later — outside the 5s window
    gw.route_setup(_s2(), 2)
    assert _conf_calls(calls) == []
    # …but a fresh S4 within the window then joins with the pending S2
    clock["t"] = 8.0
    gw.route_setup(_s4(), 4)
    assert len(_conf_calls(calls)) == 1


def test_bar_ts_mismatch_is_canonical_no_join(monkeypatch):
    monkeypatch.setenv("CONFLUENCE_RI_ZLR_V1", "1")
    monkeypatch.setattr(conf, "load_signal_bars", lambda limit=4: list(BARS_SHORT_FRESH))
    gw, calls = _gw(monkeypatch)
    gw.route_setup(_s4(bar_ts="2026-07-16 17:20:00"), 4)
    gw.route_setup(_s2(bar_ts="2026-07-16 17:25:00"), 2)   # different signal bar
    assert _conf_calls(calls) == []             # bar_ts equality is canonical


# ── per-pattern R:R at the rr_entry_gate (spec §2/§5.4) ──────────────────────
def test_rr_gate_judges_confluence_on_position_average(monkeypatch):
    monkeypatch.setenv("CONFLUENCE_RI_ZLR_V1", "1")
    monkeypatch.setenv("RR_ENTRY_GATE_V1", "1")
    monkeypatch.setattr(conf, "load_signal_bars", lambda limit=4: list(BARS_SHORT_FRESH))
    gw, calls = _gw(monkeypatch)
    # Parents deliberately fail the generic 1.0 T1-only test (T1 2pt vs stop 6/4.5pt)
    gw.route_setup(_s4(stop=7594.0, t1=7587.5), 4)
    gw.route_setup(_s2(t1=7587.5), 2)
    zlr_dec = [x for x in gw.decisions if x["pattern"] == "ZLR"]
    assert zlr_dec and zlr_dec[-1]["blocked_by"] == "rr_entry_gate"   # parent blocked
    conf_dec = [x for x in gw.decisions if x["pattern"] == "CONFLUENCE_RI_ZLR"]
    # confluence judged on (4+8)/2=6 vs stop 4.5 × 0.85 → PASSES to shadow
    assert conf_dec and conf_dec[-1]["outcome"] == "shadow_only"
    assert conf_dec[-1]["blocked_by"] is None


def test_rr_gate_confluence_min_still_blocks_when_raised(monkeypatch):
    monkeypatch.setenv("CONFLUENCE_RI_ZLR_V1", "1")
    monkeypatch.setenv("RR_ENTRY_GATE_V1", "1")
    monkeypatch.setenv("CONFLUENCE_RR_MIN", "1.5")   # 6 < 4.5×1.5=6.75 → block
    monkeypatch.setattr(conf, "load_signal_bars", lambda limit=4: list(BARS_SHORT_FRESH))
    gw, calls = _gw(monkeypatch)
    gw.route_setup(_s4(), 4)
    gw.route_setup(_s2(), 2)
    conf_dec = [x for x in gw.decisions if x["pattern"] == "CONFLUENCE_RI_ZLR"]
    assert conf_dec and conf_dec[-1]["blocked_by"] == "rr_entry_gate"
    assert _conf_calls(calls) == []             # blocked before shadow execution
