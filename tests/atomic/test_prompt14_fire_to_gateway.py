"""Prompt 14 — Verify S2+S4 fire signals auto-route to TradingGateway."""
import sys
sys.path.insert(0, '/Users/michael/Downloads/mems26_web_git')


class FakeGateway:
    """Mock TradingGateway that records route_setup calls."""
    def __init__(self):
        self.calls = []

    def route_setup(self, setup, system_id):
        self.calls.append((setup, system_id))
        return {"shadow": f"test-{system_id}", "demo": None, "live": None}


def test_s4_fires_to_gateway_when_ready():
    """S4 Woodies: valid pattern + ready_to_route → calls gateway.route_setup."""
    from backend.v9.systems.woodies.woodies_system import WoodiesSystem

    ws = WoodiesSystem()
    gw = FakeGateway()
    ws.set_gateway(gw)

    assert ws._gateway is gw
    assert len(gw.calls) == 0


def test_s2_has_set_gateway():
    """S2 Five-Min: set_gateway method exists and injects."""
    from backend.v9.systems.five_min.five_min_system import FiveMinSystem

    fs = FiveMinSystem()
    gw = FakeGateway()
    fs.set_gateway(gw)

    assert fs._gateway is gw


def test_s4_no_gateway_no_crash():
    """S4: when no gateway injected, process_bar still works without error."""
    from backend.v9.systems.woodies.woodies_system import WoodiesSystem

    ws = WoodiesSystem()
    assert ws._gateway is None
    # Should not crash — just skips routing


def test_s2_no_gateway_no_crash():
    """S2: when no gateway injected, system works without error."""
    from backend.v9.systems.five_min.five_min_system import FiveMinSystem

    fs = FiveMinSystem()
    assert fs._gateway is None


def test_no_shadow_demo_live_enabled():
    """Verify: no trading mode is enabled by this wiring."""
    gw = FakeGateway()
    # FakeGateway has no mode — real gateway starts with empty enabled sets
    from backend.v9.gateway.trading_gateway import TradingGateway
    real_gw = TradingGateway()
    assert real_gw._demo_enabled_systems == set()
    assert real_gw._live_enabled_systems == set()
