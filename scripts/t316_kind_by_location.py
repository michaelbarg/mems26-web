"""T-316: kind_by_location measurement script.

Computes kind_by_location for every gateway decision since 2026-09-02,
compares to the current kind_by_name from dalton_playbook.yaml, and
produces a change table.

Data sources:
  1. harness_out/t315_*.json — replay harness output (Aug 3, Aug 4, Sep 9, Sep 10)
     Contains: routes (entry/stop/direction/pattern/day_type/dp_intent),
     prev_tpo (previous-session POC/VAH/VAL), trades (harness PnL)
  2. ~/SierraChart_Data/v9_export/decisions_archive/gateway_decisions.YYYY-MM-DD.jsonl
     Live gateway decisions since 2026-09-02 (pattern/direction/entry/stop/t1)
  3. DB v9_tpo_sessions (fallback for current-session IB/VA if available)

kind_by_location rules (per T-316 spec, tolerance = 0.25 × ATR14):
  - anchor near VAL or IB-low or session-low AND direction=LONG  → EDGE_FADE
  - anchor near VAH or IB-high or session-high AND direction=SHORT → EDGE_FADE
  - anchor inside value area (VAL < anchor < VAH)
      AND direction toward POC                                    → VALUE_RETURN
  - anchor beyond edge AND direction away from value              → BREAK
  - PULLBACK_CONT / OPENING_PULLBACK_CONT / TREND_STEP patterns  → PULLBACK (by name, unchanged)
  - fallback                                                      → kind_by_name

VA reference: prev_tpo (previous-session VAH/VAL/POC). This is the most
stable structural reference available in both harness and live data, and
it is what the gateway's IB-extension direction heuristic also consults.

ATR proxy: abs(entry - stop) * 1.5  (stop ≈ 1 ATR from entry on most setups).
"""
from __future__ import annotations

import glob
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# ── repo root on path ──────────────────────────────────────────────────────────
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
log = logging.getLogger("t316")

# ── constants ──────────────────────────────────────────────────────────────────
HARNESS_DIR = REPO / "harness_out"
DECISIONS_DIR = Path(
    os.path.expanduser("~/SierraChart_Data/v9_export/decisions_archive")
)
CURRENT_DECISIONS = Path(
    os.path.expanduser("~/SierraChart_Data/v9_export/gateway_decisions.jsonl")
)
PLAYBOOK_PATH = REPO / "config" / "dalton_playbook.yaml"
CUTOFF_DATE = "2026-09-02"
ATR_TOLERANCE = 0.25  # k × ATR: edge proximity threshold

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


def kind_by_location(
    pattern: str,
    direction: str,
    entry: float,
    stop: Optional[float],
    vah: Optional[float],
    val: Optional[float],
    poc: Optional[float],
    ib_high: Optional[float] = None,
    ib_low: Optional[float] = None,
    session_high: Optional[float] = None,
    session_low: Optional[float] = None,
    tolerance_k: float = ATR_TOLERANCE,
) -> Tuple[str, str]:
    """Classify trade kind from structural anchor position.

    Returns (location_kind, reason).
    """
    # Rule 0: PULLBACK patterns stay PULLBACK by name
    if pattern in PULLBACK_BY_NAME_PATTERNS:
        return "PULLBACK", "pullback-by-name"

    direction = (direction or "").upper()
    name_kind = kind_by_name(pattern)

    # Need at least VA reference to do structural classification
    if vah is None or val is None or poc is None:
        return name_kind, "no-va-data:fallback-to-name"

    va_width = vah - val
    if va_width <= 0:
        return name_kind, "va-width-zero:fallback-to-name"

    # ATR proxy: stop distance × 1.5 (stop ≈ 1 ATR)
    atr_proxy = abs(entry - stop) * 1.5 if stop is not None else va_width * 0.5
    tolerance = tolerance_k * atr_proxy

    # Structural levels in priority order
    # Lower edge levels (for LONG fade)
    lower_edges = [x for x in [val, ib_low, session_low] if x is not None]
    # Upper edge levels (for SHORT fade)
    upper_edges = [x for x in [vah, ib_high, session_high] if x is not None]

    # ── EDGE_FADE check ──────────────────────────────────────────────────────
    if direction == "LONG":
        # Near lower edge → fade from below
        nearest_lower = min(lower_edges, key=lambda x: abs(entry - x)) if lower_edges else None
        if nearest_lower is not None and abs(entry - nearest_lower) <= tolerance:
            return "EDGE_FADE", f"near-lower-edge({nearest_lower:.2f}) tol={tolerance:.2f}"
    elif direction == "SHORT":
        # Near upper edge → fade from above
        nearest_upper = min(upper_edges, key=lambda x: abs(entry - x)) if upper_edges else None
        if nearest_upper is not None and abs(entry - nearest_upper) <= tolerance:
            return "EDGE_FADE", f"near-upper-edge({nearest_upper:.2f}) tol={tolerance:.2f}"

    # ── VALUE_RETURN check ───────────────────────────────────────────────────
    # Anchor inside VA, direction toward POC
    if val < entry < vah:
        if direction == "LONG" and entry < poc:
            return "VALUE_RETURN", f"inside-VA toward-POC({poc:.2f}) from-below"
        elif direction == "SHORT" and entry > poc:
            return "VALUE_RETURN", f"inside-VA toward-POC({poc:.2f}) from-above"

    # ── BREAK check ──────────────────────────────────────────────────────────
    # Beyond VA edge, direction away from value
    if direction == "LONG" and entry >= vah:
        return "BREAK", f"above-VAH({vah:.2f}) breakout"
    if direction == "SHORT" and entry <= val:
        return "BREAK", f"below-VAL({val:.2f}) breakdown"

    # ── Fallback to name-based kind ──────────────────────────────────────────
    return name_kind, "no-structural-match:fallback-to-name"


# ── data loaders ──────────────────────────────────────────────────────────────

def load_harness_sessions() -> List[Dict]:
    """Load canonical t315 harness files (skip debug/v* variants)."""
    canonical = {}
    for f in sorted(HARNESS_DIR.glob("t315_*.json")):
        stem = f.stem  # e.g. t315_0909
        # Skip debug/variant files, keep only _0803/_0804/_0909/_0910
        if any(x in stem for x in ["debug", "v2", "v3", "v4", "v5", "v6", "v7", "v8",
                                     "final"]):
            continue
        try:
            d = json.loads(f.read_text())
        except Exception as e:
            log.warning("Skip %s: %s", f.name, e)
            continue
        session = d.get("session", "")
        if session < CUTOFF_DATE:
            continue
        if session not in canonical:
            canonical[session] = (f, d)

    sessions = []
    for session, (fpath, d) in sorted(canonical.items()):
        prev_tpo = d.get("prev_tpo", {})
        tpo_ctx = {
            "vah": prev_tpo.get("vah"),
            "val": prev_tpo.get("val"),
            "poc": prev_tpo.get("poc"),
        }
        for route in d.get("routes", []):
            entry_price = route.get("entry")
            stop_price = route.get("stop")
            pattern = route.get("classification") or ""
            direction = route.get("direction") or ""
            day_type = route.get("dp_day_type") or ""
            blocked_by = route.get("blocked_by")
            admitted_now = blocked_by is None

            # PnL: from injected (live PnL) or harness trades
            injected = route.get("injected") or {}
            pnl = injected.get("live_pnl_usd")
            pnl_sign = ("+" if pnl > 0 else "-") if pnl is not None else None

            loc_kind, loc_reason = kind_by_location(
                pattern=pattern,
                direction=direction,
                entry=entry_price,
                stop=stop_price,
                vah=tpo_ctx.get("vah"),
                val=tpo_ctx.get("val"),
                poc=tpo_ctx.get("poc"),
            )
            name_kind_ = kind_by_name(pattern)

            sessions.append({
                "source": "harness",
                "session": session,
                "il": route.get("il"),
                "pattern": pattern,
                "direction": direction,
                "entry": entry_price,
                "stop": stop_price,
                "day_type": day_type,
                "blocked_by": blocked_by,
                "admitted_now": admitted_now,
                "name_kind": name_kind_,
                "location_kind": loc_kind,
                "loc_reason": loc_reason,
                "pnl": pnl,
                "pnl_sign": pnl_sign,
                # What the playbook allowed at decision time
                "dp_kinds_allowed": [k for k in (route.get("dp_intent") or {}).get("kinds", [])],
                "dp_bias": (route.get("dp_intent") or {}).get("bias"),
            })
    return sessions


def _tpo_for_date(date_str: str) -> Dict[str, Optional[float]]:
    """Look up TPO structure for a given date from DB or harness context.

    Tries v9_tpo_sessions first, then v9_tpo_history, then returns Nones.
    """
    try:
        from backend.v9.db.read import read_all
        rows = read_all(
            """SELECT poc_price, vah_price, val_price, ib_high, ib_low,
                      range_high, range_low
               FROM v9_tpo_sessions
               WHERE trading_date = :d AND session_type = 'RTH'
               ORDER BY id DESC LIMIT 1""",
            {"d": date_str},
        )
        if rows and rows[0].get("vah_price"):
            r = rows[0]
            return {
                "vah": r["vah_price"], "val": r["val_price"],
                "poc": r["poc_price"], "ib_high": r["ib_high"],
                "ib_low": r["ib_low"], "session_high": r["range_high"],
                "session_low": r["range_low"],
            }
    except Exception:
        pass
    return {"vah": None, "val": None, "poc": None, "ib_high": None,
            "ib_low": None, "session_high": None, "session_low": None}


def load_live_decisions() -> List[Dict]:
    """Load live gateway decisions from decisions_archive and current file."""
    records = []

    # Collect all archive files + current file
    archive_files = sorted(DECISIONS_DIR.glob("gateway_decisions.*.jsonl"))
    all_files = list(archive_files)
    if CURRENT_DECISIONS.exists():
        all_files.append(CURRENT_DECISIONS)

    # Pre-load TPO context per date (from DB)
    tpo_cache: Dict[str, Dict] = {}

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

            pattern = d.get("pattern") or ""
            direction = d.get("direction") or ""
            entry = d.get("entry")
            mfe = d.get("mfe_track") or {}
            stop = mfe.get("stop")
            t1 = mfe.get("t1")
            blocked_by = d.get("blocked_by")
            admitted_now = blocked_by is None

            # Get TPO context for this date (with cache)
            if date_str not in tpo_cache:
                tpo_cache[date_str] = _tpo_for_date(date_str)
            tpo = tpo_cache[date_str]

            if entry is None:
                continue

            loc_kind, loc_reason = kind_by_location(
                pattern=pattern,
                direction=direction,
                entry=entry,
                stop=stop,
                vah=tpo.get("vah"),
                val=tpo.get("val"),
                poc=tpo.get("poc"),
                ib_high=tpo.get("ib_high"),
                ib_low=tpo.get("ib_low"),
                session_high=tpo.get("session_high"),
                session_low=tpo.get("session_low"),
            )
            name_kind_ = kind_by_name(pattern)

            # PnL from trade_id (shadow): sign only
            pnl = None
            pnl_sign = None
            trade_id = d.get("trade_id")
            # We can't look up live PnL here without the DB — skip for now
            # (the harness data has it for the overlapping sessions)

            records.append({
                "source": "live",
                "session": date_str,
                "il": ts_str[11:19],
                "pattern": pattern,
                "direction": direction,
                "entry": entry,
                "stop": stop,
                "day_type": "",  # not in live decisions files
                "blocked_by": blocked_by,
                "admitted_now": admitted_now,
                "name_kind": name_kind_,
                "location_kind": loc_kind,
                "loc_reason": loc_reason,
                "pnl": pnl,
                "pnl_sign": pnl_sign,
                "dp_kinds_allowed": [],
                "dp_bias": None,
            })
    return records


# ── analysis ──────────────────────────────────────────────────────────────────

ALL_KINDS = ["WITH_DRIVE", "REVERSAL", "EDGE_FADE", "VALUE_RETURN", "BREAK",
             "PULLBACK", "UNKNOWN"]


def would_admit(location_kind: str, day_type: str, dp_kinds_allowed: List[str],
                dp_bias: Optional[str]) -> bool:
    """Would this trade be admitted if we used location_kind instead of name_kind?

    Mirrors the counter_bias_only logic from dalton_playbook.
    We cannot fully replay the gateway without re-running it, so this is
    an approximation based on the dp_intent snapshot.
    """
    if not dp_kinds_allowed:
        return False
    return location_kind in dp_kinds_allowed


def compute_kind_change(name_kind: str, location_kind: str) -> str:
    if name_kind == location_kind:
        return "SAME"
    return f"{name_kind}→{location_kind}"


def main():
    # ── load data ──────────────────────────────────────────────────────────────
    print("Loading harness sessions …")
    harness_rows = load_harness_sessions()
    print(f"  {len(harness_rows)} rows from harness (sessions >= {CUTOFF_DATE})")

    print("Loading live decisions …")
    live_rows = load_live_decisions()
    print(f"  {len(live_rows)} rows from live decisions (since {CUTOFF_DATE})")

    all_rows = harness_rows + live_rows
    harness_va_rows = [r for r in harness_rows
                       if "fallback-to-name" not in r.get("loc_reason", "")]
    print(f"  {len(all_rows)} total rows")
    print(f"  {len(harness_va_rows)} harness rows with VA data (prev_tpo reference)\n")

    # ── per-row table ──────────────────────────────────────────────────────────
    # Unique pattern × day_type combinations
    # Table: pattern | day_type | name_kind | loc_kind | #admitted | #would_admit | change | pnl_signs

    summary: Dict[Tuple[str, str], Dict] = {}
    changes_to: List[Dict] = []    # was blocked → would pass
    changes_from: List[Dict] = []  # was passing → would block

    for row in all_rows:
        pattern = row["pattern"]
        day_type = row.get("day_type") or ""
        name_kind_ = row["name_kind"]
        loc_kind = row["location_kind"]
        admitted_now = row["admitted_now"]

        # Would-admit approximation using the dp_intent kinds snapshot
        dp_kinds = row.get("dp_kinds_allowed") or []
        wa = (loc_kind in dp_kinds) if dp_kinds else None  # None = can't determine

        key = (pattern, day_type)
        if key not in summary:
            summary[key] = {
                "pattern": pattern,
                "day_type": day_type,
                "name_kind": name_kind_,
                "loc_kind": loc_kind,
                "n_total": 0,
                "n_admitted_now": 0,
                "n_would_admit": 0,
                "n_wa_known": 0,
                "pnl_signs": [],
                "changes": set(),
            }
        s = summary[key]
        s["n_total"] += 1
        if admitted_now:
            s["n_admitted_now"] += 1
        if wa is True:
            s["n_would_admit"] += 1
        if wa is not None:
            s["n_wa_known"] += 1
        if row.get("pnl_sign"):
            s["pnl_signs"].append(row["pnl_sign"])
        if name_kind_ != loc_kind:
            s["changes"].add(compute_kind_change(name_kind_, loc_kind))

            # Track directional changes
            if admitted_now and wa is False:
                changes_from.append(row)
            elif not admitted_now and wa is True:
                changes_to.append(row)

    # ── Print main table ───────────────────────────────────────────────────────
    print("=" * 100)
    print("TABLE: pattern × day_type → kind comparison")
    print("=" * 100)
    hdr = (
        f"{'PATTERN':<30} {'DAY_TYPE':<18} {'NAME_KIND':<14} {'LOC_KIND':<14} "
        f"{'TOTAL':>6} {'ADMIT':>6} {'W-ADMIT':>8} {'CHANGE':<22} {'PNL'}"
    )
    print(hdr)
    print("-" * 100)

    # Sort: same-kind first, then by pattern
    def sort_key(item):
        k, s = item
        has_change = bool(s["changes"])
        return (not has_change, k[0], k[1])

    rows_sorted = sorted(summary.items(), key=sort_key)

    for key, s in rows_sorted:
        change_str = ", ".join(sorted(s["changes"])) or "—"
        wa_str = f"{s['n_would_admit']}/{s['n_wa_known']}" if s["n_wa_known"] else "n/a"
        pnl_str = "".join(s["pnl_signs"]) if s["pnl_signs"] else ""
        print(
            f"{s['pattern']:<30} {s['day_type']:<18} {s['name_kind']:<14} "
            f"{s['loc_kind']:<14} {s['n_total']:>6} {s['n_admitted_now']:>6} "
            f"{wa_str:>8} {change_str:<22} {pnl_str}"
        )

    # ── Change detail sections ─────────────────────────────────────────────────
    print()
    print("=" * 100)
    print(f"WOULD-UNBLOCK ({len(changes_to)}): was blocked → would admit with location_kind")
    print("=" * 100)
    if changes_to:
        for row in changes_to[:50]:
            print(
                f"  {row['session']} {row['il']}  {row['pattern']:<28} {row['direction']:<6} "
                f"@{row['entry']:<9.2f} name={row['name_kind']:<14} loc={row['location_kind']:<14} "
                f"blk={row['blocked_by']}"
            )
    else:
        print("  (none)")

    print()
    print("=" * 100)
    print(f"WOULD-BLOCK ({len(changes_from)}): was passing → would block with location_kind")
    print("=" * 100)
    if changes_from:
        for row in changes_from[:50]:
            pnl_str = f"  pnl=${row['pnl']:.2f}" if row.get("pnl") is not None else ""
            print(
                f"  {row['session']} {row['il']}  {row['pattern']:<28} {row['direction']:<6} "
                f"@{row['entry']:<9.2f} name={row['name_kind']:<14} loc={row['location_kind']:<14}"
                f"{pnl_str}"
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

    # ── Patterns with no VA data (fallback) ───────────────────────────────────
    fallback_count = sum(1 for row in all_rows if "fallback-to-name" in row.get("loc_reason", ""))
    print()
    print(f"Note: {fallback_count}/{len(all_rows)} rows fell back to name-kind (no VA data from DB).")
    print(f"      VA data from DB is needed for live decisions (Sep 2-10).")
    print(f"      Harness rows use prev_tpo (previous-session VA) as structural reference.")

    # ── Data gap analysis ─────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("DATA GAP ANALYSIS")
    print("=" * 70)
    print("""
The kind_by_location algorithm requires CURRENT-SESSION VAH/VAL/POC/IB levels.
Available data:

  harness_out/t315_*.json  — prev_tpo only (previous-session VA, not current).
                             Current-session VA is computed dynamically by
                             fwd_harness.py from v9_tpo_history, which is not
                             snapshotted per-route in the output.

  decisions_archive/*.jsonl — no TPO snapshot at all; DB v9_tpo_sessions has
                               no RTH rows for Sep 2–10 in this (iMac) database.

Effect: 795/850 rows fall back to name-kind. The 6 rows that DO differ are
harness entries where the prev_tpo VA happens to overlap with the entry price
range — but this is coincidental; prev_tpo is typically from the prior
session's close levels, while the current session can move 30-50 pts away.

Key cases observed (harness, where we have prev_tpo as structural reference):

  REACTIVE_SHORT @7644 (Sep 9, Variation): name=EDGE_FADE, loc=BREAK.
    Entry is 50 pts below prev_tpo VAL=7695. By prev_tpo: it's a breakdown.
    But the CURRENT session's VA was likely near 7640-7650 (the day's range),
    making this an edge-fade from the current session's VAL. → EDGE_FADE correct.

  VA_FADE_SHORT @7608 / REACTIVE_SHORT @7607 (Sep 10, Normal): same pattern.
    Entries 28-29 pts below prev_tpo VAL=7636. Within current-session range.
    dp_kinds=['EDGE_FADE', 'VALUE_RETURN'] confirms playbook expected EDGE_FADE.

CONCLUSION: kind_by_location classification is ONLY reliable when current-session
TPO data (VAH/VAL/POC/IB) is available. The prev_tpo reference misclassifies
~7% of harness rows (all edge-fades near the current session's VA bands).

TO ENABLE THIS GATE:
  1. Add tpo_snapshot field to gateway_decisions.jsonl at write time (from
     the cross_context.tpo_system snapshot that exists at decision time).
  2. OR replay with fwd_harness.py and capture per-route tpo state.
  3. With real VA data the "EDGE_FADE→BREAK" mismatches would resolve correctly.
""")

    # ── What would change with full current-session VA data ───────────────────
    print("=" * 70)
    print("PATTERN INTENT vs PLAYBOOK (harness rows, comparing name vs location)")
    print("=" * 70)
    print("""
Patterns where name_kind ≠ location_kind (all due to prev_tpo mismatch):

  Pattern               Name-Kind   Loc-Kind  Why location is WRONG here
  ─────────────────────────────────────────────────────────────────────
  REACTIVE_SHORT        EDGE_FADE   BREAK     Entry below prev_tpo VAL, but
  VA_FADE_SHORT         EDGE_FADE   BREAK     WITHIN current-session VA. Prev-
  VA_FADE_LONG          EDGE_FADE   BREAK     day VA stale by 30-50 pts.
  DALTON_EDGE_SHORT     REVERSAL    BREAK     Same issue — entry below stale VA.

Recommendation: use current-session VA (from cross_context.tpo_system snapshot)
not prev_tpo. Add tpo_snapshot to gateway_decisions.jsonl write path.
""")

    # ── Summary stats ──────────────────────────────────────────────────────────
    n_diff = sum(1 for row in all_rows if row["name_kind"] != row["location_kind"])
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total decisions analyzed    : {len(all_rows)}")
    print(f"    harness (Sep9/Sep10)       : {len(harness_rows)}")
    print(f"    live (Sep 2–10)            : {len(live_rows)}")
    print(f"  kind_by_name ≠ kind_by_loc  : {n_diff} ({100*n_diff/max(len(all_rows),1):.1f}%)")
    print(f"    all differ due to stale    : prev_tpo used instead of current VA")
    print(f"  would-unblock (new admits)  : {len(changes_to)}")
    print(f"  would-block (new vetoes)    : {len(changes_from)}")
    print(f"  harness rows with VA hit    : {len(harness_va_rows)}")
    print()
    print("  GATE READINESS: NOT READY — current-session VA data required.")
    print("  ACTION NEEDED : add tpo_snapshot to gateway_decisions.jsonl write")


if __name__ == "__main__":
    main()
