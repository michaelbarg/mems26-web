"""P31-04 — journal /trades/log SQL filter + row cap."""

from backend.v9.db.models import V9Trade
from backend.v9.api.journal_compat_routes import _fetch_v9_trades, _modes_for_types


def test_modes_for_types():
    assert _modes_for_types(["shadow"]) == ["shadow"]
    assert "demo" in _modes_for_types(["live"])
    assert "shadow" in _modes_for_types(["shadow", "live"])


def test_fetch_v9_trades_respects_limit(db):
    for i in range(12):
        db.add(
            V9Trade(
                mode="shadow",
                firing_system=2,
                direction="LONG",
                state="CLOSED",
                entry_price=5000.0 + i,
                stop=4990.0,
                t1=5010.0,
                t2=0.0,
                t3=0.0,
                quality={"classification": "TEST", "metadata": {}},
                cross_context=[{"systems": {"woodies_system": {"x": "y" * 5000}}}],
            )
        )
    db.commit()

    rows = _fetch_v9_trades(["shadow"], limit=5, min_score=0, db=db)
    assert len(rows) == 5
    assert all(r["is_shadow"] for r in rows)


def test_fetch_v9_trades_excludes_demo_when_shadow_only(db):
    db.add(
        V9Trade(
            mode="demo",
            firing_system=2,
            direction="LONG",
            state="CLOSED",
            entry_price=6000.0,
            stop=5990.0,
            t1=6010.0,
            t2=0.0,
            t3=0.0,
        )
    )
    db.add(
        V9Trade(
            mode="shadow",
            firing_system=2,
            direction="LONG",
            state="CLOSED",
            entry_price=6100.0,
            stop=6090.0,
            t1=6110.0,
            t2=0.0,
            t3=0.0,
        )
    )
    db.commit()

    rows = _fetch_v9_trades(["shadow"], limit=50, min_score=0, db=db)
    assert len(rows) == 1
    assert rows[0]["entry_price"] == 6100.0
