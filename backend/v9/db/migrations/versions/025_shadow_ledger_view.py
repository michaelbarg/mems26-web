#!/usr/bin/env python3
"""025: Shadow ledger — v9_shadow_events table + unified v9_shadow_ledger VIEW.

T-153 fix: the original VIEW (t153_shadow_ledger_view.sql) was never run by
any migration runner. This versioned migration creates:
  1. v9_shadow_events — the new shadow events table (the fourth UNION leg)
  2. v9_shadow_ledger — the unified VIEW with ts::timestamptz cast and unit column

Run: python3 backend/v9/db/migrations/versions/025_shadow_ledger_view.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, ROOT)


SQL = """
-- v9_shadow_events: the durable shadow ledger for all new flags
CREATE TABLE IF NOT EXISTS v9_shadow_events (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    session_date DATE,
    flag VARCHAR(80) NOT NULL,
    trade_id INTEGER,
    pattern VARCHAR(120),
    direction VARCHAR(10),
    price DOUBLE PRECISION,
    decision VARCHAR(40),
    pnl_sim DOUBLE PRECISION,
    unit VARCHAR(30),
    outcome VARCHAR(40),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_v9_shadow_events_ts ON v9_shadow_events(ts);
CREATE INDEX IF NOT EXISTS ix_v9_shadow_events_flag ON v9_shadow_events(flag);

-- Drop the old VIEW if it exists (may have been applied manually)
DROP VIEW IF EXISTS v9_shadow_ledger;

-- Unified VIEW with ts cast and unit column
CREATE VIEW v9_shadow_ledger AS

SELECT
    ts,
    'S7' AS source,
    'SYSTEM7_SCORE' AS flag,
    trade_id,
    pattern,
    direction,
    entry_price AS price,
    CASE WHEN blocked THEN 'BLOCKED' ELSE 'PASSED' END AS decision,
    score AS pnl_sim,
    'score_s7' AS unit,
    outcome
FROM v9_s7_shadow_log

UNION ALL

SELECT
    ts,
    'TSF' AS source,
    'TREND_STEP_ENTRY_V1' AS flag,
    trade_id,
    day_type AS pattern,
    direction,
    NULL AS price,
    CASE WHEN would_apply THEN 'WOULD_APPLY' ELSE 'NO_CHANGE' END AS decision,
    delta_pts AS pnl_sim,
    'pts_delta' AS unit,
    NULL AS outcome
FROM v9_tsf_shadow_log

UNION ALL

SELECT
    ts::timestamptz,
    'DAYTYPE' AS source,
    'DAY_TYPE_TRANSITIONS' AS flag,
    NULL AS trade_id,
    from_type || ' -> ' || to_type AS pattern,
    NULL AS direction,
    price,
    trigger AS decision,
    NULL AS pnl_sim,
    'transition' AS unit,
    NULL AS outcome
FROM v9_day_type_shadow_transitions

UNION ALL

SELECT
    ts,
    'SHADOW_EVENT' AS source,
    flag,
    trade_id,
    pattern,
    direction,
    price,
    decision,
    pnl_sim,
    unit,
    outcome
FROM v9_shadow_events

ORDER BY ts DESC;
"""


def main():
    _env_path = os.path.join(ROOT, ".env")
    if os.path.exists(_env_path):
        with open(_env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())

    from backend.v9.db.safe_writer import safe_execute
    for stmt in SQL.split(";"):
        stmt = stmt.strip()
        if stmt:
            safe_execute(stmt, ())
    print("025: v9_shadow_events table + v9_shadow_ledger VIEW created/updated")

    # Verify
    from backend.v9.db.read import read_all
    rows = read_all("SELECT count(*) as n FROM v9_shadow_ledger", {})
    print(f"  v9_shadow_ledger: {rows[0]['n']} rows")
    rows2 = read_all("SELECT count(*) as n FROM v9_shadow_events", {})
    print(f"  v9_shadow_events: {rows2[0]['n']} rows")


if __name__ == "__main__":
    main()
