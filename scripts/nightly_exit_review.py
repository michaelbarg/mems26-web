#!/usr/bin/env python3
"""nightly_exit_review — the nightly learning loop (Michael ruling 2026-07-11/12).

For every closed real trade of the day (live/demo/sim — not shadow), compare the
ACTUAL exit against what the day's bars made available, and turn the gap into
concrete calibration proposals for the morning ruling.

Per trade:
  MFE        — best favorable excursion from entry to EOD (the ceiling).
  captured%  — actual P&L points vs MFE points.
  trail_sim  — what a 1-bar-delayed structural trail would have captured
               (rolling 3-bar extreme minus/plus 1 tick) — the realistic bar.
  verdict    — GOOD (>=70% of trail_sim) · OK (40-70%) · POOR (<40%).

Aggregation per pattern × day_type; proposals when a bucket is consistently
POOR (target/trail issue) or when actual >= MFE*0.9 (exits already excellent).

Honest by construction: only real bars, only recorded fills; trades without
bars/entry are SKIPPED loudly, never invented (Rule 1).

Usage: python3 scripts/nightly_exit_review.py [--date YYYY-MM-DD] [--days N]
Output: docs/reports/EXIT_REVIEW_<date>.md (+ stdout summary).
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

TICK = 0.25
PT_USD = 5.0  # MES $/point per contract

IL = ZoneInfo("Asia/Jerusalem")
ET = ZoneInfo("America/New_York")


def _engine():
    from sqlalchemy import create_engine
    url = os.getenv("DATABASE_URL", "postgresql://localhost/mems26")
    return create_engine(url)


def _rows(engine, sql, **params):
    from sqlalchemy import text
    with engine.connect() as c:
        return [dict(r._mapping) for r in c.execute(text(sql), params)]


def load_trades(engine, date_str: str):
    return _rows(engine, """
        SELECT id, mode, direction, entry_price, exit_price, stop, t1, t2, t3,
               pnl_usd, outcome, exit_reason, entry_ts, exit_ts,
               quality->>'pattern' AS pattern, quality->>'classification' AS classification,
               day_type_at_entry, firing_system,
               COALESCE((quality->>'contracts')::int, 2) AS contracts,
               (quality->>'initial_stop')::float AS initial_stop
        FROM v9_trades
        WHERE mode != 'shadow'
          AND state IN ('CLOSED')
          AND pnl_usd IS NOT NULL
          AND (entry_ts AT TIME ZONE 'Asia/Jerusalem')::date = :d
        ORDER BY id
    """, d=date_str)


def load_bars(engine, start_utc, end_utc):
    return _rows(engine, """
        SELECT ts, high, low, close FROM v9_bars_5min_woodies
        WHERE ts >= :a AND ts <= :b ORDER BY ts ASC
    """, a=start_utc, b=end_utc)


def analyze(trade, bars):
    """Returns dict with mfe_pts, captured_pct, trail_pts, verdict — or None (no bars)."""
    if not bars or trade["entry_price"] is None:
        return None
    e = float(trade["entry_price"])
    long = (trade["direction"] or "").upper() == "LONG"
    sign = 1.0 if long else -1.0

    # MFE from entry to end of window
    if long:
        mfe_px = max(float(b["high"]) for b in bars)
    else:
        mfe_px = min(float(b["low"]) for b in bars)
    mfe_pts = max(0.0, sign * (mfe_px - e))

    # Realistic 1-bar-delayed structural trail: stop = rolling 3-bar extreme ∓ 1 tick,
    # applied from the bar after entry; exit when a bar crosses the trailed stop.
    risk0 = None
    if trade["initial_stop"] is not None:
        risk0 = abs(e - float(trade["initial_stop"]))
    trail_stop = (e - (risk0 or 4.0)) if long else (e + (risk0 or 4.0))
    trail_exit_px = None
    window = []
    for b in bars:
        h, l = float(b["high"]), float(b["low"])
        # check exit FIRST (adverse priority)
        if long and l <= trail_stop:
            trail_exit_px = trail_stop
            break
        if (not long) and h >= trail_stop:
            trail_exit_px = trail_stop
            break
        window.append(b)
        if len(window) >= 3:
            last3 = window[-3:]
            if long:
                cand = min(float(x["low"]) for x in last3) - TICK
                trail_stop = max(trail_stop, cand)
            else:
                cand = max(float(x["high"]) for x in last3) + TICK
                trail_stop = min(trail_stop, cand)
    if trail_exit_px is None:  # survived to EOD → closes at last close
        trail_exit_px = float(bars[-1]["close"])
    trail_pts = sign * (trail_exit_px - e)

    contracts = trade["contracts"] or 2
    actual_pts = (float(trade["pnl_usd"]) / PT_USD) / max(1, contracts)
    captured_pct = (actual_pts / mfe_pts * 100.0) if mfe_pts > 0.5 else None

    if trail_pts > 0.5:
        ratio = actual_pts / trail_pts
        verdict = "GOOD" if ratio >= 0.7 else ("OK" if ratio >= 0.4 else "POOR")
    else:
        verdict = "GOOD" if actual_pts >= trail_pts else "OK"  # trail did no better

    return {
        "mfe_pts": round(mfe_pts, 2),
        "actual_pts": round(actual_pts, 2),
        "captured_pct": round(captured_pct, 1) if captured_pct is not None else None,
        "trail_pts": round(trail_pts, 2),
        "verdict": verdict,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="IL date YYYY-MM-DD (default: today)")
    args = ap.parse_args()
    date_str = args.date or datetime.now(IL).strftime("%Y-%m-%d")

    engine = _engine()
    trades = load_trades(engine, date_str)
    if not trades:
        print(f"[exit_review] no closed real trades on {date_str} — nothing to learn.")
        return 0

    day_end_utc = (datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=IL)
                   + timedelta(hours=23)).astimezone(timezone.utc)

    rows, skipped = [], []
    for t in trades:
        if t["entry_ts"] is None:
            skipped.append((t["id"], "no entry_ts"))
            continue
        entry_utc = t["entry_ts"] if t["entry_ts"].tzinfo else t["entry_ts"].replace(tzinfo=timezone.utc)
        bars = load_bars(engine, entry_utc, day_end_utc)
        a = analyze(t, bars)
        if a is None:
            skipped.append((t["id"], f"no bars after entry ({len(bars)})"))
            continue
        rows.append({**t, **a})

    # aggregate per pattern×day_type
    buckets = {}
    for r in rows:
        key = (r["pattern"] or r["classification"] or "?", r["day_type_at_entry"] or "?")
        b = buckets.setdefault(key, {"n": 0, "poor": 0, "good": 0, "cap": [], "left": []})
        b["n"] += 1
        b["poor"] += r["verdict"] == "POOR"
        b["good"] += r["verdict"] == "GOOD"
        if r["captured_pct"] is not None:
            b["cap"].append(r["captured_pct"])
        b["left"].append(max(0.0, r["trail_pts"] - r["actual_pts"]))

    proposals = []
    for (pat, dt), b in sorted(buckets.items()):
        avg_left = sum(b["left"]) / b["n"]
        if b["n"] >= 2 and b["poor"] >= max(1, b["n"] // 2):
            proposals.append(
                f"**{pat}×{dt}** — {b['poor']}/{b['n']} POOR, ממוצע {avg_left:.1f} נק' על השולחן: "
                f"הטרייל/יעד איטיים מהמבנה — לשקול הידוק chr STOP_PERBAR window או T-קרוב יותר.")
        elif b["n"] >= 2 and b["good"] == b["n"]:
            proposals.append(f"**{pat}×{dt}** — כל {b['n']} GOOD: המימוש עובד, לא לגעת.")

    out = Path(REPO / "docs/reports" / f"EXIT_REVIEW_{date_str}.md")
    lines = [
        f"# Exit Review — {date_str} (לולאת-הלמידה הלילית)",
        "",
        f"עסקאות-אמת שנותחו: {len(rows)} · דולגו (בלי ברים/entry): {len(skipped)}",
        "",
        "| # | תבנית | יום | כיוון | נק' בפועל | MFE | %נתפס | טרייל-סימולציה | פסק |",
        "|---|-------|-----|-------|-----------|-----|--------|----------------|-----|",
    ]
    for r in rows:
        lines.append(
            f"| {r['id']} | {r['pattern'] or r['classification'] or '?'} | {r['day_type_at_entry'] or '?'} "
            f"| {r['direction']} | {r['actual_pts']} | {r['mfe_pts']} "
            f"| {r['captured_pct'] if r['captured_pct'] is not None else '—'}% "
            f"| {r['trail_pts']} | {r['verdict']} |")
    lines += ["", "## הצעות-כיול לבוקר (פסיקת מייקל)", ""]
    lines += [f"- {p}" for p in proposals] or ["- אין דפוס מובהק היום (מדגם קטן) — ממשיכים לצבור."]
    if skipped:
        lines += ["", "## דולגו (honest skip)", ""]
        lines += [f"- #{i}: {why}" for i, why in skipped]
    out.write_text("\n".join(lines), encoding="utf-8")

    print(f"[exit_review] {len(rows)} trades → {out}")
    for p in proposals:
        print("  •", p.replace("**", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
