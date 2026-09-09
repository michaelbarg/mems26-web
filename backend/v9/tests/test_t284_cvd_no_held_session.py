"""T-284 — regression test for the *hold + borrow-from-the-same-pool* class.

Incident (2026-09-09, twice: 12:14 and 16:31): ingestion stopped for hours.
Root cause (docs/reports/T284_LEAK_SITE_2026-09-09.md, fix 09928b03):
`post_cumulative_delta` took `db: Session = Depends(get_db)` and ran
`db.query(V9Bar5Min)...first()` INSIDE the 90-point loop with no commit.
The first ORM SELECT autobegins a transaction, so the session's pool
connection stays checked out `idle in transaction` for the WHOLE request,
while every `safe_execute` in the same loop borrows a SECOND connection from
the SAME pool. The bridge abandons the HTTP call at 15 s and re-POSTs 2 s
later without cancelling the running sync handler, so handlers overlap
without bound; at pool_size+max_overflow concurrent handlers the pool is
exhausted, every borrow waits `pool_timeout` and fails. A restart only
resets the clock — the class survives it.

These tests reproduce the class on a deliberately tiny pool (size 1,
overflow 0, timeout 1 s) so the exhaustion happens at ONE concurrent holder
instead of fifteen:

  test_old_pattern_...  — the OLD shape (ORM session held across the loop)
                          starves the pool: safe_execute returns None.
  test_fixed_handler_... — the CURRENT handler completes every point and
                          leaves the pool at checkedout()==0.
  test_handler_signature_... — anti-regression: the handler must never take
                          an ORM session dependency again.
"""

import datetime as dt
import inspect
import os

# bars.py imports auth, which raises at IMPORT time without BRIDGE_TOKEN
# (same guard as test_bars_safe_writer.py / test_b13_d2_staleness.py).
if not os.getenv("BRIDGE_TOKEN"):
    os.environ["BRIDGE_TOKEN"] = "test-token-for-isolation"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# RTH-safe grid: 2026-09-09 13:30 UTC == 09:30 ET (EDT). 78 five-minute
# points => 09:30 .. 15:55 ET, every one inside the handler's RTH gate.
_RTH_OPEN_EPOCH = int(
    dt.datetime(2026, 9, 9, 13, 30, tzinfo=dt.timezone.utc).timestamp()
)
_N_POINTS = 78


@pytest.fixture
def one_conn_engine(tmp_path, monkeypatch):
    """A 1-connection pool shared by the writer and the read helper.

    pool_size=1 / max_overflow=0 / pool_timeout=1 makes "one holder starves
    everyone" observable in a second instead of the production 15-handler,
    30-second version of the same arithmetic.
    """
    eng = create_engine(
        f"sqlite:///{tmp_path / 't284.db'}",
        poolclass=QueuePool,
        pool_size=1,
        max_overflow=0,
        pool_timeout=1,
        connect_args={"check_same_thread": False},
    )

    import backend.v9.db.session as s
    import backend.v9.db.read as r

    # safe_writer._get_engine() does `from ...session import engine` at CALL
    # time, so patching the module attribute is enough.
    monkeypatch.setattr(s, "engine", eng)
    monkeypatch.setattr(s, "SessionLocal", sessionmaker(bind=eng))
    # read.py binds `_read_engine as engine` at import time.
    monkeypatch.setattr(r, "engine", eng)

    from backend.v9.db.models.bars_5min import V9Bar5Min
    from backend.v9.db.models.missing_tables import V9BarsCumulativeDelta

    V9Bar5Min.__table__.create(bind=eng)
    V9BarsCumulativeDelta.__table__.create(bind=eng)

    from backend.v9.db.safe_writer import safe_executemany

    safe_executemany(
        "INSERT INTO v9_bars_5min (ts, symbol, open, high, low, close, volume) "
        "VALUES (?, 'MES', 1, 1, 1, 1, 1)",
        [
            (
                dt.datetime.fromtimestamp(
                    _RTH_OPEN_EPOCH + 300 * i, tz=dt.timezone.utc
                ),
            )
            for i in range(_N_POINTS)
        ],
    )
    assert eng.pool.checkedout() == 0, eng.pool.status()
    return eng


def _points():
    return [
        {"t": _RTH_OPEN_EPOCH + 300 * i, "i": i, "d": 1.0, "cum": float(i)}
        for i in range(_N_POINTS)
    ]


@pytest.fixture
def quiet_bars(monkeypatch):
    """Silence the handler's live side-channels (dispatch / push / router)."""
    import backend.v9.api.v9.bars as bars

    monkeypatch.setattr(bars, "_dispatch", lambda *a, **k: None)
    monkeypatch.setattr(bars, "_record_push", lambda *a, **k: None)
    monkeypatch.setattr(bars, "_route_bar", lambda *a, **k: None)
    return bars


def test_old_pattern_holding_orm_session_starves_the_pool(one_conn_engine):
    """The OLD shape: an ORM SELECT held open across the loop blocks writes.

    This is the mechanism, isolated: one session that has autobegun a
    transaction holds the only pooled connection, so the very next
    safe_execute cannot get one and returns None (its 1-s pool_timeout).
    In production the same arithmetic played out at 15 handlers × 30 s.
    """
    from backend.v9.db.session import SessionLocal
    from backend.v9.db.models.bars_5min import V9Bar5Min
    from backend.v9.db.safe_writer import safe_execute

    db = SessionLocal()
    try:
        # First ORM SELECT autobegins the transaction and checks out conn A.
        row = db.query(V9Bar5Min).order_by(V9Bar5Min.ts).first()
        assert row is not None
        assert one_conn_engine.pool.checkedout() == 1, one_conn_engine.pool.status()
        assert db.in_transaction(), "ORM SELECT must have autobegun a transaction"

        # ... and now the loop body wants a SECOND connection from the same pool.
        result = safe_execute(
            "UPDATE v9_bars_5min SET cumulative_delta=? WHERE id=?", (1.0, row.id)
        )
        assert result is None, (
            "expected pool starvation while the ORM session is held; "
            f"pool={one_conn_engine.pool.status()}"
        )
    finally:
        db.close()


def test_fixed_handler_holds_no_pool_connection(one_conn_engine, quiet_bars):
    """The CURRENT handler: every point lands, nothing is left checked out.

    20 sequential calls stand in for the overlapping bridge re-POSTs. On the
    old code the first call already returns inserted==0 (every INSERT timed
    out behind the held session); on the fixed code all 78 points land and
    the pool returns to zero after each call.
    """
    bars = quiet_bars
    payload = bars.CumulativeDeltaPayload(points=_points())

    for call in range(20):
        out = bars.post_cumulative_delta(payload, _token="x")
        assert out["ok"] is True, out
        assert out["inserted"] == _N_POINTS, (call, out)
        assert out["updated"] == _N_POINTS, (call, out)
        assert out["skipped"] == 0, (call, out)
        assert one_conn_engine.pool.checkedout() == 0, (
            call,
            one_conn_engine.pool.status(),
        )


def test_handler_signature_takes_no_orm_session():
    """Anti-regression: re-adding `db: Session = Depends(get_db)` must fail here.

    The whole T-284 class is "this handler holds a main-pool session across a
    loop that borrows from the same pool". The cheapest permanent guard is
    that the handler simply has no session dependency to hold.
    """
    import backend.v9.api.v9.bars as bars

    params = inspect.signature(bars.post_cumulative_delta).parameters
    assert "db" not in params, (
        "post_cumulative_delta must not depend on an ORM session (T-284) — "
        f"signature is {list(params)}"
    )
    # Strip the docstring first: it deliberately QUOTES the old `db.query(...)`
    # shape as the incident record, so a naive substring check on getsource()
    # matches the description instead of the code.
    src = inspect.getsource(bars.post_cumulative_delta)
    body = src.replace(bars.post_cumulative_delta.__doc__ or "", "")
    assert "db.query(" not in body, "T-284: no ORM query inside this handler"
    assert "read_one(" in body, "T-284: the bar lookup must use the read engine"


# ─────────────────────────────────────────────────────────────────────────────
# T-284 SIBLING — post_volume_profile (cowork 09.09 night-repair).
#
# The leak-site report named post_cumulative_delta as the handler that wedged
# the backend, but the SAME shape lived one screen up in the same file:
# `Depends(get_db)` + `db.query(V9Bar5Min)` materialised into a list that is
# then iterated while `safe_execute` borrows a second connection per row, in
# TWO loops. The class is "hold a main-pool session across a loop that borrows
# from the same pool" — the handler's name is incidental, so the guard has to
# cover every handler with that shape, not just the one that happened to fire.
# ─────────────────────────────────────────────────────────────────────────────


def test_volume_profile_handler_signature_takes_no_orm_session():
    """Anti-regression for the sibling: no ORM session dependency here either."""
    import backend.v9.api.v9.bars as bars

    params = inspect.signature(bars.post_volume_profile).parameters
    assert "db" not in params, (
        "post_volume_profile must not depend on an ORM session (T-284 sibling) — "
        f"signature is {list(params)}"
    )
    src = inspect.getsource(bars.post_volume_profile)
    body = src.replace(bars.post_volume_profile.__doc__ or "", "")
    assert "db.query(" not in body, "T-284: no ORM query inside this handler"
    assert "read_all(" in body, "T-284: the bar lookup must use the read engine"


def test_no_bridge_ingest_handler_depends_on_an_orm_session():
    """Class-level guard: NO bridge POST handler in bars.py may hold a session.

    This is the test that would have caught the sibling on 09-09 without
    anyone thinking to look for it. It enumerates the module's POST handlers
    and asserts none of them takes `db`. If a future handler legitimately
    needs an ORM session it must be added to the allowlist WITH a reason —
    which is the review conversation this class needs to trigger.
    """
    import backend.v9.api.v9.bars as bars

    # name -> reason. An entry here is a REVIEWED exception, not a snooze:
    # both handlers below take a session, `db.add(row)` + `db.commit()`, and
    # never call safe_execute — so they commit and RELEASE the connection
    # instead of pinning it idle-in-transaction while borrowing a second one.
    # That is a different (safe) shape from the T-284 class. Both paths are
    # also muted per CLAUDE.md §DB. Re-check if either ever gains a
    # safe_execute call or a loop.
    ALLOWLIST = {
        "post_footprint": "db.add+db.commit only, no safe_execute, path muted",
        "post_tick_reversal": "db.add+db.commit only, no safe_execute, path muted",
    }

    offenders = []
    for name in dir(bars):
        if not name.startswith("post_"):
            continue
        fn = getattr(bars, name)
        if not callable(fn) or not hasattr(fn, "__module__"):
            continue
        if fn.__module__ != bars.__name__:
            continue
        try:
            params = inspect.signature(fn).parameters
        except (TypeError, ValueError):
            continue
        if "db" in params and name not in ALLOWLIST:
            offenders.append(name)

    assert not offenders, (
        "T-284: these bridge handlers hold an ORM session across their body "
        "while safe_execute borrows from the same pool — the shape that "
        f"stopped ingestion twice on 2026-09-09: {sorted(offenders)}"
    )


def test_fixed_volume_profile_handler_holds_no_pool_connection(
    one_conn_engine, quiet_bars
):
    """The CURRENT sibling handler leaves the pool at checkedout()==0.

    Same 20-sequential-calls stand-in for overlapping bridge re-POSTs.
    """
    bars = quiet_bars
    profiles = [
        {"bar_idx": i, "poc": 1.0, "vah": 2.0, "val": 0.5,
         "total_vol": 10, "levels": []}
        for i in range(8)
    ]
    payload = bars.VolumeProfilePayload(profiles=profiles)

    for call in range(20):
        out = bars.post_volume_profile(payload, _token="x")
        assert one_conn_engine.pool.checkedout() == 0, (
            call,
            one_conn_engine.pool.status(),
        )
