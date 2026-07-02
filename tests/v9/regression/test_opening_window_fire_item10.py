"""Item-10 — OPENING_WINDOW_FIRE_V1: first trade by OPENING TYPE in the first 30 min.

Michael's standing order (2026-07-02): "לצורך עסקה ראשונה, ברגע שהמערכת מזהה
לפי סוג הפתיחה עסקה — לבצע גם בחצי השעה הראשונה." Live incidents encoded:
  16:35:04 IL  [Gateway] BLOCKED by day-type playbook: ZLR SKIP on Nontrend
  16:45:03 IL  [S2] T1Setup skipped: INITIATIVE_LONG day_type=UNKNOWN · Auth Table SKIP

The override is POSITIVE-confirmation only (flag ON + inside 08:30-09:00 CT +
with-drive + drive not failed) and touches BOTH live choke points (full-pipeline
wiring rule). Flag default OFF — enabling is Michael's call.
"""
import pytest

from backend.v9.systems.opening_type_gate import opening_window_override

IN_WINDOW = 8 * 60 + 45   # 08:45 America/Chicago
OUT_WINDOW = 9 * 60 + 30  # 09:30 America/Chicago


def _drive_up_bars(n=3):
    """Synthetic opening drive UP: open 7500, closes climbing away."""
    bars, px = [], 7500.0
    for i in range(n):
        bars.append({"o": px + 2 * i, "h": px + 2 * i + 3, "l": px + 2 * i - 0.5,
                     "c": px + 2 * (i + 1)})
    return bars


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for f in ("OPENING_WINDOW_FIRE_V1", "OPENING_FIRE_CVD_V1",
              "FIXED_CONTRACTS_3", "DAYTYPE_PLAYBOOK", "DEDUP_FIRE_GUARD"):
        monkeypatch.delenv(f, raising=False)


# --- unit: the override itself ---------------------------------------------

def test_flag_off_never_overrides(monkeypatch):
    ok, reason = opening_window_override(
        direction="LONG", rth_bars=_drive_up_bars(), now_min_ct=IN_WINDOW)
    assert ok is False and "off" in reason


def test_with_drive_long_allowed(monkeypatch):
    monkeypatch.setenv("OPENING_WINDOW_FIRE_V1", "1")
    ok, reason = opening_window_override(
        direction="LONG", rth_bars=_drive_up_bars(), now_min_ct=IN_WINDOW)
    assert ok is True, reason
    assert "WITH-drive" in reason


def test_counter_drive_short_refused(monkeypatch):
    monkeypatch.setenv("OPENING_WINDOW_FIRE_V1", "1")
    ok, reason = opening_window_override(
        direction="SHORT", rth_bars=_drive_up_bars(), now_min_ct=IN_WINDOW)
    assert ok is False and "counter-drive" in reason


def test_outside_window_refused(monkeypatch):
    monkeypatch.setenv("OPENING_WINDOW_FIRE_V1", "1")
    ok, reason = opening_window_override(
        direction="LONG", rth_bars=_drive_up_bars(), now_min_ct=OUT_WINDOW)
    assert ok is False and "outside" in reason


def test_no_bias_refused(monkeypatch):
    """Flat open (<1pt from opening print) = rotation → no override."""
    monkeypatch.setenv("OPENING_WINDOW_FIRE_V1", "1")
    flat = [{"o": 7500.0, "h": 7501.0, "l": 7499.5, "c": 7500.25}]
    ok, reason = opening_window_override(
        direction="LONG", rth_bars=flat, now_min_ct=IN_WINDOW)
    assert ok is False


def test_failed_drive_refused(monkeypatch):
    """3 closes above the open, then a return through it → drive failed."""
    monkeypatch.setenv("OPENING_WINDOW_FIRE_V1", "1")
    bars = _drive_up_bars(3) + [{"o": 7504.0, "h": 7505.0, "l": 7495.0, "c": 7498.0}]
    ok, reason = opening_window_override(
        direction="LONG", rth_bars=bars, now_min_ct=IN_WINDOW)
    assert ok is False and "failed" in reason


# --- behavioral: S2 emitter choke point (fails on pre-item-10 code) ---------

def _emit(monkeypatch, day_type):
    import backend.v9.systems.five_min.setup_emitter as em
    return em.emit_t1_setup(
        "INITIATIVE_LONG", "LONG", 7500.0, 7495.0, 7510.0, 7520.0, 3,
        day_type=day_type,
    )


def test_emitter_auth_skip_overridden_in_window(monkeypatch):
    """The 16:45 incident: Auth-Table SKIP must be bypassed on positive override.
    Pre-item-10 code returns None here."""
    import backend.v9.systems.five_min.setup_emitter as em
    import backend.v9.systems.opening_type_gate as og
    monkeypatch.setenv("FIXED_CONTRACTS_3", "1")
    monkeypatch.setattr(em, "get_quality_tier_v2",
                        lambda *a, **kw: ("SKIP", "LOW", 0))
    monkeypatch.setattr(og, "opening_window_override",
                        lambda **kw: (True, "test WITH-drive"))
    setup = _emit(monkeypatch, "UNKNOWN")
    assert setup is not None, "Auth-Table SKIP must be overridden in the opening window (item-10)"
    assert setup.sizing_contracts == 3, "override must floor contracts via FIXED_CONTRACTS_3"


def test_emitter_auth_skip_stays_skip_when_flag_off(monkeypatch):
    """Default behavior unchanged: flag OFF → SKIP still kills the setup."""
    import backend.v9.systems.five_min.setup_emitter as em
    monkeypatch.setattr(em, "get_quality_tier_v2",
                        lambda *a, **kw: ("SKIP", "LOW", 0))
    assert _emit(monkeypatch, "UNKNOWN") is None


def test_emitter_no_trade_overridden_in_window(monkeypatch):
    """Nontrend is NO_TRADE (D-091.Q2) — a stage-1 'Nontrend' in the opening
    window must also be overridable (full-pipeline wiring)."""
    import backend.v9.systems.five_min.setup_emitter as em
    import backend.v9.systems.opening_type_gate as og
    monkeypatch.setattr(em, "get_quality_tier_v2",
                        lambda *a, **kw: ("FULL", "HIGH", 3))
    monkeypatch.setattr(og, "opening_window_override",
                        lambda **kw: (True, "test WITH-drive"))
    setup = _emit(monkeypatch, "Nontrend")
    assert setup is not None, "NO_TRADE refuse must be overridden in the opening window (item-10)"


def test_emitter_no_trade_stays_refused_when_no_override(monkeypatch):
    import backend.v9.systems.five_min.setup_emitter as em
    monkeypatch.setattr(em, "get_quality_tier_v2",
                        lambda *a, **kw: ("FULL", "HIGH", 3))
    assert _emit(monkeypatch, "Nontrend") is None


# --- behavioral: gateway playbook choke point (fails on pre-item-10 code) ---

def _bare_gateway(monkeypatch):
    from backend.v9.gateway.trading_gateway import TradingGateway
    from backend.v9.gateway.cooldown import CooldownManager, ClusterGuard
    import backend.v9.gateway.trading_gateway as tg

    class _NoVeto:
        def check_veto(self, direction):
            return False

        def record_outcome(self, *a):
            pass

    monkeypatch.setattr(tg, "is_within_firing_window", lambda: True)
    gw = TradingGateway.__new__(TradingGateway)
    gw._recent_fires = []
    gw.shadow_trades = []
    gw._slot_candidates = []
    gw._rr_selection_enabled = False
    gw.cooldown = CooldownManager()
    gw.cluster_guard = ClusterGuard()
    gw.ssv = _NoVeto()
    gw.demo_slot = None
    gw.live_slot = None
    gw._demo_enabled_systems = set()
    gw._live_enabled_systems = set()
    gw._trade_manager = None
    gw._system_registry = {}
    monkeypatch.setattr(gw, "_execute_shadow",
                        lambda setup, sid, ctx: {"trade_id": 99}, raising=False)
    monkeypatch.setattr(gw, "_selfheal_demo_slot", lambda: None, raising=False)
    return gw


def _zlr_setup():
    return {
        "firing_system": 4, "direction": "LONG", "classification": "ZLR",
        "confidence": 0.67, "entry_price": 7566.25, "stop": 7561.0,
        "t1": 7572.0, "t2": None, "t3": None, "metadata": {"pattern": "ZLR"},
    }


def _skip_playbook(monkeypatch):
    import backend.v9.systems.daytype_playbook as pb

    class _Skip:
        verdict, contracts, reason = "SKIP", 0, "ZLR SKIP on Nontrend"
        allow = False

    monkeypatch.setenv("DAYTYPE_PLAYBOOK", "1")
    monkeypatch.setattr(pb, "decide", lambda **kw: _Skip())


def test_gateway_playbook_skip_overridden_in_window(monkeypatch):
    """The 16:35 incident: playbook 'ZLR SKIP on Nontrend' must be bypassed on
    positive override. Pre-item-10 gateway blocks here regardless."""
    import backend.v9.systems.opening_type_gate as og
    gw = _bare_gateway(monkeypatch)
    _skip_playbook(monkeypatch)
    monkeypatch.setattr(og, "opening_window_override",
                        lambda **kw: (True, "test WITH-drive"))
    r = gw.route_setup(_zlr_setup(), 4)
    assert r.get("blocked_by") is None, f"blocked_by={r.get('blocked_by')} — playbook SKIP must be overridden (item-10)"
    assert r.get("shadow") == 99


def test_gateway_playbook_skip_stays_blocked_when_no_override(monkeypatch):
    """Default unchanged: no positive override → playbook SKIP still blocks."""
    gw = _bare_gateway(monkeypatch)
    _skip_playbook(monkeypatch)
    r = gw.route_setup(_zlr_setup(), 4)
    assert r.get("blocked_by") == "daytype_playbook"
