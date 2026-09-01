#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-152 — what the ONE live slot could actually have taken from the shadow set.

The bias this measures, stated plainly:

  live has exactly one `live_slot` (trading_gateway.py:418, a scalar).
  shadow has `self.shadow_trades: List[Dict]` — a list, appended without any
  slot check (`:3489-3494`, comment: "unlimited slots"). The 500/300 trim is a
  memory ring buffer, not a limit.

So when a mechanism fires 5 candidates inside one trade's holding period, the
shadow set records 5 and the promotion board counts 5 — while a live account
could have taken exactly 1. Every Σ metric is multiplied by N/K, AND so is the
sample count the promotion gate reads (SHADOW_TO_LIVE_POLICY.md:38 — 20 entry /
15 exit / 10 gate events). At N/K = 5 a mechanism "reaches the 20 minimum" on
FOUR real opportunities.

That is why T-152 blocks T-153 and not the other way round.

Two errors are reported SEPARATELY on purpose, because they have different
fixes and different signs:

  1. count inflation  = N/K — a pure multiplier, sign always ≥ 1, deterministic.
  2. selection bias   = mean(accepted) − mean(raw) — sign NOT determinable from
     code. Acceptance is time-ordered first-come, so the skipped fires are
     systematically those that arrived while a position was open, i.e.
     correlated with the prior trade's direction and with volatility
     clustering. `cluster_guard` exists precisely because fires cluster, which
     is direct evidence the correlation is non-zero. It must be MEASURED.

Honest-failure rules (Rule 1):
  * a trade with no exit_ts cannot bound the slot -> the whole session is
    NOT_JUDGEABLE. We do not impute a holding period.
  * K == 0 -> inflation is undefined, printed as NOT_JUDGEABLE, never as 1.0.

Scope limit, stated up front and repeated in the output: shadow has no
`pnl_sierra` and never can (no real fills), so every dollar here is
`pnl_usd` — the calculation, not the broker. T-193 fixes that for live only.

    python3 scripts/shadow_slot_scan.py                  # all shadow, by pattern
    python3 scripts/shadow_slot_scan.py --since 2026-08-01
    python3 scripts/shadow_slot_scan.py --mode live      # sanity: should be ~1.0
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# .env FIRST — three scripts have already reported a false zero because they
# fell through to SQLite without it (T-161, and sot_health before that).
try:
    from backend.v9.core.env_loader import load_env  # type: ignore
    load_env()
except Exception:
    for _ln in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        _ln = _ln.strip()
        if _ln and not _ln.startswith("#") and "=" in _ln:
            _k, _v = _ln.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.split("#")[0].strip())

if "postgres" not in os.environ.get("DATABASE_URL", ""):
    sys.exit("DATABASE_URL is not Postgres — refusing to report a number from "
             "a stale SQLite mirror (T-161).")

from backend.v9.db.read import read_all  # noqa: E402


def scan(rows: List[dict]) -> dict:
    """One pass. `rows` must already be sorted by entry_ts ascending."""
    accepted: List[dict] = []
    skipped: List[dict] = []
    slot_free_at = None
    holder: Optional[int] = None

    for t in rows:
        if slot_free_at is not None and t["entry_ts"] < slot_free_at:
            skipped.append({"id": t["id"], "blocked_by": "live_slot_occupied",
                            "holder": holder})
            continue
        accepted.append(t)
        slot_free_at = t["exit_ts"]
        holder = t["id"]
    return {"accepted": accepted, "skipped": skipped}


def _pnl(rows: List[dict]) -> float:
    return sum(float(r["pnl_usd"] or 0.0) for r in rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-07-01")
    ap.add_argument("--mode", default="shadow")
    a = ap.parse_args()

    rows = read_all(
        "SELECT id, entry_ts, exit_ts, pnl_usd, pattern_id_at_entry AS pat, "
        "       direction, firing_system "
        "FROM v9_trades "
        "WHERE mode = :m AND state = 'CLOSED' AND entry_ts >= :s "
        "ORDER BY entry_ts ASC",
        {"m": a.mode, "s": a.since}) or []

    if not rows:
        print(f"no CLOSED {a.mode} trades since {a.since} — nothing to scan")
        return 1

    # Rule 1: a missing exit_ts cannot bound the slot. Do not impute.
    unbounded = [r for r in rows if r["exit_ts"] is None]
    rows = [r for r in rows if r["exit_ts"] is not None]

    print(f"\n{'='*74}")
    print(f" T-152 · slot-aware scan · mode={a.mode} · since={a.since}")
    print(f"{'='*74}")
    if unbounded:
        print(f" ⚠️  {len(unbounded)} rows have no exit_ts and were DROPPED, not "
              f"imputed (Rule 1).\n     ids: {[r['id'] for r in unbounded][:12]}")

    # ── whole set ───────────────────────────────────────────────────────────
    res = scan(rows)
    N, K = len(rows), len(res["accepted"])
    print(f"\n POOLED")
    print(f"   fires_raw (N)      {N}")
    print(f"   fires_accepted (K) {K}")
    print(f"   fires_skipped      {N - K}")
    if K:
        print(f"   inflation N/K      {N/K:.2f}×")
    else:
        print(f"   inflation N/K      NOT_JUDGEABLE (K=0)")
    print(f"   pnl_raw            ${_pnl(rows):,.2f}")
    print(f"   pnl_slot_limited   ${_pnl(res['accepted']):,.2f}")
    print(f"   pnl_bias           ${_pnl(rows) - _pnl(res['accepted']):,.2f}")
    if K:
        mr, ma = _pnl(rows)/N, _pnl(res["accepted"])/K
        print(f"   mean_raw           ${mr:,.2f}")
        print(f"   mean_accepted      ${ma:,.2f}")
        print(f"   selection bias     ${ma - mr:+,.2f} per trade   "
              f"← sign is a MEASUREMENT, not an assumption")

    # ── per mechanism ───────────────────────────────────────────────────────
    # The slot is global: a mechanism's candidate is skipped by whatever holds
    # the slot, not only by its own kind. So the scan runs on the FULL stream
    # and the per-pattern numbers are read off that one pass.
    by: Dict[str, dict] = defaultdict(lambda: {"n": 0, "k": 0})
    acc_ids = {r["id"] for r in res["accepted"]}
    for r in rows:
        p = r["pat"] or f"system{r['firing_system']}"
        by[p]["n"] += 1
        if r["id"] in acc_ids:
            by[p]["k"] += 1

    print(f"\n PER MECHANISM  (K is what the promotion gate must read, never N)")
    print(f"   {'pattern':<28} {'N':>5} {'K':>5} {'N/K':>7}  {'gate 20/15/10':>14}")
    for p, d in sorted(by.items(), key=lambda kv: -kv[1]["n"]):
        infl = f"{d['n']/d['k']:.2f}×" if d["k"] else "n/a"
        gate = "OK" if d["k"] >= 20 else f"{d['k']}/20 short"
        print(f"   {p[:28]:<28} {d['n']:>5} {d['k']:>5} {infl:>7}  {gate:>14}")

    print(f"\n ⚠️  LIMIT — shadow has no `pnl_sierra` and never can (no real")
    print(f"     fills). Every dollar above is `pnl_usd`: the calculation, not")
    print(f"     the broker. T-193 fixes that for LIVE only.")
    print(f"{'='*74}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
