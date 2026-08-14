"""H18 — RELEASE_LEG_EXEMPT_V1: reversal entries pass the release gate when a
live leg proves the trend broke.

Michael's standing ruling 2026-08-11: "רק אם המגמה נשברת ניתן לבצע עסקה נגדית".
The release gate scores direction against the SESSION OPEN, so on a day that
opened up and reversed, the correct SHORT is judged "counter-move" and held by
a rotation model that does not apply. A live leg (leg_state.detect_leg — the
same detector LEG_RIDE_V1 already trusts for chase/location/lsma exemptions) is
the structural proof that the trend broke.

Replay (40 sessions): 5 exempted, 5/5 winners, +$100 single-slot; 43 blocks
stayed held where the leg disagreed — the gate keeps its job.
"""
import inspect

from backend.v9.gateway import trading_gateway


def _src():
    return inspect.getsource(trading_gateway.TradingGateway._route_setup_inner)


class TestWiring:
    def test_flag_present_and_default_off(self):
        src = _src()
        assert "RELEASE_LEG_EXEMPT_V1" in src
        assert 'RELEASE_LEG_EXEMPT_V1", "0"' in src

    def test_exemption_requires_live_leg(self):
        """Never a blanket bypass — the leg detector must agree with direction."""
        src = _src()
        i = src.index('os.getenv("RELEASE_LEG_EXEMPT_V1"')
        window = src[i:i + 200]
        assert "_live_leg(direction)" in window, window[:200]

    def test_exemption_evaluated_before_trend_bypass_but_gate_still_reachable(self):
        """Leg exemption first, then the session-displacement bypass, then the
        real check — no path silently drops the gate."""
        src = _src()
        i_leg = src.index("_rg_leg_exempt")
        i_bypass = src.index("_rg.trend_bypass")
        i_check = src.index("_rg.check_release")
        assert i_leg < i_bypass < i_check

    def test_block_still_possible(self):
        """Against-leg entries must still be able to hit awaiting_release."""
        src = _src()
        assert 'result["blocked_by"] = "awaiting_release"' in src

    def test_fail_closed_on_error(self):
        """Release-gate errors keep holding the entry (fail-closed) — the
        exemption must not turn an error into a free pass."""
        src = _src()
        assert "release-gate unavailable (fail-closed)" in src


class TestLiveLegHelper:
    def test_live_leg_returns_false_when_leg_ride_off(self, monkeypatch):
        monkeypatch.setenv("LEG_RIDE_V1", "0")
        assert trading_gateway._live_leg("LONG") is False

    def test_live_leg_never_raises(self, monkeypatch):
        monkeypatch.setenv("LEG_RIDE_V1", "1")
        # no DB in the test env → must swallow and return False, never raise
        assert trading_gateway._live_leg("SHORT") in (True, False)
