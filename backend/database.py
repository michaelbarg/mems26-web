"""
database.py — PostgreSQL persistence for MEMS26 trades and setup attempts.

Uses asyncpg for async Postgres access.  Falls back gracefully when
DATABASE_URL is not set (Redis-only mode for backwards compat).
"""

import os
import json
import logging
import asyncio
import hashlib
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

        # Phase 6: setup_quality_score on setup_attempts too
        try:
            await conn.execute("ALTER TABLE setup_attempts ADD COLUMN IF NOT EXISTS setup_quality_score INTEGER")
        except Exception:
                pass

        # Phase 6.6: Full setup details on setup_attempts
        for col, typ in [
            ("c1_target", "REAL"),
            ("c2_target", "REAL"),
            ("c3_target", "REAL"),
            ("c3_enabled", "BOOLEAN"),
            ("be_strategy", "TEXT"),
            ("executed", "BOOLEAN DEFAULT FALSE"),
            ("executed_trade_id", "TEXT"),
            ("vegas_score", "INTEGER"),
            ("tpo_score", "INTEGER"),
            ("fvg_score", "INTEGER"),
            ("footprint_score", "INTEGER"),
            ("score_reasons", "TEXT"),
        ]:
            try:
                await conn.execute(f"ALTER TABLE setup_attempts ADD COLUMN IF NOT EXISTS {col} {typ}")
            except Exception:
                pass

        # V6.5.2: Entry mode tags on trades + setup_attempts
        v652_cols = [
            ("entry_mode", "VARCHAR(16)"),
            ("trade_number_of_day", "INTEGER"),
            ("health_score_at_entry", "INTEGER"),
            ("confidence_at_entry", "INTEGER"),
            ("pre_close_blocked", "BOOLEAN DEFAULT FALSE"),
        ]
        for col, typ in v652_cols:
            for tbl in ("trades", "setup_attempts"):
                try:
                    await conn.execute(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS {col} {typ}")
                except Exception:
                    pass

        # Sprint 6: Setup Lifecycle tables
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS setups (
                setup_id            TEXT PRIMARY KEY,
                anchor_ts           BIGINT NOT NULL,
                first_detected_ts   BIGINT NOT NULL,
                last_seen_ts        BIGINT NOT NULL,
                direction           TEXT NOT NULL,
                setup_type          TEXT,
                level_name          TEXT,
                level_price         REAL,
                day_type            TEXT,
                killzone            TEXT,
                initial_entry       REAL,
                initial_stop        REAL,
                initial_score       INTEGER,
                peak_score          INTEGER,
                latest_score        INTEGER,
                observation_count   INTEGER DEFAULT 1,
                status              TEXT DEFAULT 'BUILDING',
                executed            BOOLEAN DEFAULT FALSE,
                executed_trade_id   TEXT,
                outcome             TEXT,
                outcome_ts          BIGINT,
                mae_pts             REAL,
                mfe_pts             REAL,
                c1_target           REAL,
                c2_target           REAL,
                c3_target           REAL,
                be_strategy         TEXT,
                score_reasons       TEXT,
                extra_json          JSONB,
                created_at          TIMESTAMPTZ DEFAULT NOW(),
                updated_at          TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_setups_anchor_ts ON setups (anchor_ts)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_setups_status ON setups (status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_setups_direction ON setups (direction)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_setups_day_type ON setups (day_type)")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS setup_observations (
                id                  SERIAL PRIMARY KEY,
                setup_id            TEXT NOT NULL,
                observation_ts      BIGINT NOT NULL,
                current_price       REAL,
                total_score         INTEGER,
                vegas_score         INTEGER,
                tpo_score           INTEGER,
                fvg_score           INTEGER,
                footprint_score     INTEGER,
                score_reasons       TEXT,
                created_at          TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_obs_setup_id ON setup_observations (setup_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_obs_ts ON setup_observations (observation_ts)")

        # Phase 3.1: Shadow Trade Simulator columns on setups
        for col, typ in [
            ("t1_hit", "BOOLEAN DEFAULT FALSE"),
            ("t1_hit_ts", "BIGINT"),
            ("t2_hit", "BOOLEAN DEFAULT FALSE"),
            ("t2_hit_ts", "BIGINT"),
            ("t3_hit", "BOOLEAN DEFAULT FALSE"),
            ("t3_hit_ts", "BIGINT"),
            ("stop_hit", "BOOLEAN DEFAULT FALSE"),
            ("stop_hit_ts", "BIGINT"),
            ("closed_ts", "BIGINT"),
            ("close_reason", "TEXT"),
            ("pnl_pts", "REAL"),
            ("pnl_usd", "REAL"),
            ("contracts_used", "INTEGER"),
        ]:
            try:
                await conn.execute(f"ALTER TABLE setups ADD COLUMN IF NOT EXISTS {col} {typ}")
            except Exception:
                pass

    log.info("Postgres tables initialized")


# ── Setup Lifecycle ──────────────────────────────────────────────────────

def generate_setup_id(direction: str, setup_type: str, level_name: str,
                      anchor_ts: int) -> str:
    """Anchor Method: deterministic setup_id from anchor signal."""
    raw = f"{direction}|{setup_type or 'UNKNOWN'}|{level_name or 'NONE'}|{anchor_ts}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def upsert_setup(setup_id, anchor_ts, direction, setup_type, level_name,
                       day_type, killzone, initial_entry, initial_stop,
                       score, c1_target, c2_target, c3_target, be_strategy,
                       score_reasons, now_ts):
    """Insert new setup or update existing one's last_seen + scores."""
    pool = await get_pool()
    if not pool:
        return
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO setups (
                setup_id, anchor_ts, first_detected_ts, last_seen_ts,
                direction, setup_type, level_name, day_type, killzone,
                initial_entry, initial_stop, initial_score,
                peak_score, latest_score, observation_count,
                c1_target, c2_target, c3_target, be_strategy, score_reasons,
                status
            )
            VALUES (
                $1, $2, $16, $16,
                $3, $4, $5, $6, $7,
                $8, $9, $10,
                $10, $10, 1,
                $11, $12, $13, $14, $15,
                CASE WHEN $10 >= 50 THEN 'LIVE' ELSE 'BUILDING' END
            )
            ON CONFLICT (setup_id) DO UPDATE SET
                last_seen_ts = $16,
                latest_score = $10,
                peak_score = GREATEST(setups.peak_score, $10),
                observation_count = setups.observation_count + 1,
                day_type = COALESCE(EXCLUDED.day_type, setups.day_type),
                killzone = COALESCE(EXCLUDED.killzone, setups.killzone),
                status = CASE
                    WHEN $10 >= 50 AND setups.status = 'BUILDING' THEN 'LIVE'
                    ELSE setups.status
                END,
                updated_at = NOW()
        """, setup_id, anchor_ts, direction, setup_type, level_name,
             day_type, killzone, initial_entry, initial_stop, score,
             c1_target, c2_target, c3_target, be_strategy, score_reasons,
             now_ts)


async def insert_observation(setup_id, observation_ts, current_price,
                             total_score, vegas_score, tpo_score,
                             fvg_score, footprint_score, score_reasons):
    pool = await get_pool()
    if not pool:
        return
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO setup_observations (
                setup_id, observation_ts, current_price, total_score,
                vegas_score, tpo_score, fvg_score, footprint_score, score_reasons
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, setup_id, observation_ts, current_price, total_score,
             vegas_score, tpo_score, fvg_score, footprint_score, score_reasons)


async def get_recent_setups(limit: int = 50, status: str = None):
    pool = await get_pool()
    if not pool:
        return []
    async with pool.acquire() as conn:
        if status:
            rows = await conn.fetch(
                "SELECT * FROM setups WHERE status = $1 ORDER BY last_seen_ts DESC LIMIT $2",
                status, limit)
        else:
            rows = await conn.fetch(
                "SELECT * FROM setups ORDER BY last_seen_ts DESC LIMIT $1",
                limit)
        return [dict(r) for r in rows]


async def get_setup_with_observations(setup_id: str):
    pool = await get_pool()
    if not pool:
        return None
    async with pool.acquire() as conn:
        setup = await conn.fetchrow("SELECT * FROM setups WHERE setup_id = $1", setup_id)
        if not setup:
            return None
        obs = await conn.fetch(
            "SELECT * FROM setup_observations WHERE setup_id = $1 ORDER BY observation_ts ASC",
            setup_id)
        return {
            "setup": dict(setup),
            "observations": [dict(o) for o in obs],
        }


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
        'entry_mode', 'trade_number_of_day',
        'health_score_at_entry', 'confidence_at_entry', 'pre_close_blocked',
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
        'entry_mode', 'trade_number_of_day',
        'health_score_at_entry', 'confidence_at_entry', 'pre_close_blocked',
        'setup_quality_score',
        'c1_target', 'c2_target', 'c3_target', 'c3_enabled',
        'be_strategy', 'executed', 'executed_trade_id',
        'vegas_score', 'tpo_score', 'fvg_score', 'footprint_score',
        'score_reasons',
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
    sql = f"INSERT INTO setup_attempts ({col_names}) VALUES ({placeholders}) RETURNING id"
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, *vals)
        return row['id'] if row else None


async def get_pending_outcome_attempts(min_age_seconds: int = 3600, limit: int = 50) -> list:
    """Find attempts that are 60+ min old but have no MAE/MFE yet."""
    pool = await get_pool()
    if not pool:
        return []
    import time as _time
    cutoff = int(_time.time()) - min_age_seconds
    max_age = cutoff - 86400  # don't go further than 24 hours back
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, ts, direction, entry_price_hypothetical, stop_hypothetical,
                   setup_quality_score, health_score_at_entry, day_type
            FROM setup_attempts
            WHERE ts <= $1
              AND ts >= $2
              AND hypothetical_mae_60min_pts IS NULL
              AND entry_price_hypothetical IS NOT NULL
              AND stop_hypothetical IS NOT NULL
            ORDER BY ts ASC
            LIMIT $3
        """, cutoff, max_age, limit)
        return [dict(r) for r in rows]


async def update_attempt_outcome(
    attempt_id: int, mae_pts: float, mfe_pts: float,
    outcome: str, extra: dict = None,
):
    """Update MAE/MFE and outcome for a setup attempt."""
    pool = await get_pool()
    if not pool:
        return
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE setup_attempts SET
                hypothetical_mae_60min_pts = $1,
                hypothetical_mfe_60min_pts = $2,
                extra_json = COALESCE(extra_json, '{}'::jsonb) || $3::jsonb
            WHERE id = $4
        """, mae_pts, mfe_pts, json.dumps({"outcome": outcome, **(extra or {})}), attempt_id)


async def get_attempts_with_outcomes(limit: int = 20) -> list:
    """Return recent attempts that have outcomes computed."""
    pool = await get_pool()
    if not pool:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM setup_attempts
            WHERE hypothetical_mae_60min_pts IS NOT NULL
            ORDER BY ts DESC
            LIMIT $1
        """, limit)
        return [_row_to_dict(r) for r in rows]


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


async def mark_attempt_executed(direction: str, day_type: str, trade_id: str):
    """Mark most recent matching attempt as executed (within last 5 min)."""
    pool = await get_pool()
    if not pool:
        return
    import time as _time
    cutoff = int(_time.time()) - 300
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE setup_attempts
            SET executed = TRUE, executed_trade_id = $1
            WHERE id = (
                SELECT id FROM setup_attempts
                WHERE direction = $2
                  AND ts >= $3
                  AND (executed IS NULL OR executed = FALSE)
                  AND setup_quality_score IS NOT NULL
                ORDER BY ts DESC LIMIT 1
            )
        """, trade_id, direction, cutoff)


async def get_journal_unified(types: list = None, limit: int = 100, offset: int = 0):
    """UNION trades + setup_attempts in unified format."""
    pool = await get_pool()
    if not pool:
        return []

    types = types or ['live', 'shadow']
    wants_shadow = 'shadow' in types
    wants_live = 'live' in types
    results = []

    async with pool.acquire() as conn:
        if wants_live or wants_shadow:
            trade_rows = await conn.fetch("""
                SELECT
                    id, entry_ts as ts, direction,
                    entry_price as entry, stop, t1, t2, t3,
                    setup_quality_score as score,
                    pnl_pts, pnl_usd, status, close_reason,
                    COALESCE(is_shadow, FALSE) as is_shadow,
                    day_type, killzone,
                    CASE
                        WHEN entry_price IS NOT NULL AND stop IS NOT NULL
                        THEN ABS(entry_price - stop)
                        ELSE NULL
                    END as risk_pts,
                    'trade' as source
                FROM trades
                WHERE
                    ($1 = TRUE AND COALESCE(is_shadow, FALSE) = TRUE)
                    OR ($2 = TRUE AND COALESCE(is_shadow, FALSE) = FALSE)
                ORDER BY entry_ts DESC
                LIMIT $3
            """, wants_shadow, wants_live, limit)
            results.extend([dict(r) for r in trade_rows])

        if wants_shadow:
            import time as _time
            attempt_rows = await conn.fetch("""
                SELECT
                    id::text as id, ts, direction,
                    entry_price_hypothetical as entry,
                    stop_hypothetical as stop,
                    c1_target as t1, c2_target as t2, c3_target as t3,
                    setup_quality_score as score,
                    hypothetical_mfe_60min_pts as pnl_pts,
                    NULL::float as pnl_usd,
                    CASE
                        WHEN executed = TRUE THEN 'EXECUTED'
                        ELSE 'PENDING'
                    END as status,
                    NULL as close_reason,
                    TRUE as is_shadow,
                    day_type, killzone,
                    CASE
                        WHEN entry_price_hypothetical IS NOT NULL AND stop_hypothetical IS NOT NULL
                        THEN ABS(entry_price_hypothetical - stop_hypothetical)
                        ELSE NULL
                    END as risk_pts,
                    vegas_score, tpo_score, fvg_score, footprint_score,
                    score_reasons,
                    'attempt' as source
                FROM setup_attempts
                WHERE setup_quality_score IS NOT NULL
                  AND ts > $1
                ORDER BY ts DESC
                LIMIT $2
            """, int(_time.time()) - 86400 * 7, limit)
            results.extend([dict(r) for r in attempt_rows])

            # Setups (lifecycle-tracked with simulation results)
            setup_rows = await conn.fetch("""
                SELECT
                    setup_id as id, first_detected_ts as ts, direction,
                    initial_entry as entry, initial_stop as stop,
                    c1_target as t1, c2_target as t2, c3_target as t3,
                    initial_score as score,
                    pnl_pts, pnl_usd,
                    CASE WHEN closed_ts IS NOT NULL THEN 'CLOSED' ELSE status END as status,
                    close_reason,
                    TRUE as is_shadow, day_type, killzone,
                    CASE
                        WHEN initial_entry IS NOT NULL AND initial_stop IS NOT NULL
                        THEN ABS(initial_entry - initial_stop)
                        ELSE NULL
                    END as risk_pts,
                    setup_type, score_reasons, peak_score, observation_count,
                    contracts_used,
                    'setup' as source
                FROM setups
                WHERE initial_entry IS NOT NULL AND initial_entry > 0
                  AND first_detected_ts > $1
                ORDER BY first_detected_ts DESC
                LIMIT $2
            """, int(_time.time()) - 86400 * 7, limit)
            results.extend([dict(r) for r in setup_rows])

    results.sort(key=lambda x: x.get('ts', 0) or 0, reverse=True)
    return results[:limit]


async def get_open_setups_for_simulation() -> list:
    """Get setups that need shadow simulation (not yet closed)."""
    pool = await get_pool()
    if not pool:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT setup_id, first_detected_ts, direction, initial_entry, initial_stop,
                   initial_score, c1_target, c2_target, c3_target,
                   t1_hit, t2_hit, t3_hit, stop_hit
            FROM setups
            WHERE closed_ts IS NULL
              AND initial_entry IS NOT NULL AND initial_entry > 0
              AND initial_stop IS NOT NULL AND initial_stop > 0
              AND status IN ('LIVE', 'BUILDING')
            ORDER BY first_detected_ts DESC
            LIMIT 100
        """)
        return [dict(r) for r in rows]


async def update_setup_simulation(setup_id: str, updates: dict):
    """Update setup with simulation results."""
    pool = await get_pool()
    if not pool:
        return
    sets = []
    vals = []
    idx = 1
    for k, v in updates.items():
        sets.append(f"{k} = ${idx}")
        vals.append(v)
        idx += 1
    sets.append(f"updated_at = NOW()")
    vals.append(setup_id)
    sql = f"UPDATE setups SET {', '.join(sets)} WHERE setup_id = ${idx}"
    async with pool.acquire() as conn:
        await conn.execute(sql, *vals)


async def get_today_shadow_summary() -> dict:
    """Summary of today's shadow trades."""
    pool = await get_pool()
    if not pool:
        return {}
    import time as _t
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now_et = datetime.now(ZoneInfo("America/New_York"))
    today_str = now_et.strftime("%Y-%m-%d")
    # Start of today ET in unix
    start_of_day = datetime(now_et.year, now_et.month, now_et.day, tzinfo=ZoneInfo("America/New_York"))
    sod_ts = int(start_of_day.timestamp())

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT setup_id, direction, close_reason, pnl_pts, pnl_usd,
                   contracts_used, killzone, day_type,
                   t1_hit, t2_hit, t3_hit, stop_hit, closed_ts
            FROM setups
            WHERE first_detected_ts >= $1
              AND initial_entry IS NOT NULL
            ORDER BY first_detected_ts DESC
        """, sod_ts)

    setups = [dict(r) for r in rows]
    closed = [s for s in setups if s.get("closed_ts")]
    wins = [s for s in closed if (s.get("pnl_pts") or 0) > 0]
    losses = [s for s in closed if (s.get("pnl_pts") or 0) < 0]
    total_pnl = sum(s.get("pnl_usd") or 0 for s in closed)

    best = max(closed, key=lambda s: s.get("pnl_usd") or 0) if closed else None
    worst = min(closed, key=lambda s: s.get("pnl_usd") or 0) if closed else None

    return {
        "date": today_str,
        "total_setups": len(setups),
        "closed": len(closed),
        "still_open": len(setups) - len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": len(closed) - len(wins) - len(losses),
        "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0,
        "total_pnl_usd": round(total_pnl, 2),
        "avg_pnl_per_trade": round(total_pnl / len(closed), 2) if closed else 0,
        "best_trade": {"setup_id": best["setup_id"], "direction": best["direction"],
                       "pnl_usd": best.get("pnl_usd"), "close_reason": best.get("close_reason")} if best else None,
        "worst_trade": {"setup_id": worst["setup_id"], "direction": worst["direction"],
                        "pnl_usd": worst.get("pnl_usd"), "close_reason": worst.get("close_reason")} if worst else None,
    }


async def get_closed_setups(date: str = None, limit: int = 100) -> list:
    """Get closed setups, optionally filtered by date."""
    pool = await get_pool()
    if not pool:
        return []
    async with pool.acquire() as conn:
        if date:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            dt = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=ZoneInfo("America/New_York"))
            sod = int(dt.timestamp())
            eod = sod + 86400
            rows = await conn.fetch("""
                SELECT * FROM setups
                WHERE closed_ts IS NOT NULL AND first_detected_ts >= $1 AND first_detected_ts < $2
                ORDER BY first_detected_ts DESC LIMIT $3
            """, sod, eod, limit)
        else:
            rows = await conn.fetch("""
                SELECT * FROM setups WHERE closed_ts IS NOT NULL
                ORDER BY first_detected_ts DESC LIMIT $1
            """, limit)
        return [dict(r) for r in rows]


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
