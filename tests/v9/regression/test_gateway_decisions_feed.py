"""07-15 (Michael: "שיהיה ברור בכל רגע נתון למה לא ירה") — the live decisions feed.

Every route_setup attempt must be recorded on gw.decisions (fired / shadow-only /
blocked+gate), and /api/v9/gateway/decisions must summarize today's counts.
The recorder must never raise into the trading path.
"""
import asyncio
from types import SimpleNamespace

from backend.v9.gateway import trading_gateway as tg
from backend.v9.api.v9.gateway_routes import gateway_decisions


def _isolate_gates(monkeypatch):
    """Pin competing production-ON gates OFF so each test owns its blocked_by.

    .env loads DIRECTION_CONTEXT / CONT_TREND_FILTER / ZONE_LIMIT_ENTRY_V1 =1;
    those fire before dedup/shadow paths and make hermetic assertions flake
    (cowork 07-20: duplicate_fire → zone_limit_late_entry).
    """
    for flag in (
        "DIRECTION_CONTEXT",
        "CONT_TREND_FILTER",
        "ZONE_LIMIT_ENTRY_V1",
        "LSMA_FLAT_GATE_V1",
        "DAYTYPE_PLAYBOOK",
        "DAYTYPE_POSITION_GATE",
        "RR_ENTRY_GATE_V1",
        "RISK_CONSECUTIVE_LOSS_LIMIT",
        "DEDUP_FIRE_GUARD",
        # cowork 07-20 (Rule-5 symmetric verify): wall-clock gates — under full
        # .env at night, eod_entry_cutoff (past 14:15 CT) steals every block.
        "EOD_RISK_WINDOW_V1",
        "NEWS_BLACKOUT_V1",
        "OPENING_TYPE_GATE",
        "RISK_HALT_V1",
    ):
        monkeypatch.setenv(flag, "0")


def _gw(monkeypatch):
    _isolate_gates(monkeypatch)
    monkeypatch.setattr(tg, "is_within_firing_window", lambda: True)
    gw = tg.TradingGateway()
    monkeypatch.setattr(gw, "_execute_shadow", lambda *a, **k: {"trade_id": "t"})
    monkeypatch.setattr(gw, "_capture_cross_context",
                        lambda: {"day_type_machine": {}, "woodies_system": {}, "tpo_system": {}})
    return gw


def _setup(price=7537.75, pat="REACTIVE_SHORT", direction="SHORT"):
    return {"direction": direction, "classification": pat, "metadata": {"pattern": pat},
            "entry_price": price, "stop": 7546.25, "t1": 7531.38}


def test_shadow_only_decision_recorded(monkeypatch):
    gw = _gw(monkeypatch)
    gw.route_setup(_setup(), 2)
    assert len(gw.decisions) == 1
    d = gw.decisions[-1]
    assert d["blocked_by"] is None
    assert d["outcome"] == "shadow_only"
    assert d["pattern"] == "REACTIVE_SHORT"
    assert d["direction"] == "SHORT"
    assert d["trade_id"] == "t"


def test_blocked_decision_recorded_with_gate(monkeypatch):
    gw = _gw(monkeypatch)
    monkeypatch.setenv("DEDUP_FIRE_GUARD", "1")  # after isolate
    gw.route_setup(_setup(), 2)
    gw.route_setup(_setup(), 2)  # identical → duplicate_fire
    assert len(gw.decisions) == 2
    d = gw.decisions[-1]
    assert d["blocked_by"] == "duplicate_fire"
    assert d["outcome"] == "blocked"


def test_recorder_survives_patternless_setup(monkeypatch):
    gw = _gw(monkeypatch)
    gw.route_setup({"direction": "LONG", "entry_price": 7500.0,
                    "stop": 7495.0, "t1": 7505.0}, 2)
    assert len(gw.decisions) == 1  # recorded, pattern=None, no exception


def test_ring_buffer_capped():
    gw = tg.TradingGateway()
    assert gw.decisions.maxlen == 300


def test_decisions_endpoint_counts_today(monkeypatch):
    gw = _gw(monkeypatch)
    monkeypatch.setenv("DEDUP_FIRE_GUARD", "1")  # after isolate
    gw.route_setup(_setup(), 2)          # shadow_only
    gw.route_setup(_setup(), 2)          # blocked (dup)
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(trading_gateway=gw)))
    out = asyncio.run(gateway_decisions(req, limit=10))
    assert out["today"]["blocked"] == 1
    assert out["today"]["shadow_only"] == 1
    assert out["today"]["fired"] == 0
    assert out["today"]["by_gate"] == {"duplicate_fire": 1}
    assert out["decisions"][0]["blocked_by"] == "duplicate_fire"  # newest first
    assert out["decisions"][0]["t_il"]  # IL clock present
