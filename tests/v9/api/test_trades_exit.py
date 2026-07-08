"""POST /api/v9/trades/{id}/exit — cockpit manual close."""

from backend.v9.app import app
from backend.v9.services.trade_manager import TradeManager
from backend.v9.services.trade_manager.state_machine import TradeState


def test_exit_trade_closes_filled_shadow(client, db):
    tm = TradeManager(db=db)
    app.state.trade_manager = tm
    setup = {
        "firing_system": 2,
        "direction": "LONG",
        "stop": 5240.0,
        "t1": 5250.0,
        "t2": 5255.0,
        "t3": 5260.0,
        # L7 (2026-07-08): the trade's contract count is now persisted from the
        # setup (DB == Sierra bracket). This test means a 3-contract trade —
        # say so explicitly (a sizing-less setup is honestly 1 contract).
        "contracts": 3,
    }
    tid = tm.accept_setup(setup, "shadow")
    tm.on_fill(tid, 5245.0)
    db.commit()

    resp = client.post(
        f"/api/v9/trades/{tid}/exit",
        json={"exit_price": 5250.0},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["state"] == TradeState.CLOSED.value
    assert body["exit_reason"] == "manual"
    assert body["pnl_usd"] == 75.0  # 3 contracts × 5 pts × $5/pt

    from backend.v9.db.models import V9Trade

    trade = db.query(V9Trade).filter(V9Trade.id == tid).first()
    assert trade.state == TradeState.CLOSED.value
    assert trade.pnl_usd == 75.0


def test_exit_trade_idempotent_when_already_closed(client, db):
    tm = TradeManager(db=db)
    app.state.trade_manager = tm
    tid = tm.accept_setup(
        {
            "firing_system": 2,
            "direction": "LONG",
            "stop": 5240.0,
            "t1": 5250.0,
            "t2": 5255.0,
            "t3": 5260.0,
        },
        "shadow",
    )
    tm.on_fill(tid, 5245.0)
    trade = tm._get_trade(tid)
    trade.exit_price = 5245.0
    tm.close_trade(tid, "manual")
    db.commit()

    resp = client.post(f"/api/v9/trades/{tid}/exit", json={})
    assert resp.status_code == 200
    assert resp.json().get("already_closed") is True


def test_exit_trade_404(client, db):
    app.state.trade_manager = TradeManager(db=db)
    resp = client.post("/api/v9/trades/999999/exit", json={})
    assert resp.status_code == 404


def test_exit_trade_legacy_open_state(client, db):
    """Cockpit active card uses state=OPEN — must not 500 on manual exit."""
    from backend.v9.db.models import V9Trade

    tm = TradeManager(db=db)
    app.state.trade_manager = tm
    row = V9Trade(
        mode="shadow",
        firing_system=4,
        direction="LONG",
        state="OPEN",
        entry_price=5900.0,
        stop=5890.0,
        t1=5910.0,
        t2=5920.0,
        t3=5930.0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    resp = client.post(f"/api/v9/trades/{row.id}/exit", json={"reason": "manual"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["state"] == TradeState.CLOSED.value

    trade = db.query(V9Trade).filter(V9Trade.id == row.id).first()
    assert trade.state == TradeState.CLOSED.value
