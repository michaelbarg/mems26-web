#!/usr/bin/env python3
"""T-426 A/B on the harness: prov (T-425 + structural stop + provisional label) vs
noprov (T-425 + structural stop, label lag kept) vs the night's fix_* (T-422 only)."""
import json, os, glob
D = os.path.dirname(os.path.abspath(__file__))
NIGHT = os.path.join(D, "..", "t422")
OPENING = ("OPENING",)

def load(p):
    return json.load(open(p)) if os.path.exists(p) else None

def opening_routes(d):
    out = []
    for r in d.get("routes") or []:
        c = str(r.get("classification") or "")
        if c.startswith("OPENING"):
            ex = (r.get("exec") or {}).get("live") or {}
            cmd = ex.get("command") if isinstance(ex, dict) else None
            placed = bool(cmd and cmd.get("ok"))
            rej = (cmd or {}).get("reason") if cmd else None
            out.append((r.get("il"), c, r.get("direction"), r.get("entry"), r.get("stop"), r.get("t1"),
                        r.get("blocked_by") or r.get("live_blocked_by"), "PLACED" if placed else (rej or "-")))
    return out

def trades(d):
    return [(t.get("classification"), t.get("pnl_usd") if t.get("pnl_usd") is not None else t.get("pnl"), t.get("il") or t.get("entry_il")) for t in d.get("trades") or []]

tot = {"prov": 0.0, "noprov": 0.0, "night": 0.0}
sessions = sorted({os.path.basename(p)[5:15] for p in glob.glob(os.path.join(D, "prov_*.json"))}, reverse=True)
for s in sessions:
    P, N, F = load(os.path.join(D, f"prov_{s}.json")), load(os.path.join(D, f"noprov_{s}.json")), load(os.path.join(NIGHT, f"fix_{s}.json"))
    print(f"=== {s} ===")
    for name, d in (("prov", P), ("noprov", N), ("night-fix", F)):
        if d is None:
            print(f"  {name:9s}: (no file)"); continue
        pnl = d.get("daily_pnl_harness")
        try:
            tot[name if name != "night-fix" else "night"] += float(pnl or 0)
        except Exception:
            pass
        op = [t for t in trades(d) if str(t[0]).startswith("OPENING")]
        print(f"  {name:9s}: routes={len(d.get('routes') or [])} trades={len(d.get('trades') or [])} Σ$={pnl}  opening-trades={op}")
        for o in opening_routes(d):
            print(f"      {o}")
print("\nΣ$ over sessions:", {k: round(v, 2) for k, v in tot.items()})
