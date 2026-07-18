#!/usr/bin/env python3
"""audit_pattern_miss.py — quantified, doctrine-aware audit of WHY the pattern
detectors missed a session's major swings (2026-07-17 pattern-miss audit).

READ-ONLY on the DB. Standalone — no backend imports — so the exact numeric
criteria are reimplemented here as pure functions, each annotated with the
source file:line it mirrors. If a criterion here drifts from the code, the
code wins; regenerate this audit after any detector change.

WHAT IT DOES
  1. Loads v9_bars_5min_woodies (S4 source-of-truth) + v9_bars_5min (S2 source)
     for the RTH session (09:30-16:00 ET) of --date, with 3h warmup history.
  2. Finds major price swings (zigzag, >= --swing-pt points, default 15).
  3. For each swing's FIRST THIRD, evaluates the full criteria vector of every
     direction-matching detector at every bar:
       S4: ZLR (base + ZLR_SPEC_V2 gates), GB100, TT   [woodies bars]
       S2: REACTIVE, INITIATIVE (B1-B4 geometry + FHB) [5min bars]
     and reports: catchable-by (all criteria pass) OR the near-miss —
     WHICH criterion failed and BY HOW MUCH (e.g. "blue_bars=5 need>=6 (d=1)").
  4. --relax MODE re-runs with named relaxations and reports (a) which swings
     become caught and (b) the FALSE fires each relaxation adds across the
     whole session (fired where no >= --false-pt favorable move followed
     within --false-window bars).

LIVE-FLAG MODEL (documented state 2026-07-17, docs/FLAG_INDEX.md):
  ZLR_SPEC_V2=1 · S2_VSA_VOLUME=1 (variant=UNION, config/s2_firing.yaml)
  S2_VOL_ADAPTIVE=1 (regime >= 8.0pt avg14) · S2_CVD_DETECTION_V1=1
  S4_EXTREME_TREND_RELABEL=1 (|CCI|>=200 GRAY/YELLOW->BLUE/RED)
  HFE_DISABLED=1 · S2_REQUIRE_COT_AMT=0 (COT/AMT bypassed, S2 perp S3)
  Override any of these via env of the same name when invoking.

RELAXATIONS (--relax, comma list or "all"):
  zlr_blue_bars      ZLR SPEC_V2 S1.1 trend-side bars 6 -> 3      (zlr.py:81)
  zlr_extreme_window ZLR extreme lookback 12 -> 20 bars           (zlr.py:32 + anti_patterns.py:70 AP1)
  gb100_gray_open    GB100 may fire on GRAY trend (never YELLOW)
                     within the first 6 RTH bars (opening window)  (gb100.py:91,147)
  s2_fhb_half        First-Hour-Buffer halved 12 -> 6: REACTIVE
                     eligible from FHB count 2 (was 4), INITIATIVE
                     from 4 (was 7)                    (first_hour_buffer.py:69-79)
  s2_b4_confirm_75   REACTIVE B4 confirm at 75% of B3 range always
                     (today: 100%, or 75% only in VOLATILE regime) (five_min_system.py:88-95)

USAGE (on the trading Mac, repo root; DATABASE_URL defaults to local PG):
  python3 scripts/audit_pattern_miss.py --date 2026-07-17
  python3 scripts/audit_pattern_miss.py --date 2026-07-17 --relax all
  python3 scripts/audit_pattern_miss.py --date 2026-07-17 --relax zlr_blue_bars,gb100_gray_open
  python3 scripts/audit_pattern_miss.py --date 2026-07-17 --out docs/reports/PATTERN_MISS_RUN_2026-07-17.md
  python3 scripts/audit_pattern_miss.py --selftest        # no DB needed (synthetic day)
  python3 scripts/audit_pattern_miss.py --csv bars.csv --date 2026-07-17   # offline bars

HONESTY NOTES (Rule 1 / Rule 5):
  * This audits DETECTOR-level criteria only. Post-detection drops (P-W5 YELLOW
    lock, HTLB_DIRECTION_GATE latch, dispatcher, sizing reject, gateway gates)
    are NOT modeled — a "catchable" here that did not fire live means the loss
    happened downstream; check the backend log / decisions feed for that ts.
  * The DLL-flag fallback (woodies_system.py:491-524) fires a DLL ZLR/HFE even
    when the Python detector rejects — rows with zlr_detected=1 are listed in
    the DLL cross-check section so the non-route can be chased in the log.
  * S2 CVD gate mirrors the code's fail-open: no/short CVD data => pass.
  * S2 rolling-volume / ATR context is rebuilt from completed bars; live uses a
    rolling in-memory buffer that includes the partial bar — small drift possible.
"""
from __future__ import annotations

import argparse
import csv as _csv
import math
import os
import sys
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, time as dtime, timezone
from typing import Dict, List, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    print("python3.9+ required (zoneinfo)"); sys.exit(2)

ET = ZoneInfo("America/New_York")
IL = ZoneInfo("Asia/Jerusalem")
TICK = 0.25

RTH_START = dtime(9, 30)   # woodies_system.py:39
RTH_END = dtime(16, 0)     # woodies_system.py:40
DAY_TYPE_MODE_ET = dtime(10, 30)  # session_classifier.py:76 — FHB gate ends here


# ────────────────────────────────────────────────────────────────────────────
# Live-flag model (override with env of same name)
# ────────────────────────────────────────────────────────────────────────────
def _envbool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes")


@dataclass
class Flags:
    zlr_spec_v2: bool = True          # FLAG_INDEX: ZLR_SPEC_V2=1 (.env)
    s2_vsa_volume: bool = True        # S2_VSA_VOLUME=1
    s2_variant: str = "UNION"         # config/s2_firing.yaml: variant: UNION
    s2_vol_adaptive: bool = True      # S2_VOL_ADAPTIVE=1
    s2_cvd: bool = True               # S2_CVD_DETECTION_V1=1
    s4_extreme_relabel: bool = True   # S4_EXTREME_TREND_RELABEL=true
    hfe_disabled: bool = True         # HFE_DISABLED=1
    zlr_cci_min: float = 100.0        # ZLR_CCI_MIN unset -> 100 (zlr.py:132-142)

    @classmethod
    def from_env(cls) -> "Flags":
        f = cls()
        f.zlr_spec_v2 = _envbool("ZLR_SPEC_V2", f.zlr_spec_v2)
        f.s2_vsa_volume = _envbool("S2_VSA_VOLUME", f.s2_vsa_volume)
        f.s2_variant = os.environ.get("S2_FIRING_VARIANT", f.s2_variant)
        f.s2_vol_adaptive = _envbool("S2_VOL_ADAPTIVE", f.s2_vol_adaptive)
        f.s2_cvd = _envbool("S2_CVD_DETECTION_V1", f.s2_cvd)
        f.s4_extreme_relabel = _envbool("S4_EXTREME_TREND_RELABEL", f.s4_extreme_relabel)
        f.hfe_disabled = _envbool("HFE_DISABLED", f.hfe_disabled)
        try:
            f.zlr_cci_min = float(os.environ.get("ZLR_CCI_MIN", f.zlr_cci_min))
        except ValueError:
            pass
        return f


@dataclass
class Relax:
    """Numeric knobs. BASE == today's live values."""
    label: str = "BASE"
    zlr_blue_bars: int = 6            # zlr.py:81 (SPEC_V2 S1.1)
    zlr_extreme_window: int = 12      # zlr.py:32 LOOKBACK; anti_patterns.py:70 AP1 max
    gb100_allow_gray_opening: bool = False   # gb100.py:91,147
    opening_window_bars: int = 6      # first 30 RTH minutes (item-10 window)
    fhb_reactive_min: int = 4         # first_hour_buffer.py:72 (EARLY from count 4)
    fhb_initiative_min: int = 7       # first_hour_buffer.py:74 (DEVELOPING from 7)
    s2_confirm_frac: Optional[float] = None  # None = live rule (1.0, 0.75 in VOLATILE)


RELAXATIONS: Dict[str, Tuple[str, dict]] = {
    "zlr_blue_bars": ("ZLR SPEC_V2 blue-bar count 6->3 (zlr.py:81)",
                      {"zlr_blue_bars": 3}),
    "zlr_extreme_window": ("ZLR extreme window 12->20 bars (zlr.py:32 + AP1 anti_patterns.py:70)",
                           {"zlr_extreme_window": 20}),
    "gb100_gray_open": ("GB100 GRAY allowed in opening window, first 6 RTH bars (gb100.py:91,147)",
                        {"gb100_allow_gray_opening": True}),
    "s2_fhb_half": ("S2 First-Hour-Buffer 12->6: REACTIVE from count 2, INITIATIVE from 4 "
                    "(first_hour_buffer.py:69-79)",
                    {"fhb_reactive_min": 2, "fhb_initiative_min": 4}),
    "s2_b4_confirm_75": ("S2 REACTIVE B4-confirm 100%->75% of B3 range, all regimes "
                         "(five_min_system.py:88-95)",
                         {"s2_confirm_frac": 0.75}),
}


# ────────────────────────────────────────────────────────────────────────────
# Data loading
# ────────────────────────────────────────────────────────────────────────────
@dataclass
class Bar:
    ts: datetime                 # tz-aware UTC
    open: float; high: float; low: float; close: float
    volume: float = 0.0
    cci_14: float = 0.0
    cci_6_tcci: float = 0.0
    ema_34: float = 0.0
    lsma_value: float = 0.0
    swi_value: float = 0.0
    czi_value: float = 0.0
    trend_state: str = "GRAY"    # RAW Sierra value from DB
    trend_eff: str = "GRAY"      # after S4_EXTREME_TREND_RELABEL (live path)
    zlr_detected: int = 0
    zlr_direction: str = "NONE"
    hfe_detected: int = 0
    hfe_direction: str = "NONE"
    poc_vol: Optional[float] = None

    @property
    def et(self) -> datetime:
        return self.ts.astimezone(ET)

    def hhmm_il(self) -> str:
        return self.ts.astimezone(IL).strftime("%H:%M")

    def hhmm_et(self) -> str:
        return self.et.strftime("%H:%M")


def _apply_relabel(bars: List[Bar], flags: Flags) -> None:
    """trend_relabel.py:15-30 — |CCI|>=200 & GRAY/YELLOW -> BLUE/RED (live=ON).
    The DB stores RAW Sierra trend; the live in-memory buffer holds the
    relabeled value per bar, so we mirror that here."""
    for b in bars:
        b.trend_eff = b.trend_state or "GRAY"
        if flags.s4_extreme_relabel and b.trend_eff in ("GRAY", "GREY", "YELLOW"):
            if abs(b.cci_14) >= 200:
                b.trend_eff = "BLUE" if b.cci_14 > 0 else "RED"


def _connect():
    url = os.environ.get("DATABASE_URL", "postgresql://localhost/mems26")
    try:
        from sqlalchemy import create_engine, text  # backend dependency, present on Mac
        eng = create_engine(url)
        return ("sqlalchemy", eng, text)
    except ImportError:
        try:
            import psycopg2  # type: ignore
            conn = psycopg2.connect(url)
            return ("psycopg2", conn, None)
        except ImportError:
            print("ERROR: neither sqlalchemy nor psycopg2 importable. Run from repo "
                  "root on the Mac (backend venv) or use --csv.", file=sys.stderr)
            sys.exit(2)


def _query(dbh, sql: str, params: dict) -> List[dict]:
    kind, conn, text = dbh
    if kind == "sqlalchemy":
        with conn.connect() as c:
            rs = c.execute(text(sql), params)
            cols = rs.keys()
            return [dict(zip(cols, row)) for row in rs.fetchall()]
    else:  # psycopg2 — convert :name to %(name)s
        import re
        sql2 = re.sub(r":(\w+)", r"%(\1)s", sql)
        with conn.cursor() as cur:
            cur.execute(sql2, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def _session_bounds_utc(date_str: str, warmup_h: float = 3.0):
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    start_et = datetime.combine(d, RTH_START, tzinfo=ET)
    end_et = datetime.combine(d, RTH_END, tzinfo=ET)
    return (start_et - timedelta(hours=warmup_h)).astimezone(timezone.utc), \
        end_et.astimezone(timezone.utc), start_et.astimezone(timezone.utc)


def _norm_ts(v) -> datetime:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    s = str(v).replace("Z", "+00:00").replace(" ", "T")
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def load_woodies(dbh, date_str: str) -> List[Bar]:
    t0, t1, _ = _session_bounds_utc(date_str)
    rows = _query(dbh, """
        SELECT ts, open, high, low, close, volume, cci_14, cci_6_tcci, ema_34,
               lsma_value, swi_value, czi_value, trend_state,
               zlr_detected, zlr_direction, hfe_detected, hfe_direction
        FROM v9_bars_5min_woodies
        WHERE ts >= :t0 AND ts <= :t1
        ORDER BY ts ASC""", {"t0": t0, "t1": t1})
    out, seen = [], set()
    for r in rows:
        ts = _norm_ts(r["ts"])
        if ts in seen:
            continue
        seen.add(ts)
        out.append(Bar(
            ts=ts, open=float(r["open"]), high=float(r["high"]),
            low=float(r["low"]), close=float(r["close"]),
            volume=float(r.get("volume") or 0),
            cci_14=float(r.get("cci_14") or 0), cci_6_tcci=float(r.get("cci_6_tcci") or 0),
            ema_34=float(r.get("ema_34") or 0), lsma_value=float(r.get("lsma_value") or 0),
            swi_value=float(r.get("swi_value") or 0), czi_value=float(r.get("czi_value") or 0),
            trend_state=(r.get("trend_state") or "GRAY").upper(),
            zlr_detected=int(r.get("zlr_detected") or 0),
            zlr_direction=(r.get("zlr_direction") or "NONE"),
            hfe_detected=int(r.get("hfe_detected") or 0),
            hfe_direction=(r.get("hfe_direction") or "NONE"),
        ))
    return out


def load_s2(dbh, date_str: str) -> Tuple[List[Bar], str]:
    """v9_bars_5min (has volume+poc_vol). Rule 2: verify coverage; fall back to
    woodies bars (poc=None) if the table is gapped/empty for the session."""
    t0, t1, rth0 = _session_bounds_utc(date_str)
    rows = _query(dbh, """
        SELECT ts, open, high, low, close, volume, poc_vol
        FROM v9_bars_5min WHERE ts >= :t0 AND ts <= :t1 ORDER BY ts ASC""",
        {"t0": t0, "t1": t1})
    out, seen = [], set()
    for r in rows:
        ts = _norm_ts(r["ts"])
        if ts in seen:
            continue
        seen.add(ts)
        out.append(Bar(ts=ts, open=float(r["open"]), high=float(r["high"]),
                       low=float(r["low"]), close=float(r["close"]),
                       volume=float(r.get("volume") or 0),
                       poc_vol=(float(r["poc_vol"]) if r.get("poc_vol") is not None else None)))
    rth_rows = [b for b in out if b.ts >= rth0]
    if len(rth_rows) >= 30:
        return out, "v9_bars_5min"
    return [], "v9_bars_5min EMPTY/GAPPED (%d RTH rows) — fallback to woodies OHLCV" % len(rth_rows)


def load_cvd(dbh, date_str: str) -> List[Tuple[datetime, float]]:
    """v9_bars_cumulative_delta (ts is a STRING column — parse best-effort).
    Missing/unparseable => [] => the CVD gate passes (fail-open, mirrors
    five_min_system.py:591-613 returning None on any error)."""
    try:
        rows = _query(dbh, """
            SELECT ts, cumulative FROM v9_bars_cumulative_delta
            WHERE ts >= :d0 ORDER BY ts ASC""", {"d0": date_str})
    except Exception:
        return []
    out = []
    for r in rows:
        try:
            ts = _norm_ts(r["ts"])
            if r.get("cumulative") is None:
                continue
            out.append((ts, float(r["cumulative"])))
        except Exception:
            continue
    return out


def load_csv(path: str) -> List[Bar]:
    out = []
    with open(path) as fh:
        for r in _csv.DictReader(fh):
            out.append(Bar(
                ts=_norm_ts(r["ts"]), open=float(r["open"]), high=float(r["high"]),
                low=float(r["low"]), close=float(r["close"]),
                volume=float(r.get("volume") or 0),
                cci_14=float(r.get("cci_14") or 0), cci_6_tcci=float(r.get("cci_6_tcci") or 0),
                ema_34=float(r.get("ema_34") or 0), lsma_value=float(r.get("lsma_value") or 0),
                swi_value=float(r.get("swi_value") or 0), czi_value=float(r.get("czi_value") or 0),
                trend_state=(r.get("trend_state") or "GRAY").upper(),
                zlr_detected=int(r.get("zlr_detected") or 0),
                zlr_direction=r.get("zlr_direction") or "NONE",
                poc_vol=(float(r["poc_vol"]) if r.get("poc_vol") else None)))
    return out


# ────────────────────────────────────────────────────────────────────────────
# Criteria machinery
# ────────────────────────────────────────────────────────────────────────────
@dataclass
class Crit:
    name: str
    ok: bool
    detail: str          # "blue_bars=5 need>=6 (d=1 bar)"
    severity: float = 0  # normalized how-far-from-passing (0 == passed)


def C(name: str, ok: bool, detail: str, severity: float = 1.0) -> Crit:
    return Crit(name, ok, detail, 0.0 if ok else max(severity, 1e-6))


def _rth_index(bars: List[Bar], i: int, rth0_utc: datetime) -> int:
    """1-based index of bar i among the session's RTH bars (FHB counting)."""
    n = 0
    for j in range(0, i + 1):
        if bars[j].ts >= rth0_utc:
            n += 1
    return n


# ── S4: ZLR (zlr.py) ──
def _swi_color(v: float) -> str:  # zlr.py:46-53
    a = abs(v)
    if a >= 40:
        return "green"
    if a <= 20:
        return "red"
    return "yellow"


def eval_zlr(bars: List[Bar], i: int, direction: str, rx: Relax, fl: Flags) -> List[Crit]:
    """ZLR criteria vector at signal bar i. Mirrors zlr.py detect() + SPEC_V2.
    LONG shown; SHORT is the mirror."""
    crits: List[Crit] = []
    W = rx.zlr_extreme_window
    n = i + 1
    if n < W + 1:
        return [C("history", False, "only %d bars, need %d" % (n, W + 1))]
    cci = [b.cci_14 for b in bars[:n]]
    cur, prev = cci[-1], cci[-2]
    sgn = 1.0 if direction == "LONG" else -1.0

    # AP8 (anti_patterns.py:197-229): CCI range over last 3 bars >= 50
    rng3 = max(cci[-3:]) - min(cci[-3:])
    crits.append(C("AP8_cci_flat", rng3 >= 50.0,
                   "cci_range3=%.0f need>=50 (d=%.0f)" % (rng3, max(0, 50 - rng3)),
                   max(0, 50 - rng3) / 50))

    # AP1 (anti_patterns.py:44-82): bars since last |CCI|>=100 <= window
    since_any = None
    for j in range(n - 2, -1, -1):
        if abs(cci[j]) >= 100:
            since_any = n - 1 - j
            break
    if since_any is None:
        crits.append(C("AP1_pullback_len", False, "no |CCI|>=100 extreme in history"))
    else:
        crits.append(C("AP1_pullback_len", since_any <= W,
                       "bars_since_any_extreme=%d max=%d (d=%d)" % (since_any, W, max(0, since_any - W)),
                       max(0, since_any - W) / max(W, 1)))

    # Stage 1 (zlr.py:200-209 / 277-285): most recent trend-side extreme in window
    ext_idx = None
    for j in range(n - 2, max(n - W - 2, -1), -1):
        if sgn * cci[j] >= fl.zlr_cci_min:
            ext_idx = j
            break
    if ext_idx is None:
        # delta: how far back is the nearest qualifying extreme?
        far = None
        for j in range(n - 2, -1, -1):
            if sgn * cci[j] >= fl.zlr_cci_min:
                far = n - 1 - j
                break
        d = "none in history" if far is None else "extreme %d bars ago, window %d (d=%d)" % (far, W, far - W)
        crits.append(C("extreme_in_window", False, d,
                       1.0 if far is None else (far - W) / max(W, 1)))
        return crits
    bars_since = n - 1 - ext_idx
    crits.append(C("extreme_in_window", True,
                   "extreme %d bars ago (cci=%.0f), window %d" % (bars_since, cci[ext_idx], W)))

    # Stage 2: pullback bar strictly between extreme and current
    if direction == "LONG":
        pulled = any(-100 < cci[j] <= 100 for j in range(ext_idx + 1, n - 1))
    else:
        pulled = any(-100 <= cci[j] < 100 for j in range(ext_idx + 1, n - 1))
    crits.append(C("pullback_toward_zero", pulled,
                   "no bar with CCI in pullback band since extreme" if not pulled else "ok"))

    # Stage 3 base: bounce + band
    crits.append(C("bounce_dir", sgn * (cur - prev) > 0,
                   "cci %.0f->%.0f not %s" % (prev, cur, "rising" if direction == "LONG" else "falling"),
                   abs(cur - prev) / 100 if sgn * (cur - prev) <= 0 else 0))
    in_band = (0 < cur < 200) if direction == "LONG" else (-200 < cur < 0)
    crits.append(C("cci_band_0_200", in_band, "cci=%.0f need %s" %
                   (cur, "(0,200)" if direction == "LONG" else "(-200,0)")))

    if fl.zlr_spec_v2:
        # S1.1 (zlr.py:75-82): >= N trend-side bars since extreme (relabeled trend)
        tgt = "BLUE" if direction == "LONG" else "RED"
        blue_ct = sum(1 for j in range(ext_idx, n) if bars[j].trend_eff == tgt)
        need = rx.zlr_blue_bars
        crits.append(C("S1.1_blue_bars", blue_ct >= need,
                       "%s_bars=%d need>=%d (d=%d)" % (tgt.lower(), blue_ct, need, max(0, need - blue_ct)),
                       max(0, need - blue_ct) / max(need, 1)))
        # S1.3 (zlr.py:84-88): SWI yellow/green >= 1 bar in trend window
        swi_ok = any(_swi_color(bars[j].swi_value) in ("yellow", "green") for j in range(ext_idx, n))
        crits.append(C("S1.3_swi_window", swi_ok, "no SWI yellow/green bar since extreme" if not swi_ok else "ok"))
        # S1.4 (zlr.py:90-98): last 3 closes beyond EMA-34
        last3 = bars[n - 3:n]
        if direction == "LONG":
            ema_ok = all(b.close > b.ema_34 for b in last3 if b.ema_34 > 0)
        else:
            ema_ok = all(b.close < b.ema_34 for b in last3 if b.ema_34 > 0)
        bad = [round(abs(b.close - b.ema_34), 2) for b in last3
               if b.ema_34 > 0 and ((b.close <= b.ema_34) if direction == "LONG" else (b.close >= b.ema_34))]
        crits.append(C("S1.4_ema34_3bars", ema_ok,
                       "last3 not all %s EMA34 (worst %.2fpt wrong side)" %
                       ("above" if direction == "LONG" else "below", max(bad) if bad else 0),
                       (max(bad) / 2.0) if bad else 1.0))
        # S3.3 (zlr.py:102-105): |CCI diff| >= 15
        diff = abs(cur - prev)
        crits.append(C("S3.3_cci_diff15", diff >= 15,
                       "cci_diff=%.1f need>=15 (d=%.1f)" % (diff, max(0, 15 - diff)),
                       max(0, 15 - diff) / 15))
        # S3.7 (zlr.py:107-111): entry CCI <= 120
        over = sgn * cur - 120
        crits.append(C("S3.7_entry_le120", sgn * cur <= 120,
                       "entry cci=%.0f limit 120 (d=%.0f)" % (cur, max(0, over)), max(0, over) / 120))
        # S3.4/3.8 (zlr.py:113-118): SWI at entry not red
        esw = _swi_color(bars[i].swi_value)
        crits.append(C("S3.4_swi_entry", esw != "red",
                       "SWI red at entry (|swi|=%.0f<=20) — 2nd-bar rule" % abs(bars[i].swi_value)
                       if esw == "red" else "ok(%s)" % esw))
        # S3.5 (zlr.py:120-124): CZI with-direction all last 3 bars
        cz = sum(1 for b in last3 if (b.czi_value > 0 if direction == "LONG" else b.czi_value < 0))
        crits.append(C("S3.5_czi_3of3", cz >= 3, "czi_cyan=%d/3 (d=%d)" % (cz, 3 - cz), (3 - cz) / 3))
    return crits


# ── S4: GB100 (gb100.py) ──
def eval_gb100(bars: List[Bar], i: int, direction: str, rx: Relax, fl: Flags,
               rth_idx: int) -> List[Crit]:
    crits: List[Crit] = []
    if i < 2:
        return [C("history", False, "need 3 bars")]
    cci = [b.cci_14 for b in bars[:i + 1]]
    cur, prev, prev2 = cci[-1], cci[-2], cci[-3]
    trend = bars[i].trend_eff
    sgn = 1.0 if direction == "LONG" else -1.0
    lvl = 100.0 * sgn

    rng3 = max(cci[-3:]) - min(cci[-3:])
    crits.append(C("AP8_cci_flat", rng3 >= 50.0,
                   "cci_range3=%.0f need>=50 (d=%.0f)" % (rng3, max(0, 50 - rng3)),
                   max(0, 50 - rng3) / 50))
    # AP2 (anti_patterns.py:85-109): YELLOW blocked, always
    crits.append(C("AP2_not_yellow", trend != "YELLOW", "trend=YELLOW blocked"))
    # Trend requirement (gb100.py:91/147): BLUE (LONG) / RED (SHORT).
    need = "BLUE" if direction == "LONG" else "RED"
    t_ok = (trend == need)
    if not t_ok and rx.gb100_allow_gray_opening and trend in ("GRAY", "GREY") \
            and 1 <= rth_idx <= rx.opening_window_bars:
        t_ok = True
        crits.append(C("trend_established", True,
                       "GRAY allowed (opening window bar %d<=%d)" % (rth_idx, rx.opening_window_bars)))
    else:
        crits.append(C("trend_established", t_ok,
                       "trend=%s need %s" % (trend, need), 1.0))
    # AP6 (gb100.py:69-79 + anti_patterns.py:155-171): opposite-of-ZL streak <= 6
    opp = 0
    for j in range(i - 1, -1, -1):
        c = bars[j].cci_14
        if (direction == "LONG" and c < 0) or (direction == "SHORT" and c > 0):
            opp += 1
        else:
            break
    crits.append(C("AP6_pullback_depth", opp <= 6,
                   "opposite_ZL_bars=%d max 6 (d=%d)" % (opp, max(0, opp - 6)), max(0, opp - 6) / 6))
    # Fresh cross (gb100.py:91/147)
    crits.append(C("cross_now", sgn * cur > 100,
                   "cci=%.0f need %s100 (d=%.0f)" % (cur, ">" if direction == "LONG" else "<-",
                                                     max(0, 100 - sgn * cur)),
                   max(0, 100 - sgn * cur) / 100))
    crits.append(C("cross_fresh_prev", sgn * prev <= 100,
                   "prev cci=%.0f must be %s100 — cross not fresh (d=%.0f)" %
                   (prev, "<=" if direction == "LONG" else ">=-", max(0, sgn * prev - 100)),
                   max(0, sgn * prev - 100) / 100))
    crits.append(C("cross_fresh_prev2", sgn * prev2 < 100,
                   "prev2 cci=%.0f must be %s100" % (prev2, "<" if direction == "LONG" else ">-"),
                   max(0, sgn * prev2 - 100) / 100))
    return crits


# ── S4: TT (tt.py:80-145) ──
def eval_tt(bars: List[Bar], i: int, direction: str) -> List[Crit]:
    crits: List[Crit] = []
    if i < 2:
        return [C("history", False, "need 3 bars")]
    b, bp, bp2 = bars[i], bars[i - 1], bars[i - 2]
    cci = [x.cci_14 for x in bars[max(0, i - 2):i + 1]]
    rng3 = max(cci) - min(cci)
    crits.append(C("AP8_cci_flat", rng3 >= 50.0, "cci_range3=%.0f need>=50" % rng3,
                   max(0, 50 - rng3) / 50))
    gap = abs(b.cci_14 - b.cci_6_tcci)
    crits.append(C("AP7_tcci_gap", gap >= 5, "tcci_gap=%.1f need>=5 (d=%.1f)" % (gap, max(0, 5 - gap)),
                   max(0, 5 - gap) / 5))
    if direction == "LONG":
        crits.append(C("trend_blue_cci_pos", b.trend_eff == "BLUE" and b.cci_14 > 0,
                       "trend=%s cci=%.0f need BLUE & >0" % (b.trend_eff, b.cci_14)))
        crits.append(C("touched", bp.cci_6_tcci <= bp.cci_14 + 5,
                       "tcci_prev=%.0f vs cci_prev+5=%.0f" % (bp.cci_6_tcci, bp.cci_14 + 5)))
        crits.append(C("bounced", (b.cci_6_tcci > b.cci_14 + 5) and (b.cci_6_tcci > bp.cci_6_tcci),
                       "tcci=%.0f need > cci+5=%.0f and rising" % (b.cci_6_tcci, b.cci_14 + 5)))
        crits.append(C("was_above", bp2.cci_6_tcci > bp2.cci_14 + 10,
                       "tcci_prev2=%.0f need > cci_prev2+10=%.0f" % (bp2.cci_6_tcci, bp2.cci_14 + 10)))
    else:
        crits.append(C("trend_red_cci_neg", b.trend_eff == "RED" and b.cci_14 < 0,
                       "trend=%s cci=%.0f need RED & <0" % (b.trend_eff, b.cci_14)))
        crits.append(C("touched", bp.cci_6_tcci >= bp.cci_14 - 5,
                       "tcci_prev=%.0f vs cci_prev-5=%.0f" % (bp.cci_6_tcci, bp.cci_14 - 5)))
        crits.append(C("bounced", (b.cci_6_tcci < b.cci_14 - 5) and (b.cci_6_tcci < bp.cci_6_tcci),
                       "tcci=%.0f need < cci-5 and falling" % b.cci_6_tcci))
        crits.append(C("was_below", bp2.cci_6_tcci < bp2.cci_14 - 10,
                       "tcci_prev2=%.0f need < cci_prev2-10" % bp2.cci_6_tcci))
    return crits


# ── TLB (tlb.py) — trend-line break via CCI linear regression ──
def eval_tlb(bars: List[Bar], i: int, direction: str) -> List[Crit]:
    """TLB criteria: linreg slope over 10 bars, CCI deviation from predicted."""
    crits: List[Crit] = []
    W = 10
    if i < W:
        return [C("history", False, "need %d bars, have %d" % (W, i))]
    cci = [b.cci_14 for b in bars[i - W + 1:i + 1]]
    # AP8
    rng3 = max(cci[-3:]) - min(cci[-3:])
    crits.append(C("AP8_cci_flat", rng3 >= 50.0,
                   "cci_range3=%.0f need>=50" % rng3, max(0, 50 - rng3) / 50))
    # Linear regression slope
    n = len(cci)
    x_mean = (n - 1) / 2.0
    y_mean = sum(cci) / n
    num = sum((j - x_mean) * (cci[j] - y_mean) for j in range(n))
    den = sum((j - x_mean) ** 2 for j in range(n))
    slope = num / den if den != 0 else 0
    predicted = y_mean + slope * (n - 1 - x_mean)
    deviation = cci[-1] - predicted
    if direction == "LONG":
        crits.append(C("slope_down", slope < -2,
                       "slope=%.2f need < -2 (d=%.2f)" % (slope, max(0, slope + 2)),
                       max(0, slope + 2) / 2))
        crits.append(C("break_above", deviation > 10,
                       "deviation=%.1f need >10 (d=%.1f)" % (deviation, max(0, 10 - deviation)),
                       max(0, 10 - deviation) / 10))
        crits.append(C("cci_rising", cci[-1] > cci[-2],
                       "cur=%.0f prev=%.0f" % (cci[-1], cci[-2])))
    else:
        crits.append(C("slope_up", slope > 2,
                       "slope=%.2f need > 2 (d=%.2f)" % (slope, max(0, 2 - slope)),
                       max(0, 2 - slope) / 2))
        crits.append(C("break_below", deviation < -10,
                       "deviation=%.1f need <-10 (d=%.1f)" % (deviation, max(0, deviation + 10)),
                       max(0, deviation + 10) / 10))
        crits.append(C("cci_falling", cci[-1] < cci[-2],
                       "cur=%.0f prev=%.0f" % (cci[-1], cci[-2])))
    return crits


# ── HTLB (htlb.py) — horizontal S/R level break on CCI ──
def eval_htlb(bars: List[Bar], i: int, direction: str) -> List[Crit]:
    """HTLB criteria: horizontal CCI level (2+ touches), then break."""
    crits: List[Crit] = []
    W = 15
    if i < W:
        return [C("history", False, "need %d bars, have %d" % (W, i))]
    cci = [b.cci_14 for b in bars[i - W + 1:i + 1]]
    rng3 = max(cci[-3:]) - min(cci[-3:])
    crits.append(C("AP8_cci_flat", rng3 >= 50.0,
                   "cci_range3=%.0f need>=50" % rng3, max(0, 50 - rng3) / 50))
    # Find horizontal level: cluster of similar CCI values (tolerance 15)
    tol = 15
    if direction == "LONG":
        # Resistance: look for peaks
        peaks = [cci[j] for j in range(1, len(cci) - 1) if cci[j] >= cci[j - 1] and cci[j] >= cci[j + 1]]
        if len(peaks) < 2:
            crits.append(C("resistance_found", False, "only %d peaks, need 2+" % len(peaks)))
            return crits
        # Check if 2+ peaks within tolerance
        level_found = False
        level = 0.0
        for p in range(len(peaks)):
            cluster = [pk for pk in peaks if abs(pk - peaks[p]) <= tol]
            if len(cluster) >= 2:
                level = sum(cluster) / len(cluster)
                level_found = True
                break
        crits.append(C("resistance_found", level_found,
                       "level=%.0f" % level if level_found else "no cluster within %d tol" % tol))
        if level_found:
            crits.append(C("break_above", cci[-1] > level + 5 and cci[-2] <= level,
                           "cur=%.0f level+5=%.0f prev=%.0f" % (cci[-1], level + 5, cci[-2])))
    else:
        troughs = [cci[j] for j in range(1, len(cci) - 1) if cci[j] <= cci[j - 1] and cci[j] <= cci[j + 1]]
        if len(troughs) < 2:
            crits.append(C("support_found", False, "only %d troughs, need 2+" % len(troughs)))
            return crits
        level_found = False
        level = 0.0
        for p in range(len(troughs)):
            cluster = [tr for tr in troughs if abs(tr - troughs[p]) <= tol]
            if len(cluster) >= 2:
                level = sum(cluster) / len(cluster)
                level_found = True
                break
        crits.append(C("support_found", level_found,
                       "level=%.0f" % level if level_found else "no cluster within %d tol" % tol))
        if level_found:
            crits.append(C("break_below", cci[-1] < level - 5 and cci[-2] >= level,
                           "cur=%.0f level-5=%.0f prev=%.0f" % (cci[-1], level - 5, cci[-2])))
    return crits


# ── VEGAS (vegas.py) — cup-and-handle on CCI ──
def eval_vegas(bars: List[Bar], i: int, direction: str) -> List[Crit]:
    """VEGAS criteria: CCI touches ±200, recovers to ±100, shallow handle, break."""
    crits: List[Crit] = []
    W = 20
    if i < W:
        return [C("history", False, "need %d bars, have %d" % (W, i))]
    cci = [b.cci_14 for b in bars[i - W + 1:i + 1]]
    rng3 = max(cci[-3:]) - min(cci[-3:])
    crits.append(C("AP8_cci_flat", rng3 >= 50.0,
                   "cci_range3=%.0f need>=50" % rng3, max(0, 50 - rng3) / 50))
    if direction == "LONG":
        cup_found = any(c <= -200 for c in cci[:-3])
        crits.append(C("cup_bottom", cup_found,
                       "found CCI<=-200 in window" if cup_found else "no CCI<=-200"))
        rim_cross = any(cci[j] > -100 and cci[j - 1] <= -100 for j in range(1, len(cci) - 1))
        crits.append(C("rim_recovery", rim_cross,
                       "crossed -100 upward" if rim_cross else "no -100 recovery"))
        crits.append(C("handle_break", cci[-1] > -100 and cci[-2] <= -100,
                       "cur=%.0f prev=%.0f rim=-100" % (cci[-1], cci[-2])))
    else:
        cup_found = any(c >= 200 for c in cci[:-3])
        crits.append(C("cup_top", cup_found,
                       "found CCI>=200 in window" if cup_found else "no CCI>=200"))
        rim_cross = any(cci[j] < 100 and cci[j - 1] >= 100 for j in range(1, len(cci) - 1))
        crits.append(C("rim_recovery", rim_cross,
                       "crossed 100 downward" if rim_cross else "no 100 recovery"))
        crits.append(C("handle_break", cci[-1] < 100 and cci[-2] >= 100,
                       "cur=%.0f prev=%.0f rim=100" % (cci[-1], cci[-2])))
    return crits


# ── GHOST (ghost.py) — head-and-shoulders on CCI ──
def eval_ghost(bars: List[Bar], i: int, direction: str) -> List[Crit]:
    """GHOST criteria: 3-peak/trough H&S shape on CCI oscillator."""
    crits: List[Crit] = []
    W = 20
    if i < W:
        return [C("history", False, "need %d bars, have %d" % (W, i))]
    cci = [b.cci_14 for b in bars[i - W + 1:i + 1]]
    rng3 = max(cci[-3:]) - min(cci[-3:])
    crits.append(C("AP8_cci_flat", rng3 >= 50.0,
                   "cci_range3=%.0f need>=50" % rng3, max(0, 50 - rng3) / 50))
    if direction == "SHORT":
        # Bearish: 3 peaks, p2 > p1, p2 > p3, p3 < p1, cur < p3
        peaks = [(j, cci[j]) for j in range(1, len(cci) - 1)
                 if cci[j] > cci[j - 1] and cci[j] > cci[j + 1]]
        crits.append(C("3_peaks", len(peaks) >= 3,
                       "%d peaks found, need 3+" % len(peaks)))
        if len(peaks) >= 3:
            p1, p2, p3 = peaks[-3][1], peaks[-2][1], peaks[-1][1]
            crits.append(C("head_highest", p2 > p1 and p2 > p3,
                           "p1=%.0f p2=%.0f p3=%.0f" % (p1, p2, p3)))
            crits.append(C("right_lower", p3 < p1,
                           "p3=%.0f < p1=%.0f" % (p3, p1)))
            crits.append(C("break_neckline", cci[-1] < p3,
                           "cur=%.0f < p3=%.0f" % (cci[-1], p3)))
    else:
        # Bullish: 3 troughs, t2 < t1, t2 < t3, t3 > t1, cur > t3
        troughs = [(j, cci[j]) for j in range(1, len(cci) - 1)
                   if cci[j] < cci[j - 1] and cci[j] < cci[j + 1]]
        crits.append(C("3_troughs", len(troughs) >= 3,
                       "%d troughs found, need 3+" % len(troughs)))
        if len(troughs) >= 3:
            t1, t2, t3 = troughs[-3][1], troughs[-2][1], troughs[-1][1]
            crits.append(C("head_lowest", t2 < t1 and t2 < t3,
                           "t1=%.0f t2=%.0f t3=%.0f" % (t1, t2, t3)))
            crits.append(C("right_higher", t3 > t1,
                           "t3=%.0f > t1=%.0f" % (t3, t1)))
            crits.append(C("break_neckline", cci[-1] > t3,
                           "cur=%.0f > t3=%.0f" % (cci[-1], t3)))
    return crits


# ── FAMIR (famir.py) — failed attempt at ±200 ──
def eval_famir(bars: List[Bar], i: int, direction: str) -> List[Crit]:
    """FAMIR criteria: CCI reaches 170-210 zone then reverses 20+ pts."""
    crits: List[Crit] = []
    W = 5
    if i < W:
        return [C("history", False, "need %d bars, have %d" % (W, i))]
    cci = [b.cci_14 for b in bars[i - W + 1:i + 1]]
    rng3 = max(cci[-3:]) - min(cci[-3:])
    crits.append(C("AP8_cci_flat", rng3 >= 50.0,
                   "cci_range3=%.0f need>=50" % rng3, max(0, 50 - rng3) / 50))
    if direction == "SHORT":
        peak = max(cci)
        crits.append(C("zone_170_210", 170 <= peak < 210,
                       "peak=%.0f need [170,210)" % peak,
                       0 if 170 <= peak < 210 else min(abs(peak - 170), abs(peak - 210)) / 40))
        crits.append(C("reversal_20pt", cci[-1] < peak - 20,
                       "cur=%.0f < peak-20=%.0f" % (cci[-1], peak - 20)))
        crits.append(C("falling", cci[-1] < cci[-2],
                       "cur=%.0f < prev=%.0f" % (cci[-1], cci[-2])))
    else:
        trough = min(cci)
        crits.append(C("zone_170_210", -210 < trough <= -170,
                       "trough=%.0f need (-210,-170]" % trough,
                       0 if -210 < trough <= -170 else min(abs(trough + 170), abs(trough + 210)) / 40))
        crits.append(C("reversal_20pt", cci[-1] > trough + 20,
                       "cur=%.0f > trough+20=%.0f" % (cci[-1], trough + 20)))
        crits.append(C("rising", cci[-1] > cci[-2],
                       "cur=%.0f > prev=%.0f" % (cci[-1], cci[-2])))
    return crits


# ── S2 DBDT (double_bt.py) — double bottom/top on price ──
def eval_s2_dbdt(bars: List[Bar], i: int, direction: str) -> List[Crit]:
    """DBDT criteria: 2 symmetric swing lows/highs + neckline break."""
    crits: List[Crit] = []
    W = 30
    if i < W:
        return [C("history", False, "need %d bars, have %d" % (W, i))]
    window = bars[i - W + 1:i + 1]
    if direction == "LONG":
        # Double bottom: 2 swing lows at similar level, neckline break
        lows = [(j, window[j].low) for j in range(1, len(window) - 1)
                if window[j].low <= window[j - 1].low and window[j].low <= window[j + 1].low]
        crits.append(C("2_swing_lows", len(lows) >= 2,
                       "%d swing lows, need 2+" % len(lows)))
        if len(lows) >= 2:
            t1, t2 = lows[-2], lows[-1]
            sym = abs(t1[1] - t2[1]) <= max(t1[1], t2[1]) * 0.005 + 2.0
            crits.append(C("symmetric_lows", sym,
                           "t1=%.2f t2=%.2f diff=%.2f" % (t1[1], t2[1], abs(t1[1] - t2[1]))))
            nl_highs = [window[j].high for j in range(t1[0] + 1, t2[0]) if j < len(window)]
            if nl_highs:
                neckline = max(nl_highs)
                crits.append(C("neckline_break", window[-1].close > neckline + 0.25,
                               "close=%.2f > neckline+1T=%.2f" % (window[-1].close, neckline + 0.25)))
            else:
                crits.append(C("neckline_break", False, "no bars between troughs"))
    else:
        # Double top: 2 swing highs at similar level, neckline break
        highs = [(j, window[j].high) for j in range(1, len(window) - 1)
                 if window[j].high >= window[j - 1].high and window[j].high >= window[j + 1].high]
        crits.append(C("2_swing_highs", len(highs) >= 2,
                       "%d swing highs, need 2+" % len(highs)))
        if len(highs) >= 2:
            p1, p2 = highs[-2], highs[-1]
            sym = abs(p1[1] - p2[1]) <= max(p1[1], p2[1]) * 0.005 + 2.0
            crits.append(C("symmetric_highs", sym,
                           "p1=%.2f p2=%.2f diff=%.2f" % (p1[1], p2[1], abs(p1[1] - p2[1]))))
            nl_lows = [window[j].low for j in range(p1[0] + 1, p2[0]) if j < len(window)]
            if nl_lows:
                neckline = min(nl_lows)
                crits.append(C("neckline_break", window[-1].close < neckline - 0.25,
                               "close=%.2f < neckline-1T=%.2f" % (window[-1].close, neckline - 0.25)))
            else:
                crits.append(C("neckline_break", False, "no bars between peaks"))
    return crits


# ── S2 helpers (five_min_system.py) ──
def _wilder_atr(bars: List[Bar], i: int, period: int = 14) -> Optional[float]:
    lo = max(0, i - 19)
    win = bars[lo:i + 1]
    if len(win) < period:
        return None
    trs = []
    for k, b in enumerate(win):
        if k == 0:
            trs.append(b.high - b.low)
        else:
            pc = win[k - 1].close
            trs.append(max(b.high - b.low, abs(b.high - pc), abs(b.low - pc)))
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = ((atr * (period - 1)) + tr) / period
    return atr


def _vol_adaptive(bars: List[Bar], i: int, fl: Flags) -> bool:
    """five_min_system.py:72-85 — flag ON and avg 14-bar range >= 8.0pt."""
    if not fl.s2_vol_adaptive or i < 4:
        return False
    win = bars[max(0, i - 13):i + 1]
    avg = sum(b.high - b.low for b in win) / len(win)
    return avg >= 8.0


def _fhb_state(rth_idx: int, det_moment_et: dtime, rx: Relax, kind: str) -> Tuple[bool, str]:
    """FHB eligibility at detection moment (five_min_system.py:1102-1104,
    1186-1194; first_hour_buffer.py). Signal bar = rth_idx-th RTH bar; the
    detection push is the (rth_idx+1)-th bar => fhb_count = rth_idx+1.
    Gate applies only while mode == FIRST_HOUR_TACTICAL (before 10:30 ET)."""
    if det_moment_et >= DAY_TYPE_MODE_ET:
        return True, "DAY_TYPE_MODE (>=10:30 ET), FHB off"
    cnt = rth_idx + 1
    need = rx.fhb_reactive_min if kind == "REACTIVE" else rx.fhb_initiative_min
    return cnt >= need, "fhb_count=%d need>=%d (%s) (d=%d)" % (cnt, need, kind, max(0, need - cnt))


def _cvd_window(cvd: List[Tuple[datetime, float]], t0: datetime, t1: datetime) -> Optional[dict]:
    """five_min_system.py:580-613 — cumulative rows in [t0,t1]; <2 rows => None."""
    cums = [v for (ts, v) in cvd if t0 <= ts <= t1]
    if len(cums) < 2:
        return None
    perbar = [cums[k] - cums[k - 1] for k in range(1, len(cums))]
    return {"net_delta": cums[-1] - cums[0], "perbar": perbar, "cums": cums}


def eval_s2_reactive(bars: List[Bar], i: int, direction: str, rx: Relax, fl: Flags,
                     rth_idx: int, cvd: List[Tuple[datetime, float]]) -> List[Crit]:
    """REACTIVE B1-B4 (five_min_system.py:617-815). b4 = bars[i]."""
    crits: List[Crit] = []
    if i < 6:
        return [C("history", False, "need 7 bars (MIN_BARS_REQUIRED)")]
    b1, b2, b3, b4 = bars[i - 3], bars[i - 2], bars[i - 1], bars[i]
    b0v = bars[i - 4].volume if i >= 4 else 0
    sgn = 1.0 if direction == "LONG" else -1.0

    # B1 (line 687/752): opposite-side drive with volume
    if direction == "LONG":
        crits.append(C("B1_sellers", b1.close < b1.open and b1.volume > 0,
                       "b1 close-open=%+.2f need bearish (sellers)" % (b1.close - b1.open)))
    else:
        crits.append(C("B1_buyers", b1.close > b1.open and b1.volume > 0,
                       "b1 close-open=%+.2f need bullish (buyers)" % (b1.close - b1.open)))

    # B2 volume gate (lines 650-681): live = S2_VSA_VOLUME=1, variant UNION
    volbuf = [b.volume for b in bars[:i - 2] if b.volume > 0]
    ravg = (sum(volbuf[-20:]) / max(len(volbuf[-20:]), 1)) if volbuf else b1.volume
    vsa = (b2.volume < b1.volume and b2.volume < b0v and b2.volume <= 0.7 * ravg) if b1.volume > 0 else False
    rvol = (b2.volume <= 0.5 * ravg) if ravg > 0 else False
    atr5 = _wilder_atr(bars, i) or 2.0
    strict = vsa and ((b2.high - b2.low) < 0.7 * atr5)
    if fl.s2_vsa_volume:
        v = fl.s2_variant.upper()
        if v == "B_RVOL":
            vol_ok = rvol
        elif v == "C_STRICT":
            vol_ok = strict
        elif v == "UNION":
            vol_ok = vsa or rvol or strict
        elif v == "INTERSECTION":
            vol_ok = vsa and rvol and strict
        else:
            vol_ok = vsa
        det = ("b2_vol=%.0f b1=%.0f b0=%.0f avg20=%.0f · vsa(<b1,<b0,<=0.7avg=%.0f)=%s "
               "rvol(<=0.5avg=%.0f)=%s strict=%s [%s]" %
               (b2.volume, b1.volume, b0v, ravg, 0.7 * ravg, vsa, 0.5 * ravg, rvol, strict, v))
        sev = 0.0 if vol_ok else min(
            abs(b2.volume - 0.7 * ravg) / max(0.7 * ravg, 1),
            abs(b2.volume - 0.5 * ravg) / max(0.5 * ravg, 1))
        crits.append(C("B2_volume_drop", vol_ok, det, sev))
    else:
        ok = b2.volume <= b1.volume * 0.10 if b1.volume > 0 else False
        crits.append(C("B2_volume_drop", ok,
                       "b2_vol=%.0f need <=10%% of b1=%.0f" % (b2.volume, 0.1 * b1.volume)))

    # B3 (line 688/753)
    if direction == "LONG":
        crits.append(C("B3_buyers", b3.close > b3.open, "b3 close-open=%+.2f need bullish" % (b3.close - b3.open)))
    else:
        crits.append(C("B3_sellers", b3.close < b3.open, "b3 close-open=%+.2f need bearish" % (b3.close - b3.open)))
    # B4 direction (line 690/754)
    b4ok = (b4.close > b4.open) if direction == "LONG" else (b4.close < b4.open)
    crits.append(C("B4_confirm_dir", b4ok, "b4 close-open=%+.2f need %s" %
                   (b4.close - b4.open, "bullish" if direction == "LONG" else "bearish")))

    # B4 beyond B3 extreme (lines 88-95 + 693/756): live frac=1.0 (0.75 VOLATILE)
    va = _vol_adaptive(bars, i, fl)
    frac = rx.s2_confirm_frac if rx.s2_confirm_frac is not None else (0.75 if va else 1.0)
    rng = b3.high - b3.low
    if direction == "LONG":
        thr = b3.high - (1.0 - frac) * rng if rng > 0 else b3.high
        ok = b4.close > thr
        d = thr - b4.close
    else:
        thr = b3.low + (1.0 - frac) * rng if rng > 0 else b3.low
        ok = b4.close < thr
        d = b4.close - thr
    crits.append(C("B4_beyond_B3", ok,
                   "b4_close=%.2f need %s %.2f (frac=%.0f%%%s) (d=%.2fpt)" %
                   (b4.close, ">" if direction == "LONG" else "<", thr, frac * 100,
                    ", VOLATILE" if va else "", max(0.0, d)),
                   max(0.0, d) / 2.0))

    # FHB eligibility (detection = next bar open)
    det_et = (b4.ts + timedelta(minutes=5)).astimezone(ET).time()
    ok, det = _fhb_state(rth_idx, det_et, rx, "REACTIVE")
    crits.append(C("FHB_eligible", ok, det))

    # CVD absorption gate (lines 726-743/776-794) — fail-open on missing data
    if fl.s2_cvd:
        w = _cvd_window(cvd, b1.ts, b4.ts)
        if w is None:
            crits.append(C("CVD_gate", True, "no CVD data — fail-open pass"))
        else:
            pb = w["perbar"]
            if direction == "LONG":
                entry_ok = pb[-1] > 0 if pb else False
                div = (b3.low < b1.low) and (len(w["cums"]) >= 3 and w["cums"][-2] > w["cums"][0])
                ok = entry_ok or div
                crits.append(C("CVD_gate", ok,
                               "entry_delta=%+.0f div=%s need absorption" % (pb[-1] if pb else 0, div)))
            else:
                entry_ok = pb[-1] < 0 if pb else False
                net = w["net_delta"] < 0
                div = (b3.high > b1.high) and (len(w["cums"]) >= 3 and w["cums"][-2] < w["cums"][0])
                ok = entry_ok or net or div
                crits.append(C("CVD_gate", ok,
                               "entry_delta=%+.0f net=%+.0f div=%s need distribution" %
                               (pb[-1] if pb else 0, w["net_delta"], div)))
    # lookback_quiet + belly + COT/AMT: bypassed live (S2_VSA_VOLUME=1 /
    # S2_REQUIRE_COT_AMT=0 / belly None passes) — five_min_system.py:694-708.
    return crits


def eval_s2_initiative(bars: List[Bar], i: int, direction: str, rx: Relax, fl: Flags,
                       rth_idx: int, cvd: List[Tuple[datetime, float]]) -> List[Crit]:
    """INITIATIVE B1-B4 (five_min_system.py:817-934). b4 = bars[i]."""
    crits: List[Crit] = []
    if i < 6:
        return [C("history", False, "need 7 bars (MIN_BARS_REQUIRED)")]
    b1, b2, b3, b4 = bars[i - 3], bars[i - 2], bars[i - 1], bars[i]
    va = _vol_adaptive(bars, i, fl)

    # B1 direction (line 863/900)
    ok = (b1.close > b1.open) if direction == "LONG" else (b1.close < b1.open)
    crits.append(C("B1_drive_dir", ok, "b1 close-open=%+.2f need %s" %
                   (b1.close - b1.open, "bullish" if direction == "LONG" else "bearish")))

    # B1 expansion (lines 115-129, 852-858): [1.3x, 2.5x] avg14 range; VOLATILE floor cap 8.0
    win = bars[max(0, i - 13):i + 1]
    avg = sum(b.high - b.low for b in win) / len(win) if win else 3.0
    emin, emax = 1.3 * avg, 2.5 * avg
    if va:
        emin = min(emin, 8.0)
    r1 = b1.high - b1.low
    ok = emin <= r1 <= emax
    d = (emin - r1) if r1 < emin else (r1 - emax if r1 > emax else 0.0)
    crits.append(C("B1_expansion", ok,
                   "b1_range=%.2f need [%.2f, %.2f]%s (d=%.2fpt)" %
                   (r1, emin, emax, " VOLATILE-cap" if va else "", max(0.0, d)), max(0.0, d) / 2.0))

    # B2 test (lines 864-869/901-903): higher-low (LONG) / lower-high, or POC return
    poc_tol = 0.2 * avg  # lines 132-144
    poc_ret = b2.poc_vol is not None and abs(b2.close - b2.poc_vol) <= poc_tol
    if direction == "LONG":
        hl = b2.low > b1.low
        crits.append(C("B2_test", hl or poc_ret,
                       "b2_low=%.2f vs b1_low=%.2f (HL=%s) poc_ret=%s" % (b2.low, b1.low, hl, poc_ret)))
    else:
        lh = b2.high < b1.high
        crits.append(C("B2_test", lh or poc_ret,
                       "b2_high=%.2f vs b1_high=%.2f (LH=%s) poc_ret=%s" % (b2.high, b1.high, lh, poc_ret)))

    # B3 joining (lines 859-860): range > b1_range x (0.8 VOLATILE else 1.0)
    fac = 0.8 if va else 1.0
    r3 = b3.high - b3.low
    ok = r3 > r1 * fac
    crits.append(C("B3_joining", ok, "b3_range=%.2f need > %.2f (b1x%.1f) (d=%.2f)" %
                   (r3, r1 * fac, fac, max(0.0, r1 * fac - r3)), max(0.0, r1 * fac - r3) / 2.0))

    # B4 second test (line 870/904)
    if direction == "LONG":
        ok = b4.low >= b2.low
        crits.append(C("B4_test", ok, "b4_low=%.2f need >= b2_low=%.2f (d=%.2f)" %
                       (b4.low, b2.low, max(0.0, b2.low - b4.low))))
    else:
        ok = b4.high <= b2.high
        crits.append(C("B4_test", ok, "b4_high=%.2f need <= b2_high=%.2f (d=%.2f)" %
                       (b4.high, b2.high, max(0.0, b4.high - b2.high))))

    # B4 breakout close (line 873/905)
    if direction == "LONG":
        ok = b4.close > b1.high
        d = b1.high - b4.close
    else:
        ok = b4.close < b1.low
        d = b4.close - b1.low
    crits.append(C("B4_beyond_B1", ok, "b4_close=%.2f need %s b1 %s=%.2f (d=%.2fpt)" %
                   (b4.close, ">" if direction == "LONG" else "<",
                    "high" if direction == "LONG" else "low",
                    b1.high if direction == "LONG" else b1.low, max(0.0, d)), max(0.0, d) / 2.0))

    det_et = (b4.ts + timedelta(minutes=5)).astimezone(ET).time()
    ok, det = _fhb_state(rth_idx, det_et, rx, "INITIATIVE")
    crits.append(C("FHB_eligible", ok, det))

    if fl.s2_cvd:
        w = _cvd_window(cvd, b1.ts, b4.ts)
        if w is None:
            crits.append(C("CVD_gate", True, "no CVD data — fail-open pass"))
        else:
            if direction == "LONG":
                ok = not (w["net_delta"] < 0)
                crits.append(C("CVD_gate", ok, "net_delta=%+.0f need >=0 with-flow" % w["net_delta"]))
            else:
                ok = not (w["net_delta"] > 0)
                crits.append(C("CVD_gate", ok, "net_delta=%+.0f need <=0 with-flow" % w["net_delta"]))
    return crits


# ────────────────────────────────────────────────────────────────────────────
# Swings (zigzag on highs/lows)
# ────────────────────────────────────────────────────────────────────────────
@dataclass
class Swing:
    start_i: int
    end_i: int
    direction: str  # UP / DOWN
    start_px: float
    end_px: float

    @property
    def size(self) -> float:
        return abs(self.end_px - self.start_px)


def find_swings(bars: List[Bar], thr: float) -> List[Swing]:
    if len(bars) < 3:
        return []
    swings: List[Swing] = []
    direction = None
    ext_i, ext_hi, ext_lo = 0, bars[0].high, bars[0].low
    ext_hi_i, ext_lo_i = 0, 0
    piv_i, piv_px = 0, bars[0].close
    for j in range(1, len(bars)):
        b = bars[j]
        if direction is None:
            if b.high > ext_hi:
                ext_hi, ext_hi_i = b.high, j
            if b.low < ext_lo:
                ext_lo, ext_lo_i = b.low, j
            if b.high - ext_lo >= thr:
                direction, piv_i, piv_px = "UP", ext_lo_i, ext_lo
                ext_i, ext_hi = j, b.high
            elif ext_hi - b.low >= thr:
                direction, piv_i, piv_px = "DOWN", ext_hi_i, ext_hi
                ext_i, ext_lo = j, b.low
            continue
        if direction == "UP":
            if b.high >= ext_hi:
                ext_hi, ext_i = b.high, j
            elif ext_hi - b.low >= thr:
                swings.append(Swing(piv_i, ext_i, "UP", piv_px, ext_hi))
                direction, piv_i, piv_px = "DOWN", ext_i, ext_hi
                ext_i, ext_lo = j, b.low
        else:
            if b.low <= ext_lo:
                ext_lo, ext_i = b.low, j
            elif b.high - ext_lo >= thr:
                swings.append(Swing(piv_i, ext_i, "DOWN", piv_px, ext_lo))
                direction, piv_i, piv_px = "UP", ext_i, ext_lo
                ext_i, ext_hi = j, b.high
    if direction == "UP" and ext_hi - piv_px >= thr:
        swings.append(Swing(piv_i, ext_i, "UP", piv_px, ext_hi))
    elif direction == "DOWN" and piv_px - ext_lo >= thr:
        swings.append(Swing(piv_i, ext_i, "DOWN", piv_px, ext_lo))
    return swings


# ────────────────────────────────────────────────────────────────────────────
# Evaluation drivers
# ────────────────────────────────────────────────────────────────────────────
S4_PATTERNS = ["ZLR", "GB100", "TT", "TLB", "HTLB", "VEGAS", "GHOST", "FAMIR"]
S2_PATTERNS = ["S2_REACTIVE", "S2_INITIATIVE", "S2_DBDT"]


def eval_pattern(pat: str, w_bars: List[Bar], s2_bars: List[Bar], wi: Optional[int],
                 si: Optional[int], direction: str, rx: Relax, fl: Flags,
                 rth0: datetime, cvd) -> Optional[List[Crit]]:
    if pat in S4_PATTERNS:
        if wi is None:
            return None
        rth_idx = _rth_index(w_bars, wi, rth0)
        if pat == "ZLR":
            return eval_zlr(w_bars, wi, direction, rx, fl)
        if pat == "GB100":
            return eval_gb100(w_bars, wi, direction, rx, fl, rth_idx)
        if pat == "TT":
            return eval_tt(w_bars, wi, direction)
        if pat == "TLB":
            return eval_tlb(w_bars, wi, direction)
        if pat == "HTLB":
            return eval_htlb(w_bars, wi, direction)
        if pat == "VEGAS":
            return eval_vegas(w_bars, wi, direction)
        if pat == "GHOST":
            return eval_ghost(w_bars, wi, direction)
        if pat == "FAMIR":
            return eval_famir(w_bars, wi, direction)
    else:
        if si is None:
            return None
        rth_idx = _rth_index(s2_bars, si, rth0)
        if pat == "S2_REACTIVE":
            return eval_s2_reactive(s2_bars, si, direction, rx, fl, rth_idx, cvd)
        if pat == "S2_INITIATIVE":
            return eval_s2_initiative(s2_bars, si, direction, rx, fl, rth_idx, cvd)
        if pat == "S2_DBDT":
            return eval_s2_dbdt(s2_bars, si, direction)
    return None


def _ts_index(bars: List[Bar]) -> Dict[datetime, int]:
    return {b.ts: k for k, b in enumerate(bars)}


@dataclass
class SwingVerdict:
    swing: Swing
    catchable: List[str] = field(default_factory=list)       # patterns fully passing
    catch_ts: Dict[str, str] = field(default_factory=dict)
    near: Dict[str, Tuple[int, str]] = field(default_factory=dict)  # pat -> (nfail, "crit detail @ts")
    trend_mix: str = ""


def analyze_swings(w_bars, s2_bars, swings, rx: Relax, fl: Flags, rth0, cvd,
                   min_swing: float) -> List[SwingVerdict]:
    s2_by_ts = _ts_index(s2_bars)
    out = []
    for s in swings:
        if s.size < min_swing:
            continue
        v = SwingVerdict(swing=s)
        # Evaluation window = first third of the swing's RTH bars (live detection
        # is RTH-gated, woodies_system.py:406-414; a gap-day swing may anchor
        # pre-open, so the window is taken over the tradeable portion).
        rth_span = [j for j in range(s.start_i, min(s.end_i, len(w_bars) - 1) + 1)
                    if w_bars[j].ts >= rth0]
        if not rth_span:
            v.trend_mix = "(entirely pre-RTH)"
            out.append(v)
            continue
        window = rth_span[:max(1, len(rth_span) // 3) + 1]
        mix: Dict[str, int] = {}
        for j in window:
            t = w_bars[j].trend_eff
            mix[t] = mix.get(t, 0) + 1
        v.trend_mix = " ".join("%s×%d" % (k, n) for k, n in sorted(mix.items(), key=lambda x: -x[1]))
        want = "LONG" if s.direction == "UP" else "SHORT"
        for pat in S4_PATTERNS + S2_PATTERNS:
            best: Optional[Tuple[int, float, str]] = None
            for j in window:
                si = s2_by_ts.get(w_bars[j].ts)
                crits = eval_pattern(pat, w_bars, s2_bars, j, si, want, rx, fl, rth0, cvd)
                if crits is None:
                    continue
                fails = [c for c in crits if not c.ok]
                sev = sum(c.severity for c in fails)
                if not fails:
                    v.catchable.append(pat)
                    v.catch_ts[pat] = w_bars[j].hhmm_il()
                    best = (0, 0.0, "PASS @%s" % w_bars[j].hhmm_il())
                    break
                # rank the most fixable bar: fewest fails, then lowest severity
                key_fail = min(fails, key=lambda c: c.severity)
                desc = "; ".join("%s: %s" % (c.name, c.detail) for c in
                                 sorted(fails, key=lambda c: c.severity)[:2])
                if len(fails) > 2:
                    desc += " (+%d more)" % (len(fails) - 2)
                cand = (len(fails), sev, "%s @%s" % (desc, w_bars[j].hhmm_il()))
                if best is None or (cand[0], cand[1]) < (best[0], best[1]):
                    best = cand
            if best is not None and best[0] > 0:
                v.near[pat] = (best[0], best[2])
        out.append(v)
    return out


# ── whole-session fire scan (for false-fire accounting) ──
def scan_fires(w_bars, s2_bars, rx: Relax, fl: Flags, rth0, cvd) -> List[Tuple[str, str, int, datetime]]:
    """All detector-level fires across RTH under config rx. Dedup: 6-bar
    cooldown per pattern+direction (matches replay_day.py distinct)."""
    fires = []
    last: Dict[str, int] = {}
    s2_by_ts = _ts_index(s2_bars)
    for j, b in enumerate(w_bars):
        if b.ts < rth0:
            continue
        si = s2_by_ts.get(b.ts)
        for pat in S4_PATTERNS + S2_PATTERNS:
            for want in ("LONG", "SHORT"):
                crits = eval_pattern(pat, w_bars, s2_bars, j, si, want, rx, fl, rth0, cvd)
                if crits is None or any(not c.ok for c in crits):
                    continue
                key = "%s_%s" % (pat, want)
                if key in last and (j - last[key]) < 6:
                    continue
                last[key] = j
                fires.append((pat, want, j, b.ts))
    return fires


def classify_fire(w_bars, j: int, direction: str, false_pt: float, window: int) -> Tuple[bool, float]:
    """TRUE fire if a >= false_pt favorable move follows within `window` bars."""
    entry = w_bars[j].close
    hi = -1e9
    lo = 1e9
    for k in range(j + 1, min(len(w_bars), j + 1 + window)):
        hi = max(hi, w_bars[k].high)
        lo = min(lo, w_bars[k].low)
    if hi == -1e9:
        return (False, 0.0)
    fav = (hi - entry) if direction == "LONG" else (entry - lo)
    return (fav >= false_pt, fav)


# ────────────────────────────────────────────────────────────────────────────
# Reporting
# ────────────────────────────────────────────────────────────────────────────
def fmt_swing(s: Swing, bars: List[Bar]) -> str:
    return "%s→%s %s %+.1fpt (%.2f→%.2f, %d bars)" % (
        bars[s.start_i].hhmm_il(), bars[s.end_i].hhmm_il(), s.direction,
        (s.end_px - s.start_px), s.start_px, s.end_px, s.end_i - s.start_i)


def run_audit(w_bars, s2_bars, cvd, date_str, rth0, args, fl: Flags) -> str:
    L: List[str] = []
    L.append("# Pattern-miss audit — %s" % date_str)
    L.append("")
    L.append("Bars: woodies=%d (RTH %d) · s2=%d · cvd_rows=%d · times shown in IL (IDT)"
             % (len(w_bars), sum(1 for b in w_bars if b.ts >= rth0), len(s2_bars), len(cvd)))
    L.append("Live-flag model: ZLR_SPEC_V2=%s VSA=%s(%s) VOL_ADAPTIVE=%s CVD=%s RELABEL=%s"
             % (fl.zlr_spec_v2, fl.s2_vsa_volume, fl.s2_variant, fl.s2_vol_adaptive,
                fl.s2_cvd, fl.s4_extreme_relabel))
    L.append("")

    swings = find_swings(w_bars, args.swing_pt)
    big = [s for s in swings if s.size >= args.swing_pt and w_bars[s.end_i].ts >= rth0]
    L.append("## Swings >= %.0fpt (RTH)" % args.swing_pt)
    if not big:
        L.append("(none)")
    base_rx = Relax()
    verdicts = analyze_swings(w_bars, s2_bars, big, base_rx, fl, rth0, cvd, args.swing_pt)

    L.append("")
    L.append("| swing | trend mix (1st third) | catchable-by (BASE) | best near-miss: blocking-criterion → delta |")
    L.append("|---|---|---|---|")
    for v in verdicts:
        catch = ", ".join("%s@%s" % (p, v.catch_ts[p]) for p in v.catchable) or "—"
        if v.near:
            near = "; ".join("**%s** (%d fail): %s" % (p, nf, d) for p, (nf, d) in
                             sorted(v.near.items(), key=lambda kv: kv[1][0])[:3])
        else:
            near = "—"
        L.append("| %s | %s | %s | %s |" % (fmt_swing(v.swing, w_bars), v.trend_mix, catch, near))
    L.append("")

    # base fires (for divergence + false-fire baseline)
    base_fires = scan_fires(w_bars, s2_bars, base_rx, fl, rth0, cvd)
    L.append("## BASE detector-level fires (this evaluator, live-flag model)")
    if base_fires:
        for pat, d, j, ts in base_fires:
            t_ok, fav = classify_fire(w_bars, j, d, args.false_pt, args.false_window)
            L.append("- %s %s @%s close=%.2f → fav_move=%.1fpt in %d bars → %s"
                     % (pat, d, w_bars[j].hhmm_il(), w_bars[j].close, fav, args.false_window,
                        "TRUE" if t_ok else "FALSE"))
        L.append("")
        L.append("> If the live decisions feed showed 0 fires while BASE fires exist above, the")
        L.append("> loss is DOWNSTREAM of detection (dispatcher/sizing/gateway) — check the log at that ts.")
    else:
        L.append("(none — detectors were structurally unable to fire under live criteria)")
    L.append("")

    # DLL cross-check
    dll = [(b.hhmm_il(), "ZLR", b.zlr_direction) for b in w_bars if b.zlr_detected and b.ts >= rth0]
    dll += [(b.hhmm_il(), "HFE", b.hfe_direction) for b in w_bars if b.hfe_detected and b.ts >= rth0]
    L.append("## DLL flag cross-check (v9_bars_5min_woodies)")
    if dll:
        for t, p, d in sorted(dll):
            L.append("- %s DLL %s=%s — the DLL-fallback path (woodies_system.py:491-524) fires even when"
                     " the Python detector rejects; if nothing routed at this ts, check backend log for"
                     " Mechanism-C dedup / sizing-reject / HTLB latch / P-W5 YELLOW." % (t, p, d))
    else:
        L.append("(no DLL zlr/hfe flags in session)")
    L.append("")

    # relax runs
    if args.relax:
        names = list(RELAXATIONS.keys()) if args.relax == "all" else [
            x.strip() for x in args.relax.split(",") if x.strip()]
        bad = [x for x in names if x not in RELAXATIONS]
        if bad:
            L.append("UNKNOWN relaxations: %s (valid: %s)" % (bad, ", ".join(RELAXATIONS)))
            names = [x for x in names if x in RELAXATIONS]
        base_keys = {(p, d, w_bars[j].ts) for p, d, j, ts in base_fires}
        base_caught = {tuple(v.catchable) for v in verdicts}
        runs = [(nm, Relax(label=nm, **RELAXATIONS[nm][1])) for nm in names]
        if len(names) > 1:
            merged: dict = {}
            for nm in names:
                merged.update(RELAXATIONS[nm][1])
            runs.append(("ALL(%s)" % "+".join(names), Relax(label="ALL", **merged)))
        L.append("## Relaxation runs (each vs BASE)")
        for nm, rx in runs:
            desc = RELAXATIONS.get(nm, (nm, {}))[0]
            L.append("")
            L.append("### %s — %s" % (nm, desc))
            vr = analyze_swings(w_bars, s2_bars, big, rx, fl, rth0, cvd, args.swing_pt)
            newly = []
            for v0, v1 in zip(verdicts, vr):
                gained = [p for p in v1.catchable if p not in v0.catchable]
                if gained:
                    newly.append("%s ← %s" % (fmt_swing(v1.swing, w_bars),
                                              ", ".join("%s@%s" % (p, v1.catch_ts[p]) for p in gained)))
            L.append("Swings newly caught: %s" % ("; ".join(newly) if newly else "NONE"))
            fires = scan_fires(w_bars, s2_bars, rx, fl, rth0, cvd)
            added = [(p, d, j, ts) for (p, d, j, ts) in fires if (p, d, ts) not in base_keys]
            n_true = n_false = 0
            det_lines = []
            for p, d, j, ts in added:
                ok, fav = classify_fire(w_bars, j, d, args.false_pt, args.false_window)
                if ok:
                    n_true += 1
                else:
                    n_false += 1
                det_lines.append("  - %s %s @%s fav=%.1fpt → %s"
                                 % (p, d, w_bars[j].hhmm_il(), fav, "true" if ok else "FALSE"))
            L.append("Added fires vs BASE: %d (true=%d, FALSE=%d; false = no >=%.0fpt favorable within %d bars)"
                     % (len(added), n_true, n_false, args.false_pt, args.false_window))
            L.extend(det_lines)
    L.append("")
    L.append("_Detector-level only; post-detection gates (dispatcher, HTLB latch, YELLOW lock,"
             " sizing, gateway) not modeled — see script docstring._")
    return "\n".join(L)


# ────────────────────────────────────────────────────────────────────────────
# Self-test (synthetic day, no DB) — validates mechanics, not market truth
# ────────────────────────────────────────────────────────────────────────────
def _mk(ts, o, h, l, c, v=1000, cci=0.0, tcci=0.0, ema=0.0, swi=30.0, czi=1.0,
        trend="GRAY", zlr=0, zdir="NONE") -> Bar:
    return Bar(ts=ts, open=o, high=h, low=l, close=c, volume=v, cci_14=cci,
               cci_6_tcci=tcci, ema_34=ema, lsma_value=0.0, swi_value=swi,
               czi_value=czi, trend_state=trend, zlr_detected=zlr, zlr_direction=zdir)


def selftest() -> int:
    """Synthetic ORR-style day exercising every code path:
      - gap-down open, +60pt rally with trend GRAY (GB100 fresh cross at RTH
        bar 3 → gb100_gray_open must NEWLY CATCH the up-swing),
      - a chop segment crafted so s2_b4_confirm_75 ADDS a REACTIVE SHORT fire
        with <8pt follow-through (must be classified FALSE),
      - a -26pt fade with GRAY trend (near-misses only).
    Mechanics validation ONLY — market truth needs the Mac DB run."""
    day = datetime(2026, 7, 17, 9, 30, tzinfo=ET)
    bars: List[Bar] = []
    ts = day - timedelta(hours=2)
    px = 7480.0
    # warmup: flat drift, steady volume 1000
    for k in range(24):
        bars.append(_mk(ts.astimezone(timezone.utc), px + 0.5, px + 1.5, px - 1.5, px - 0.5,
                        v=1000, cci=-40 - (k % 5) * 10, tcci=-30, ema=px + 4, trend="GRAY"))
        px -= 0.25
        ts += timedelta(minutes=5)
    ts = day
    px = 7473.0
    # rally: 11 bars, ~+60pt, trend GRAY; CCI 40→85→130 = fresh +100 cross at
    # RTH bar 3 (inside opening window AND the swing's first third), then on up
    for k, cci in enumerate([40, 85, 130, 160, 175, 185, 190, 185, 180, 175, 170]):
        o = px
        c = px + 5.5
        bars.append(_mk(ts.astimezone(timezone.utc), o, c + 1.0, o - 1.0, c, v=2000 + 100 * k,
                        cci=cci, tcci=cci + 12, ema=px - 6, trend="GRAY"))
        px = c
        ts += timedelta(minutes=5)
    # plateau 4 bars (trend flips BLUE late — mirrors the ~6-bar Sierra lag)
    for k in range(4):
        bars.append(_mk(ts.astimezone(timezone.utc), px, px + 2, px - 2, px + 0.5,
                        v=1500, cci=150 - 10 * k, tcci=150, ema=px - 10, trend="BLUE"))
        ts += timedelta(minutes=5)
    # fade: 6 bars down ~-26pt, trend GRAY again
    for k in range(6):
        o = px
        c = px - 4.4
        bars.append(_mk(ts.astimezone(timezone.utc), o, o + 1, c - 1.5, c, v=1800,
                        cci=60 - 40 * k, tcci=40 - 40 * k, ema=px + 6, trend="GRAY"))
        px = c
        ts += timedelta(minutes=5)
    # chop with a crafted near-miss REACTIVE SHORT: b1 bullish high-vol,
    # b2 quiet (VSA pass), b3 bearish (range 4.5), b4 bearish closing past the
    # 75% line (b3.low + 0.25*rng = px+0.125) but NOT past 100% (b3.low=px-1.0)
    # → fires ONLY under s2_b4_confirm_75; follow-through <8pt → FALSE fire.
    chop = [
        (px, px + 4.0, px - 0.5, px + 3.5, 3000, 120),        # b1 buyers, hi vol
        (px + 3.5, px + 4.0, px + 2.5, px + 3.0, 600, 60),    # b2 quiet
        (px + 3.0, px + 3.5, px - 1.0, px - 0.5, 1400, -20),  # b3 sellers
        (px + 0.4, px + 0.6, px - 0.6, px + 0.0, 1500, -80),  # b4 bearish, close=px
    ]
    for (o, h, l, c, v, cci) in chop:
        bars.append(_mk(ts.astimezone(timezone.utc), o, h, l, c, v=v, cci=cci,
                        tcci=cci - 10, ema=px + 2, trend="GRAY"))
        ts += timedelta(minutes=5)
    # aftermath: sideways (< 8pt down-follow-through)
    for k in range(8):
        bars.append(_mk(ts.astimezone(timezone.utc), px, px + 1.5, px - 1.5, px + 0.3,
                        v=1000, cci=10 - (k % 3) * 30, tcci=0, ema=px, trend="GRAY"))
        ts += timedelta(minutes=5)
    # drift to close
    while ts.astimezone(ET).time() < dtime(16, 0):
        bars.append(_mk(ts.astimezone(timezone.utc), px, px + 1.0, px - 1.0, px + 0.1,
                        v=900, cci=15 - (len(bars) % 4) * 20, tcci=5, ema=px, trend="GRAY"))
        ts += timedelta(minutes=5)

    fl = Flags()
    _apply_relabel(bars, fl)
    rth0 = day.astimezone(timezone.utc)

    class A:
        swing_pt = 15.0
        false_pt = 8.0
        false_window = 6
        relax = "all"
    rep = run_audit(bars, bars, [], "SELFTEST", rth0, A, fl)
    print(rep)

    # invariants — each proves a code path end-to-end
    sw = find_swings(bars, 15.0)
    assert any(s.direction == "UP" and s.size >= 50 for s in sw), "rally swing not found"
    assert any(s.direction == "DOWN" and s.size >= 20 for s in sw), "fade swing not found"
    assert "trend_established" in rep, "GB100 trend criterion not evaluated"
    gb_sec = rep.split("### gb100_gray_open")[1].split("###")[0]
    assert "GB100@" in gb_sec, \
        "gb100_gray_open did not newly-catch the rally (relax-catch path broken)"
    b475 = rep.split("### s2_b4_confirm_75")[1].split("###")[0]
    added_line = b475.split("Added fires vs BASE:")[1][:40]
    assert "FALSE=0" not in added_line, \
        "s2_b4_confirm_75 did not add a FALSE fire (false-fire path broken)"
    print("\nSELFTEST PASS — swings=%d; gb100_gray_open newly-catches; "
          "s2_b4_confirm_75 adds a FALSE fire (mechanics verified; market truth "
          "needs the Mac DB run)" % len(sw))
    return 0


# ────────────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--date", help="ET session date YYYY-MM-DD")
    ap.add_argument("--relax", help="comma list of relaxations, or 'all' (%s)" % ", ".join(RELAXATIONS))
    ap.add_argument("--swing-pt", type=float, default=15.0, dest="swing_pt")
    ap.add_argument("--false-pt", type=float, default=8.0, dest="false_pt",
                    help="favorable points required within --false-window bars for a TRUE fire")
    ap.add_argument("--false-window", type=int, default=6, dest="false_window")
    ap.add_argument("--csv", help="offline woodies bars CSV instead of DB")
    ap.add_argument("--out", help="write report to this path (default: print)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.date:
        ap.error("--date required (or --selftest)")

    fl = Flags.from_env()
    d = datetime.strptime(args.date, "%Y-%m-%d").date()
    rth0 = datetime.combine(d, RTH_START, tzinfo=ET).astimezone(timezone.utc)

    if args.csv:
        w_bars = load_csv(args.csv)
        s2_bars, s2_src, cvd = w_bars, "csv (same as woodies)", []
    else:
        dbh = _connect()
        try:
            w_bars = load_woodies(dbh, args.date)
        except Exception as e:
            print("ERROR: DB query failed (%s: %s)\nDATABASE_URL=%s — run on the trading "
                  "Mac against local Postgres, or use --csv / --selftest."
                  % (type(e).__name__, e, os.environ.get("DATABASE_URL",
                     "postgresql://localhost/mems26")), file=sys.stderr)
            return 1
        if not w_bars:
            print("ERROR: no v9_bars_5min_woodies rows for %s — Rule 2: verify the table/date "
                  "before trusting any conclusion." % args.date, file=sys.stderr)
            return 1
        s2_bars, s2_src = load_s2(dbh, args.date)
        if not s2_bars:
            s2_bars = w_bars  # honest fallback, poc_vol=None (B2_test POC-alt disabled)
        cvd = load_cvd(dbh, args.date)
    _apply_relabel(w_bars, fl)

    rep = run_audit(w_bars, s2_bars, cvd, args.date, rth0, args, fl)
    if not args.csv:
        rep += "\nS2 bar source: %s\n" % s2_src
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(rep + "\n")
        print("written: %s" % args.out)
    else:
        print(rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
