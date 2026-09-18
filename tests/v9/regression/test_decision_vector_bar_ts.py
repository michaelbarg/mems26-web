"""T-416 regression: the kind='BAR' SituationVector write must send a real
timestamp to v9_decision_vectors.ts (`timestamp with time zone`), never a raw
epoch string.

Found 2026-09-18 10:10 by cowork-dev. bar_level_detector passed
``ts=str(bar_ts_raw)``; for a FRESH bar ``bar_data["ts"]`` is an epoch int, so
the insert carried '1789715100' and Postgres rejected it:

    (psycopg2.errors.DatetimeFieldOverflow) date/time field value out of range:
    "1789715100"
    LINE 4: VALUES ('1789715100', 'BAR', NULL, ...

Once per 5-min bar, silently (the caller swallows). Only the STALE hydration
bars carried an ISO string and parsed, which is why the table held 6,820 rows
across just 91 distinct ts -- all stamped with the same 23:55 bar, and not one
genuine fresh bar in two days.
"""
import re
from pathlib import Path

SRC = (
    Path(__file__).resolve().parents[3]
    / "backend/v9/services/trade_manager/bar_level_detector.py"
)


def _bar_log_call() -> str:
    """The `_bld_sv_log(...)` call that writes the kind='BAR' row."""
    text = SRC.read_text(encoding="utf-8")
    m = re.search(r"_bld_sv_log\((.*?)\)\n", text, re.S)
    assert m, "the kind='BAR' _bld_sv_log(...) call vanished from bar_level_detector"
    body = m.group(1)
    assert 'kind="BAR"' in body, "matched the wrong _bld_sv_log call"
    return body


def test_bar_row_ts_is_not_the_raw_epoch():
    """The regression itself: ts=str(bar_ts_raw) is what PG rejected."""
    assert "str(bar_ts_raw)" not in _bar_log_call(), (
        "kind='BAR' is passing the raw bar ts again -- for a fresh bar that is an "
        "epoch int, and every insert will be rejected with DatetimeFieldOverflow"
    )


def test_bar_row_ts_uses_the_parsed_datetime():
    """`bar_ts` is already parsed a few lines up and used for the freshness gate."""
    assert "bar_ts.isoformat()" in _bar_log_call(), (
        "kind='BAR' must send the parsed datetime (bar_ts.isoformat())"
    )


def test_parsed_bar_ts_is_guaranteed_non_none_at_the_call_site():
    """bar_ts.isoformat() is only safe because the branch cannot be entered with
    bar_ts=None -- keep that guard honest."""
    text = SRC.read_text(encoding="utf-8")
    assert "_bld_bar_fresh = bar_ts is not None" in text, (
        "the freshness guard no longer proves bar_ts is non-None; "
        "bar_ts.isoformat() at the kind='BAR' write could raise AttributeError"
    )


def test_epoch_string_would_not_survive_a_timestamp_column():
    """Pins WHY, so a future reader does not 'simplify' the fix back."""
    from datetime import datetime, timezone

    raw = 1789715100  # the value Postgres rejected, 2026-09-18 10:05 IDT
    assert not str(raw).replace("-", "").isdigit() is False  # str() -> bare digits
    parsed = datetime.fromtimestamp(raw, tz=timezone.utc)
    assert parsed.isoformat().startswith("2026-09-18T07:05:00")
