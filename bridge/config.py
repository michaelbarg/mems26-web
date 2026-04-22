"""
MEMS26 Bridge — Central Configuration (Section 20)

All tunable parameters in one place.
MODE selects SIM vs LIVE thresholds automatically.
"""

import os

# ── Version ──────────────────────────────────────────────────────────────────
BRIDGE_VERSION = "V6.7.0"
BUILD_DATE = "2026-04-22"

# ── Mode ─────────────────────────────────────────────────────────────────────
# "SIM" = paper trading (Teton Paper), "LIVE" = real money
MODE = os.getenv("MEMS26_MODE", "SIM").upper()

# ── Entry Mode Selection (V6.5.2) ───────────────────────────────────────────
ENTRY_MODE = os.getenv("MEMS26_ENTRY_MODE", "STRICT").upper()
# STRICT = V6.1 baseline (default, backward-compatible)
# DEMO   = Data collection mode (requires MODE=SIM)
# LIVE automatically forces STRICT regardless of ENTRY_MODE

if ENTRY_MODE in ("DEMO", "RESEARCH") and MODE == "LIVE":
    import logging
    logging.warning(f"SECURITY: {ENTRY_MODE} mode blocked in LIVE -- forcing STRICT")
    ENTRY_MODE = "STRICT"

# ── Entry Gates (apply based on ENTRY_MODE) ─────────────────────────────────
if ENTRY_MODE == "DEMO":
    CB_MAX_TRADES = 999           # tag only in DEMO
    KILLZONE_REQUIRED = False     # tag only
    HEALTH_SCORE_MIN = 0          # tag only
    CONFIDENCE_MIN = 0            # tag only
    RELVOL_MIN = 1.0              # was 1.2
    FVG_MAX_PTS = 5.0             # was 4.0
    SWEEP_MIN_WICK_PTS = 1.0      # was 1.5
    PILLAR3_HARD_GATE = True      # P3 still required in DEMO
    NEWS_GUARD_HARD = True        # news freeze still enforced in DEMO
elif ENTRY_MODE == "RESEARCH":
    CB_MAX_TRADES = 999999        # unlimited
    KILLZONE_REQUIRED = False     # tag only
    HEALTH_SCORE_MIN = 0
    CONFIDENCE_MIN = 0
    RELVOL_MIN = 1.0
    FVG_MAX_PTS = 8.0             # wide FVG allowed for volatile days
    SWEEP_MIN_WICK_PTS = 0.25     # tick sweeps allowed
    PILLAR3_HARD_GATE = False     # P3 becomes informational tag
    NEWS_GUARD_HARD = False       # news freeze bypassed (tagged only)
else:  # STRICT (default)
    CB_MAX_TRADES = 3
    KILLZONE_REQUIRED = True
    HEALTH_SCORE_MIN = 70
    CONFIDENCE_MIN = 60
    RELVOL_MIN = 1.2
    FVG_MAX_PTS = 4.0
    SWEEP_MIN_WICK_PTS = 1.5
    PILLAR3_HARD_GATE = True
    NEWS_GUARD_HARD = True

# ── Pre-Close Freeze (V6.5.2 — always active) ───────────────────────────────
PRE_CLOSE_FREEZE_TIME_ET = "15:30"
PRE_CLOSE_FREEZE_ENABLED = True

# Hard limits NEVER loosened (even in DEMO):
# - 3 Pillars (P1+P2+P3)
# - Stop 3-8pt
# - News Freeze
# - Pre-Close Freeze 15:30 ET
# - EOD Flatten 15:59 ET

# ── Circuit Breaker ──────────────────────────────────────────────────────────
CB_SOFT_LIMIT  = 150 if MODE == "SIM" else 100   # $/day -> 30-min lock
CB_HARD_LIMIT  = 200                               # $/day -> lock until next day
# CB_MAX_TRADES set above by ENTRY_MODE
CB_CONSEC_LOSSES = 2                                # consecutive losses -> 30-min lock
CB_LOCK_MIN    = 30                                 # lock duration in minutes

# ── Contracts ────────────────────────────────────────────────────────────────
CONTRACTS      = 3 if MODE == "SIM" else 1          # MES contracts per trade

# ── Stop Validation ──────────────────────────────────────────────────────────
STOP_MIN_PT    = 3.0    # minimum stop distance (points)
STOP_MAX_PT    = 8.0    # maximum stop distance (points) — above = NO_TRADE

# ── Target Calculation ───────────────────────────────────────────────────────
T1_RR          = 1.5    # T1 = stop × 1.5  (min 10pt)
T1_MIN_PT      = 10.0   # T1 minimum distance
T2_RR          = 3.0    # T2 = stop × 3
T3_RR          = 0.0    # T3 = Draw on Liquidity (computed at runtime, 0 = disabled)

# ── EOD Flatten ──────────────────────────────────────────────────────────────
EOD_FLATTEN_TIME = "15:59"   # ET — auto-flatten if position open (CME maintenance ~16:15 ET)
EOD_FLATTEN_ENABLED = True

# ── Day Type Thresholds (ready for E3 calibration) ───────────────────────────
DAY_TYPE_THRESHOLDS = {
    "NARROW_IB":    6.0,     # IB range < 6pt → potential TREND day
    "NORMAL_IB":   14.0,     # 6-14pt → NORMAL day
    "WIDE_IB":     14.0,     # > 14pt → VOLATILE / rotational
    "TREND_EXT":    1.5,     # extension > 1.5× IB → confirmed TREND
}
TREND_VWAP_PERCENT       = 70    # % of session price stayed on one side of VWAP → TREND
TREND_IB_EXT             = 1.5   # extension > 1.5× IB → confirmed TREND
ROTATIONAL_VWAP_CROSSES  = 3     # 3+ VWAP crosses → ROTATIONAL day

# ── Killzone Windows (ET) ────────────────────────────────────────────────────
KILLZONES = {
    "LONDON":   ("03:00", "05:00"),    # London Open (V6.1 spec)
    "NY_OPEN":  ("09:30", "10:30"),    # NY Open — IB formation (V6.1 spec)
    "NY_CLOSE": ("15:00", "16:00"),    # NY Close — power hour (V6.1 spec)
}

# ── News Guard ───────────────────────────────────────────────────────────────
NEWS_API_TIMEOUT_SEC  = 5       # max seconds for ForexFactory fetch
NEWS_PRE_FREEZE_MIN   = 10     # minutes before event → block entries
NEWS_POST_RELEASE_MIN = 3      # minutes after event → release block
NEWS_FETCH_HOUR_ET    = 7      # hour (ET) to fetch daily calendar (once/day)

# ── Stacked Imbalance ───────────────────────────────────────────────────────
STACKED_MIN_DOMINANT_VOL = 30  # MES is thin — 5v2 hits 250% on noise alone

# ── Heartbeat Watchdog ───────────────────────────────────────────────────────
WATCHDOG_INTERVAL_SEC = 30     # check every 30 seconds
WATCHDOG_REDIS_STALE  = 60     # Redis data older than 60s = stale
WATCHDOG_SC_STALE     = 120    # SC JSON file older than 120s = stale
WATCHDOG_API_TIMEOUT  = 5      # FastAPI health check timeout (seconds)

# ── Bridge Intervals ────────────────────────────────────────────────────────
POST_INTERVAL     = 0.5        # seconds between Redis updates
CANDLE_INTERVAL   = 180        # 3-minute candles
STALE_THRESHOLD   = 120        # data freshness check (seconds)
MAX_CANDLES       = 960        # 960 × 3min = 48 hours
PATTERN_SCAN_INTERVAL = 60     # pattern scan every 60 seconds

# ── MTF Candle Config ────────────────────────────────────────────────────────
MTF_CONFIG = [
    # (mtf_key, redis_key, interval_sec, max_candles)
    ("m5",  "mems26:candles:5m",  300,  288),
    ("m15", "mems26:candles:15m", 900,  96),
    ("m30", "mems26:candles:30m", 1800, 48),
    ("m60", "mems26:candles:1h",  3600, 64),
]

# ── Paths ────────────────────────────────────────────────────────────────────
SC_JSON_PATH    = os.getenv("SC_JSON_PATH", "/Users/michael/SierraChart2/Data/mes_ai_data.json")
SC_HISTORY_PATH = os.getenv("SC_HISTORY_PATH", "/Users/michael/SierraChart2/Data/mes_ai_history.json")
SC_COMMAND_PATH = os.getenv("SC_COMMAND_PATH",
    str(__import__("pathlib").Path(SC_JSON_PATH).parent / "trade_command.json"))
SC_RESULT_PATH  = os.getenv("SC_RESULT_PATH",
    str(__import__("pathlib").Path(SC_JSON_PATH).parent / "trade_result.json"))

# ── Cloud / Redis ────────────────────────────────────────────────────────────
CLOUD_URL    = os.getenv("CLOUD_URL", "https://mems26-web.onrender.com")
BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "michael-mems26-2026")
REDIS_URL    = os.getenv("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN  = os.getenv("UPSTASH_REDIS_REST_TOKEN")

# ── Redis Keys ───────────────────────────────────────────────────────────────
REDIS_KEY         = "mems26:latest"
REDIS_CANDLES     = "mems26:candles"
REDIS_PATTERNS    = "mems26:patterns"
REDIS_SEEN_FILLS  = "mems26:seen_fills"
REDIS_NEWS_STATE  = "mems26:news:state"
REDIS_NEWS_EVENTS = "mems26:news:events"
