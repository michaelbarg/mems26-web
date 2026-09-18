#!/usr/bin/env python3
"""T-422 §3 — 3-way harness comparison: BASE (pre-fix) vs FIX vs --oe-closed.

BASE runs in a worktree pinned at the pre-fix HEAD, so its "live path" is the
buggy one (fwd_harness --push-mode firstpush pushes a developing bar with
o=h=l=c=open at ts+3s, which is exactly what the live gate judged).
If FIX == OE-CLOSED, the fix implements the counterfactual the flag encodes.
"""
import json
import os
import sys

MAIN = "/Users/michael/Downloads/mems26_web_git/harness_out/t422"
BASE = "/tmp/mems_base_t422/harness_out/t422"
SESSIONS = ["2026-09-18", "2026-09-17", "2026-09-16", "2026-09-15", "2026-09-11"]

OPENING = ("OPENING", "ORR", "DRIVE", "TEST_DRIVE", "PULLBACK_CONT")


def is_opening(c):
    c = (c or "").upper()
    return any(k in c for k in OPENING)


def load(path):
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


def summ(d):
    if d is None:
        return None
    tr = d.get("trades") or []
    op = [t for t in tr if is_opening(t.get("classification"))]
    return {
        "routes": len(d.get("routes") or []),
        "ww": len(d.get("would_write") or []),
        "trades": len(tr),
        "pnl": round(sum(float(t.get("pnl_usd") or 0) for t in tr), 2),
        "op_n": len(op),
        "op_pnl": round(sum(float(t.get("pnl_usd") or 0) for t in op), 2),
        "op": [(t.get("classification"), t.get("direction"), t.get("fired_il"),
                t.get("entry"), t.get("outcome"), t.get("pnl_usd")) for t in op],
    }


def main():
    rows = []
    print("%-12s %-10s %6s %4s %6s %9s %5s %9s" %
          ("session", "variant", "routes", "ww", "trades", "PnL$", "op_n", "openPnL$"))
    print("-" * 74)
    for s in SESSIONS:
        r = {}
        for name, path in (("BASE(pre-fix)", f"{BASE}/base_{s}.json"),
                           ("FIX", f"{MAIN}/fix_{s}.json"),
                           ("--oe-closed", f"{MAIN}/oeclosed_{s}.json")):
            v = summ(load(path))
            r[name] = v
            if v is None:
                print("%-12s %-10s  MISSING" % (s, name))
                continue
            print("%-12s %-10s %6d %4d %6d %9.2f %5d %9.2f" %
                  (s, name, v["routes"], v["ww"], v["trades"], v["pnl"],
                   v["op_n"], v["op_pnl"]))
        rows.append((s, r))
        print()

    print("=" * 74)
    print("OPENING TRADES per variant (classification, dir, fired_il, entry, outcome, $)")
    for s, r in rows:
        print("\n%s:" % s)
        for name in ("BASE(pre-fix)", "FIX", "--oe-closed"):
            v = r.get(name)
            print("  %-13s %s" % (name, v["op"] if v else "MISSING"))

    print("\n" + "=" * 74)
    print("DELTAS")
    tot = {"BASE(pre-fix)": 0.0, "FIX": 0.0, "--oe-closed": 0.0}
    totop = dict(tot)
    ident = True
    for s, r in rows:
        if not all(r.get(k) for k in tot):
            ident = False
            continue
        for k in tot:
            tot[k] += r[k]["pnl"]
            totop[k] += r[k]["op_pnl"]
        same = (r["FIX"]["op"] == r["--oe-closed"]["op"]
                and r["FIX"]["ww"] == r["--oe-closed"]["ww"])
        ident = ident and same
        print("  %s  FIX vs BASE: routes %+d, openPnL %+.2f | FIX == --oe-closed on "
              "opening trades+would_write: %s"
              % (s, r["FIX"]["routes"] - r["BASE(pre-fix)"]["routes"],
                 r["FIX"]["op_pnl"] - r["BASE(pre-fix)"]["op_pnl"], same))
    print("\n  TOTAL PnL  base=%.2f fix=%.2f oeclosed=%.2f" %
          (tot["BASE(pre-fix)"], tot["FIX"], tot["--oe-closed"]))
    print("  TOTAL opening PnL  base=%.2f fix=%.2f oeclosed=%.2f  => fix-base %+.2f"
          % (totop["BASE(pre-fix)"], totop["FIX"], totop["--oe-closed"],
             totop["FIX"] - totop["BASE(pre-fix)"]))
    print("  FIX == --oe-closed on every session (opening trades + would_write): %s"
          % ident)


if __name__ == "__main__":
    main()
