"""
database.py — PostgreSQL persistence for MEMS26 trades and setup attempts.

Uses asyncpg for async Postgres access.  Falls back gracefully when
DATABASE_URL is not set (Redis-only mode for backwards compat).
"""

import os
import json
import logging
import asyncio
from datetime import datetime, date, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

log = logging.getLogger("db")
ET = ZoneInfo("America/New_York")

DATABASE_URL = os.getenv("DATABASE_URL")

_pool = None


async def get_pool():
    global _pool
    if _pool is None and DATABASE_URL:
        import asyncpg
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
        log.info("Postgres pool created")
    return _pool


async def init_db():
    """Create tables if they don't exist."""
    pool = await get_pool()
    if not pool:
        log.warning("DATABASE_URL not set — Postgres disabled")
        return

    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id              TEXT PRIMARY KEY,
            direction       TEXT NOT NULL,
            entry_price     REAL NOT NULL,
            exit_price      REAL,
            stop            REAL,
            t1              REAL,
            t2              REAL,
            t3              REAL,
            risk_pts        REAL,
            pnl_pts         REAL,
            pnl_usd         REAL,
            contracts       INTEGER DEFAULT 1,
            entry_ts        BIGINT NOT NULL,
            exit_ts         BIGINT,
            status          TEXT DEFAULT 'OPEN',
            close_reason    TEXT,
            setup_type      TEXT,
            day_type        TEXT,
            killzone        TEXT,
            sweep_wick_pts  REAL,
            stacked_count   INTEGER,
            pillars_passed  INTEGER,
            pillar_detail   TEXT,
            rel_vol         REAL,
            cvd_trend       TEXT,
            vwap_dist       REAL,
            vwap_above      BOOLEAN,
            mtf_alignment   INTEGER,
            post_news       BOOLEAN DEFAULT FALSE,
            manual_override BOOLEAN DEFAULT FALSE,
            mae_pts         REAL,
            mfe_pts         REAL,
            duration_min    REAL,
            bars_held       INTEGER,
            exit_efficiency REAL,
            -- Shadow trading fields
            is_shadow           BOOLEAN DEFAULT FALSE,
            cb_respected        BOOLEAN DEFAULT TRUE,
            -- 15 strategic tags
            day_type_at_entry       TEXT,
            killzone_at_entry       TEXT,
            minutes_into_session    INTEGER,
            cb_state_at_entry       TEXT,
            news_state_at_entry     TEXT,
            day_pnl_before_entry    REAL,
            setup_number_today      INTEGER,
            rel_vol_at_entry        REAL,
            cvd_direction_at_entry  TEXT,
            mtf_aligned             BOOLEAN,
            vwap_side               TEXT,
            sweep_wick_pts_tag      REAL,
            fvg_size_pts            REAL,
            stacked_dominant_vol    BOOLEAN,
            bars_building_before_live INTEGER,
            -- V6.5: Entry Narrative + Quality Score
            entry_narrative     JSONB,
            setup_quality_score INTEGER,
            -- Extra
            extra_json      JSONB,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_trades_entry_ts ON trades (entry_ts);
        CREATE INDEX IF NOT EXISTS idx_trades_is_shadow ON trades (is_shadow);
        CREATE INDEX IF NOT EXISTS idx_trades_status ON trades (status);
        CREATE INDEX IF NOT EXISTS idx_trades_day_type ON trades (day_type);
        CREATE INDEX IF NOT EXISTS idx_trades_killzone ON trades (killzone);
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS setup_attempts (
            id              SERIAL PRIMARY KEY,
            ts              BIGINT NOT NULL,
            direction       TEXT,
            setup_type      TEXT,
            level_name      TEXT,
            level_price     REAL,
            price_at_detect REAL,
            rejection_reason TEXT,
            pillars_detail  TEXT,
            day_type        TEXT,
            killzone        TEXT,
            is_shadow       BOOLEAN DEFAULT FALSE,
            cb_respected    BOOLEAN DEFAULT TRUE,
            -- strategic tags (same as trades for analysis)
            day_type_at_entry       TEXT,
            killzone_at_entry       TEXT,
            minutes_into_session    INTEGER,
            cb_state_at_entry       TEXT,
            news_state_at_entry     TEXT,
            day_pnl_before_entry    REAL,
            setup_number_today      INTEGER,
            rel_vol_at_entry        REAL,
            cvd_direction_at_entry  TEXT,
            mtf_aligned             BOOLEAN,
            vwap_side               TEXT,
            -- V6.3 Appendix D: hypothetical forward performance
            hypothetical_mae_60min_pts  REAL,
            hypothetical_mfe_60min_pts  REAL,
            entry_price_hypothetical    REAL,
            stop_hypothetical           REAL,
            extra_json      JSONB,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_attempts_ts ON setup_attempts (ts);
        CREATE INDEX IF NOT EXISTS idx_attempts_is_shadow ON setup_attempts (is_shadow);
        """)

        # Migration: add new columns if missing (idempotent)
        for col, typ in [
            ("hypothetical_mae_60min_pts", "REAL"),
            ("hypothetical_mfe_60min_pts", "REAL"),
            ("entry_price_hypothetical", "REAL"),
            ("stop_hypothetical", "REAL"),
        ]:
            try:
                await conn.execute(f"ALTER TABLE setup_attempts ADD COLUMN IF NOT EXISTS {col} {typ}")
            except Exception:
                pass

        # V6.5: entry_narrative + setup_quality_score on trades table
        for col, typ in [
            ("entry_narrative", "JSONB"),
            ("setup_quality_score", "INTEGER"),
        ]:
            try:
                await conn.execute(f"ALTER TABLE trades ADD COLUMN IF NOT EXISTS {col} {typ}")
            except Exception:
                pass

    log.info("Postgres tables initialized")


# ── Trade CRUD ────────────────────────────────────────────────────────────

def _trade_to_row(t: dict) -> dict:
    """Extract known columns from trade dict, put the rest in extra_json."""
    KNOWN = {
        'id', 'direction', 'entry_price', 'exit_price', 'stop',
        't1', 't2', 't3', 'risk_pts', 'pnl_pts', 'pnl_usd',
        'contracts', 'entry_ts', 'exit_ts', 'status', 'close_reason',
        'setup_type', 'day_type', 'killzone', 'sweep_wick_pts',
        'stacked_count', 'pillars_passed', 'pillar_detail',
        'rel_vol', 'cvd_trend', 'vwap_dist', 'vwap_above',
        'mtf_alignment', 'post_news', 'manual_override',
        'mae_pts', 'mfe_pts', 'duration_min', 'bars_held', 'exit_efficiency',
        'is_shadow', 'cb_respected',
        'day_type_at_entry', 'killzone_at_entry', 'minutes_into_session',
        'cb_state_at_entry', 'news_state_at_entry', 'day_pnl_before_entry',
        'setup_number_today', 'rel_vol_at_entry', 'cvd_direction_at_entry',
        'mtf_aligned', 'vwap_side', 'sweep_wick_pts_tag', 'fvg_size_pts',
        'stacked_dominant_vol', 'bars_building_before_live',
        'entry_narrative', 'setup_quality_score',
    }
    row = {}
    extra = {}
    for k, v in t.items():
        if k in KNOWN:
            row[k] = v
        else:
            extra[k] = v
    if extra:
        row['extra_json'] = json.dumps(extra)
    return row


async def insert_trade(trade: dict):
    """Insert or upsert a trade record."""
    pool = await get_pool()
    if not pool:
        return
    row = _trade_to_row(trade)
    cols = list(row.keys())
    vals = list(row.values())
    placeholders = ', '.join(f'${i+1}' for i in range(len(cols)))
    col_names = ', '.join(cols)
    updates = ', '.join(f'{c} = EXCLUDED.{c}' for c in cols if c != 'id')
    sql = f"""
        INSERT INTO trades ({col_names})
        VALUES ({placeholders})
        ON CONFLICT (id) DO UPDATE SET {updates}
    """
    async with pool.acquire() as conn:
        await conn.execute(sql, *vals)


async def update_trade(trade_id: str, updates: dict):
    """Update specific fields of a trade."""
    pool = await get_pool()
    if not pool:
        return
    sets = ', '.join(f'{k} = ${i+1}' for i, k in enumerate(updates.keys()))
    vals = list(updates.values())
    vals.append(trade_id)
    sql = f"UPDATE trades SET {sets} WHERE id = ${len(vals)}"
    async with pool.acquire() as conn:
        await conn.execute(sql, *vals)


async def get_trade(trade_id: str) -> Optional[dict]:
    pool = await get_pool()
    if not pool:
        return None
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM trades WHERE id = $1", trade_id)
        return _row_to_dict(row) if row else None


async def get_trades_log(
    limit: int = 50,
    is_shadow: Optional[bool] = None,
    day_type: Optional[str] = None,
    killzone: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    status: str = "CLOSED",
) -> list:
    """Query closed trades with optional filters."""
    pool = await get_pool()
    if not pool:
        return []

    conditions = []
    params = []
    idx = 1

    if status:
        conditions.append(f"status = ${idx}")
        params.append(status)
        idx += 1

    if is_shadow is not None:
        conditions.append(f"is_shadow = ${idx}")
        params.append(is_shadow)
        idx += 1

    if day_type and day_type != "all":
        conditions.append(f"day_type = ${idx}")
        params.append(day_type)
        idx += 1

    if killzone and killzone != "all":
        conditions.append(f"killzone = ${idx}")
        params.append(killzone)
        idx += 1

    if from_date:
        # Convert date string to timestamp
        from_ts = int(datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=ET).timestamp())
        conditions.append(f"entry_ts >= ${idx}")
        params.append(from_ts)
        idx += 1

    if to_date:
        to_ts = int((datetime.strptime(to_date, "%Y-%m-%d").replace(tzinfo=ET) + timedelta(days=1)).timestamp())
        conditions.append(f"entry_ts < ${idx}")
        params.append(to_ts)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"SELECT * FROM trades {where} ORDER BY entry_ts DESC LIMIT ${idx}"
    params.append(limit)

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
        return [_row_to_dict(r) for r in rows]


async def get_all_trades(
    is_shadow: Optional[bool] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> list:
    """Get all trades (no limit), for analytics and export."""
    pool = await get_pool()
    if not pool:
        return []

    conditions = []
    params = []
    idx = 1

    if is_shadow is not None:
        conditions.append(f"is_shadow = ${idx}")
        params.append(is_shadow)
        idx += 1

    if from_date:
        from_ts = int(datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=ET).timestamp())
        conditions.append(f"entry_ts >= ${idx}")
        params.append(from_ts)
        idx += 1

    if to_date:
        to_ts = int((datetime.strptime(to_date, "%Y-%m-%d").replace(tzinfo=ET) + timedelta(days=1)).timestamp())
        conditions.append(f"entry_ts < ${idx}")
        params.append(to_ts)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"SELECT * FROM trades {where} ORDER BY entry_ts DESC"

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
        return [_row_to_dict(r) for r in rows]


async def delete_trade(trade_id: str):
    pool = await get_pool()
    if not pool:
        return
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM trades WHERE id = $1", trade_id)


# ── Setup Attempts ────────────────────────────────────────────────────────

async def insert_attempt(attempt: dict):
    """Log a setup attempt (rejected or taken)."""
    pool = await get_pool()
    if not pool:
        return
    KNOWN = {
        'ts', 'direction', 'setup_type', 'level_name', 'level_price',
        'price_at_detect', 'rejection_reason', 'pillars_detail',
        'day_type', 'killzone', 'is_shadow', 'cb_respected',
        'day_type_at_entry', 'killzone_at_entry', 'minutes_into_session',
        'cb_state_at_entry', 'news_state_at_entry', 'day_pnl_before_entry',
        'setup_number_today', 'rel_vol_at_entry', 'cvd_direction_at_entry',
        'mtf_aligned', 'vwap_side',
        'hypothetical_mae_60min_pts', 'hypothetical_mfe_60min_pts',
        'entry_price_hypothetical', 'stop_hypothetical',
    }
    row = {}
    extra = {}
    for k, v in attempt.items():
        if k in KNOWN:
            row[k] = v
        elif k != 'id':
            extra[k] = v
    if extra:
        row['extra_json'] = json.dumps(extra)

    cols = list(row.keys())
    vals = list(row.values())
    placeholders = ', '.join(f'${i+1}' for i in range(len(cols)))
    col_names = ', '.join(cols)
    sql = f"INSERT INTO setup_attempts ({col_names}) VALUES ({placeholders})"
    async with pool.acquire() as conn:
        await conn.execute(sql, *vals)


async def get_attempts(
    limit: int = 200,
    is_shadow: Optional[bool] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> list:
    pool = await get_pool()
    if not pool:
        return []

    conditions = []
    params = []
    idx = 1

    if is_shadow is not None:
        conditions.append(f"is_shadow = ${idx}")
        params.append(is_shadow)
        idx += 1

    if from_date:
        from_ts = int(datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=ET).timestamp())
        conditions.append(f"ts >= ${idx}")
        params.append(from_ts)
        idx += 1

    if to_date:
        to_ts = int((datetime.strptime(to_date, "%Y-%m-%d").replace(tzinfo=ET) + timedelta(days=1)).timestamp())
        conditions.append(f"ts < ${idx}")
        params.append(to_ts)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"SELECT * FROM setup_attempts {where} ORDER BY ts DESC LIMIT ${idx}"
    params.append(limit)

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
        return [_row_to_dict(r) for r in rows]


# ── Seed from Redis ───────────────────────────────────────────────────────

async def seed_from_redis(redis_get_key_fn, redis_url: str, redis_token: str):
    """Migrate existing tradelog entries from Redis to Postgres."""
    pool = await get_pool()
    if not pool:
        return 0

    import httpx
    count = 0
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{redis_url}/keys/mems26:tradelog:*",
                headers={"Authorization": f"Bearer {redis_token}"},
                timeout=10.0
            )
            keys = resp.json().get("result", [])
            if not keys:
                log.info("No Redis tradelog keys to seed")
                return 0

            log.info(f"Seeding {len(keys)} trades from Redis to Postgres...")
            for key in keys:
                val = await redis_get_key_fn(key)
                if val and isinstance(val, dict):
                    val.setdefault('is_shadow', False)
                    val.setdefault('cb_respected', True)
                    try:
                        await insert_trade(val)
                        count += 1
                    except Exception as e:
                        log.warning(f"Seed trade {key} failed: {e}")
    except Exception as e:
        log.error(f"Redis seed failed: {e}")

    log.info(f"Seeded {count} trades from Redis to Postgres")
    return count


# ── Helpers ───────────────────────────────────────────────────────────────

def _row_to_dict(row) -> dict:
    """Convert asyncpg Record to dict, merging extra_json back in."""
    if row is None:
        return {}
    d = dict(row)
    extra = d.pop('extra_json', None)
    d.pop('created_at', None)
    if extra:
        if isinstance(extra, str):
            extra = json.loads(extra)
        d.update(extra)
    return d


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
