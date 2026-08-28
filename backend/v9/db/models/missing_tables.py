"""ORM models for tables previously managed via raw DDL/migrations.

Postgres migration (2026-06-03): these 20 tables had no ORM model, so
Base.metadata.create_all() skipped them.  Adding models here ensures
init_db() creates all 41+ tables on any backend (SQLite or Postgres).
"""

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Text, Date,
    UniqueConstraint, ForeignKey, SmallInteger,
)
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import BigIntPK, JsonColumn


class V9BarsCumulativeDelta(Base):
    __tablename__ = "v9_bars_cumulative_delta"
    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(String, nullable=False, index=True)
    # R0 (2026-08-28, T-112): bar_id retired as the dedup key — it encoded
    # the chart ROW INDEX, which shifts on every Sierra reload; keyed
    # upserts on it dragged historical rows onto today's ts (08-14 + 08-21
    # lost their entire CVD). Kept nullable for legacy rows; new rows write
    # NULL. The dedup key is (ts, symbol, source_version) below — matches
    # PG constraint uq_v9_cvd_ts_symbol_source (migration 2026-08-27).
    bar_id = Column(String, unique=True)
    delta = Column(Float)
    cumulative = Column(Float)
    direction = Column(String)
    session = Column(String)
    symbol = Column(String, nullable=False, server_default="MES")
    source_version = Column(String, nullable=False, server_default="live")
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (
        UniqueConstraint("ts", "symbol", "source_version",
                         name="uq_v9_cvd_ts_symbol_source"),
    )


class V9BarsImbalance(Base):
    __tablename__ = "v9_bars_imbalance"
    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(String, nullable=False, index=True)
    bar_id = Column(String, unique=True)
    price = Column(Float)
    ratio = Column(Float)
    direction = Column(String)
    bid_vol = Column(Integer)
    ask_vol = Column(Integer)
    session = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class V9BarsStackedImbalance(Base):
    __tablename__ = "v9_bars_stacked_imbalance"
    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(String, nullable=False, index=True)
    bar_id = Column(String, unique=True)
    count = Column(Integer)
    direction = Column(String)
    start_price = Column(Float)
    end_price = Column(Float)
    session = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class V9BarsVolumeProfile(Base):
    __tablename__ = "v9_bars_volume_profile"
    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(String, nullable=False, index=True)
    bar_id = Column(String, unique=True)
    profile = Column(Text)
    poc = Column(Float)
    vah = Column(Float)
    val = Column(Float)
    total_volume = Column(Integer)
    session = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class V9BarsWoodies(Base):
    __tablename__ = "v9_bars_woodies"
    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(String, nullable=False, index=True)
    bar_id = Column(String, unique=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    cci_14 = Column(Float)
    payload = Column(Text)
    session = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class V9BuildStatusArchive(Base):
    __tablename__ = "v9_build_status_archive"
    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    trading_date = Column(String, nullable=False)
    snapshot_ts = Column(String, nullable=False)
    payload_json = Column(Text, nullable=False)
    archived_at = Column(DateTime, server_default=func.now())


class V9ChopScore(Base):
    __tablename__ = "v9_chop_score"
    ts = Column(String, primary_key=True)
    vegas_flips_60m = Column(Integer)
    cci_zl_crossings_30m = Column(Integer)
    poc_migration_stuck = Column(Integer)
    ib_breakouts_recent = Column(Integer)
    range_atr_ratio = Column(Float)
    poc_vwap_distance = Column(Float)
    composite_score = Column(Float)


class V9DayTypeArchive(Base):
    __tablename__ = "v9_day_type_archive"
    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    day_type = Column(String(32), nullable=False)
    status = Column(String(16))
    confidence = Column(Float)
    ib_high = Column(Float)
    ib_low = Column(Float)
    ib_width_ticks = Column(Integer)
    opening_type = Column(String(32))
    locked_at = Column(DateTime)
    reasoning_notes = Column(String(1024))
    created_at = Column(DateTime)
    probability = Column(Float)
    directional_certainty = Column(String(8))
    trading_confidence = Column(String(8))
    ib_width = Column(Float)
    ib_width_class = Column(String(8))
    active_zohar_rules = Column(Text)
    last_updated_at = Column(DateTime)
    updated_at = Column(DateTime)
    archived_at = Column(DateTime, server_default=func.now())


class V9DayTypeShadowTransitions(Base):
    __tablename__ = "v9_day_type_shadow_transitions"
    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(String, nullable=False)
    session_date = Column(String, nullable=False)
    session_min = Column(Integer)
    from_type = Column(String, nullable=False)
    to_type = Column(String, nullable=False)
    trigger = Column(String, nullable=False)
    e_up = Column(Float)
    e_dn = Column(Float)
    r_total = Column(Float)
    ib_w = Column(Float)
    ib_h = Column(Float)
    ib_l = Column(Float)
    vah = Column(Float)
    val = Column(Float)
    poc = Column(Float)
    cvd = Column(Float)
    price = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class V9FootprintJournal(Base):
    __tablename__ = "v9_footprint_journal"
    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(String, nullable=False, index=True)
    bar_id = Column(String, unique=True)
    cluster_data = Column(Text)
    empty_zone_data = Column(Text)
    accumulation = Column(Integer, default=0)
    jumps_count = Column(Integer, default=0)
    jumps_direction = Column(String)
    otf_state = Column(Integer)
    pattern_detected = Column(String)
    zohar_signals = Column(Text)
    industry_signals = Column(Text)
    confluence_total = Column(Integer, default=0)
    classification = Column(String, nullable=False)
    would_be_entry = Column(Float)
    would_be_stop = Column(Float)
    session = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    agg_buy_vol = Column(Float, default=0)
    agg_sell_vol = Column(Float, default=0)
    delta = Column(Float, default=0)
    cumulative_delta = Column(Float, default=0)
    dominance = Column(Float, default=0)
    cot = Column(Float, default=0)
    amt = Column(Float, default=0)
    forces_source = Column(Float, default=0)
    pas_buy_vol = Column(Float)
    pas_sell_vol = Column(Float)
    initiative_type = Column(String)
    combined_class = Column(String)
    reactive_flag = Column(Integer, default=0)


class V9FootprintSetups(Base):
    __tablename__ = "v9_footprint_setups"
    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    journal_id = Column(Integer)
    ts = Column(String, nullable=False)
    classification = Column(String, nullable=False)
    pattern_type = Column(String)
    direction = Column(String)
    confluence = Column(Integer)
    entry_price = Column(Float)
    stop_price = Column(Float)
    session = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class V9ReversalEnrichment(Base):
    __tablename__ = "v9_reversal_enrichment"
    bar_ts = Column(String, primary_key=True)
    bar_type = Column(String)
    cluster_top = Column(Float)
    cluster_bottom = Column(Float)
    cluster_volume = Column(Float)
    empty_zone_top = Column(Float)
    empty_zone_bottom = Column(Float)
    empty_zone_volume = Column(Float)
    poc_price = Column(Float)


class V9SessionMeta(Base):
    __tablename__ = "v9_session_meta"
    key = Column(String, primary_key=True)
    value = Column(String)
    updated_at = Column(String)


class V9TpoJournal(Base):
    __tablename__ = "v9_tpo_journal"
    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False)
    ts = Column(DateTime, nullable=False, index=True)
    letter = Column(String, nullable=False)
    price_low = Column(Float, nullable=False)
    price_high = Column(Float, nullable=False)
    is_single_print = Column(Integer, default=0)


class V9TpoSessions(Base):
    __tablename__ = "v9_tpo_sessions"
    __table_args__ = (UniqueConstraint("session_id", name="uq_tpo_session_id"),)
    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False)
    session_type = Column(String, nullable=False)
    trading_date = Column(String, nullable=False)
    opened_ts = Column(DateTime, nullable=False)
    closed_ts = Column(DateTime)
    poc_price = Column(Float)
    vah_price = Column(Float)
    val_price = Column(Float)
    range_high = Column(Float)
    range_low = Column(Float)
    total_volume = Column(Integer)
    profile_shape = Column(String)
    opening_type = Column(String)
    ib_high = Column(Float)
    ib_low = Column(Float)
    ib_locked = Column(Integer, default=0)
    letter_count = Column(Integer, default=0)
    ib_width = Column(Float)
    ib_class = Column(String)
    ib_locked_ts = Column(String)
    poc_migration = Column(String)
    hvn_zones = Column(String)
    lvn_zones = Column(String)
    volume_cluster = Column(String)
    previous_poc = Column(String)
    poc_stuck_since = Column(String)


class V9TpoSessionsArchive(Base):
    __tablename__ = "v9_tpo_sessions_archive"
    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False)
    session_type = Column(String, nullable=False)
    trading_date = Column(String, nullable=False)
    opened_ts = Column(DateTime, nullable=False)
    closed_ts = Column(DateTime)
    poc_price = Column(Float)
    vah_price = Column(Float)
    val_price = Column(Float)
    range_high = Column(Float)
    range_low = Column(Float)
    total_volume = Column(Integer)
    profile_shape = Column(String)
    opening_type = Column(String)
    ib_high = Column(Float)
    ib_low = Column(Float)
    ib_locked = Column(Integer, default=0)
    letter_count = Column(Integer, default=0)
    archived_at = Column(DateTime, server_default=func.now())


class V9WoodiesSignals(Base):
    __tablename__ = "v9_woodies_signals"
    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(String, nullable=False, index=True)
    bar_id = Column(String, unique=True)
    cci_14 = Column(Float)
    cci_prev = Column(Float)
    signal_type = Column(String)
    direction = Column(String)
    strength = Column(Integer)
    reasoning = Column(Text)
    session = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    czi_state = Column(String)
    swi_state = Column(String)
    persistence_bars = Column(Integer, default=0)
    signal_type_core = Column(String)
    signal_confidence = Column(Float, default=0)
    is_synthetic = Column(SmallInteger, nullable=False, default=0)


class V9WoodiesSignalsArchive(Base):
    __tablename__ = "v9_woodies_signals_archive"
    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(String, nullable=False)
    bar_id = Column(String)
    cci_14 = Column(Float)
    cci_prev = Column(Float)
    signal_type = Column(String)
    direction = Column(String)
    strength = Column(Integer)
    reasoning = Column(Text)
    session = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    archived_at = Column(DateTime, server_default=func.now())
