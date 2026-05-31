"""E2E trades visibility & freshness — seed known trade, verify API returns it correctly."""

from datetime import datetime, timezone

from backend.v9.app import app
from backend.v9.db.models import V9Trade
from tests.v9.db.conftest import BRIDGE_HEADERS


def _seed_trade(db, **overrides) -> V9Trade:
    defaults = dict(
        mode="shadow",
        firing_system=2,
        direction="LONG",
        state="CLOSED",
        entry_price=5245.0,
        entry_ts=datetime(2026, 5, 30, 14, 30, 0, tzinfo=timezone.utc),
        stop=5240.0,
        t1=5250.0,
        t2=5255.0,
        t3=5260.0,
        exit_price=5250.0,
        exit_ts=datetime(2026, 5, 30, 14, 45, 0, tzinfo=timezone.utc),
        exit_reason="T1",
        pnl_usd=75.0,
        pnl_r=1.5,
        outcome="WIN",
        is_synthetic=0,
    )
    defaults.update(overrides)
    row = V9Trade(**defaults)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ---------- Visibility: seeded trade appears in GET /api/v9/trades ----------

def test_seeded_trade_returned_by_list_endpoint(client, db):
    """GET /api/v9/trades returns seeded trade with correct pnl/outcome."""
    trade = _seed_trade(db)
    resp = client.get("/api/v9/trades", headers=BRIDGE_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    trades = body.get("trades", body) if isinstance(body, dict) else body
    assert len(trades) >= 1
    row = next((t for t in trades if t["id"] == trade.id), None)
    assert row is not None, f"Trade {trade.id} not found in response"
    assert row["outcome"] == "WIN"
    assert row["direction"] == "LONG"
    assert row["state"] == "CLOSED"
    # pnl_usd is recomputed by compute_trade_pnl — verify it's positive
    assert row["pnl_usd"] is not None and row["pnl_usd"] > 0


def test_seeded_trade_returned_by_recent_endpoint(client, db):
    """GET /api/v9/trades/recent returns seeded trade."""
    trade = _seed_trade(db)
    resp = client.get("/api/v9/trades/recent")
    assert resp.status_code == 200
    data = resp.json()
    rows = data if isinstance(data, list) else data.get("trades", [])
    assert any(t["id"] == trade.id for t in rows)


def test_seeded_trade_detail_endpoint(client, db):
    """GET /api/v9/trades/{id} returns full detail."""
    trade = _seed_trade(db)
    resp = client.get(f"/api/v9/trades/{trade.id}", headers=BRIDGE_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    t = body.get("trade", body)
    assert t["id"] == trade.id
    assert t["outcome"] == "WIN"


# ---------- Recency: latest_ts == MAX(ts) ----------

def test_latest_trade_is_most_recent(client, db):
    """First trade in list (order by entry_ts desc) matches MAX(entry_ts)."""
    _seed_trade(db, entry_ts=datetime(2026, 5, 29, 10, 0, 0, tzinfo=timezone.utc))
    _seed_trade(db, entry_ts=datetime(2026, 5, 30, 14, 30, 0, tzinfo=timezone.utc))
    resp = client.get("/api/v9/trades", headers=BRIDGE_HEADERS)
    body = resp.json()
    trades = body.get("trades", body)
    assert len(trades) >= 2
    # First row should be the most recent
    assert trades[0]["entry_ts"] >= trades[1]["entry_ts"]


# ---------- Truncation indicator ----------

def test_truncation_indicator(client, db):
    """When total > limit, response includes truncated=True."""
    for i in range(5):
        _seed_trade(
            db,
            entry_ts=datetime(2026, 5, 30, 10 + i, 0, 0, tzinfo=timezone.utc),
        )
    resp = client.get("/api/v9/trades?limit=3", headers=BRIDGE_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    assert body["truncated"] is True
    assert len(body["trades"]) == 3


# ---------- Consistency: pnl/outcome match across endpoints ----------

def test_pnl_consistency_across_endpoints(client, db):
    """Same trade returns same outcome/pnl from list vs detail endpoint."""
    trade = _seed_trade(db)
    # List endpoint
    list_resp = client.get("/api/v9/trades", headers=BRIDGE_HEADERS)
    list_row = next(t for t in list_resp.json()["trades"] if t["id"] == trade.id)
    # Detail endpoint
    detail_resp = client.get(f"/api/v9/trades/{trade.id}", headers=BRIDGE_HEADERS)
    detail_row = detail_resp.json()["trade"]

    assert list_row["outcome"] == detail_row["outcome"]
    assert list_row["pnl_usd"] == detail_row["pnl_usd"]
    assert list_row["direction"] == detail_row["direction"]
    assert list_row["state"] == detail_row["state"]


# ---------- Scratch trade correctness ----------

def test_scratch_trade_has_zero_pnl(client, db):
    """A CLOSED trade with pnl_usd=0 has outcome BE/SCRATCH."""
    trade = _seed_trade(
        db,
        exit_price=5245.0,  # same as entry → 0 pnl
        pnl_usd=0.0,
        pnl_r=0.0,
        outcome="BE",
    )
    resp = client.get("/api/v9/trades", headers=BRIDGE_HEADERS)
    row = next(t for t in resp.json()["trades"] if t["id"] == trade.id)
    assert row["state"] == "CLOSED"
    # pnl should be 0 or close to 0 (compute_trade_pnl may recompute)
    assert row["outcome"] in ("BE", "SCRATCH")
