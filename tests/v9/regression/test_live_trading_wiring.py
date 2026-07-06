"""LIVE_TRADING_V1 — gateway live-registration wiring (Michael 2026-07-06).

The finding (2026-07-06): main.py only called enable_demo(2)/(4); nothing ever
called enable_live → _live_enabled_systems empty → _is_live_enabled() always False
→ _execute_live NEVER reached even with LIVE_EXECUTION_V1=1. These guard the
enable_live/_is_live_enabled mechanism the routing depends on, and that live is
NOT enabled by default (must be explicitly wired via the flag in main.py).
"""
from backend.v9.gateway import TradingGateway


def test_live_not_enabled_by_default():
    """A fresh gateway has NO live systems — the bug the finding exposed."""
    g = TradingGateway()
    assert g._is_live_enabled(2) is False
    assert g._is_live_enabled(4) is False


def test_enable_live_registers_and_status_reflects_it():
    """enable_live → _is_live_enabled True + get_status lists it (routing depends on this)."""
    g = TradingGateway()
    g.enable_live(2)
    g.enable_live(4)
    assert g._is_live_enabled(2) and g._is_live_enabled(4)
    st = g.get_status()
    assert st["live_enabled_systems"] == [2, 4], st.get("live_enabled_systems")


def test_disable_live_unregisters():
    g = TradingGateway()
    g.enable_live(2)
    g.disable_live(2)
    assert g._is_live_enabled(2) is False


def test_live_replaces_demo_branch_logic(monkeypatch):
    """Mirror main.py's branch: flag ON → live-only; flag OFF → demo-only."""
    # demo has a runtime gate (DEMO_EXECUTION_ENABLED); prod sets it. Live has none.
    monkeypatch.setenv("DEMO_EXECUTION_ENABLED", "1")

    def wire(gateway, flag_on):
        if flag_on:
            gateway.enable_live(2); gateway.enable_live(4)
        else:
            gateway.enable_demo(2); gateway.enable_demo(4)

    g_on = TradingGateway(); wire(g_on, True)
    assert g_on._is_live_enabled(2) and not g_on._is_demo_enabled(2)

    g_off = TradingGateway(); wire(g_off, False)
    assert g_off._is_demo_enabled(2) and not g_off._is_live_enabled(2)
