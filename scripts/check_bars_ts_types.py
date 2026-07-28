#!/usr/bin/env python3
"""D-0717-B diagnostic — print the ACTUAL ts column types + sample rows for
v9_bars_5min vs v9_bars_5min_woodies from the live local Postgres.

Why: both SQLAlchemy models declare ts = DateTime(timezone=True), but live
evidence (2026-07-17) shows v9_bars_5min rows reading 3h early (13:40+03:00
for the 16:40-IL bar) while v9_bars_5min_woodies lands correct — i.e. the
live 5min table drifted to `timestamp without time zone` (create_all never
ALTERs an existing table), so the "+00:00" of the bound ISO string was
silently dropped. This script proves/refutes that from information_schema.

Run ON THE MAC (the sandbox has no DB access):
    python3 scripts/check_bars_ts_types.py
Read-only — SELECTs only, no writes, safe during live trading.
"""
import os
import sys

from sqlalchemy import create_engine, text

URL = os.environ.get("DATABASE_URL", "postgresql://localhost/mems26")
TABLES = ("v9_bars_5min", "v9_bars_5min_woodies")


def main() -> int:
    engine = create_engine(URL)
    with engine.connect() as conn:
        try:
            tz = conn.execute(text("SHOW timezone")).scalar()
            now_row = conn.execute(
                text("SELECT now(), now() AT TIME ZONE 'UTC'")).fetchone()
            print(f"DATABASE_URL              : {URL}")
            print(f"session TimeZone          : {tz}")
            print(f"now() (session tz)        : {now_row[0]}")
            print(f"now() AT TIME ZONE 'UTC'  : {now_row[1]}")
        except Exception as e:  # SQLite fallback etc.
            print(f"[warn] not Postgres or SHOW failed: {e}")

        for t in TABLES:
            print(f"\n── {t} ──")
            try:
                dt = conn.execute(text(
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_name = :t AND column_name = 'ts'"
                ), {"t": t}).scalar()
                print(f"ts data_type: {dt!r}")
            except Exception as e:
                print(f"ts data_type: ERROR {e}")
                continue
            try:
                rows = conn.execute(text(
                    f"SELECT ts, symbol, close FROM {t} "  # noqa: S608 — fixed table list
                    "ORDER BY ts DESC LIMIT 2"
                )).fetchall()
                if not rows:
                    print("  (no rows)")
                for r in rows:
                    print(f"  sample: ts={r[0]!r}  (py type={type(r[0]).__name__}, "
                          f"tzinfo={getattr(r[0], 'tzinfo', None)})  "
                          f"symbol={r[1]} close={r[2]}")
            except Exception as e:
                print(f"  sample read ERROR: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
