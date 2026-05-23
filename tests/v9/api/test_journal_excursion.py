"""Journal /trades/log includes range + legs from v9_bars_5min."""

import os
from datetime import datetime, timezone
from types import SimpleNamespace

os.environ.setdefault("BRIDGE_TOKEN", "michael-mems26-2026")

from backend.v9.api.journal_compat_routes import _v9_row_to_journal
from backend.v9.services.trade_excursion import prefetch_bars_for_trades


def test_journal_row_has_range_and_legs(db):
    row = SimpleNamespace(
        id=1,
        mode="shadow",
        firing_system=4,
        direction="SHORT",
        state="CLOSED",
        entry_ts=datetime(2026, 5, 21, 2, 0, tzinfo=timezone.utc),
        entry_price=7435.25,
        stop=7438.25,
        t1=7431.25,
        t2=7427.25,
        t3=0.0,
        t1_hit_ts=datetime(2026, 5, 21, 2, 15, tzinfo=timezone.utc),
        t2_hit_ts=datetime(2026, 5, 21, 2, 15, tzinfo=timezone.utc),
        t3_hit_ts=None,
        stop_hit_ts=None,
        exit_ts=datetime(2026, 5, 21, 3, 0, tzinfo=timezone.utc),
        exit_price=7427.25,
        exit_reason="MANUAL",
        pnl_usd=None,
        pnl_r=None,
        outcome="WIN",
        quality={"trigger": "TLB", "metadata": {"pattern": "TLB"}},
    )
    bar_cache = prefetch_bars_for_trades(db, [row])
    mapped = _v9_row_to_journal(row, db, bar_cache)
    assert mapped["price_high"] is not None or mapped["range_note"] is None
    legs = mapped["trade_legs"]
    assert any(l["event"] == "ENTRY" for l in legs)
    assert any(l["event"] == "T1" for l in legs)
    if mapped["mfe_pts"] is not None:
        assert mapped["mfe_pts"] >= 0
