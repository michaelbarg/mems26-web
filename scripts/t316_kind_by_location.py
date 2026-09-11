"""T-316: kind_by_location measurement script — rewrite (2026-09-11).

Critiques addressed:
  1. TPO data from v9_tpo_sessions directly, NOT JSONL.  Query per
     trading_date, prefer session_type='CASH'.  If no CASH row exists
     for a date, that date is skipped entirely (IB trap: CASH-only IB).
  2. IB trap: ib_high/ib_low are shared across CASH/GLOBEX rows in the
     current schema — so only the CASH row is used.
  3. zone_of imported from backend.v9.systems.location_gate — not copied.
  4. Each gateway decision:
       - trading_date from ts
       - CASH TPO for that date (skip day if absent)
       - structural_anchor if present, else entry_price → zone_of
       - kind_by_location from zone + direction rules
       - compare to kind_by_name from dalton_playbook entry_kind_map
  5. Output table: pattern × day_type → name_kind, location_kind,
     blocked_now, would_block_location, change direction.
  6. Lists "was blocked→passes" and "was passing→blocked".

DATABASE_URL=postgresql://localhost/mems26.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

# ── repo root on path ──────────────────────────────────────────────────────────
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
log = logging.getLogger("t316")

# ── import zone_of from the canonical source ──────────────────────────────────
from backend.v9.systems.location_gate import zone_of  # noqa: E402

# ── constants ──────────────────────────────────────────────────────────────────
DECISIONS_DIR = Path(
    os.path.expanduser("~/SierraChart_Data/v9_export/decisions_archive")
)
CURRENT_DECISIONS = Path(
    os.path.expanduser("~/SierraChart_Data/v9_export/gateway_decisions.jsonl")
)
PLAYBOOK_PATH = REPO / "config" / "dalton_playbook.yaml"
CUTOFF_DATE = "2026-09-02"

# ── load playbook ──────────────────────────────────────────────────────────────
with open(PLAYBOOK_PATH, encoding="utf-8") as _f:
    _PLAYBOOK = yaml.safe_load(_f)
KIND_BY_NAME: Dict[str, str] = _PLAYBOOK.get("entry_kind_map", {})

# Patterns whose kind is purely name-driven (PULLBACK rule)
PULLBACK_BY_NAME_PATTERNS = {
    "PULLBACK_CONT", "OPENING_PULLBACK_CONT", "TREND_STEP",
    "TREND_STEP_LEG",
}


def kind_by_name(pattern: str) -> str:
    """Map pattern to kind via playbook entry_kind_map."""
    if not pattern:
        return "UNKNOWN"
    return KIND_BY_NAME.get(pattern, KIND_BY_NAME.get(pattern.upper(), "BREAK"))


def compute_location_kind(
    pattern: str,
    direction: str,
    anchor: float,
    tpo: Dict,
) -> Tuple[str, str]:
    """Compute kind_by_location using zone_of from location_gate.

    Rules (per T-316 spec):
      PULLBACK patterns → PULLBACK (by name, unchanged)
      near_val + LONG or near_vah + SHORT → EDGE_FADE
      below_value + LONG or above_value + SHORT → EDGE_FADE
      mid_value + toward POC → VALUE_RETURN
      beyond edge + away from value → BREAK
      no CASH TPO → fallback to name-based kind
    """
    # Rule 0: PULLBACK patterns stay PULLBACK by name
    if pattern in PULLBACK_BY_NAME_PATTERNS:
        return "PULLBACK", "pullback-by-name"

    direction = (direction or "").upper()
    name_k = kind_by_name(pattern)

    vah = tpo.get("vah")
    val = tpo.get("val")
    poc = tpo.get("poc")
    ib_width = tpo.get("ib_width")

    # Need at least VA reference
    if vah is None or val is None:
        return name_k, "no-cash-tpo:fallback-to-name"

    zone = zone_of(anchor, vah, val, ib_width)

    # EDGE_FADE: near edge on the correct side
    if zone == "near_val" and direction == "LONG":
        return "EDGE_FADE", f"near_val({val:.2f})+LONG"
    if zone == "near_vah" and direction == "SHORT":
        return "EDGE_FADE", f"near_vah({vah:.2f})+SHORT"

    # EDGE_FADE: outside value on the correct responsive side
    if zone == "below_value" and direction == "LONG":
        return "EDGE_FADE", f"below_value(<{val:.2f})+LONG"
    if zone == "above_value" and direction == "SHORT":
        return "EDGE_FADE", f"above_value(>{vah:.2f})+SHORT"

    # VALUE_RETURN: mid-value + direction toward POC
    if zone == "mid_value" and poc is not None:
        if direction == "LONG" and anchor < poc:
            return "VALUE_RETURN", f"mid_value toward POC({poc:.2f}) from below"
        if direction == "SHORT" and anchor > poc:
            return "VALUE_RETURN", f"mid_value toward POC({poc:.2f}) from above"

    # BREAK: beyond edge away from value
    if zone == "above_value" and direction == "LONG":
        return "BREAK", f"above_value(>{vah:.2f})+LONG breakout"
    if zone == "below_value" and direction == "SHORT":
        return "BREAK", f"below_value(<{val:.2f})+SHORT breakdown"

    # Edge on wrong side / mid-value away from POC → fallback to name
    return name_k, f"zone={zone}+{direction}:fallback-to-name"


# ── TPO loader: v9_tpo_sessions, CASH row only ────────────────────────────────

def load_tpo_by_date() -> Dict[str, Dict]:
    """Return dict[trading_date] → CASH TPO row for all dates >= CUTOFF.

    IB trap: only use the CASH row.  If no CASH row, the date is absent
    from the dict and must be skipped.
    """
    try:
        from backend.v9.db.read import read_all
    except ImportError as e:
        log.error("Cannot import backend.v9.db.read: %s", e)
        return {}

    rows = read_all(
        """SELECT trading_date, poc_price, vah_price, val_price,
                  ib_high, ib_low, ib_width
           FROM v9_tpo_sessions
           WHERE session_type = 'CASH'
             AND trading_date >= :cutoff
           ORDER BY trading_date""",
        {"cutoff": CUTOFF_DATE},
    )

    result: Dict[str, Dict] = {}
    for r in rows:
        d = r["trading_date"]
        result[d] = {
            "vah": r["vah_price"],
            "val": r["val_price"],
            "poc": r["poc_price"],
            "ib_high": r["ib_high"],
            "ib_low": r["ib_low"],
            "ib_width": r["ib_width"],
        }
    return result


# ── decision loader ────────────────────────────────────────────────────────────

def load_decisions(tpo_by_date: Dict[str, Dict]) -> List[Dict]:
    """Load gateway decisions from decisions_archive and current file.

    Only keeps decisions whose trading_date has a CASH TPO row.
    Skips decisions without entry_price.
    """
    archive_files = sorted(DECISIONS_DIR.glob("gateway_decisions.*.jsonl"))
    all_files = list(archive_files)
    if CURRENT_DECISIONS.exists():
        all_files.append(CURRENT_DECISIONS)

    records: List[Dict] = []
    skipped_no_tpo = 0
    skipped_no_entry = 0

    for fpath in all_files:
        try:
            lines = [l.strip() for l in fpath.read_text().splitlines() if l.strip()]
        except Exception as e:
            log.warning("Cannot read %s: %s", fpath.name, e)
            continue

        for line in lines:
            try:
                d = json.loads(line)
            except Exception:
                continue

            ts_str = d.get("ts") or d.get("timestamp") or ""
            date_str = ts_str[:10]
            if not date_str or date_str < CUTOFF_DATE:
                continue

            # Must have a CASH TPO row
            tpo = tpo_by_date.get(date_str)
            if tpo is None:
                skipped_no_tpo += 1
                continue

            entry = d.get("entry")
            if entry is None:
                skipped_no_entry += 1
                continue

            pattern = d.get("pattern") or ""
            direction = d.get("direction") or ""
            blocked_by = d.get("blocked_by")
            admitted_now = blocked_by is None

            # Structural anchor: prefer explicit field if present, else entry
            anchor = d.get("structural_anchor") or entry

            loc_kind, loc_reason = compute_location_kind(
                pattern=pattern,
                direction=direction,
                anchor=anchor,
                tpo=tpo,
            )
            name_k = kind_by_name(pattern)

            mfe = d.get("mfe_track") or {}
            stop = mfe.get("stop")

            records.append({
                "source": "live",
                "session": date_str,
                "time": ts_str[11:19],
                "pattern": pattern,
                "direction": direction,
                "entry": entry,
                "anchor": anchor,
                "stop": stop,
                "blocked_by": blocked_by,
                "admitted_now": admitted_now,
                "name_kind": name_k,
                "location_kind": loc_kind,
                "loc_reason": loc_reason,
                "zone": _get_zone(anchor, tpo),
                # day_type not in live decisions files
                "day_type": d.get("day_type") or "",
            })

    log.warning(
        "Decisions skipped: no_tpo=%d, no_entry=%d",
        skipped_no_tpo, skipped_no_entry,
    )
    return records


def _get_zone(anchor: float, tpo: Dict) -> str:
    vah = tpo.get("vah")
    val = tpo.get("val")
    ib_width = tpo.get("ib_width")
    if vah is None or val is None:
        return "?"
    return zone_of(anchor, vah, val, ib_width)


# ── analysis helpers ───────────────────────────────────────────────────────────

def compute_kind_change(name_kind: str, location_kind: str) -> str:
    if name_kind == location_kind:
        return "SAME"
    return f"{name_kind}→{location_kind}"


def main():
    print("Loading CASH TPO rows from v9_tpo_sessions …")
    tpo_by_date = load_tpo_by_date()
    if not tpo_by_date:
        print("  WARNING: no TPO rows found — check DB and CUTOFF_DATE")
    for d, tpo in sorted(tpo_by_date.items()):
        print(f"  {d}  VAH={tpo['vah']:.2f}  VAL={tpo['val']:.2f}  "
              f"POC={tpo['poc']:.2f}  IB={tpo['ib_high']}/{tpo['ib_low']}  "
              f"ib_width={tpo['ib_width']}")

    print(f"\nLoading gateway decisions (>= {CUTOFF_DATE}) …")
    all_rows = load_decisions(tpo_by_date)
    print(f"  {len(all_rows)} decisions loaded with CASH TPO data\n")

    if not all_rows:
        print("No decisions to analyze.")
        return

    # ── per-row summary table ─────────────────────────────────────────────────
    # key: (pattern, day_type)
    summary: Dict[Tuple[str, str], Dict] = {}
    changes_to: List[Dict] = []    # was blocked → would pass with location_kind
    changes_from: List[Dict] = []  # was passing → would block with location_kind

    for row in all_rows:
        pattern = row["pattern"]
        day_type = row.get("day_type") or ""
        name_k = row["name_kind"]
        loc_k = row["location_kind"]
        admitted_now = row["admitted_now"]

        # "would_block_location" = admitted now but location_kind would have
        # a different gating effect.  For approximation: if name_kind ≠
        # location_kind they would have been assessed differently.
        kind_changed = name_k != loc_k
        # would_admit with location is meaningful only when we know the
        # playbook allowed kinds — we don't have dp_intent in live files.
        # Instead track: admitted now but location_kind differs (direction change).

        key = (pattern, day_type)
        if key not in summary:
            summary[key] = {
                "pattern": pattern,
                "day_type": day_type,
                "name_kind": name_k,
                "loc_kind": loc_k,
                "n_total": 0,
                "n_admitted_now": 0,
                "n_kind_changed": 0,
                "changes": set(),
            }
        s = summary[key]
        s["n_total"] += 1
        if admitted_now:
            s["n_admitted_now"] += 1
        if kind_changed:
            s["n_kind_changed"] += 1
            s["changes"].add(compute_kind_change(name_k, loc_k))

            # Directional change tracking:
            # "was passing, location says different kind" → potential new block
            if admitted_now:
                changes_from.append(row)
            # "was blocked, location says different kind" → potential unblock
            else:
                changes_to.append(row)

    # ── Print main table ───────────────────────────────────────────────────────
    print("=" * 110)
    print("TABLE: pattern × day_type → kind comparison (decisions since 2026-09-02, CASH TPO)")
    print("=" * 110)
    hdr = (
        f"{'PATTERN':<32} {'DAY_TYPE':<6} {'NAME_KIND':<14} {'LOC_KIND':<14} "
        f"{'TOTAL':>6} {'ADMIT':>6} {'DIFF':>6}  {'CHANGE'}"
    )
    print(hdr)
    print("-" * 110)

    def sort_key(item):
        k, s = item
        has_change = bool(s["changes"])
        return (not has_change, k[0], k[1])

    for key, s in sorted(summary.items(), key=sort_key):
        change_str = ", ".join(sorted(s["changes"])) or "—"
        print(
            f"{s['pattern']:<32} {s['day_type']:<6} {s['name_kind']:<14} "
            f"{s['loc_kind']:<14} {s['n_total']:>6} {s['n_admitted_now']:>6} "
            f"{s['n_kind_changed']:>6}  {change_str}"
        )

    # ── Change detail sections ─────────────────────────────────────────────────
    print()
    print("=" * 110)
    print(f"WAS-PASSING → LOCATION-DIFFERS ({len(changes_from)}): admitted now but location_kind ≠ name_kind")
    print("  (These would be assessed with a different kind — could be newly blocked by playbook rules)")
    print("=" * 110)
    if changes_from:
        for row in sorted(changes_from, key=lambda r: (r["session"], r["time"]))[:60]:
            z = row.get("zone", "?")
            print(
                f"  {row['session']} {row['time']}  {row['pattern']:<28} {row['direction']:<6} "
                f"@{row['entry']:<9.2f}  zone={z:<12} "
                f"name={row['name_kind']:<14} loc={row['location_kind']:<14}  "
                f"reason: {row['loc_reason']}"
            )
    else:
        print("  (none)")

    print()
    print("=" * 110)
    print(f"WAS-BLOCKED → LOCATION-DIFFERS ({len(changes_to)}): blocked now but location_kind ≠ name_kind")
    print("  (These would be assessed with a different kind — could be newly admitted by playbook rules)")
    print("=" * 110)
    if changes_to:
        for row in sorted(changes_to, key=lambda r: (r["session"], r["time"]))[:60]:
            z = row.get("zone", "?")
            print(
                f"  {row['session']} {row['time']}  {row['pattern']:<28} {row['direction']:<6} "
                f"@{row['entry']:<9.2f}  zone={z:<12} "
                f"name={row['name_kind']:<14} loc={row['location_kind']:<14}  "
                f"blk={row['blocked_by']}  reason: {row['loc_reason']}"
            )
    else:
        print("  (none)")

    # ── Kind frequency comparison ──────────────────────────────────────────────
    print()
    print("=" * 60)
    print("KIND FREQUENCY: name_kind vs location_kind")
    print("=" * 60)
    name_freq: Dict[str, int] = defaultdict(int)
    loc_freq: Dict[str, int] = defaultdict(int)
    for row in all_rows:
        name_freq[row["name_kind"]] += 1
        loc_freq[row["location_kind"]] += 1

    all_kinds = sorted(set(list(name_freq.keys()) + list(loc_freq.keys())))
    print(f"{'KIND':<16} {'BY_NAME':>10} {'BY_LOC':>10} {'DELTA':>10}")
    print("-" * 50)
    for k in all_kinds:
        n = name_freq.get(k, 0)
        l = loc_freq.get(k, 0)
        print(f"{k:<16} {n:>10} {l:>10} {l-n:>+10}")

    # ── Zone distribution ─────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("ZONE DISTRIBUTION (from zone_of using CASH TPO VAH/VAL)")
    print("=" * 60)
    zone_freq: Dict[str, int] = defaultdict(int)
    for row in all_rows:
        zone_freq[row.get("zone", "?")] += 1
    for z, cnt in sorted(zone_freq.items(), key=lambda x: -x[1]):
        pct = 100 * cnt / len(all_rows)
        print(f"  {z:<16}  {cnt:>5}  ({pct:.1f}%)")

    # ── Dates without CASH TPO ─────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("TPO COVERAGE")
    print("=" * 60)
    dates_with_tpo = set(tpo_by_date.keys())
    decisions_dates = set()
    archive_files = sorted(DECISIONS_DIR.glob("gateway_decisions.*.jsonl"))
    all_files = list(archive_files)
    if CURRENT_DECISIONS.exists():
        all_files.append(CURRENT_DECISIONS)
    for fpath in all_files:
        try:
            for l in fpath.read_text().splitlines():
                try:
                    d = json.loads(l)
                    date = (d.get("ts") or "")[:10]
                    if date >= CUTOFF_DATE:
                        decisions_dates.add(date)
                except Exception:
                    pass
        except Exception:
            pass
    missing_tpo = sorted(decisions_dates - dates_with_tpo)
    print(f"  Dates with CASH TPO   : {sorted(dates_with_tpo)}")
    print(f"  Dates with decisions  : {sorted(decisions_dates)}")
    print(f"  Dates MISSING CASH TPO (skipped): {missing_tpo or '(none)'}")

    # ── Summary ────────────────────────────────────────────────────────────────
    n_diff = sum(1 for row in all_rows if row["name_kind"] != row["location_kind"])
    n_fallback = sum(1 for row in all_rows if "fallback-to-name" in row["loc_reason"])
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total decisions analyzed       : {len(all_rows)}")
    print(f"  Dates covered (CASH TPO found) : {sorted(dates_with_tpo)}")
    print(f"  name_kind ≠ location_kind      : {n_diff} ({100*n_diff/max(len(all_rows),1):.1f}%)")
    print(f"  fallback-to-name (zone unclear): {n_fallback}")
    print(f"  passing → location differs     : {len(changes_from)}")
    print(f"  blocked → location differs     : {len(changes_to)}")


if __name__ == "__main__":
    main()
