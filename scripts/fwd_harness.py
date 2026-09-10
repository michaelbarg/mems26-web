#!/usr/bin/env python3
"""fwd_harness.py — FORWARD production-path test (cowork-dev 2026-09-10).

Feeds one session's real 5-min bars (v9_bars_5min_woodies), one at a time and in
order, through the REAL live objects:

    S1  DayTypeStateMachine.process_bar + classifier_core.classify_session
        (+ DAYTYPE_RECLASS_STABILITY_V1 gating exactly as backend/main.py:590-642)
    S2  FiveMinSystem.process_bar   (opening engine + every S2 producer)
    S4  WoodiesSystem.process_bar   (ZLR/VEGAS/GB100/HTLB/TT/FAMIR/...)
    GW  TradingGateway.route_setup  (the full gate chain, DALTON_PLAYBOOK_V1=1)
    CMD sierra_command.command_from_setup  (T-214 belt, sizing) — write patched out

Faithful clock: every clock the code reads (market_clock REPLAY mode,
datetime.now, date.today, time.time, SQL now()/current_date) is pinned to the
bar being processed. The machine never sees bar N+1 while evaluating bar N.

Push cadence (--push-mode firstpush, the live truth): the bridge routes the
DEVELOPING bar; S2/S4/S1 dedup on ts, so detection runs on the FIRST push of a
new bar (o=h=l=c=open, ~1% volume) and the final OHLC arrives as a duplicate
push. --push-mode closed feeds each bar once, already closed.

Safety: DB opened with default_transaction_read_only=on (any write raises);
PYTEST_CURRENT_TEST set (decision/ledger files untouched); write_trade_command,
ntfy, ops_log, feed_watchdog, margin cap patched. Nothing reaches Sierra.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time as _time_mod
import datetime as _dt_mod
from datetime import datetime, timedelta, timezone, date, time as dtime
from zoneinfo import ZoneInfo
from types import SimpleNamespace

ET = ZoneInfo("America/New_York")
IL = ZoneInfo("Asia/Jerusalem")
UTC = timezone.utc

# ──────────────────────────────────────────────────────────────────────────
# 0. args + env (BEFORE any backend import)
# ──────────────────────────────────────────────────────────────────────────
ap = argparse.ArgumentParser()
ap.add_argument("--session", required=True)
ap.add_argument("--variant", default="head")
ap.add_argument("--stability", default=None, help="override DAYTYPE_RECLASS_STABILITY_V1")
ap.add_argument("--env", default="/Users/michael/Downloads/mems26_web_git/.env")
ap.add_argument("--out", required=True)
ap.add_argument("--push-mode", default="firstpush", choices=["firstpush", "closed"])
ap.add_argument("--oe-closed", action="store_true",
                help="counterfactual: let the opening engine evaluate CLOSED RTH bars instead of the "
                     "first-seconds developing bar it sees live (five_min_system.py:2139/2149/2190)")
ap.add_argument("--quiet", action="store_true")
args = ap.parse_args()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from backend.env_loader import load_dotenv_file  # noqa: E402
load_dotenv_file(args.env, override=False)

# Harness overrides (documented in the report)
os.environ["MEMS26_CLOCK_MODE"] = "REPLAY"
os.environ["DALTON_PLAYBOOK_V1"] = "1"
if args.stability is not None:
    os.environ["DAYTYPE_RECLASS_STABILITY_V1"] = str(args.stability)
os.environ["PYTEST_CURRENT_TEST"] = "fwd_harness"       # no decision/ledger file writes
os.environ["GATEWAY_DECISIONS_HYDRATE"] = "0"
os.environ["GATEWAY_DECISIONS_PATH"] = "/tmp/fwd_out/_never_written.jsonl"
os.environ["BLOCKED_TWIN_V1"] = "0"                     # post-decision shadow twin (DB write) off
os.environ["REHYDRATE_CLS_BARS"] = "0"
os.environ["MEMS26_LOG_LEVEL"] = "WARNING"
os.environ["V9_DISABLE_WATCHDOG"] = "1"
# DB belt: every transaction read-only → any write raises instead of landing.
_dburl = os.environ.get("DATABASE_URL", "postgresql://localhost/mems26")
if "default_transaction_read_only" not in _dburl:
    sep = "&" if "?" in _dburl else "?"
    os.environ["DATABASE_URL"] = _dburl + sep + "options=-c%20default_transaction_read_only%3Don"

import logging  # noqa: E402
logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(name)s %(message)s")
LOG = logging.getLogger("fwd")
LOG.setLevel(logging.INFO)

# ──────────────────────────────────────────────────────────────────────────
# 1. clock virtualisation (freezegun-style, stdlib only)
# ──────────────────────────────────────────────────────────────────────────
_NOW = {"utc": None}
_real_datetime = _dt_mod.datetime
_real_date = _dt_mod.date
_real_time = _time_mod.time


class _DTMeta(type):
    def __instancecheck__(cls, o):
        return isinstance(o, _real_datetime)

    def __subclasscheck__(cls, s):
        return issubclass(s, _real_datetime)


class FakeDatetime(_real_datetime, metaclass=_DTMeta):
    @classmethod
    def now(cls, tz=None):
        n = _NOW["utc"]
        if n is None:
            return _real_datetime.now(tz)
        if tz is None:
            return n.astimezone(IL).replace(tzinfo=None)   # machine local = IL
        return n.astimezone(tz)

    @classmethod
    def utcnow(cls):
        n = _NOW["utc"]
        if n is None:
            return _real_datetime.utcnow()
        return n.replace(tzinfo=None)

    @classmethod
    def today(cls):
        return cls.now()


class _DMeta(type):
    def __instancecheck__(cls, o):
        return isinstance(o, _real_date)

    def __subclasscheck__(cls, s):
        return issubclass(s, _real_date)


class FakeDate(_real_date, metaclass=_DMeta):
    @classmethod
    def today(cls):
        n = _NOW["utc"]
        if n is None:
            return _real_date.today()
        return n.astimezone(IL).date()


def _fake_time():
    n = _NOW["utc"]
    return _real_time() if n is None else n.timestamp()


def install_clock():
    """Rebind datetime/date/time.time in every loaded module (after backend imports)."""
    rd, rdate, rt = _real_datetime, _real_date, _real_time   # locals: the scan must not clobber the sentinels
    _dt_mod.datetime = FakeDatetime
    _dt_mod.date = FakeDate
    _time_mod.time = _fake_time
    n = 0
    for name, mod in list(sys.modules.items()):
        if mod is None:
            continue
        try:
            d = vars(mod)
        except TypeError:
            continue
        for attr, val in list(d.items()):
            if attr.startswith("_real_"):
                continue
            if val is rd:
                setattr(mod, attr, FakeDatetime); n += 1
            elif val is rdate:
                setattr(mod, attr, FakeDate); n += 1
            elif val is rt and attr == "time":
                setattr(mod, attr, _fake_time); n += 1
    return n


def set_now(utc_dt: datetime):
    _NOW["utc"] = utc_dt.astimezone(UTC)
    from backend.v9.services import market_clock
    market_clock.update_replay_timestamp(_NOW["utc"], source="fwd_harness")


# ──────────────────────────────────────────────────────────────────────────
# 2. DB read layer: SQL now()/current_date → the replay instant
# ──────────────────────────────────────────────────────────────────────────
import re  # noqa: E402
import backend.v9.db.read as _dbread  # noqa: E402

_orig_read_all, _orig_read_one, _orig_read_scalar = (
    _dbread.read_all, _dbread.read_one, _dbread.read_scalar)
_NOW_RE = re.compile(r"\bnow\(\)", re.IGNORECASE)
_CD_RE = re.compile(r"\bcurrent_date\b", re.IGNORECASE)
_CT_RE = re.compile(r"\bcurrent_timestamp\b", re.IGNORECASE)


# AS-OF guard: a live gate that reads "today's bars" without a ts bound must not see the
# future. Every read of these tables is wrapped in (SELECT * FROM T WHERE <col> <= now).
# Bars count as available once CLOSED (ts + 5 min <= now). Trades/labels of THIS session
# are hidden entirely — the harness's own chain did not take the live system's trades.
_ASOF = {
    "v9_bars_5min_woodies": "ts + interval '5 minutes' <= CAST(:__fwd_now AS timestamptz)",
    "v9_bars_5min": "ts + interval '5 minutes' <= CAST(:__fwd_now AS timestamptz)",
    "v9_bars_5min_continuous": "ts + interval '5 minutes' <= CAST(:__fwd_now AS timestamptz)",
    "v9_bars_cumulative_delta": "ts + interval '5 minutes' <= CAST(:__fwd_now AS timestamptz)",
    "v9_bars_footprint": "ts <= CAST(:__fwd_now AS timestamptz)",
    "v9_tpo_history": "created_at <= CAST(:__fwd_now AS timestamptz)",
    "v9_day_type_history": "created_at <= CAST(:__fwd_now AS timestamptz)",
    "v9_day_type_state": "(created_at AT TIME ZONE 'UTC') <= CAST(:__fwd_now AS timestamptz)",
    "v9_trades": "created_at < CAST(:__fwd_sess AS timestamptz)",
    "v9_five_min_setups": "created_at < CAST(:__fwd_sess AS timestamptz)",
    "v9_woodies_signals": "ts < CAST(:__fwd_sess AS timestamptz)",
    "v9_tpo_sessions": "trading_date < :__fwd_sess_date",   # varchar ISO date
}
_KW = {"WHERE", "ORDER", "GROUP", "ON", "LIMIT", "LEFT", "INNER", "JOIN", "RIGHT", "CROSS", "USING",
       "HAVING", "UNION", "AND", "OR", "SET", "RETURNING", "FULL", "NATURAL", "AS"}
_ASOF_RE = {t: re.compile(r"\b(FROM|JOIN)\s+" + t + r"\b(\s+(?:AS\s+)?([A-Za-z_]\w*))?", re.IGNORECASE)
            for t in _ASOF}
_SESSION_OPEN_UTC = None   # set after args parsed
REWRITE_STATS = {"now": 0, "asof": 0}


def _asof_sub(t, pred):
    def _f(m):
        kw, alias_grp, alias = m.group(1), m.group(2), m.group(3)
        if alias and alias.upper() in _KW:
            alias_grp = ""
            alias = None
        sub = f"{kw} (SELECT * FROM {t} WHERE {pred}) {alias or t}"
        # re-append the keyword we swallowed as a non-alias
        if m.group(3) and m.group(3).upper() in _KW:
            sub += " " + m.group(3)
        return sub
    return _f


def _rewrite(sql, params):
    n = _NOW["utc"]
    if n is None:
        return sql, params
    p = dict(params or {})
    changed = False
    if _NOW_RE.search(sql) or _CD_RE.search(sql) or _CT_RE.search(sql):
        sql = _NOW_RE.sub("CAST(:__fwd_now AS timestamptz)", sql)
        sql = _CT_RE.sub("CAST(:__fwd_now AS timestamptz)", sql)
        sql = _CD_RE.sub("(CAST(:__fwd_now AS timestamptz) AT TIME ZONE 'Asia/Jerusalem')::date", sql)
        changed = True; REWRITE_STATS["now"] += 1
    for t, rx in _ASOF_RE.items():
        if rx.search(sql):
            sql = rx.sub(_asof_sub(t, _ASOF[t]), sql)
            changed = True; REWRITE_STATS["asof"] += 1
    if changed:
        p["__fwd_now"] = n.isoformat()
        p["__fwd_sess"] = _SESSION_OPEN_UTC.isoformat() if _SESSION_OPEN_UTC else n.isoformat()
        p["__fwd_sess_date"] = args.session
    return sql, p


def read_all(sql, params=None):
    s, p = _rewrite(sql, params); return _orig_read_all(s, p)


def read_one(sql, params=None):
    s, p = _rewrite(sql, params); return _orig_read_one(s, p)


def read_scalar(sql, params=None):
    s, p = _rewrite(sql, params); return _orig_read_scalar(s, p)


_dbread.read_all, _dbread.read_one, _dbread.read_scalar = read_all, read_one, read_scalar

# ──────────────────────────────────────────────────────────────────────────
# 3. fake `backend.main` (what get_live_day_type()/_live_five_min_system() resolve)
# ──────────────────────────────────────────────────────────────────────────
import types  # noqa: E402
_fake_main = types.ModuleType("backend.main")
_fake_main.app = SimpleNamespace(state=SimpleNamespace())
sys.modules["backend.main"] = _fake_main
APP = _fake_main.app

# ──────────────────────────────────────────────────────────────────────────
# 4. real imports
# ──────────────────────────────────────────────────────────────────────────
from backend.v9.services import market_clock  # noqa: E402
from backend.v9.services.market_clock import now_et, minutes_since_rth_open  # noqa: E402
from backend.v9.services.bar_router import BarEvent  # noqa: E402
from backend.v9.systems.day_type.state_machine import DayTypeStateMachine, DayType as _DT  # noqa: E402
from backend.v9.systems.day_type.schemas import BarInput  # noqa: E402
from backend.v9.api.v9.day_type_seed import maybe_seed_ib_from_tpo  # noqa: E402
from backend.v9.systems.day_type.classifier_core import classify_session  # noqa: E402
from backend.v9.systems.day_type.prev_day import load_previous_day_context, missing_pd_context, load_tpo_previous_day_summary  # noqa: E402
from backend.v9.systems.five_min.five_min_system import FiveMinSystem, FiveMinMode  # noqa: E402
import backend.v9.systems.five_min.five_min_system as _fms_mod  # noqa: E402
from backend.v9.systems.woodies.woodies_system import WoodiesSystem  # noqa: E402
from backend.v9.gateway.trading_gateway import TradingGateway  # noqa: E402
import backend.v9.gateway.trading_gateway as _gw_mod  # noqa: E402
import backend.v9.services.sierra_command as _sc_mod  # noqa: E402
import backend.v9.api.v9.tpo_routes as _tpo_routes  # noqa: E402
import backend.v9.services.feed_watchdog as _fw_mod  # noqa: E402
import backend.v9.services.margin_sizing as _ms_mod  # noqa: E402
import backend.v9.services.trade_context as _tc_mod  # noqa: E402
import backend.v9.systems.delta_features as _df_mod  # noqa: E402
import backend.v9.systems.day_type.label_stability as _stab_mod  # noqa: E402
from backend.v9.systems.day_type.daytype_classifier import smooth_confidence  # noqa: E402
import backend.v9.systems.tpo.tpo_system  # noqa: E402  (bind datetime before clock install)
import backend.v9.gateway.session_gate  # noqa: E402
import backend.v9.common.trading_date  # noqa: E402
import backend.v9.systems.opening_entry  # noqa: E402
import backend.v9.services.dalton_playbook  # noqa: E402
import backend.v9.systems.day_type.opening_detector_v2  # noqa: E402

_n_patched = install_clock()
market_clock.set_clock_mode("REPLAY")
LOG.info("clock installed: %d module bindings rebound", _n_patched)

# ──────────────────────────────────────────────────────────────────────────
# 5. side-effect patches
# ──────────────────────────────────────────────────────────────────────────
_WOULD_WRITE = []


def _fake_write_trade_command(**kw):
    payload = {k: (v if not isinstance(v, float) else round(v, 2)) for k, v in kw.items()}
    _WOULD_WRITE.append(payload)
    return {"ok": True, "harness": "not_written", **payload}


_sc_mod.write_trade_command = _fake_write_trade_command
_fw_mod.is_feed_alive = lambda *a, **k: (True, "fwd_harness: feed check bypassed")
_ms_mod.cap_contracts = lambda n, *a, **k: (n, "fwd_harness: margin cap bypassed (live account state is not historical)")

try:
    import backend.v9.services.ntfy_notify as _ntfy
    for _fn in ("on_fire", "on_emergency", "on_exit", "notify", "send"):
        if hasattr(_ntfy, _fn):
            setattr(_ntfy, _fn, lambda *a, **k: None)
except Exception:
    pass
try:
    import scripts.ops_log as _ops
    _ops.log_event = lambda *a, **k: None
except Exception:
    pass
try:
    import backend.v9.services.phone_alert as _pa
    _pa.push = lambda *a, **k: None
except Exception:
    pass
try:
    import backend.v9.services.sierra_position_reconciler as _spr
    _spr.position_mismatch_blocks_entry = lambda *a, **k: False   # live account state ≠ history
except Exception:
    pass

# ──────────────────────────────────────────────────────────────────────────
# 6. data: bars, tpo-as-observed, delta-as-observed
# ──────────────────────────────────────────────────────────────────────────
SESSION = args.session
_sd = date.fromisoformat(SESSION)
_prev_td = market_clock.get_previous_trading_day(_sd)
_SESSION_OPEN_UTC = datetime.combine(_prev_td, dtime(18, 0), tzinfo=ET).astimezone(UTC)  # replay window start

BARS = _orig_read_all(
    "SELECT ts, open, high, low, close, volume, cci_14, cci_6_tcci, lsma_value, swi_value, "
    "czi_value, ema_34, trend_state, predictor_next_cci, zlr_detected, zlr_direction, "
    "hfe_detected, hfe_direction, hfe_extreme_bars_ago, lsma_above_price, proj_hi, proj_lo "
    "FROM v9_bars_5min_woodies WHERE symbol='MES' AND ts >= :a AND ts < :b ORDER BY ts",
    {"a": datetime.combine(_prev_td, dtime(18, 0), tzinfo=ET).isoformat(),
     "b": datetime.combine(_sd, dtime(16, 0), tzinfo=ET).isoformat()})
PRE = _orig_read_all(
    "SELECT ts, open, high, low, close, volume, cci_14, cci_6_tcci, lsma_value, swi_value, "
    "czi_value, ema_34, trend_state, predictor_next_cci FROM v9_bars_5min_woodies "
    "WHERE symbol='MES' AND ts < :a ORDER BY ts DESC LIMIT 60",
    {"a": datetime.combine(_prev_td, dtime(18, 0), tzinfo=ET).isoformat()})
PRE = list(reversed(PRE))
RTH = [b for b in BARS if dtime(9, 30) <= b["ts"].astimezone(ET).time() < dtime(16, 0)]
LOG.info("session %s: %d bars from %s 18:00 ET, %d RTH bars", SESSION, len(BARS), _prev_td, len(RTH))
if len(RTH) < 12:
    LOG.error("fewer than 12 RTH bars — cannot run"); sys.exit(2)

TPO_HIST = _orig_read_all(
    "SELECT created_at, poc, vah, val, ib_high, ib_low, profile_shape FROM v9_tpo_history "
    "WHERE (created_at AT TIME ZONE 'Asia/Jerusalem')::date = :d ORDER BY created_at", {"d": SESSION})
PREV_TPO = load_tpo_previous_day_summary(previous_trading_day=_prev_td)
DELTA_ROWS = _orig_read_all(
    "SELECT ts, delta, cumulative FROM v9_bars_cumulative_delta WHERE symbol='MES' "
    "AND ts >= :a AND ts < :b ORDER BY ts",
    {"a": datetime.combine(_sd, dtime(9, 30), tzinfo=ET).isoformat(),
     "b": datetime.combine(_sd, dtime(16, 0), tzinfo=ET).isoformat()})
PD_CTX = load_previous_day_context(previous_trading_day=_prev_td)
PD_CTX_NOTE = None
if PD_CTX.get("pd_close") is None or PD_CTX.get("pd_high") is None:
    # The legacy v9_bars_5min table (prev_day.py:47) has been purged for dates before
    # 2026-08-27; live had those rows at the time. Substitute the canonical bars for the
    # same prior session so the machine gets the context it had (data availability, not
    # a behaviour change). Recorded in the output.
    _hl = _orig_read_one(
        "SELECT max(high) AS h, min(low) AS l, "
        "(SELECT close FROM v9_bars_5min_woodies WHERE symbol='MES' AND (ts AT TIME ZONE 'America/New_York')::date = :pd "
        " AND (ts AT TIME ZONE 'America/New_York')::time < '16:00' ORDER BY ts DESC LIMIT 1) AS c "
        "FROM v9_bars_5min_woodies WHERE symbol='MES' AND (ts AT TIME ZONE 'America/New_York')::date = :pd "
        "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' AND (ts AT TIME ZONE 'America/New_York')::time < '16:00'",
        {"pd": _prev_td.isoformat()})
    if _hl and _hl.get("c") is not None:
        PD_CTX = {"pd_high": float(_hl["h"]), "pd_low": float(_hl["l"]), "pd_close": float(_hl["c"]),
                  "pd_context_status": "OK", "degraded_reason": None, "missing_pd_fields": []}
        PD_CTX_NOTE = "pd context substituted from v9_bars_5min_woodies (legacy v9_bars_5min purged for this date)"
        LOG.warning(PD_CTX_NOTE)
LOG.info("pd_ctx=%s prev_tpo found=%s vah=%s val=%s tpo_hist=%d delta=%d",
         {k: PD_CTX.get(k) for k in ("pd_high", "pd_low", "pd_close", "pd_context_status")},
         PREV_TPO.get("found"), PREV_TPO.get("vah"), PREV_TPO.get("val"), len(TPO_HIST), len(DELTA_ROWS))


def _rth_so_far():
    n = _NOW["utc"]
    return [b for b in RTH if b["ts"] + timedelta(minutes=5) <= n]   # CLOSED RTH bars only


def _rth_open_bars_seen():
    n = _NOW["utc"]
    return [b for b in RTH if b["ts"] <= n]


def fake_load_sierra_tpo(*a, **k):
    """tpo.json as it was observable at the replay instant (v9_tpo_history, created_at<=now)."""
    n = _NOW["utc"]
    row = None
    for r in TPO_HIST:
        if r["created_at"] <= n:
            row = r
        else:
            break
    seen = _rth_open_bars_seen()
    sm = minutes_since_rth_open(n.astimezone(ET))
    ib_bars = [b for b in seen if b["ts"].astimezone(ET).time() < dtime(10, 30)]
    ib_found = bool(ib_bars) and n.astimezone(ET).time() >= dtime(9, 30)
    ib_high = max(float(b["high"]) for b in ib_bars) if ib_bars else None
    ib_low = min(float(b["low"]) for b in ib_bars) if ib_bars else None
    ib_locked = ib_found and sm >= 60
    poc = vah = val = None
    if row is not None:
        poc, vah, val = row["poc"], row["vah"], row["val"]
    s_hi = max(float(b["high"]) for b in seen) if seen else None
    s_lo = min(float(b["low"]) for b in seen) if seen else None
    return {
        "running": True, "hydrated": True, "source": "fwd_harness:v9_tpo_history",
        "export_ts": int(n.timestamp()), "age_s": 3.0, "stale": False, "session_type": "SIERRA",
        "poc": poc, "vah": vah, "val": val, "session_va_ok": bool(poc and vah and val and vah > val),
        "session_high": s_hi, "session_low": s_lo, "total_volume": None,
        "ib_high": ib_high, "ib_mid": (round((ib_high + ib_low) / 2, 2) if ib_found else None),
        "ib_low": ib_low, "ib_locked": ib_locked, "ib_found": ib_found,
        "ib_width": (ib_high - ib_low) if ib_found else None,
        "ib_source": "fwd_harness:first12_rth_bars",
        "prior_day": {"found": PD_CTX.get("pd_high") is not None, "high": PD_CTX.get("pd_high"),
                      "low": PD_CTX.get("pd_low"), "close": PD_CTX.get("pd_close")},
        "previous_session": {"found": bool(PREV_TPO.get("found")), "poc": PREV_TPO.get("poc"),
                             "vah": PREV_TPO.get("vah"), "val": PREV_TPO.get("val"),
                             "ib_found": PREV_TPO.get("ib_high") is not None,
                             "ib_high": PREV_TPO.get("ib_high"), "ib_low": PREV_TPO.get("ib_low")},
        "profile_shape": "NA", "opening_type": "NA",
        "poc_migration": {"direction": "UNKNOWN", "magnitude_pts": None, "stuck_minutes": 0, "previous_poc": None},
        "extremes": None, "periods": [],
    }


_tpo_routes._load_sierra_tpo = fake_load_sierra_tpo
_fms_mod._load_sierra_tpo = fake_load_sierra_tpo


def _delta_points():
    n = _NOW["utc"]
    return [{"d": float(r["delta"] or 0), "cum": float(r["cumulative"] or 0)}
            for r in DELTA_ROWS if r["ts"] + timedelta(minutes=5) <= n]


_fms_mod.read_cumulative_delta = lambda: {"points": _delta_points()}
_orig_cvd_dir, _orig_dce = _df_mod.cvd_directionality, _df_mod.delta_confirms_extension
_df_mod.cvd_directionality = lambda pts, *a, **k: _orig_cvd_dir(_delta_points(), *a, **k)
_df_mod.delta_confirms_extension = lambda pts, *a, **k: _orig_dce(_delta_points(), *a, **k)


class FakeTPO:
    """Stand-in for TPOSystem.current_state (the real one persists to DB)."""

    def __init__(self):
        self.current_state = {"running": True, "hydrated": True, "bars_processed_today": 0,
                              "buffer_size": 0, "ib_locked": False}

    @property
    def ib_locked(self):
        return bool(self.current_state.get("ib_locked"))

    def refresh(self):
        t = fake_load_sierra_tpo()
        st = self.current_state
        st.update({"poc": t["poc"], "vah": t["vah"], "val": t["val"],
                   "session_high": t["session_high"], "session_low": t["session_low"],
                   "rth_high": t["session_high"], "rth_low": t["session_low"],
                   "ib_high": t["ib_high"], "ib_low": t["ib_low"], "ib_locked": t["ib_locked"],
                   "ib_width": t["ib_width"], "profile_shape": "NA", "opening_type": "NA"})
        st["bars_processed_today"] = len(_rth_open_bars_seen())
        st["buffer_size"] = st["bars_processed_today"]

    def get_current(self):
        return dict(self.current_state)


# ── --oe-closed counterfactual: the opening engine evaluates the CLOSED RTH bars that exist
#    at the moment (instead of _oe_bars = the first-seconds developing bars it collects live).
#    Only the three opening_entry entry points are re-pointed; window/one-per-session/fusion/
#    strict/skip logic in five_min_system runs unchanged.
OE_CLOSED_TRACE = []
if args.oe_closed:
    import backend.v9.systems.opening_entry as _oe_mod
    _o_eval, _o_build, _o_ft = (_oe_mod.evaluate_opening_entry, _oe_mod.build_opening_setup,
                                _oe_mod.opening_first_trade_ok)

    def _closed_rth_dicts():
        return [{"ts": b["ts"].isoformat(), "o": float(b["open"]), "h": float(b["high"]), "l": float(b["low"]),
                 "c": float(b["close"]), "v": int(b["volume"] or 0), "open": float(b["open"]),
                 "high": float(b["high"]), "low": float(b["low"]), "close": float(b["close"])}
                for b in _rth_so_far()]

    def _eval_closed(session_bars, already_fired=None, **kw):
        cb = _closed_rth_dicts()
        # keep the caller's window semantics: evaluate the closed bars available now
        r = _o_eval(cb, already_fired, **kw)
        OE_CLOSED_TRACE.append({"il": _NOW["utc"].astimezone(IL).strftime("%H:%M:%S"), "n_closed": len(cb),
                                "n_oe_bars": len(session_bars), "trigger": r})
        return r

    def _build_closed(trigger, session_bars, shadow_only, **kw):
        return _o_build(trigger, _closed_rth_dicts(), shadow_only, **kw)

    def _ft_closed(session_bars, direction, conf, **kw):
        return _o_ft(_closed_rth_dicts(), direction, conf, **kw)

    _oe_mod.evaluate_opening_entry = _eval_closed
    _oe_mod.build_opening_setup = _build_closed
    _oe_mod.opening_first_trade_ok = _ft_closed

# ──────────────────────────────────────────────────────────────────────────
# 7. build the real objects
# ──────────────────────────────────────────────────────────────────────────
_first_ts = BARS[0]["ts"]
set_now(_first_ts - timedelta(minutes=1))

dtm = DayTypeStateMachine(prev_day_summary={"vah": PREV_TPO.get("vah"), "val": PREV_TPO.get("val"),
                                            "session_date": SESSION})
APP.state.day_type_machine = dtm
tpo = FakeTPO()
APP.state.tpo_system = tpo

fms = FiveMinSystem()
fms.mode = FiveMinMode.OVERNIGHT_MODE
for r in PRE[-20:]:
    fms._bar_buffer.append({"ts": r["ts"].isoformat(), "o": float(r["open"]), "h": float(r["high"]),
                            "l": float(r["low"]), "c": float(r["close"]), "v": int(r["volume"] or 0)})
fms._hydrated = True
APP.state.five_min_system = fms

ws = WoodiesSystem()
for r in PRE[-40:]:
    from backend.v9.systems.woodies.woodies_system import WoodiesBar
    ws._highs.append(float(r["high"])); ws._lows.append(float(r["low"])); ws._closes.append(float(r["close"]))
    ws._bar_buffer.append(WoodiesBar(
        ts=r["ts"].timestamp(), open=float(r["open"]), high=float(r["high"]), low=float(r["low"]),
        close=float(r["close"]), volume=float(r["volume"] or 0), cci_14=float(r["cci_14"] or 0),
        cci_6_tcci=float(r["cci_6_tcci"] or 0), ema_34=float(r["ema_34"] or 0),
        lsma_value=float(r["lsma_value"] or 0), swi_value=float(r["swi_value"] or 0),
        czi_value=float(r["czi_value"] or 0), trend_state=r["trend_state"] or "GRAY",
        predictor_next_cci=float(r["predictor_next_cci"] or 0)))
ws.current_state["running"] = True; ws.current_state["hydrated"] = True
APP.state.woodies_system = ws

gw = TradingGateway()
gw.set_system_registry({"day_type_machine": dtm, "five_min_system": fms,
                        "tpo_system": tpo, "woodies_system": ws})
gw.enable_live(2); gw.enable_live(4)
gw.enable_demo(2); gw.enable_demo(4)
APP.state.trading_gateway = gw
fms.set_gateway(gw)
ws.set_gateway(gw) if hasattr(ws, "set_gateway") else setattr(ws, "_gateway", gw)

# ── execution capture: the real gate chain runs; execution is recorded, not done ──
RECORDS = []
_seq = {"n": 0}


def _capture_exec(mode):
    def _f(setup, system_id, cross_context):
        _seq["n"] += 1
        tid = f"FWD-{mode}-{_seq['n']}"
        cmd = None
        if mode == "live":
            s2 = dict(setup)
            try:
                t1, t2, t3 = gw._seed_runner_targets(setup)
                _d = (setup.get("direction") or "LONG").upper()
                _e = setup.get("entry_price") or 0.0
                _s = setup.get("stop") or (setup.get("metadata") or {}).get("stop_initial") or 0.0
                t1, t2, t3 = gw._clamp_targets_to_max_r(_d, _e, _s, t1, t2, t3)
                t1, t2, t3 = gw._target_degeneracy_guard(t1, t2, t3)
                s2["t2"], s2["t3"] = t2, t3
            except Exception as e:
                s2["_seed_err"] = str(e)
            try:
                cmd = _sc_mod.command_from_setup(s2, trade_id=tid, account="FWD", mode="live")
            except ValueError as ve:
                cmd = {"rejected": True, "reason": "ValueError", "detail": str(ve)}
            except Exception as e:
                cmd = {"rejected": True, "reason": "exception", "detail": repr(e)}
        RECORDS[-1]["exec"][mode] = {"trade_id": tid, "command": cmd}
        return {"trade_id": tid, "mode": mode, "direction": setup.get("direction"),
                "entry_price": setup.get("entry_price"), "state": "PENDING"}
    return _f


gw._execute_shadow = _capture_exec("shadow")
gw._execute_demo = _capture_exec("demo")
gw._execute_live = _capture_exec("live")
gw._persist_trade = lambda *a, **k: None
gw._persist_exit = lambda *a, **k: None

_orig_route = gw.route_setup


def _route_setup_capture(setup, system_id):
    n = _NOW["utc"]
    rec = {
        "il": n.astimezone(IL).strftime("%H:%M:%S"), "et": n.astimezone(ET).strftime("%H:%M"),
        "system": system_id, "classification": setup.get("classification") or setup.get("pattern"),
        "direction": setup.get("direction"), "entry": setup.get("entry_price"),
        "stop": setup.get("stop"), "t1": setup.get("t1"), "t2": setup.get("t2"), "t3": setup.get("t3"),
        "shadow_only": bool((setup.get("metadata") or {}).get("shadow_only")),
        "dp_ot_seen": None, "dp_intent": None, "exec": {},
    }
    RECORDS.append(rec)
    try:
        import backend.v9.gateway.session_gate as _sg
        rec["_dbg_clock"] = {"sg_now": str(_sg.datetime.now(timezone.utc)), "window": _sg.is_within_firing_window(),
                             "now_et": str(now_et()), "time_time": _time_mod.time(),
                             "sg_dt_is_fake": _sg.datetime is FakeDatetime, "sg_dt": repr(_sg.datetime),
                             "dtmod_is_fake": _dt_mod.datetime is FakeDatetime, "fake_now": str(FakeDatetime.now(timezone.utc))}
    except Exception as _e:
        rec["_dbg_clock"] = repr(_e)
    res = _orig_route(setup, system_id)
    rec["blocked_by"] = res.get("blocked_by")
    rec["reason"] = res.get("reason")
    rec["live_blocked_by"] = res.get("live_blocked_by")
    rec["result"] = {k: (v if isinstance(v, (str, int, float, type(None))) else str(v)[:80])
                     for k, v in res.items() if k in ("shadow", "demo", "live", "blocked_by", "live_blocked_by")}
    rec["dp_ot_seen"] = _DP_TRACE.get("ot")
    rec["dp_intent"] = _DP_TRACE.get("intent")
    rec["dp_dir_hint"] = _DP_TRACE.get("dir_hint")
    rec["dp_day_type"] = _DP_TRACE.get("day_type")
    return res


gw.route_setup = _route_setup_capture
fms._gateway = gw
ws._gateway = gw

# trace what the playbook actually received (wrap dalton_playbook.intent)
import backend.v9.services.dalton_playbook as _dp_mod  # noqa: E402
_DP_TRACE = {}
_orig_intent = _dp_mod.intent


def _intent_trace(**kw):
    it = _orig_intent(**kw)
    _DP_TRACE.update({"ot": kw.get("opening_type"), "day_type": kw.get("day_type"),
                      "dir_hint": kw.get("direction_hint"),
                      "intent": {"bias": it.bias, "kinds": sorted(it.entry_kinds), "size_frac": it.size_frac,
                                 "reason": it.reason}})
    return it


_dp_mod.intent = _intent_trace

# ──────────────────────────────────────────────────────────────────────────
# 8. S1 handler — faithful port of backend/main.py:_day_type_on_bar (no persistence)
# ──────────────────────────────────────────────────────────────────────────
_cls_rth_bars = []
_cls_ctx = {"loaded": False}
_prev_bar_ts = {"value": None}
_cls_prev_neutral = {"value": None}
_stab_on = os.environ.get("DAYTYPE_RECLASS_STABILITY_V1", "0").lower() in ("1", "true", "yes")
_S1_NEW_CLS = os.environ.get("S1_ENGINE_NEW_CLASSIFIER", "").lower() in ("1", "true", "yes")
S1_LOG = []


def _machine_opening():
    if getattr(dtm, "opening", None):
        ot = getattr(dtm.opening, "opening_type", None)
        if ot:
            return ot.value if hasattr(ot, "value") else str(ot)
    return "UNKNOWN"


def _load_cls_ctx():
    """main.py:412-481 — context loaded ONCE at IB lock (queries carry explicit dates)."""
    try:
        _today = SESSION
        _sib = read_one("SELECT profile_shape, vah_price, val_price, poc_price FROM v9_tpo_sessions "
                        "WHERE trading_date = :d AND session_type = 'CASH' ORDER BY id DESC LIMIT 1", {"d": _today})
        # NOTE: the live row for `today` at 17:30 is the in-progress row; the stored row is the
        # END-OF-DAY row (lookahead). Rule 1: use None for the shape and the developing POC.
        _cls_ctx["profile_shape"] = None
        _cls_ctx["tpo_vah"] = None; _cls_ctx["tpo_val"] = None; _cls_ctx["poc_at_ib"] = None
        _hist = read_all("SELECT ib_width FROM v9_day_type_history WHERE date < :d AND ib_width IS NOT NULL", {"d": _today})
        _cls_ctx["ib_width_hist"] = [float(r["ib_width"]) for r in _hist if r.get("ib_width") is not None]
        _pd_iso = _prev_td.isoformat()
        _hl = read_one("SELECT max(high) AS h, min(low) AS l FROM v9_bars_5min_woodies "
                       "WHERE (ts AT TIME ZONE 'America/New_York')::date = :pd AND symbol='MES'", {"pd": _pd_iso})
        _cls_ctx["pdh"] = float((_hl or {}).get("h") or 0) or None
        _cls_ctx["pdl"] = float((_hl or {}).get("l") or 0) or None
        _pv = read_one("SELECT vah_price AS vah, val_price AS val FROM v9_tpo_sessions "
                       "WHERE trading_date = :pd ORDER BY id DESC LIMIT 1", {"pd": _pd_iso})
        _cls_ctx["prior_vah"] = float((_pv or {}).get("vah") or 0) or None if _pv else None
        _cls_ctx["prior_val"] = float((_pv or {}).get("val") or 0) or None if _pv else None
        _vol_rows = read_all("SELECT sum(volume) AS vol FROM v9_bars_5min_woodies WHERE symbol='MES' "
                             "AND (ts AT TIME ZONE 'America/New_York')::date < :d "
                             "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
                             "AND (ts AT TIME ZONE 'America/New_York')::time < '16:00' "
                             "GROUP BY (ts AT TIME ZONE 'America/New_York')::date HAVING count(*) >= 60", {"d": _today})
        _vols = sorted(float(r["vol"]) for r in _vol_rows if r.get("vol"))
        _cls_ctx["med_vol"] = _vols[len(_vols) // 2] if len(_vols) >= 3 else None
        _ibm = read_all("SELECT (ib_high - ib_low) AS w FROM v9_tpo_sessions WHERE session_type='CASH' "
                        "AND trading_date < :d AND ib_high IS NOT NULL AND ib_low IS NOT NULL "
                        "ORDER BY trading_date DESC LIMIT 20", {"d": _today})
        _ibmeds = sorted(float(r["w"]) for r in _ibm if r.get("w") is not None)
        _cls_ctx["ib_median"] = _ibmeds[len(_ibmeds) // 2] if _ibmeds else None
    except Exception as e:
        LOG.warning("cls ctx load failed: %s", e)
    _cls_ctx["loaded"] = True


def s1_on_bar(bar: dict):
    bar_ts = bar.get("ts")
    if bar_ts is not None and bar_ts == _prev_bar_ts["value"]:
        if os.environ.get("S1_BAR_REFRESH_V1", "0").lower() in ("1", "true", "yes") and _cls_rth_bars:
            _cls_rth_bars[-1] = {"o": float(bar["open"]), "h": float(bar["high"]), "l": float(bar["low"]),
                                 "c": float(bar["close"]), "v": float(bar.get("volume") or 0),
                                 "cum": bar.get("cumulative_delta")}
        return
    _prev_bar_ts["value"] = bar_ts
    sierra = fake_load_sierra_tpo()
    ib_h = ib_l = None
    if sierra.get("ib_found"):
        ib_h, ib_l = sierra.get("ib_high"), sierra.get("ib_low")
    et_now = now_et()
    _session_min = minutes_since_rth_open(et_now)
    _is_rth = dtime(9, 30) <= et_now.time() < dtime(16, 0)
    bi = BarInput(ts=et_now.timestamp(), session_min=_session_min, is_rth=_is_rth,
                  open=float(bar["open"]), high=float(bar["high"]), low=float(bar["low"]),
                  close=float(bar["close"]), volume=float(bar.get("volume") or 0),
                  pd_high=PD_CTX.get("pd_high"), pd_low=PD_CTX.get("pd_low"), pd_close=PD_CTX.get("pd_close"),
                  ib_high=ib_h, ib_low=ib_l)
    maybe_seed_ib_from_tpo(machine=dtm, session_min=_session_min, tpo_ib_locked=tpo.ib_locked,
                           tpo_ib_high=ib_h, tpo_ib_low=ib_l, logger=LOG)
    state = dtm.process_bar(bi)
    if _is_rth:
        _cls_rth_bars.append({"o": bi.open, "h": bi.high, "l": bi.low, "c": bi.close, "v": bi.volume,
                              "cum": bar.get("cumulative_delta")})
        dtm._opening_gate_bars = _cls_rth_bars
    entry = {"il": et_now.astimezone(IL).strftime("%H:%M"), "stage": str(getattr(dtm, "stage", "?")),
             "machine_opening": _machine_opening(), "ib_locked": bool(dtm.ib_locked),
             "day_type_pre": (state.day_type.value if hasattr(state.day_type, "value") else str(state.day_type))}
    # canonical v2 opening type on the CLOSED RTH bars available at this moment (what FIX 1 reads)
    try:
        from backend.v9.systems.day_type.opening_detector_v2 import detect_opening_type as _v2
        _closed = _cls_rth_bars[:-1] if (_is_rth and _cls_rth_bars) else list(_cls_rth_bars)
        if len(_closed) >= 3:
            _ob = dtm.opening_bars or []
            _r = _v2(_closed[:6], _closed[0]["o"], prior_vah=dtm.prev_vah, prior_val=dtm.prev_val,
                     pdh=_ob[0].pd_high if _ob else None, pdl=_ob[0].pd_low if _ob else None)
            entry["canonical_opening"] = f"{_r.get('opening_type')}/{_r.get('direction')}"
        else:
            entry["canonical_opening"] = "UNKNOWN(<3 bars)"
    except Exception as e:
        entry["canonical_opening"] = f"err:{e}"
    if _S1_NEW_CLS and dtm.ib_locked:
        try:
            if not _cls_ctx["loaded"]:
                _load_cls_ctx()
            if len(_cls_rth_bars) >= 12:
                _ses_vol = sum(b.get("v", 0) for b in _cls_rth_bars)
                _med = _cls_ctx.get("med_vol")
                _vr = round(_ses_vol / _med, 3) if _med and _med > 0 else None
                _cls_result = classify_session(
                    bars=_cls_rth_bars, ib_high=dtm.ib_high, ib_low=dtm.ib_low, open_price=_cls_rth_bars[0]["o"],
                    ib_width_hist=_cls_ctx.get("ib_width_hist"), profile_shape=_cls_ctx.get("profile_shape"),
                    vol_ratio=_vr, prior_vah=_cls_ctx.get("prior_vah"), prior_val=_cls_ctx.get("prior_val"),
                    pdh=_cls_ctx.get("pdh"), pdl=_cls_ctx.get("pdl"), poc_now=tpo.current_state.get("poc"),
                    poc_at_ib=_cls_ctx.get("poc_at_ib"), prev_neutral_subtype=_cls_prev_neutral["value"])
                _cls_dt_str = _cls_result.get("day_type", "")
                if _cls_dt_str.startswith("Neutral_"):
                    _cls_prev_neutral["value"] = _cls_dt_str
                elif _cls_dt_str not in ("FORMING", ""):
                    _cls_prev_neutral["value"] = None
                _cls_status = _cls_result.get("status", "")
                _DT_MAP = {"Trend_Normal": _DT.Trend_Normal, "Trend_DD": _DT.Trend_DD, "Variation": _DT.Variation,
                           "Normal_Variation": _DT.Variation, "Normal": _DT.Normal,
                           "Neutral_Center": getattr(_DT, "Neutral_Center", _DT.Normal),
                           "Neutral_Extreme": getattr(_DT, "Neutral_Extreme", _DT.Normal), "Nontrend": _DT.Nontrend}
                _new_dt = _DT_MAP.get(_cls_dt_str)
                entry["canonical"] = _cls_dt_str
                entry["accepted_break"] = _cls_result.get("accepted_break")
                if _new_dt is not None and _cls_dt_str != "FORMING":
                    _old_val = state.day_type.value if hasattr(state.day_type, "value") else str(state.day_type)
                    _publish = (_new_dt != state.day_type)
                    if _stab_on:
                        _stab_n = _stab_mod.confirm_bars()
                        _stab_st = getattr(APP.state, "_daytype_stability", None)
                        if not isinstance(_stab_st, dict):
                            _stab_st = {}; APP.state._daytype_stability = _stab_st
                        _force = bool(_cls_result.get("dual_ib_break"))
                        _publish = _stab_mod.confirm_label(_stab_st, _old_val, _new_dt.value, _stab_n,
                                                           SESSION, force_immediate=_force)
                        if not _publish and _new_dt != state.day_type:
                            entry["stability_held"] = f"{_old_val}->{_new_dt.value} pending {_stab_mod.pending_view(_stab_st)}"
                    if _publish:
                        state.day_type = _new_dt
                        dtm.day_type = _new_dt
                        if getattr(dtm, "_last_state", None):
                            dtm._last_state.day_type = _new_dt
                        if _old_val != _new_dt.value:
                            entry["promoted"] = f"{_old_val}->{_new_dt.value} ({_cls_status})"
                    elif _stab_on:
                        _cur_m = getattr(dtm, "day_type", None)
                        if str(_cur_m) != "Nonconviction" and _cur_m != state.day_type:
                            dtm.day_type = state.day_type
                        _ls = getattr(dtm, "_last_state", None)
                        if _ls is not None and getattr(_ls, "day_type", None) != state.day_type:
                            _ls.day_type = state.day_type
                    _cls_conf = _cls_result.get("confidence")
                    if _cls_conf is not None:
                        _sm_st = getattr(APP.state, "_s1_conf_smooth", None) or {}
                        _sm_prev = _sm_st.get("conf") if _sm_st.get("date") == SESSION else None
                        _sm_val = smooth_confidence(_sm_prev, float(_cls_conf), _cls_dt_str)
                        APP.state._s1_conf_smooth = {"date": SESSION, "conf": (None if _cls_dt_str == "FORMING" else _sm_val)}
                        state.confidence = float(_sm_val)
                    _cls_result["session_date"] = SESSION
                    APP.state.last_cls_result = _cls_result
        except Exception as e:
            entry["cls_error"] = repr(e)
    # DAYTYPE_ACCEPTANCE_DEMOTION_V1 (main.py:712-747) — ON in .env
    if os.environ.get("DAYTYPE_ACCEPTANCE_DEMOTION_V1", "0").lower() in ("1", "true", "yes"):
        try:
            _cur_dt = getattr(dtm, "day_type", None)
            _cur_str = _cur_dt.value if hasattr(_cur_dt, "value") else str(_cur_dt or "")
            if _cur_str.startswith("Trend"):
                _ib_h2, _ib_l2 = getattr(dtm, "ib_high", None), getattr(dtm, "ib_low", None)
                if _ib_h2 is not None and _ib_l2 is not None:
                    _ib_w = float(_ib_h2) - float(_ib_l2)
                    _tol = min(max(0.25 * _ib_w, 1.0), 4.0) if _ib_w > 0 else 2.0
                    _inside = (bi.high < float(_ib_h2) - _tol and bi.low > float(_ib_l2) + _tol)
                    if not hasattr(APP.state, "_dem_inside_count"):
                        APP.state._dem_inside_count = 0
                    APP.state._dem_inside_count = APP.state._dem_inside_count + 1 if _inside else 0
                    if APP.state._dem_inside_count >= int(os.environ.get("DAYTYPE_DEMOTION_K_BARS", "3")):
                        APP.state._dem_inside_count = 0
                        state.day_type = _DT.Variation; dtm.day_type = _DT.Variation
                        if getattr(dtm, "_last_state", None):
                            dtm._last_state.day_type = _DT.Variation
                        entry["demotion"] = f"{_cur_str}->Normal_Variation"
        except Exception as e:
            entry["dem_error"] = repr(e)
    dt_val = state.day_type.value if hasattr(state.day_type, "value") else str(state.day_type)
    entry["published"] = dt_val
    entry["live_label"] = _tc_mod.get_live_day_type()
    entry["conf"] = round(float(state.confidence or 0), 2)
    S1_LOG.append(entry)
    # publish day_type_classification to S2 (main.py:884)
    fms._on_day_type_update({"payload": {"day_type": dt_val, "status": str(state.lock_state),
                                         "confidence": state.confidence, "opening_type": _machine_opening()}})


# ──────────────────────────────────────────────────────────────────────────
# 8b. tape scoring + live-slot lifecycle (the gateway's on_trade_close reads
#     TODAY's sierra_state.json, so the harness settles against the bars itself)
# ──────────────────────────────────────────────────────────────────────────
OPEN_TRADES = []     # in-flight harness trades (live commands)
TRADES = []          # settled
PT_VALUE = 5.0


def _legs_from_command(cmd, n):
    """Per-contract target ladder exactly as the PLACE payload carries it:
    C1→target_price, C2→context.t2, C3→context.t3, C4→context.t4, extra contracts → runner (no target)."""
    ctx = cmd.get("context") or {}
    ladder = [cmd.get("target_price"), ctx.get("t2"), ctx.get("t3"), ctx.get("t4")]
    legs = []
    last_defined = None
    for k in range(int(n)):
        tgt = ladder[k] if k < len(ladder) else None
        try:
            tgt = float(tgt) if tgt not in (None, 0, 0.0) else None
        except (TypeError, ValueError):
            tgt = None
        if tgt is None and k >= len(ladder):
            tgt = last_defined      # contracts beyond the 4-slot ladder follow the last target (DLL split unknown)
        if tgt is not None:
            last_defined = tgt
        legs.append({"leg": k + 1, "target": tgt, "exit": None, "exit_price": None, "pts": None, "bar_il": None})
    return legs


def _open_trade(rec, cmd, bar_index):
    n = int(cmd.get("contracts") or 0)
    legs = _legs_from_command(cmd, n)
    # T0 (T0_TARGET_PTS, contracts>=4) shifts the ladder: C1→T0, C2→T1 … so "T1" is leg 2 there.
    _t0_on = n >= 4 and float(os.getenv("T0_TARGET_PTS", "0") or 0) > 0
    t1_leg = 2 if _t0_on and len(legs) >= 2 else 1
    tr = {"trade_id": rec["exec"]["live"]["trade_id"], "classification": rec["classification"],
          "direction": (rec["direction"] or "").upper(), "entry": float(cmd.get("price") or rec["entry"] or 0),
          "stop": float(cmd.get("stop_price") or rec["stop"] or 0), "contracts": n,
          "stop_initial": float(cmd.get("stop_price") or rec["stop"] or 0), "t1_leg": t1_leg,
          "fired_il": rec["il"], "entry_bar_index": bar_index, "filled": False, "fill_price": None,
          "legs": legs, "be_moved": False, "ambiguous_bars": 0,
          "pnl_usd": None, "outcome": None, "exit_il": None}
    OPEN_TRADES.append(tr)
    rec["harness_trade"] = tr["trade_id"]


def _settle_bar(b, bar_index):
    """Walk one CLOSED bar through every open trade (conservative: stop before target on the same bar)."""
    hi, lo, op, cl = float(b["high"]), float(b["low"]), float(b["open"]), float(b["close"])
    il = b["ts"].astimezone(IL).strftime("%H:%M")
    for tr in list(OPEN_TRADES):
        d = tr["direction"]; sgn = 1 if d == "LONG" else -1
        if not tr["filled"]:
            if bar_index < tr["entry_bar_index"]:
                continue
            e = tr["entry"]
            tr["fill_price"] = e if lo <= e <= hi else op
            tr["filled"] = True
        e = tr["fill_price"]
        stop = tr["stop"]
        stop_hit = (lo <= stop) if d == "LONG" else (hi >= stop)
        t1_filled = False
        for leg in tr["legs"]:
            if leg["exit"]:
                continue
            tgt = leg["target"]
            tgt_hit = tgt is not None and ((hi >= tgt) if d == "LONG" else (lo <= tgt))
            if stop_hit and tgt_hit:
                tr["ambiguous_bars"] += 1
                leg.update(exit="STOP(ambiguous)", exit_price=stop, pts=sgn * (stop - e), bar_il=il)
            elif stop_hit:
                leg.update(exit="STOP" if not tr["be_moved"] else "BE", exit_price=stop, pts=sgn * (stop - e), bar_il=il)
            elif tgt_hit:
                leg.update(exit=f"T{leg['leg']}", exit_price=tgt, pts=sgn * (tgt - e), bar_il=il)
                if leg["leg"] == tr.get("t1_leg", 1):
                    t1_filled = True
        # protective BE after T1 fills (ruling 07-14 "אחרי-T1→BE"; System6 protective AUTO = MODIFY_STOP→BE)
        if t1_filled and not tr["be_moved"]:
            tr["stop"] = e; tr["be_moved"] = True
        if all(l["exit"] for l in tr["legs"]):
            _close_trade(tr, il)


def _harness_stop_cooldown(pattern_id, direction, entry_price):
    """Same semantics as trading_gateway._stop_cooldown_check, over the HARNESS's own trades
    (v9_trades holds the live system's trades of that day — a different chain)."""
    if not pattern_id or not direction or entry_price is None:
        return (False, "")
    _bars = int(os.getenv("PATTERN_STOP_COOLDOWN_BARS", "6") or 6)
    _min_dist = float(os.getenv("PATTERN_STOP_COOLDOWN_MIN_DIST_PT", "4.0") or 4.0)
    _base = str(pattern_id).upper().strip()
    for _suf in ("_LONG", "_SHORT"):
        if _base.endswith(_suf):
            _base = _base[: -len(_suf)]
    n = _NOW["utc"]
    for tr in sorted(TRADES, key=lambda t: t.get("exit_utc") or n, reverse=True):
        if tr["outcome"] != "STOP" or (tr["direction"] or "") != str(direction).upper():
            continue
        if not str(tr["classification"] or "").upper().startswith(_base):
            continue
        ex = tr.get("exit_utc")
        if ex is None or ex < n - timedelta(minutes=_bars * 5):
            continue
        if abs(float(entry_price) - float(tr["fill_price"])) >= _min_dist:
            return (False, "")
        return (True, f"{_base} {direction} stopped at {ex} within {_bars * 5}min cooldown; "
                      f"re-entry {entry_price} within {_min_dist}pt of stopped entry {tr['fill_price']} (harness)")
    return (False, "")


_gw_mod._stop_cooldown_check = _harness_stop_cooldown


def _close_trade(tr, il, eod=False, eod_price=None):
    for leg in tr["legs"]:
        if not leg["exit"]:
            e = tr["fill_price"] if tr["fill_price"] is not None else tr["entry"]
            sgn = 1 if tr["direction"] == "LONG" else -1
            leg.update(exit="EOD", exit_price=eod_price, pts=sgn * (eod_price - e) if eod_price is not None else 0.0, bar_il=il)
    pnl = sum((l["pts"] or 0) * PT_VALUE for l in tr["legs"])
    tr["pnl_usd"] = round(pnl, 2)
    tr["outcome"] = "WIN" if pnl > 0 else ("STOP" if pnl < 0 else "FLAT")
    tr["exit_il"] = il
    tr["exit_utc"] = _NOW["utc"]
    _t1l = next((l for l in tr["legs"] if l["leg"] == tr.get("t1_leg", 1)), None)
    tr["t1_before_stop"] = bool(_t1l and _t1l["exit"] and _t1l["exit"].startswith("T"))
    tr["pnl_stop_only_usd"] = round(-abs(tr["entry"] - tr["stop_initial"]) * tr["contracts"] * PT_VALUE, 2)
    OPEN_TRADES.remove(tr); TRADES.append(tr)
    # gateway bookkeeping the live on_trade_close would do (slot, daily stats, cooldown)
    if gw.live_slot and str(gw.live_slot.get("trade_id")) == str(tr["trade_id"]):
        gw.live_slot = None
    gw._daily_trades += 1; gw._daily_pnl += pnl
    gw._consecutive_losses = gw._consecutive_losses + 1 if pnl < 0 else 0
    try:
        gw.cooldown.on_trade_close(tr["outcome"])
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────
# 9. drive the session
# ──────────────────────────────────────────────────────────────────────────
loop = asyncio.new_event_loop()


def _woodies_payload(b, developing=None, prev=None):
    src = b if developing is None else developing
    st = b if prev is None else prev   # studies source
    return {"ts": src["ts"].isoformat(), "open": float(src["open"]), "high": float(src["high"]),
            "low": float(src["low"]), "close": float(src["close"]), "volume": int(src["volume"] or 0),
            "cci_14": st.get("cci_14"), "cci_6_tcci": st.get("cci_6_tcci"), "ema_34": st.get("ema_34"),
            "lsma_value": st.get("lsma_value"), "swi_value": st.get("swi_value"), "czi_value": st.get("czi_value"),
            "trend_state": st.get("trend_state"), "predictor_next_cci": st.get("predictor_next_cci"),
            "zlr_detected": bool(b.get("zlr_detected")) if developing is None else False,
            "zlr_direction": (b.get("zlr_direction") or "NONE") if developing is None else "NONE",
            "hfe_detected": bool(b.get("hfe_detected")) if developing is None else False,
            "hfe_direction": (b.get("hfe_direction") or "NONE") if developing is None else "NONE",
            "hfe_extreme_bars_ago": int(b.get("hfe_extreme_bars_ago") or 0),
            "lsma_above_price": bool(st.get("lsma_above_price")) if st.get("lsma_above_price") is not None else False}


def _5min_payload(w):
    return {"ts": w["ts"], "o": w["open"], "h": w["high"], "l": w["low"], "c": w["close"], "vol": w["volume"],
            "open": w["open"], "high": w["high"], "low": w["low"], "close": w["close"], "volume": w["volume"],
            "cumulative_delta": None}


_BAR_INDEX = {"i": 0}


def _push(w, when):
    set_now(when)
    tpo.refresh()
    n_before = len(RECORDS)
    p5 = _5min_payload(w)
    if p5.get("ts") == _prev_bar_ts["value"]:
        # duplicate push: live has ~40 pushes per bar and S1 refreshes _cls_rth_bars[-1] on
        # each, so at any push the gateway sees the previous push's values (seconds old).
        # With two pushes per bar the refresh must precede the dispatch or the gateway
        # would read a 5-minute-old stub — refresh first (S1 does nothing else on a duplicate).
        s1_on_bar(p5)
    ev_w = BarEvent(bar_type="woodies_5min", bar_id=f"w_{w['ts']}", ts=w["ts"], payload=w, session="RTH")
    loop.run_until_complete(ws.process_bar(ev_w))
    ev5 = BarEvent(bar_type="5min", bar_id=f"5_{w['ts']}", ts=w["ts"], payload=p5, session="RTH")
    loop.run_until_complete(fms.process_bar(ev5))
    s1_on_bar(p5)
    # open harness trades for every live command produced during this push
    for rec in RECORDS[n_before:]:
        lv = rec["exec"].get("live") or {}
        cmd = lv.get("command")
        if cmd and not cmd.get("rejected") and cmd.get("contracts"):
            _open_trade(rec, cmd, _BAR_INDEX["i"])


# ── the LIVE system's own fires that day (v9_trades mode=live), re-routed through THIS chain at
#    their real fire time. Answers "does the fixed chain still admit them" independently of the
#    harness's producer emulation. Marked injected=True in the output.
INJECT = _orig_read_all(
    "SELECT id, firing_system, direction, created_at, entry_price, stop, t1, t2, t3, t4, quality, "
    "pattern_id_at_entry, exit_reason, pnl_usd, pnl_sierra, outcome FROM v9_trades "
    "WHERE mode='live' AND created_at >= :a AND created_at < :b ORDER BY created_at",
    {"a": _SESSION_OPEN_UTC.isoformat(), "b": datetime.combine(_sd, dtime(16, 0), tzinfo=ET).isoformat()})
for _tr in INJECT:
    _tr["_done"] = False


def _inject_due(upto):
    for tr in INJECT:
        if tr["_done"] or tr["created_at"] > upto:
            continue
        tr["_done"] = True
        set_now(tr["created_at"]); tpo.refresh()
        q = tr.get("quality") or {}
        if isinstance(q, str):
            try:
                q = json.loads(q)
            except Exception:
                q = {}
        meta = dict((q.get("metadata") or {}))
        meta.pop("shadow_only", None)
        setup = {"firing_system": tr["firing_system"], "direction": tr["direction"],
                 "classification": q.get("trigger") or tr["pattern_id_at_entry"],
                 "pattern": q.get("trigger") or tr["pattern_id_at_entry"],
                 "entry_price": float(tr["entry_price"]), "stop": float(tr["stop"] or 0),
                 "t1": tr["t1"], "t2": tr["t2"], "t3": tr["t3"], "confidence": 0.65, "metadata": meta}
        n_before = len(RECORDS)
        gw.route_setup(setup, int(tr["firing_system"]))
        for rec in RECORDS[n_before:]:
            rec["injected"] = {"live_trade_id": tr["id"], "live_exit_reason": tr["exit_reason"],
                               "live_pnl_usd": tr["pnl_usd"], "live_pnl_sierra": tr["pnl_sierra"], "live_outcome": tr["outcome"]}
            lv = rec["exec"].get("live") or {}
            cmd = lv.get("command")
            if cmd and not cmd.get("rejected") and cmd.get("contracts"):
                _open_trade(rec, cmd, _BAR_INDEX["i"])


prev_row = PRE[-1] if PRE else None
for i, b in enumerate(BARS):
    _BAR_INDEX["i"] = i
    ts = b["ts"]
    if args.push_mode == "firstpush":
        dev = {"ts": ts, "open": b["open"], "high": b["open"], "low": b["open"], "close": b["open"],
               "volume": max(1, int((b["volume"] or 0) * 0.01))}
        _push(_woodies_payload(b, developing=dev, prev=prev_row or b), ts + timedelta(seconds=3))
        _inject_due(ts + timedelta(minutes=2, seconds=30))
        _push(_woodies_payload(b), ts + timedelta(minutes=4, seconds=58))
        _inject_due(ts + timedelta(minutes=4, seconds=59))
    else:
        _push(_woodies_payload(b), ts + timedelta(minutes=5, seconds=2))
        _inject_due(ts + timedelta(minutes=5, seconds=3))
    _settle_bar(b, i)          # the bar is closed now — score every open trade on it
    prev_row = b
# session end: flatten whatever is still open at the last close
if BARS:
    _last = BARS[-1]
    for tr in list(OPEN_TRADES):
        if not tr["filled"]:
            tr["fill_price"] = tr["entry"]; tr["filled"] = True
        _close_trade(tr, _last["ts"].astimezone(IL).strftime("%H:%M"), eod=True, eod_price=float(_last["close"]))

# tape context per trade: MFE/MAE to session end and hold-to-close, from the bars after entry
for tr in TRADES:
    try:
        sgn = 1 if tr["direction"] == "LONG" else -1
        e = tr["fill_price"] if tr["fill_price"] is not None else tr["entry"]
        seg = BARS[tr["entry_bar_index"]:]
        rth_seg = [b for b in seg if dtime(9, 30) <= b["ts"].astimezone(ET).time() < dtime(16, 0)]
        if rth_seg:
            tr["mfe_pts"] = round(max(sgn * (float(b["high"] if sgn > 0 else b["low"]) - e) for b in rth_seg), 2)
            tr["mae_pts"] = round(min(sgn * (float(b["low"] if sgn > 0 else b["high"]) - e) for b in rth_seg), 2)
            tr["hold_to_close_pts"] = round(sgn * (float(rth_seg[-1]["close"]) - e), 2)
            tr["t1_target"] = tr["legs"][0]["target"] if tr["legs"] else None
            _t1 = tr["t1_target"]; _st = tr["stop"] if not tr["be_moved"] else tr["entry"]
            tr["t1_pts"] = round(sgn * (_t1 - e), 2) if _t1 else None
    except Exception as _e:
        tr["tape_err"] = repr(_e)

# ──────────────────────────────────────────────────────────────────────────
# 10. output
# ──────────────────────────────────────────────────────────────────────────
out = {
    "session": SESSION, "variant": args.variant, "push_mode": args.push_mode, "oe_closed": bool(args.oe_closed),
    "pd_ctx_note": PD_CTX_NOTE, "rewrite_stats": REWRITE_STATS,
    "oe_closed_trace": [t for t in OE_CLOSED_TRACE if t.get("trigger")],
    "flags": {k: os.environ.get(k) for k in (
        "DALTON_PLAYBOOK_V1", "DAYTYPE_RECLASS_STABILITY_V1", "DAYTYPE_ANTIFLAP_V1", "DAYTYPE_ANTIFLAP_HOLD_S",
        "OPENING_ENTRY_V1", "OPENING_FIRE_V1", "OPENING_DIR_FUSION_V1", "OPENING_FIRST_TRADE_STRICT_V1",
        "ZLR_SHADOW_V1", "T3_REQUIRED_V1", "OPENING_LADDER_V1", "RISK_BUDGET_SIZING_V1", "RISK_MIN_CONTRACTS",
        "FIXED_CONTRACTS_5", "S1_ENGINE_NEW_CLASSIFIER", "S1_BAR_REFRESH_V1", "DELTA_FEATURES_V1",
        "COLD_START_GUARD_V1", "OPENING_ANCHOR_ET_V1", "MEMS26_CLOCK_MODE")},
    "bars": {"total": len(BARS), "rth": len(RTH), "first_ts": BARS[0]["ts"].isoformat(), "last_ts": BARS[-1]["ts"].isoformat()},
    "pd_ctx": {k: PD_CTX.get(k) for k in ("pd_high", "pd_low", "pd_close", "pd_context_status")},
    "prev_tpo": {k: PREV_TPO.get(k) for k in ("found", "poc", "vah", "val")},
    "s1": S1_LOG, "routes": RECORDS, "would_write": _WOULD_WRITE,
    "trades": TRADES, "gateway_decisions": list(gw.decisions),
    "daily_pnl_harness": round(gw._daily_pnl, 2),
}
os.makedirs(os.path.dirname(args.out), exist_ok=True)
with open(args.out, "w") as f:
    json.dump(out, f, default=str, indent=1)
print(f"[fwd] {SESSION} {args.variant} push={args.push_mode} routes={len(RECORDS)} "
      f"blocked={sum(1 for r in RECORDS if r.get('blocked_by'))} "
      f"live_cmds={sum(1 for r in RECORDS if r['exec'].get('live', {}).get('command') and not (r['exec']['live']['command'] or {}).get('rejected'))} "
      f"-> {args.out}")
