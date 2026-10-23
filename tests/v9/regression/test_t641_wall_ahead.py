"""T-641 (23.10) · WALL_AHEAD_SKIP_V1 — a wall between entry and a viable T1 stands the setup down.

#3898 REACTIVE_LONG 18:55:02 @7689.25 (fill 7690), stop 7675.75: S2 logged
"structure exhausted ahead (end 7697.25) — T1=1R 7709.50"; the gateway's structural C1 was
7692.75 (R:R 0.26) and RR_NO_SELF_INFLICTED restored 7709.50 "instead of blocking" ⇒ stop 19:53,
−$213.75. The wall: 7697.25, touched 18:25 + 18:30, 8.0pt ahead vs 13.5 risk (0.59R < 0.65R).
Michael 23.10: "למה העסקה האחרונה נכנסו אליה … מה היו הפערים … שנלמד ונשתפר".
"""
from types import SimpleNamespace

from backend.v9.systems.stop_anchors.resolver import wall_ahead


def _b(*hl):
    return [{"h": h, "l": l} for h, l in hl]


# the 12 closed 5-min bars before the 18:55 fire (17:55 … 18:50 IL), v9_bars_5min_woodies 23.10
W_3898 = _b((7693.5, 7686.5), (7691.75, 7682.5), (7690.5, 7680.75), (7691.0, 7679.75),
            (7692.25, 7684.25), (7691.0, 7684.75), (7697.25, 7688.75), (7697.25, 7689.25),
            (7695.5, 7685.5), (7691.0, 7681.75), (7689.25, 7681.25), (7691.5, 7686.75))


def test_3898_is_a_wall():
    w = wall_ahead(W_3898, "LONG", 7689.25, 13.5)
    assert w is not None
    end, dist, age, touches = w
    assert end == 7697.25 and abs(dist - 8.0) < 1e-9 and age == 4 and touches == 2


def test_breakout_end_printed_by_the_last_bar_is_not_a_wall():
    # 07-22 18:55 blind-spot class: the end sits next to entry because the CURRENT move prints it
    bars = W_3898[:-1] + _b((7699.0, 7690.0))
    assert wall_ahead(bars, "LONG", 7697.0, 5.75) is None
    # touched 2 bars ago is still the current move (min_age_bars=3)
    bars2 = W_3898[:-3] + _b((7699.0, 7690.0), (7697.0, 7692.0), (7698.0, 7693.0))
    assert wall_ahead(bars2, "LONG", 7696.0, 6.0) is None


def test_viable_room_is_not_a_wall():
    # 8.0pt ahead vs risk 10 ⇒ 0.8R ≥ 0.65R — T1_STRUCTURE_END uses the structural T1, no wall
    assert wall_ahead(W_3898, "LONG", 7689.25, 10.0) is None


def test_end_at_or_behind_entry_is_not_a_wall():
    assert wall_ahead(W_3898, "LONG", 7697.25, 13.5) is None   # at the end (< 2 ticks ahead)
    assert wall_ahead(W_3898, "LONG", 7700.0, 13.5) is None    # beyond it — a breakout
    assert wall_ahead([], "LONG", 7689.25, 13.5) is None
    assert wall_ahead(W_3898, "LONG", 7689.25, 0.0) is None


def test_short_mirror():
    # floor 7679.75 (18:10) is the window low; a SHORT at 7686 with risk 12 ⇒ 6.25pt = 0.52R, touched 8 bars ago
    w = wall_ahead(W_3898, "SHORT", 7686.0, 12.0)
    assert w is not None and w[0] == 7679.75 and w[2] == 8
    assert wall_ahead(W_3898, "SHORT", 7686.0, 9.0) is None    # 6.25 ≥ 0.65×9 = 5.85 ⇒ viable


def test_build_s2_gateway_setup_carries_the_key_only_when_present():
    from backend.v9.systems.five_min.five_min_system import build_s2_gateway_setup
    t1s = SimpleNamespace(direction="LONG", pattern_name="REACTIVE_LONG", confidence=80, entry_price=7689.25,
                          stop_price=7675.75, t1_price=7709.5, t2_price=7716.25, t3_price=None,
                          sizing_contracts=3)
    off = build_s2_gateway_setup(t1s, {"t1_structure_exhausted": True})
    assert "t1_wall_ahead" not in off["metadata"]                      # OFF ⇒ byte-identical
    on = build_s2_gateway_setup(t1s, {"t1_wall_ahead": "S2 REACTIVE LONG: wall 7697.25 …"})
    assert on["metadata"]["t1_wall_ahead"].startswith("S2 REACTIVE LONG: wall 7697.25")


class _PastTheWallGate(Exception):
    """Raised by the gate that runs right AFTER wall_ahead (cluster_guard) ⇒ the setup was not stopped by it."""


def _route(monkeypatch, wall_flag, with_key=True):
    from unittest.mock import MagicMock
    from tests.v9.regression.test_sizing_consolidation import _make_gateway
    monkeypatch.setenv("SIZING_CONSOLIDATION_V1", "1")
    if wall_flag is None:
        monkeypatch.delenv("WALL_AHEAD_SKIP_V1", raising=False)
    else:
        monkeypatch.setenv("WALL_AHEAD_SKIP_V1", wall_flag)
    gw = _make_gateway()
    gw.cluster_guard = MagicMock(is_blocked=MagicMock(side_effect=_PastTheWallGate()))
    monkeypatch.setattr("backend.v9.gateway.trading_gateway.is_within_firing_window", lambda: True)
    monkeypatch.setattr("backend.v9.services.kill_switch.is_engaged", lambda: (False, ""))
    monkeypatch.setattr("backend.v9.services.feed_watchdog.is_feed_alive", lambda: (True, "ok"))
    md = {"pattern": "ZLR", "sizing": "full"}
    if with_key:
        md["t1_wall_ahead"] = "S4 ZLR LONG: wall 7507.00 is 4.00pt ahead = 0.57R < 0.65R"
    setup = {"firing_system": 4, "direction": "LONG", "classification": "ZLR", "confidence": 0.8,
             "entry_price": 7503.0, "stop": 7496.0, "t1": 7510.0, "t2": None, "t3": None, "metadata": md}
    return gw.route_setup(setup, 4)


def test_gateway_blocks_with_the_flag(monkeypatch):
    r = _route(monkeypatch, "1")
    assert r["blocked_by"] == "wall_ahead" and "wall 7507.00" in r["reason"]


def test_gateway_ignores_the_key_without_the_flag(monkeypatch):
    # anti-tautology: the same setup, flag unset / "0" ⇒ it walks past the gate to cluster_guard
    import pytest
    with pytest.raises(_PastTheWallGate):
        _route(monkeypatch, None)
    with pytest.raises(_PastTheWallGate):
        _route(monkeypatch, "0")


def test_gateway_no_key_no_block(monkeypatch):
    import pytest
    with pytest.raises(_PastTheWallGate):
        _route(monkeypatch, "1", with_key=False)
