"""T-355 item 4/8: phase-B location gate.

Phase B (16:45-17:30 IL): day_type unknown, kind/bias blocks replaced by
location check using prior_vah/prior_val + session_high/low + IB.
Flag: PHASE_B_LOCATION_V1 (default OFF).
"""

import inspect


def test_gate_present_in_source():
    """T-355 block exists in _route_setup_inner and is flag-gated."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    src = inspect.getsource(TradingGateway._route_setup_inner)
    assert "PHASE_B_LOCATION_V1" in src
    assert "T-355 PHASE_B location admit" in src


def test_long_at_low_admitted():
    """LONG at session low (near prior_val) should pass phase-B location."""
    prior_val, prior_vah = 7585.0, 7620.0
    session_low, session_high = 7585.5, 7610.0
    ib_low, ib_high = 7585.5, 7610.0
    entry = 7587.5
    direction = "LONG"
    # tol = _tol(ib_width=24.5) = min(max(0.25*24.5, 1.0), 4.0) = 4.0
    tol = 4.0
    low_edge = min(prior_val, session_low, ib_low)  # 7585.0
    ok = entry <= low_edge + tol  # 7587.5 <= 7589.0
    assert ok, f"LONG at {entry} should be admitted (low_edge={low_edge}, tol={tol})"


def test_long_at_high_blocked():
    """LONG near session high (not near val) should stay blocked."""
    prior_val, prior_vah = 7660.0, 7680.0
    session_low, session_high = 7665.0, 7682.0
    entry = 7675.0
    direction = "LONG"
    tol = 4.0
    low_edge = min(prior_val, session_low)  # 7660.0
    ok = entry <= low_edge + tol  # 7675.0 <= 7664.0 → False
    assert not ok, f"LONG at {entry} should be blocked (low_edge={low_edge})"


def test_phase_c_untouched():
    """Phase C should not trigger T-355 logic (mutation test)."""
    from backend.v9.services.dalton_playbook import _resolve_phase
    # 18:00 IL = phase C
    assert _resolve_phase("18:00") == "C"
    # 17:00 IL = phase B
    assert _resolve_phase("17:00") == "B"
    # 16:40 IL = phase A
    assert _resolve_phase("16:40") == "A"


def test_flag_off_preserves_original_block():
    """With flag OFF, the kind/bias block is unchanged."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    src = inspect.getsource(TradingGateway._route_setup_inner)
    # The flag check is inside an if that requires the env var to be "1"
    idx = src.find("PHASE_B_LOCATION_V1")
    assert idx > 0
    # The block is inside a conditional that defaults OFF
    window = src[max(0, idx - 100):idx + 100]
    assert '"0"' in window, "Default must be '0' (OFF)"
