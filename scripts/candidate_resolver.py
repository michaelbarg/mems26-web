#!/usr/bin/env python3
"""Candidate Resolver — EOD script that appends RESOLVED events to gateway_decisions.jsonl.

Per CANDIDATE_LEDGER_CONTRACT §9: runs OUTSIDE the firing path (script/EOD).
Reads DETECTED events, computes MFE/MAE from v9_bars_5min_woodies, writes
RESOLVED with outcomes. Idempotent: re-run = 0 new rows.

Usage: python3 scripts/candidate_resolver.py [--jsonl PATH] [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DSN = os.environ.get("DATABASE_URL", "postgresql://localhost/mems26")
DEFAULT_JSONL = os.path.expanduser("~/SierraChart_Data/v9_export/gateway_decisions.jsonl")
ARCHIVE_DIR = os.path.expanduser("~/SierraChart_Data/v9_export/decisions_archive")
TICK = 0.25
HORIZONS = (3, 6, 12)  # bars forward


def _load_events(jsonl_path: str) -> List[dict]:
    """Load all parseable events from JSONL + archive."""
    events = []
    paths = []
    arch = Path(ARCHIVE_DIR)
    if arch.exists():
        paths.extend(sorted(arch.glob("gateway_decisions.*.jsonl")))
    p = Path(jsonl_path)
    if p.exists():
        paths.append(p)
    for fp in paths:
        for line in fp.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except (json.JSONDecodeError, ValueError):
                continue
    return events


def _candidates(events: List[dict]) -> Dict[str, dict]:
    """Group by candidate_id, return {cid: {detected: event, resolved: bool}}."""
    cands = {}
    for e in events:
        cid = e.get("candidate_id")
        if not cid:
            continue
        et = e.get("event_type", "")
        if et == "DETECTED":
            cands.setdefault(cid, {"detected": e, "resolved": False})
        elif et == "RESOLVED":
            if cid in cands:
                cands[cid]["resolved"] = True
    return cands


def _load_bars(session_date: str) -> List[dict]:
    """Load RTH bars from v9_bars_5min_woodies for a date."""
    try:
        import psycopg2
        conn = psycopg2.connect(DSN)
        conn.set_session(readonly=True, autocommit=True)
        cur = conn.cursor()
        cur.execute("""
            SELECT (ts AT TIME ZONE 'America/New_York') AS et,
                   open, high, low, close, volume
            FROM v9_bars_5min_woodies
            WHERE (ts AT TIME ZONE 'America/New_York')::date = %s
              AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30'
              AND (ts AT TIME ZONE 'America/New_York')::time < '16:00'
              AND symbol = 'MES'
            ORDER BY ts
        """, (session_date,))
        bars = [{"ts": r[0], "o": float(r[1]), "h": float(r[2]),
                 "l": float(r[3]), "c": float(r[4]), "v": int(r[5] or 0)}
                for r in cur.fetchall()]
        conn.close()
        return bars
    except Exception as e:
        print(f"  WARNING: bar load failed for {session_date}: {e}", file=sys.stderr)
        return []


def _session_quality(bars: List[dict], session_date: str) -> Optional[List[str]]:
    """Minimal quality check. Returns reason_codes if NOT_JUDGEABLE, else None."""
    reasons = []
    if len(bars) != 78:
        reasons.append(f"RTH_CARDINALITY(actual={len(bars)},expected=78)")
    return reasons if reasons else None


def _compute_mfe_mae(bars: List[dict], entry_bar_idx: int,
                     direction: str, entry_price: float) -> dict:
    """Compute MFE/MAE at multiple horizons."""
    sign = 1.0 if direction == "LONG" else -1.0
    result = {}
    for h in HORIZONS:
        mfe = 0.0
        mae = 0.0
        for i in range(entry_bar_idx + 1, min(entry_bar_idx + 1 + h, len(bars))):
            excur_h = (bars[i]["h"] - entry_price) * sign
            excur_l = (bars[i]["l"] - entry_price) * sign
            mfe = max(mfe, excur_h, excur_l)
            mae = min(mae, excur_h, excur_l)
        result[f"mfe_{h}"] = round(mfe, 2)
        result[f"mae_{h}"] = round(mae, 2)
    return result


def resolve(jsonl_path: str, dry_run: bool = False) -> dict:
    """Resolve all unresolved candidates. Returns summary."""
    events = _load_events(jsonl_path)
    cands = _candidates(events)

    unresolved = {cid: c for cid, c in cands.items() if not c["resolved"]}
    if not unresolved:
        return {"total": len(cands), "unresolved": 0, "resolved_now": 0,
                "not_judgeable": 0, "message": "all already resolved"}

    # Group by session date
    by_date = defaultdict(list)
    for cid, c in unresolved.items():
        det = c["detected"]
        ts = det.get("signal_bar_ts") or det.get("observed_at") or ""
        date_str = str(ts)[:10]
        by_date[date_str].append((cid, det))

    resolved_events = []
    not_judgeable_count = 0

    for date_str, candidates in sorted(by_date.items()):
        bars = _load_bars(date_str)
        quality_issues = _session_quality(bars, date_str)

        for cid, det in candidates:
            resolved_event = {
                "schema": "candidate_ledger.v1",
                "event_type": "RESOLVED",
                "candidate_id": cid,
                "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "signal_bar_ts": det.get("signal_bar_ts"),
                "system": det.get("system"),
                "pattern": det.get("pattern"),
                "direction": det.get("direction"),
            }

            if quality_issues:
                resolved_event["outcome_status"] = "NOT_JUDGEABLE"
                resolved_event["reason_codes"] = quality_issues
                not_judgeable_count += 1
            else:
                # Find the entry bar.
                # Rule-4 fix (cowork-night 28.08): signal_bar_ts is UTC-ISO
                # ("...T19:15:00+00:00") while bars carry NAIVE ET datetimes
                # ("2026-08-27 14:50:00"). The old str[:16] compare put 'T'(84)
                # against ' '(32) at index 10, so NO bar ever matched and all
                # 136 candidates resolved MISSING_ENTRY_OR_BARS. Convert the
                # signal ts to naive-ET and compare datetimes, not strings.
                entry_ts = det.get("signal_bar_ts", "")
                entry_et = None
                try:
                    from zoneinfo import ZoneInfo
                    _sig = dt.datetime.fromisoformat(str(entry_ts))
                    if _sig.tzinfo is not None:
                        _sig = _sig.astimezone(
                            ZoneInfo("America/New_York")).replace(tzinfo=None)
                    entry_et = _sig
                except (TypeError, ValueError):
                    entry_et = None

                def _bar_dt(b):
                    v = b["ts"]
                    if isinstance(v, dt.datetime):
                        return v.replace(tzinfo=None)
                    try:
                        return dt.datetime.fromisoformat(str(v)[:19])
                    except ValueError:
                        return None

                entry_price = None
                try:
                    prices = det.get("prices") or {}
                    entry_price = float(prices.get("entry") or prices.get("entry_price") or 0)
                except (TypeError, ValueError):
                    pass

                direction = (det.get("direction") or "").upper()
                entry_bar_idx = None
                if entry_et is not None:
                    for i, b in enumerate(bars):
                        bdt = _bar_dt(b)
                        if bdt is not None and bdt >= entry_et:
                            entry_bar_idx = i
                            break
                if not entry_price and entry_bar_idx is not None:
                    # Use the bar's close at signal time
                    entry_price = bars[entry_bar_idx]["c"]

                if entry_bar_idx is not None and entry_price and direction in ("LONG", "SHORT"):
                    outcomes = _compute_mfe_mae(bars, entry_bar_idx, direction, entry_price)
                    # t1_before_stop check
                    stop_price = None
                    t1_price = None
                    try:
                        prices = det.get("prices") or {}
                        stop_price = float(prices.get("stop") or 0) or None
                        t1_price = float(prices.get("t1") or 0) or None
                    except (TypeError, ValueError):
                        pass
                    t1_before_stop = None
                    if stop_price and t1_price:
                        for i in range(entry_bar_idx + 1, len(bars)):
                            h, l = bars[i]["h"], bars[i]["l"]
                            if direction == "LONG":
                                if h >= t1_price:
                                    t1_before_stop = True
                                    break
                                if l <= stop_price:
                                    t1_before_stop = False
                                    break
                            else:
                                if l <= t1_price:
                                    t1_before_stop = True
                                    break
                                if h >= stop_price:
                                    t1_before_stop = False
                                    break

                    resolved_event["outcome_status"] = "RESOLVED"
                    resolved_event["outcomes"] = outcomes
                    resolved_event["t1_before_stop"] = t1_before_stop
                    resolved_event["entry_price_used"] = entry_price
                else:
                    resolved_event["outcome_status"] = "NOT_JUDGEABLE"
                    resolved_event["reason_codes"] = ["MISSING_ENTRY_OR_BARS"]
                    not_judgeable_count += 1

            resolved_events.append(resolved_event)

    # Write
    written = 0
    if not dry_run and resolved_events:
        p = Path(jsonl_path)
        with open(p, "a", encoding="utf-8") as fh:
            for ev in resolved_events:
                fh.write(json.dumps(ev, separators=(",", ":"), default=str) + "\n")
                written += 1

    return {
        "total_candidates": len(cands),
        "already_resolved": len(cands) - len(unresolved),
        "unresolved": len(unresolved),
        "resolved_now": written if not dry_run else len(resolved_events),
        "not_judgeable": not_judgeable_count,
        "dry_run": dry_run,
        "events": resolved_events if dry_run else [],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default=DEFAULT_JSONL)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    result = resolve(args.jsonl, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
