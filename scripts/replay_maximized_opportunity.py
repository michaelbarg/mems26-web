#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Counterfactual opportunity replay from candles + volume, never actual fires.

Michael (2026-08-23): measure what MEMS26 would have fired in a maximization
mode from the historical market, not what happened to survive the live chain.

The harness reuses, rather than rebuilds:
  * current S2/S4/opening detector functions (good_pattern_fix/dead_pattern_replay)
  * the causal seven-type classifier + S1_STRUCTURAL_BINARY_V1 wrapper
  * oracle_study's uniform MEMS ladder and cost model
  * causal TPO snapshots, 5-minute candles/volume, and migrated CVD rows

Arms:
  CURRENT_ALL   every currently-live detector candidate; shadow-only producers
                (TREND_STEP, S2_DELTA_DBL) are measured but do not take a slot
  MAX_CONTEXT   CURRENT_ALL selected by binary BALANCE/DISCOVERY context:
                edge-confirmed REV in BALANCE; with-direction CONT/REACTIVE in
                DISCOVERY; unlimited sequential rotations, one open slot
  MAX_EXPANDED  MAX_CONTEXT plus the known detector repairs (DT_AA Adam
                tolerance + 32-bar buffer).  Research only.
  MAX_2SLOT     sensitivity only; proves whether "more trades" increases risk

Coverage is measured against a bar-derived opportunity universe:
  REV  = causal developing-VA rejection / failed-IB extension / delta absorption
  CONT = causal BREAK / STAIR / PB triggers from oracle_study.find_triggers

READ-ONLY against Postgres.  Writes stdout + --json only.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import importlib.util
import json
import os
import statistics
import sys
from bisect import bisect_right
from zoneinfo import ZoneInfo

import psycopg2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load_module(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, relpath))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GPF = _load_module("max_gpf", "scripts/good_pattern_fix.py")
DPR = _load_module("max_dpr", "scripts/dead_pattern_replay.py")
EDA = _load_module("max_eda", "scripts/extreme_detection_audit.py")
ORA = GPF.ORA
ESR = GPF.ESR

from backend.v9.config_loader import load_s2_reactive_calibration  # noqa: E402
from backend.v9.systems.day_type.classifier_core import classify_session  # noqa: E402
from backend.v9.systems.day_type.structural_binary_v1 import (  # noqa: E402
    StructuralBinaryClassifier,
)
from backend.v9.systems.five_min import five_min_system as FMS  # noqa: E402
from backend.v9.systems.woodies.schemas import WoodiesBar  # noqa: E402
import backend.v9.services.trade_context as TC  # noqa: E402

GPF.FMS = FMS
GPF.CAL = load_s2_reactive_calibration

DSN = os.environ.get("MEMS26_DSN", "postgresql://localhost/mems26")
ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
IB_BARS = 12
MATCH_BARS = 3
IS0, IS1 = dt.date(2026, 7, 15), dt.date(2026, 8, 12)

REV_KINDS = {
    "REACTIVE", "DOUBLE_BOTTOM_EE", "DOUBLE_TOP_AA",
    "INVERSE_HNS", "HNS_TOP", "GHOST", "HTLB",
}
CONT_KINDS = {
    "INITIATIVE", "ZLR", "GB100", "TLB", "TT",
    "BULL_FLAG", "BEAR_FLAG", "TREND_STEP",
}
NONTRADE_LABELS = {"UNKNOWN", "NOT_YET", "FORMING", "Nontrend", "Nonconviction"}


def _aware_utc(et_naive: dt.datetime) -> dt.datetime:
    if et_naive.tzinfo is None:
        et_naive = et_naive.replace(tzinfo=ET)
    return et_naive.astimezone(UTC)


def _med(values):
    return round(statistics.median(values), 2) if values else 0.0


def _norm_dir(value):
    s = str(value or "").upper()
    if "DOWN" in s or s == "SHORT":
        return -1
    if "UP" in s or s == "LONG":
        return 1
    return 0


def _dedup(candidates):
    """Deduplicate exact detector identity, preserving the earliest row."""
    out, seen = [], set()
    for c in sorted(candidates, key=lambda x: (x["i"], x["kind"], x["dir"])):
        key = (c["i"], c["kind"], c["dir"])
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def load_data(cur):
    days = ESR.load_bars(cur)
    session_dates = ESR.live_days(days)

    cur.execute(
        """
        select (ts at time zone 'America/New_York') as et,
               open, high, low, close, coalesce(volume,0),
               coalesce(cci_14,0), coalesce(cci_6_tcci,0),
               coalesce(ema_34,0), coalesce(lsma_value,0),
               coalesce(swi_value,0), coalesce(czi_value,0),
               coalesce(trend_state,'GRAY'), coalesce(lsma_above_price,0)
        from v9_bars_5min_woodies
        where (ts at time zone 'America/New_York')::date between %s and %s
          and (ts at time zone 'America/New_York')::time >= %s
          and (ts at time zone 'America/New_York')::time < %s
        order by ts
        """,
        (ESR.WARM, GPF.D1, ESR.RTH0, ESR.RTH1),
    )
    woodies = collections.OrderedDict()
    for et, o, h, l, c, v, c14, c6, e34, lsma, swi, czi, trend, above in cur.fetchall():
        woodies.setdefault(et.date(), []).append(
            WoodiesBar(
                ts=_aware_utc(et).timestamp(),
                open=float(o), high=float(h), low=float(l), close=float(c),
                volume=float(v), cci_14=float(c14), cci_6_tcci=float(c6),
                ema_34=float(e34), lsma_value=float(lsma),
                swi_value=float(swi), czi_value=float(czi),
                trend_state=trend, lsma_above_price=bool(above),
            )
        )

    cvd = GPF.load_cvd(cur)

    cur.execute(
        """
        select (ts at time zone 'America/New_York') as et, poc, vah, val
        from v9_tpo_history
        where (ts at time zone 'America/New_York')::date between %s and %s
        order by ts
        """,
        (GPF.D0, GPF.D1),
    )
    tpo = collections.defaultdict(list)
    for et, poc, vah, val in cur.fetchall():
        tpo[et.date()].append(
            (et,
             float(poc) if poc is not None else None,
             float(vah) if vah is not None else None,
             float(val) if val is not None else None)
        )
    return days, session_dates, woodies, cvd, tpo


def causal_context(days, day, bars):
    """Return event-held S1 label plus BALANCE/DISCOVERY phase per bar."""
    keys = sorted(k for k in days if k < day)
    prev = days[keys[-1]] if keys else None
    pdh = max(b["h"] for b in prev) if prev else None
    pdl = min(b["l"] for b in prev) if prev else None
    pvah = pval = None
    if prev:
        pvah, pval, _ = ESR.value_area(prev)

    ib_hist = []
    for old_day in keys[-40:]:
        old_bars = days[old_day]
        if len(old_bars) >= IB_BARS:
            old_ib = old_bars[:IB_BARS]
            ib_hist.append(max(x["h"] for x in old_ib) - min(x["l"] for x in old_ib))

    ib = bars[:IB_BARS]
    ibh, ibl = max(x["h"] for x in ib), min(x["l"] for x in ib)
    _, _, poc_ib = ESR.value_area(ib)

    wrapper = StructuralBinaryClassifier()
    wrapper.reset(str(day))
    phase = "UNKNOWN"
    phase_dir = 0
    accepted_dir = 0
    contexts = [dict(label="NOT_YET", determined=False, phase="UNKNOWN", direction=0)
                for _ in bars]

    for i in range(IB_BARS - 1, len(bars)):
        seg = bars[:i + 1]
        _, _, poc_now = ESR.value_area(seg)
        result = classify_session(
            bars=[dict(o=b["o"], h=b["h"], l=b["l"], c=b["c"], v=b["v"])
                  for b in seg],
            ib_high=ibh, ib_low=ibl, open_price=bars[0]["o"],
            ib_width_hist=ib_hist, profile_shape=None, vol_ratio=None,
            prior_vah=pvah, prior_val=pval, pdh=pdh, pdl=pdl,
            poc_now=poc_now, poc_at_ib=poc_ib,
            is_eod=(i == len(bars) - 1),
        )
        held = wrapper.on_bar(result, i + 1)
        label = held["label"]
        measured = result.get("measured") or {}
        accepted = _norm_dir(result.get("accepted_break"))
        migration = _norm_dir(measured.get("value_migration"))
        sides = int(measured.get("sides") or 0)
        failed = bool(result.get("failed_break") or measured.get("failed_break"))
        returned = bool(result.get("returned_through_open") or
                        measured.get("returned_through_open"))

        if i == IB_BARS - 1:
            phase, phase_dir = "BALANCE", 0
        if accepted:
            accepted_dir = accepted
            if migration == accepted and not failed:
                phase, phase_dir = "DISCOVERY", accepted
        if failed or returned or sides >= 2:
            phase, phase_dir, accepted_dir = "BALANCE", 0, 0

        if str(label).startswith("Trend"):
            phase = "DISCOVERY"
            phase_dir = (
                _norm_dir(result.get("direction"))
                or _norm_dir(measured.get("one_tf"))
                or accepted_dir
                or (1 if bars[i]["c"] >= bars[0]["o"] else -1)
            )
        elif label in {"Normal", "Neutral_Center", "Neutral_Extreme"}:
            phase, phase_dir = "BALANCE", 0

        contexts[i] = {
            "label": label,
            "determined": bool(held["determined"]),
            "phase": phase,
            "direction": phase_dir,
            "event": held.get("event"),
        }
    return contexts


def tpo_levels_at(day, when, snapshots, previous_levels):
    rows = snapshots.get(day, [])
    times = [r[0] for r in rows]
    pos = bisect_right(times, when) - 1
    if pos >= 0:
        _, _, vah, val = rows[pos]
        if vah is not None and val is not None:
            return vah, val, "developing_tpo"
    return (*previous_levels, "prior_value")


def value_location(price, vah, val):
    if vah is None or val is None or vah <= val:
        return "UNKNOWN"
    edge = max(0.15 * (vah - val), 1.0)
    if val - edge <= price <= val + edge:
        return "AT_EDGE_LOW"
    if vah - edge <= price <= vah + edge:
        return "AT_EDGE_HIGH"
    if price < val:
        return "BELOW_VAL"
    if price > vah:
        return "ABOVE_VAH"
    return "IN_VALUE"


def previous_value(days, day):
    keys = sorted(k for k in days if k < day)
    if not keys:
        return None, None
    vah, val, _ = ESR.value_area(days[keys[-1]])
    return vah, val


def align_cvd(bars, rows):
    """Latest non-future cumulative value within six minutes of each bar."""
    aligned, j, latest = [], 0, None
    for bar in bars:
        t = _aware_utc(bar["t"])
        while j < len(rows) and rows[j][0] <= t:
            latest = rows[j]
            j += 1
        if latest is not None and (t - latest[0]).total_seconds() <= 360:
            aligned.append(latest[1])
        else:
            aligned.append(None)
    deltas = [0.0] * len(aligned)
    for i in range(1, len(aligned)):
        if aligned[i] is not None and aligned[i - 1] is not None:
            deltas[i] = aligned[i] - aligned[i - 1]
    return aligned, deltas


def scan_delta_double(bars, labels, deltas):
    """Current shadow detector; counted separately from fireable candidates."""
    from backend.v9.systems.five_min.patterns.delta_dbl import detect_delta_dbl

    out, seen = [], set()
    for i in range(6, len(bars)):
        setup = detect_delta_dbl(
            [dict(o=b["o"], h=b["h"], l=b["l"], c=b["c"], v=b["v"])
             for b in bars[:i + 1]],
            ESR.norm_dt(labels[i]),
            ESR.atr5(bars, i),
            deltas[:i + 1],
        )
        if not setup:
            continue
        direction = 1 if setup["direction"] == "LONG" else -1
        key = (setup["pattern"], direction)
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(i=i, dir=direction, kind="S2_DELTA_DBL",
                        conf=0.75, src="shadow"))
    return out


def current_candidates(bars, labels, woodies, shim):
    """Every currently enabled detector, generated from bars rather than logs."""
    out = []
    out += GPF.scan_s2(bars, labels, shim, "LIVE")
    for which in ("DOUBLE_BOTTOM_EE", "INVERSE_HNS", "HNS_TOP"):
        out += GPF.scan_chart(bars, labels, shim, which)
    out += DPR.scan_s2_chart(bars, labels, "DOUBLE_TOP_AA", adam_fix=False)
    out += DPR.scan_flags(bars, labels, "BULL_FLAG")
    out += DPR.scan_flags(bars, labels, "BEAR_FLAG")
    for pid in ("ZLR", "TLB", "TT", "GB100", "VEGAS", "GHOST", "FAMIR", "HTLB"):
        out += DPR.scan_woodies(woodies, pid)
    out += DPR.scan_opening(bars)
    # TREND_STEP and S2_DELTA_DBL are shadow-only in the current .env; they are
    # deliberately excluded from the slot arm and reported separately.
    return _dedup(out)


def expanded_candidates(bars, labels, current):
    """Known wiring/detector repair only; no threshold search."""
    old_window = DPR.WINDOW
    try:
        DPR.WINDOW = 32
        dt_fixed = DPR.scan_s2_chart(bars, labels, "DOUBLE_TOP_AA", adam_fix=True)
    finally:
        DPR.WINDOW = old_window
    return _dedup(current + dt_fixed)


def candidate_family(kind):
    if kind in REV_KINDS or "DOUBLE_" in kind or "HNS" in kind:
        return "REV"
    if kind.startswith("OPENING_ORR") or kind.startswith("OPENING_EXTREME"):
        return "REV"
    if kind in CONT_KINDS or kind.startswith("OPENING_"):
        return "CONT"
    return "UNKNOWN"


def select_context(bars, contexts, candidates, tpo, day, prior_va):
    """Deterministic context selection; no learned weights, no hindsight."""
    selected = []
    for cand in candidates:
        i = cand["i"]
        if i >= len(contexts):
            continue
        ctx = contexts[i]
        label = ctx["label"]
        if not ctx["determined"] or label in NONTRADE_LABELS:
            continue
        vah, val, level_source = tpo_levels_at(day, bars[i]["t"], tpo, prior_va)
        loc = value_location(bars[i]["c"], vah, val)
        family = candidate_family(cand["kind"])
        allow = False
        reason = ""
        score = 0.0

        if ctx["phase"] == "BALANCE":
            edge_ok = ((cand["dir"] > 0 and loc in {"BELOW_VAL", "AT_EDGE_LOW"}) or
                       (cand["dir"] < 0 and loc in {"ABOVE_VAH", "AT_EDGE_HIGH"}))
            allow = family == "REV" and edge_ok
            reason = "balance_edge" if allow else "balance_mismatch"
            score = 4.0 if allow else 0.0
        elif ctx["phase"] == "DISCOVERY":
            with_dir = bool(ctx["direction"] and cand["dir"] == ctx["direction"])
            # REACTIVE is the existing confirmation geometry for a pullback
            # continuation; all other REV families stay out of discovery.
            allow = with_dir and (family == "CONT" or cand["kind"] == "REACTIVE")
            reason = "discovery_with_direction" if allow else "discovery_mismatch"
            score = 4.0 if allow else 0.0

        if not allow:
            continue
        recent = [b["v"] for b in bars[max(0, i - 20):i] if b["v"] > 0]
        median_v = statistics.median(recent) if recent else max(bars[i]["v"], 1)
        score += min(2.0, bars[i]["v"] / max(median_v, 1.0))
        chosen = dict(cand)
        chosen.update(
            context_label=label, phase=ctx["phase"], location=loc,
            context_reason=reason, level_source=level_source, score=round(score, 3),
        )
        selected.append(chosen)
    return _dedup(selected)


def structural_opportunities(days, day, bars, tpo, cumulative):
    """Independent market-opportunity population from bars/volume/CVD."""
    prior_va = previous_value(days, day)
    rev, cont = [], []
    for i in range(IB_BARS + 2, len(bars)):
        vah, val, _ = tpo_levels_at(day, bars[i]["t"], tpo, prior_va)
        events = []
        if vah is not None and val is not None:
            events += EDA.detect_extremes_B(bars, i, vah, val)
        events += EDA.detect_extremes_C(bars, i)
        events += EDA.detect_extremes_D(bars, i, cumulative)
        for event in events:
            rev.append(dict(i=i, dir=(1 if event["direction"] == "LONG" else -1),
                            family="REV", kind=event["type"]))

    threshold = ORA.thr_for(days, day)
    pivots = ORA.zigzag(bars, threshold)
    for trigger in ORA.find_triggers(bars, pivots, threshold):
        if trigger["kind"] in {"BREAK", "STAIR", "PB"}:
            cont.append(dict(i=trigger["i"], dir=trigger["dir"],
                             family="CONT", kind=trigger["kind"]))

    def dedup_events(events):
        result, last = [], {}
        for event in sorted(events, key=lambda x: x["i"]):
            key = (event["family"], event["dir"], event["kind"])
            if event["i"] - last.get(key, -999) <= MATCH_BARS:
                continue
            last[key] = event["i"]
            result.append(event)
        return result

    return dedup_events(rev + cont)


def coverage(opportunities, candidates):
    matches, lags, matched_candidates = 0, [], set()
    for oi, opportunity in enumerate(opportunities):
        family = opportunity["family"]
        eligible = [
            (ci, c) for ci, c in enumerate(candidates)
            if candidate_family(c["kind"]) == family
            and c["dir"] == opportunity["dir"]
            and opportunity["i"] <= c["i"] <= opportunity["i"] + MATCH_BARS
        ]
        if eligible:
            ci, cand = min(eligible, key=lambda pair: pair[1]["i"])
            matches += 1
            lags.append(cand["i"] - opportunity["i"])
            matched_candidates.add(ci)
    return {
        "opportunities": len(opportunities),
        "matched": matches,
        "coverage_pct": round(100.0 * matches / max(1, len(opportunities)), 1),
        "median_lag_bars": _med(lags),
        "candidate_count": len(candidates),
        "unmatched_candidates": len(candidates) - len(matched_candidates),
    }


def sim_ranked(bars, candidates, threshold, contracts=6, slip=1, slots=1):
    """Same-bar ranking only; no lookahead across bars."""
    ORA.SLIP_TICKS = slip
    ORA.CONTRACTS = contracts
    ordered = sorted(candidates, key=lambda c: (c["i"], -float(c.get("score", 0))))
    trades, busy, used_bar = [], [], None
    for cand in ordered:
        busy = [exit_i for exit_i in busy if exit_i >= cand["i"]]
        if len(busy) >= slots:
            continue
        if used_bar == cand["i"]:
            continue
        trade = ORA.sim_ladder(bars, cand["i"], cand["dir"], threshold, contracts)
        if not trade:
            continue
        trade["kind"] = cand["kind"]
        trades.append(trade)
        busy.append(trade["exit_i"])
        used_bar = cand["i"]
    ORA.SLIP_TICKS = 1
    ORA.CONTRACTS = 4
    return trades


def summarize(per_day, trades, dates):
    total = round(sum(per_day.values()), 2)
    wins = sum(1 for trade in trades if trade["usd"] > 0)
    is_total = round(sum(v for d, v in per_day.items() if IS0 <= d <= IS1), 2)
    oos_total = round(sum(v for d, v in per_day.items() if not (IS0 <= d <= IS1)), 2)
    july = round(sum(v for d, v in per_day.items() if d.month == 7), 2)
    august = round(sum(v for d, v in per_day.items() if d.month == 8), 2)
    worst = min(per_day.items(), key=lambda item: item[1]) if per_day else (None, 0)
    return {
        "n": len(trades),
        "trades_per_day": round(len(trades) / max(1, len(dates)), 2),
        "wins": wins,
        "win_pct": round(100.0 * wins / max(1, len(trades)), 1),
        "usd": total,
        "median_day": _med(list(per_day.values())),
        "positive_days": sum(1 for v in per_day.values() if v > 0),
        "negative_days": sum(1 for v in per_day.values() if v < 0),
        "legacy_is": is_total,
        "pseudo_oos": oos_total,
        "july": july,
        "august": august,
        "worst_day": [str(worst[0]), round(worst[1], 2)],
        "per_day": {str(d): v for d, v in per_day.items()},
    }


def run_arm(days, dates, streams, thresholds, *, ranked=False, slots=1, slip=1):
    per_day, trades = {}, []
    for day in dates:
        if ranked:
            day_trades = sim_ranked(days[day], streams[day], thresholds[day],
                                    contracts=6, slip=slip, slots=slots)
        else:
            day_trades = GPF.sim_stream(days[day], streams[day], thresholds[day],
                                        contracts=6, slip=slip, slots=slots)
        per_day[day] = round(sum(t["usd"] for t in day_trades), 2)
        trades.extend(day_trades)
    return summarize(per_day, trades, dates)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default="/tmp/maximized_opportunity_replay.json")
    args = parser.parse_args()

    conn = psycopg2.connect(DSN)
    conn.set_session(readonly=True)
    cur = conn.cursor()
    days, dates, woodies, cvd, tpo = load_data(cur)
    conn.close()

    print(f"[data] sessions={len(dates)} {dates[0]}..{dates[-1]} "
          f"cvd_days={len(cvd)} tpo_days={len(tpo)}")
    labels = {day: ESR.causal_labels(days, day, days[day]) for day in dates}
    contexts = {day: causal_context(days, day, days[day]) for day in dates}
    thresholds = {day: ORA.thr_for(days, day) for day in dates}

    shim = GPF.S2Shim()
    TC.get_live_day_type = lambda: shim.current_day_type
    current, expanded, shadow, opportunities = {}, {}, {}, {}
    max_context, max_expanded = {}, {}
    coverage_rows = {}

    for day in dates:
        shim._cvd_sorted = cvd.get(str(day), [])
        current[day] = current_candidates(days[day], labels[day], woodies[day], shim)
        expanded[day] = expanded_candidates(days[day], labels[day], current[day])
        cumulative, deltas = align_cvd(days[day], cvd.get(str(day), []))
        trend_step_bars = [
            dict(
                o=w.open, h=w.high, l=w.low, c=w.close, v=w.volume,
                lsma=w.lsma_value, hhmm=days[day][i]["t"].strftime("%H:%M"),
            )
            for i, w in enumerate(woodies[day])
        ]
        shadow[day] = {
            "trend_step": GPF.scan_trend_step(trend_step_bars),
            "delta_double": scan_delta_double(days[day], labels[day], deltas),
        }
        prior_va = previous_value(days, day)
        max_context[day] = select_context(
            days[day], contexts[day], current[day], tpo, day, prior_va)
        max_expanded[day] = select_context(
            days[day], contexts[day], expanded[day], tpo, day, prior_va)
        opportunities[day] = structural_opportunities(
            days, day, days[day], tpo, cumulative)
        coverage_rows[str(day)] = {
            "current": coverage(opportunities[day], current[day]),
            "max_context": coverage(opportunities[day], max_context[day]),
            "max_expanded": coverage(opportunities[day], max_expanded[day]),
            "current_rev": coverage(
                [o for o in opportunities[day] if o["family"] == "REV"],
                [c for c in current[day] if candidate_family(c["kind"]) == "REV"],
            ),
            "current_cont": coverage(
                [o for o in opportunities[day] if o["family"] == "CONT"],
                [c for c in current[day] if candidate_family(c["kind"]) == "CONT"],
            ),
            "shadow_trend_step": len(shadow[day]["trend_step"]),
            "shadow_delta_double": len(shadow[day]["delta_double"]),
        }

    arms = {
        "CURRENT_ALL": run_arm(days, dates, current, thresholds),
        "MAX_CONTEXT": run_arm(days, dates, max_context, thresholds, ranked=True),
        "MAX_EXPANDED": run_arm(days, dates, max_expanded, thresholds, ranked=True),
        "MAX_2SLOT": run_arm(days, dates, max_context, thresholds, ranked=True, slots=2),
    }
    sensitivity = {}
    for slip in (0, 1, 2):
        sensitivity[f"MAX_CONTEXT_s{slip}"] = run_arm(
            days, dates, max_context, thresholds, ranked=True, slip=slip)

    total_opp = sum(len(v) for v in opportunities.values())
    all_current = [c for day in dates for c in current[day]]
    all_max = [c for day in dates for c in max_context[day]]
    all_expanded = [c for day in dates for c in max_expanded[day]]
    all_opps = [o for day in dates for o in opportunities[day]]
    overall_coverage = {
        "current": coverage(all_opps, all_current),
        "max_context": coverage(all_opps, all_max),
        "max_expanded": coverage(all_opps, all_expanded),
    }
    # Coverage must be day-scoped; the aggregate list can cross-match equal bar
    # indexes across days, so headline uses summed day-scoped counts.
    for key in overall_coverage:
        matched = sum(coverage_rows[str(day)][key]["matched"] for day in dates)
        cand_n = sum(coverage_rows[str(day)][key]["candidate_count"] for day in dates)
        unmatched = sum(coverage_rows[str(day)][key]["unmatched_candidates"] for day in dates)
        lags = [coverage_rows[str(day)][key]["median_lag_bars"] for day in dates
                if coverage_rows[str(day)][key]["matched"]]
        overall_coverage[key] = {
            "opportunities": total_opp,
            "matched": matched,
            "coverage_pct": round(100.0 * matched / max(1, total_opp), 1),
            "candidate_count": cand_n,
            "unmatched_candidates": unmatched,
            "median_daily_lag_bars": _med(lags),
        }

    print("\nARM RESULTS — 6 contracts, one-tick slip")
    for name, result in arms.items():
        print(
            f"{name:14s} n={result['n']:3d} t/day={result['trades_per_day']:.2f} "
            f"win={result['win_pct']:5.1f}% ${result['usd']:9.2f} "
            f"med/day=${result['median_day']:7.2f} "
            f"IS=${result['legacy_is']:8.2f} pOOS=${result['pseudo_oos']:8.2f} "
            f"Jul=${result['july']:8.2f} Aug=${result['august']:8.2f} "
            f"worst={result['worst_day']}"
        )

    print("\nOPPORTUNITY COVERAGE — bars/volume/CVD population, no fire logs")
    for name, row in overall_coverage.items():
        print(
            f"{name:14s} {row['matched']:3d}/{row['opportunities']:3d} "
            f"({row['coverage_pct']:5.1f}%) candidates={row['candidate_count']:4d} "
            f"unmatched={row['unmatched_candidates']:4d}"
        )
    print(
        "\nSHADOW ONLY:",
        "TREND_STEP=", sum(len(shadow[d]["trend_step"]) for d in dates),
        "S2_DELTA_DBL=", sum(len(shadow[d]["delta_double"]) for d in dates),
    )

    output = {
        "meta": {
            "sessions": len(dates),
            "date_start": str(dates[0]),
            "date_end": str(dates[-1]),
            "contracts": 6,
            "slippage_ticks": 1,
            "opportunity_match_bars": MATCH_BARS,
            "population": "candles+volume+causal TPO snapshots+CVD; no setups/trades/decisions",
        },
        "arms": arms,
        "sensitivity": sensitivity,
        "coverage": overall_coverage,
        "coverage_by_day": coverage_rows,
        "candidate_counts": {
            "current": sum(len(current[d]) for d in dates),
            "expanded": sum(len(expanded[d]) for d in dates),
            "max_context": sum(len(max_context[d]) for d in dates),
            "max_expanded": sum(len(max_expanded[d]) for d in dates),
            "shadow_trend_step": sum(len(shadow[d]["trend_step"]) for d in dates),
            "shadow_delta_double": sum(len(shadow[d]["delta_double"]) for d in dates),
        },
        "candidate_kinds": {
            "current": dict(collections.Counter(
                c["kind"] for d in dates for c in current[d])),
            "max_context": dict(collections.Counter(
                c["kind"] for d in dates for c in max_context[d])),
            "max_expanded": dict(collections.Counter(
                c["kind"] for d in dates for c in max_expanded[d])),
            "opportunities": dict(collections.Counter(
                f"{o['family']}:{o['kind']}" for d in dates for o in opportunities[d])),
        },
    }
    with open(args.json, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n[out] {args.json}")


if __name__ == "__main__":
    main()
