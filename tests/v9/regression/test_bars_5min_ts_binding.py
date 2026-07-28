"""D-0717-B — v9_bars_5min write path must bind ts as a tz-AWARE datetime.

Live finding 2026-07-17: v9_bars_5min rows read 3h early (13:40+03:00 for the
16:40-IL bar) while v9_bars_5min_woodies landed correct. Root: the live
v9_bars_5min.ts column drifted from the model (DateTime(timezone=True)) to
plain `timestamp without time zone`; Postgres silently DROPS the "+00:00"
suffix of a bound ISO *string*, storing the UTC wall-clock which session-TZ
casts / local readers then mis-attribute as IL time. Binding the aware
datetime OBJECT makes the driver send an explicit timestamptz value that
round-trips the true instant regardless of column type (naive column →
symmetric session-TZ assignment cast; timestamptz → exact; TEXT → keeps
offset). See backend/v9/api/v9/bars.py post_bars_5min comment D-0717-B and
scripts/check_bars_ts_types.py.

Anti-tautological: POSTs through the REAL route handler and inspects the rows
handed to safe_executemany. Reverting the fix back to `ts.isoformat()` turns
the first param into `str` → RED.
"""
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.v9.api.v9.bars as bars_mod
from backend.v9.api.v9.auth import verify_bridge_token

# 2023-11-14 15:00 UTC = 10:00 EST — inside the RTH gate; >24h old so the
# B-13 fresh-bar staleness/price-band guard is bypassed (same epoch the
# existing test_bars_safe_writer.py RTH tests use).
_RTH_EPOCH = 1699974000


def _app():
    app = FastAPI()
    app.include_router(bars_mod.router)
    app.dependency_overrides[verify_bridge_token] = lambda: "test"
    return TestClient(app)


def test_post_5min_binds_aware_datetime_not_string(monkeypatch):
    captured = {}

    def _spy_executemany(sql, rows):
        captured["sql"] = sql
        captured["rows"] = rows
        return len(rows)

    monkeypatch.setattr(bars_mod, "safe_executemany", _spy_executemany)
    # Isolate from module-level price tracker state left by other tests
    monkeypatch.setattr(bars_mod, "_latest_known_price", None)
    monkeypatch.setattr(bars_mod, "_bar_router", None)

    client = _app()
    resp = client.post("/api/v9/bars/5min", json=[
        {"ts": _RTH_EPOCH, "symbol": "MES", "o": 5000, "h": 5005,
         "l": 4998, "c": 5003, "vol": 3000},
    ])
    assert resp.status_code == 200, resp.text
    assert captured.get("rows"), "write path did not reach safe_executemany"

    ts_param = captured["rows"][0][0]
    assert isinstance(ts_param, datetime), (
        f"ts bound as {type(ts_param).__name__!r} — must be a datetime OBJECT "
        "(an isoformat() string loses its +00:00 offset in a naive PG column → "
        "the 3h-early live bug)"
    )
    assert ts_param.tzinfo is not None and ts_param.utcoffset() == timedelta(0), (
        f"ts must be tz-aware UTC, got tzinfo={ts_param.tzinfo!r}"
    )
    assert ts_param == datetime.fromtimestamp(_RTH_EPOCH, tz=timezone.utc)
