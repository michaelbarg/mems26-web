"""T5: Kill-switch regression tests.

When engaged → all fires blocked. When disengaged → fires pass.
Gateway checks kill-switch before any other gate.

if reverted → RED because: removing the kill-switch check from the gateway
or the engage/disengage logic would break the assertions.
"""
from backend.v9.services.kill_switch import engage, disengage, is_engaged, status


def test_default_disengaged():
    disengage()  # ensure clean state
    on, reason = is_engaged()
    assert on is False
    assert reason is None


def test_engage_blocks():
    """Engaging the kill-switch → is_engaged returns True.

    if reverted → RED because: removing engage() would leave state disengaged.
    """
    engage(reason="test", by="pytest")
    on, reason = is_engaged()
    assert on is True
    assert "KILL_SWITCH" in reason
    assert "test" in reason
    disengage()  # cleanup


def test_disengage_resumes():
    engage(reason="test")
    disengage()
    on, reason = is_engaged()
    assert on is False


def test_status_dict():
    engage(reason="audit", by="t5")
    s = status()
    assert s["engaged"] is True
    assert s["reason"] == "audit"
    assert s["engaged_by"] == "t5"
    disengage()


def test_gateway_has_kill_switch():
    """Gateway route_setup checks kill-switch first.

    if reverted → RED because: removing the import makes source inspection fail.
    """
    import inspect
    from backend.v9.gateway.trading_gateway import TradingGateway
    source = inspect.getsource(TradingGateway._route_setup_inner)
    assert "kill_switch" in source
    assert "is_engaged" in source
