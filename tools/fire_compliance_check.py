#!/usr/bin/env python3
"""
fire_compliance_check.py — audit each LIVE (shadow) fire of the day against:
  (1) DIRECTION alignment — does the fire direction match the system's direction
      (trend_state / day-type) at fire time? ("only with the move")
  (2) READINESS — did it fire with real session structure (bar_count, opening_type,
      day_type, TPO bars), or pre-structure (the #188 failure)?
  (3) PATTERN SPEC (basic) — per-pattern source conditions: a continuation pattern
      must be with-trend and have reached an extreme, not fire flat near the 0 line.

Reads the live fire's cross_context snapshot (the exact system state at fire time).
Writes tools/fire_audit_<date>.md (full per-fire table) and PRINTS any NEW
out-of-accordance fire since the last run (state in tools/.fire_audit_state.json),
so a scheduled task can alert Michael on them. READ-ONLY on the DB.

Usage: PYTHONPATH=<repo> python3 tools/fire_compliance_check.py [--date YYYY-MM-DD]
"""
import argparse
import json
import os
import datetime as dt
from pathlib import Path

from sqlalchemy import create_engine, text

HERE = Path(__file__).resolve().parent
STATE = HERE / ".fire_audit_state.json"
DB = os.environ.get("DATABASE_URL", "postgresql://localhost/mems26")

CONT = {"TLB", "ZLR", "TT", "GB100", "HTLB", "INITIATIVE"}
REV = {"HFE", "VEGAS", "GHOST", "FAMIR", "DBDT", "REACTIVE", "HNS"}


def _systems(cc):
    if isinstance(cc, list) and cc:
        cc = cc[0]
    if not isinstance(cc, dict):
        return {}
    return cc.get("systems", {}) or {}


def check_fire(f):
    """Return (verdict, flags, facts) for one fire row."""
    sysd = _systems(f.get("cross_context"))
    w = sysd.get("woodies_system", {}) or {}
    tpo = sysd.get("tpo_system", {}) or {}
    pid = (f.get("pattern_id_at_entry") or "").upper()
    base = pid.split("_")[0]
    direction = (f.get("direction") or "").upper()
    trend = (w.get("trend_state") or "").upper()
    cci = w.get("cci_14")
    swi = w.get("swi_value")
    bar_count = w.get("bar_count")
    ready = w.get("ready_to_route")
    opening = tpo.get("opening_type")
    bars_today = tpo.get("bars_processed_today")
    day_type = f.get("day_type_at_entry")
    is_cont = pid in CONT or base in CONT
    flags = []

    # (1) DIRECTION alignment — continuation must run WITH the trend color.
    exp = {"BLUE": "LONG", "RED": "SHORT"}.get(trend)
    if is_cont and exp and direction != exp:
        flags.append(f"counter-trend {base} {direction} vs trend={trend} (expect {exp})")

    # (2) READINESS — real session structure must exist before any fire.
    if isinstance(bar_count, (int, float)) and bar_count < 6:
        flags.append(f"premature: bar_count={bar_count} (<6 session bars)")
    if opening in (None, "NA", ""):
        flags.append("no opening_type (day structure not set)")
    if bars_today == 0:
        flags.append("TPO bars_today=0 (fired pre-structure)")
    if str(day_type).upper() in ("UNKNOWN", "NONE", ""):
        flags.append(f"day_type not classified ({day_type})")

    # (3) PATTERN SPEC (basic) — continuation near the 0 line = no extreme reached.
    if is_cont and isinstance(cci, (int, float)) and abs(cci) < 100:
        flags.append(f"{base} fired near 0 (CCI={round(cci, 1)}) — source needs ±200/SWI extreme first")

    verdict = "OUT" if flags else "IN"
    facts = {"pattern": pid or "?", "dir": direction, "trend": trend or "?",
             "cci": cci, "swi": swi, "bar_count": bar_count,
             "opening": opening, "day_type": day_type, "ready": ready}
    return verdict, flags, facts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    a = ap.parse_args()
    date = a.date or dt.datetime.now().strftime("%Y-%m-%d")

    eng = create_engine(DB)
    sql = text(
        """select id, entry_ts, direction, entry_price, pnl_usd, outcome, state,
                  day_type_at_entry, pattern_id_at_entry, cross_context
           from v9_trades
           where (entry_ts AT TIME ZONE 'America/Chicago')::date = :d
             and mode = 'shadow'
           order by id asc"""
    )
    with eng.connect() as c:
        rows = [dict(r) for r in c.execute(sql, {"d": date}).mappings()]

    results = [(f, *check_fire(f)) for f in rows]
    n_out = sum(1 for _, v, _, _ in results if v == "OUT")

    seen = set()
    if STATE.exists():
        try:
            seen = set(json.loads(STATE.read_text()).get("seen", []))
        except Exception:
            seen = set()
    new_out = [(f, flags, facts) for (f, v, flags, facts) in results
               if v == "OUT" and f["id"] not in seen]

    # ── full report ──
    lines = [
        f"# Fire compliance audit — {date}", "",
        f"_Generated {dt.datetime.now().strftime('%Y-%m-%d %H:%M')} · {len(rows)} shadow fires · "
        f"{n_out} OUT-of-accordance_", "",
        "Checks: (1) direction alignment · (2) readiness/structure · (3) pattern-spec extreme.", "",
        "| id | time | pattern | dir | trend | day_type | bars | CCI | verdict | reasons |",
        "|----|------|---------|-----|-------|----------|------|-----|---------|---------|",
    ]
    for f, v, flags, facts in results:
        t = f["entry_ts"].strftime("%H:%M") if f.get("entry_ts") else "—"
        mark = "🔴 OUT" if v == "OUT" else "✅ IN"
        lines.append(
            f"| {f['id']} | {t} | {facts['pattern']} | {facts['dir']} | {facts['trend']} | "
            f"{facts['day_type']} | {facts['bar_count']} | {facts['cci']} | {mark} | "
            f"{'; '.join(flags) or '—'} |"
        )
    (HERE / f"fire_audit_{date}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    STATE.write_text(json.dumps({"seen": [f["id"] for (f, _, _, _) in results]}), encoding="utf-8")

    # ── alert payload (what a scheduled task surfaces) ──
    if new_out:
        print(f"NEW OUT-OF-ACCORDANCE FIRES ({len(new_out)}):")
        for f, flags, facts in new_out:
            t = f["entry_ts"].strftime("%H:%M") if f.get("entry_ts") else "—"
            print(f"  - id {f['id']} {t} {facts['pattern']} {facts['dir']} "
                  f"(trend={facts['trend']}, day_type={facts['day_type']}, CCI={facts['cci']}): "
                  f"{'; '.join(flags)}")
    else:
        print(f"No NEW out-of-accordance fires. ({len(rows)} shadow fires today, "
              f"{n_out} OUT total — all already reported.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
