"""Tests: V9 model save/load."""

from datetime import datetime, timezone
from backend.v9.db.models import (
    V9Bar5Min, V9BarTickReversal, V9Bar30MinWoodies, V9TpoBar,
    V9SystemSignal, V9SystemMarker, V9Trade, V9TradeManagementLog,
    V9DailyQualityReport, V9SystemConfig, V9AccountStatus,
)


def test_bar_5min_save_load(db):
    bar = V9Bar5Min(
        ts=datetime(2026, 5, 9, 14, 30, tzinfo=timezone.utc),
        symbol="MES", open=5412.50, high=5415.00, low=5410.25, close=5411.00,
        volume=1234, poc_vol=234, vah=5414.00, val=5410.50,
    )
    db.add(bar)
    db.commit()
    result = db.query(V9Bar5Min).first()
    assert result.open == 5412.50
    assert result.symbol == "MES"
    assert result.volume == 1234


def test_tick_reversal_save_load(db):
    bar = V9BarTickReversal(
        ts=datetime(2026, 5, 9, 14, 30, tzinfo=timezone.utc),
        tick_size=15,
        open=5412.50, high=5415.00, low=5410.25, close=5411.00,
        volume=1234, ask_vol=700, bid_vol=534, delta=166, direction=1,
        footprint_json={"levels": [{"p": 5412.50, "bid": 45, "ask": 120}]},
    )
    db.add(bar)
    db.commit()
    result = db.query(V9BarTickReversal).first()
    assert result.tick_size == 15
    assert result.direction == 1


def test_woodies_save_load(db):
    bar = V9Bar30MinWoodies(
        ts=datetime(2026, 5, 9, 14, 0, tzinfo=timezone.utc),
        open=5412.50, high=5415.00, low=5410.25, close=5411.00,
        volume=5000,
        cci_14=125.5, cci_6_tcci=130.2, trend_state="BLUE",
        zlr_detected=True, zlr_direction="UP",
    )
    db.add(bar)
    db.commit()
    result = db.query(V9Bar30MinWoodies).first()
    assert result.cci_14 == 125.5
    assert result.trend_state == "BLUE"
    assert result.zlr_detected is True


def test_tpo_save_load(db):
    bar = V9TpoBar(
        ts=datetime(2026, 5, 9, 14, 0, tzinfo=timezone.utc),
        letter="D", price=5412.50, level=42, period_id=8,
    )
    db.add(bar)
    db.commit()
    result = db.query(V9TpoBar).first()
    assert result.letter == "D"
    assert result.period_id == 8


def test_signal_save_load(db):
    sig = V9SystemSignal(
        ts=datetime(2026, 5, 9, 14, 30, tzinfo=timezone.utc),
        system_id=1, classification="TACTICAL",
        direction="LONG", confidence=0.85,
        payload={"confluence": 6},
    )
    db.add(sig)
    db.commit()
    result = db.query(V9SystemSignal).first()
    assert result.system_id == 1
    assert result.classification == "TACTICAL"


def test_marker_save_load(db):
    marker = V9SystemMarker(
        ts=datetime(2026, 5, 9, 14, 30, tzinfo=timezone.utc),
        system_id=3, marker_type="ARROW", price=5412.50,
        color="#56d364", label="Cluster Zone",
    )
    db.add(marker)
    db.commit()
    result = db.query(V9SystemMarker).first()
    assert result.marker_type == "ARROW"
    assert result.color == "#56d364"


def test_trade_with_log(db):
    trade = V9Trade(
        mode="SHADOW", firing_system=1, direction="LONG",
        entry_ts=datetime(2026, 5, 9, 14, 30, tzinfo=timezone.utc),
        entry_price=5412.50, stop=5408.00,
        t1=5416.00,
    )
    db.add(trade)
    db.commit()

    log = V9TradeManagementLog(
        trade_id=trade.id,
        ts=datetime(2026, 5, 9, 14, 35, tzinfo=timezone.utc),
        action="STOP_MOVED",
        value={"old": 5408.00, "new": 5412.50},
    )
    db.add(log)
    db.commit()

    result = db.query(V9Trade).first()
    assert result.mode == "SHADOW"
    assert len(result.management_log) == 1
    assert result.management_log[0].action == "STOP_MOVED"


def test_daily_quality_save_load(db):
    report = V9DailyQualityReport(
        date=datetime(2026, 5, 9).date(),
        mode="SHADOW", system_id=1,
        trade_count=5, win_rate=0.60, profit_factor=1.5, max_dd=150.0,
    )
    db.add(report)
    db.commit()
    result = db.query(V9DailyQualityReport).first()
    assert result.win_rate == 0.60


def test_config_save_load(db):
    config = V9SystemConfig(
        system_id=1, mode="SHADOW",
        params={"min_confluence": 5, "max_trades_day": 3},
    )
    db.add(config)
    db.commit()
    result = db.query(V9SystemConfig).first()
    assert result.params["min_confluence"] == 5


def test_account_status_save_load(db):
    status = V9AccountStatus(
        mode="SHADOW", daily_pnl=250.0, trade_count=3, margin_used_pct=15.5,
    )
    db.add(status)
    db.commit()
    result = db.query(V9AccountStatus).first()
    assert result.daily_pnl == 250.0
