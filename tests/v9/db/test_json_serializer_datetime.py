"""P31 §10 — Engine-level JSON serializer accepts datetime in JSON columns.

Regression for the Woodies 18s SLOW: each TLB/ZLR/VEGAS pattern fire built
a quality.metadata dict that may contain datetime objects. SQLAlchemy's
default JSON encoder raised `TypeError: Object of type datetime is not
JSON serializable`, which surfaced as PendingRollbackError storms and
~18s wall-clock per Woodies bar.

Fix lives in `backend/v9/db/session.py`: a `_json_serializer` that wraps
`json.dumps` with `default=str` is passed to `create_engine`.

These tests pin:
1. `_json_serializer` itself accepts datetime/date/Decimal.
2. A V9Trade INSERT through an engine configured with `_json_serializer`
   succeeds when `quality` / `cross_context` contain datetime values
   (full round-trip via SQLAlchemy session).
3. A vanilla engine (no json_serializer) raises TypeError on the same
   payload — proves the fix is what's saving us.
"""

import json
import os
from datetime import datetime, date, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("BRIDGE_TOKEN", "michael-mems26-2026")

from backend.v9.db.session import Base, _json_serializer  # noqa: E402
from backend.v9.db.models.trades import V9Trade  # noqa: E402


def test_json_serializer_handles_datetime():
    """Engine serializer must convert datetime via str()."""
    payload = {"ts": datetime(2026, 5, 21, 12, 34, 56, tzinfo=timezone.utc)}
    s = _json_serializer(payload)
    parsed = json.loads(s)
    assert "ts" in parsed
    assert "2026-05-21" in parsed["ts"]
    assert "12:34:56" in parsed["ts"]


def test_json_serializer_handles_date_and_decimal():
    payload = {"d": date(2026, 5, 21), "amt": Decimal("123.45")}
    s = _json_serializer(payload)
    parsed = json.loads(s)
    assert parsed == {"d": "2026-05-21", "amt": "123.45"}


def test_json_serializer_passes_through_native_json_types():
    payload = {
        "i": 1,
        "f": 1.5,
        "s": "x",
        "b": True,
        "n": None,
        "lst": [1, 2, 3],
        "obj": {"k": "v"},
    }
    parsed = json.loads(_json_serializer(payload))
    assert parsed == payload


def _build_engine(with_fix: bool):
    kwargs = {"connect_args": {"check_same_thread": False}}
    if with_fix:
        kwargs["json_serializer"] = _json_serializer
    eng = create_engine("sqlite:///:memory:", **kwargs)
    Base.metadata.create_all(eng)
    return eng


def _build_trade_with_datetime_metadata():
    now = datetime(2026, 5, 21, 12, 34, 56, tzinfo=timezone.utc)
    return V9Trade(
        mode="shadow",
        firing_system=4,
        direction="SHORT",
        state="PENDING",
        entry_ts=now,
        entry_price=7430.0,
        stop=7432.0,
        t1=7428.0,
        t2=7426.0,
        t3=7424.0,
        quality={
            "classification": "TLB",
            "confidence": 0.55,
            "trigger": "TLB",
            "metadata": {
                "pattern": "TLB",
                "sizing": "half",
                # ← the killer: datetime object nested in metadata
                "detected_at": now,
            },
        },
        cross_context=[
            {
                "trigger": "TLB",
                "classification": "TLB",
                "systems": {
                    # ← another common path: system snapshot with timestamps
                    "woodies": {
                        "last_signal_ts": now,
                        "active_patterns": [],
                    },
                },
            }
        ],
    )


def test_insert_with_datetime_in_metadata_succeeds_when_fix_applied():
    """Production-style engine MUST accept datetime in quality.metadata."""
    eng = _build_engine(with_fix=True)
    Session = sessionmaker(bind=eng)
    db = Session()
    try:
        trade = _build_trade_with_datetime_metadata()
        db.add(trade)
        db.commit()  # this is the line that exploded in production
        # Round-trip read
        fetched = db.query(V9Trade).first()
        assert fetched is not None
        # datetime serialized to string is fine for advisory metadata
        assert "2026-05-21" in fetched.quality["metadata"]["detected_at"]
        assert (
            "2026-05-21"
            in fetched.cross_context[0]["systems"]["woodies"]["last_signal_ts"]
        )
    finally:
        db.close()


def test_insert_with_datetime_in_metadata_fails_without_fix():
    """Confirm the bug exists on a vanilla engine — proves what the fix solves.

    SQLAlchemy wraps the underlying TypeError in StatementError, so we match
    on the message (which still mentions JSON serializable).
    """
    from sqlalchemy.exc import StatementError

    eng = _build_engine(with_fix=False)
    Session = sessionmaker(bind=eng)
    db = Session()
    try:
        trade = _build_trade_with_datetime_metadata()
        db.add(trade)
        with pytest.raises((TypeError, StatementError), match="not JSON serializable"):
            db.commit()
    finally:
        db.rollback()
        db.close()
