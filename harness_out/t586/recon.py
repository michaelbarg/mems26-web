#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-586 (18.10) — live books vs the reference replay, trade by trade, on every live session since 23.09.
Reads: harness_out/t586/live_trades.psv (v9_trades mode=live), harness_out/t466/<REF>_<d>.json,
~/SierraChart_Data/v9_export/gateway_decisions.jsonl (+ decisions_archive/*). Read-only.
usage: recon.py [REF=t567ref] [--detail]"""
import json, glob, os, sys, collections, datetime
from zoneinfo import ZoneInfo
IL = ZoneInfo("Asia/Jerusalem")
ROOT = "/Users/michael/Downloads/mems26_web_git"
EXP = "/Users/michael/SierraChart_Data/v9_export"
REF = next((a for a in sys.argv[1:] if not a.startswith("--")), "t567ref")
DETAIL = "--detail" in sys.argv
COMM = 2.60

def mins(hhmmss):
    h, m, s = (hhmmss.split(":") + ["0", "0"])[:3]
    return int(h) * 60 + int(m) + int(s) / 60.0

live = []
for line in open(f"{ROOT}/harness_out/t586/live_trades.psv", encoding="utf-8"):
    r = line.rstrip("\n").split("|")
    if len(r) < 16:
        continue
    id_, sys_, dir_, state, e, ep, stop, t1, x, xp, xr, pnl, pnls, pat, dt, ses = r[:16]
    live.append(dict(id=int(id_), sys=int(sys_), dir=dir_, d="2026-" + e[:5], il=e[6:14], entry=float(ep),
                     stop=float(stop or 0), t1=float(t1 or 0), exit_il=x, exit_price=xp, exit_reason=xr,
                     pnl=float(pnl) if pnl else None, pnl_b=float(pnls) if pnls else None, pat=pat, dt=dt, ses=ses))

# live ledger (gateway_decisions.jsonl + archive), keyed by IL date
led = collections.defaultdict(list)
for p in [f"{EXP}/gateway_decisions.jsonl"] + sorted(glob.glob(f"{EXP}/decisions_archive/*.jsonl")):
    if not os.path.exists(p):
        continue
    for line in open(p, encoding="utf-8", errors="replace"):
        try:
            j = json.loads(line)
            t = datetime.datetime.fromisoformat(str(j.get("ts")).replace("Z", "+00:00")).astimezone(IL)
        except Exception:
            continue
        led[t.date().isoformat()].append((t.strftime("%H:%M:%S"), j))

def base(p):
    p = (p or "").upper()
    for suf in ("_LONG", "_SHORT"):
        if p.endswith(suf):
            p = p[: -len(suf)]
    return p

def load(d):
    p = f"{ROOT}/harness_out/t466/{REF}_{d}.json"
    return json.load(open(p)) if os.path.exists(p) else None

sessions = sorted(set(t["d"] for t in live))
if os.environ.get("RECON_FROM") and os.environ.get("RECON_TO"):
    # every session in the range that has a reference replay — sessions with zero live trades count too
    sessions = sorted(set(sessions) | {os.path.basename(p)[len(REF) + 1:len(REF) + 11]
                                        for p in glob.glob(f"{ROOT}/harness_out/t466/{REF}_2026-*.json")
                                        if os.environ["RECON_FROM"] <= os.path.basename(p)[len(REF) + 1:len(REF) + 11] <= os.environ["RECON_TO"]})
cat = collections.defaultdict(list)      # category -> rows
tot = collections.Counter()
missing_ref = []

for d in sessions:
    j = load(d)
    if not j:
        missing_ref.append(d); continue
    htr = [t for t in (j.get("trades") or [])]
    used = set()
    lday = [t for t in live if t["d"] == d]
    for lt in lday:
        if lt["pnl"] is None and lt["exit_reason"] == "SIERRA_FLAT" and lt["exit_il"] and mins(lt["exit_il"]) - mins(lt["il"]) < 1.5:
            cat["live_rejected"].append((d, lt, None, "broker reject (<90s SIERRA_FLAT)")); continue
        m = None
        for k, ht in enumerate(htr):
            if k in used or ht["direction"] != lt["dir"] or base(ht["classification"]) != base(lt["pat"]):
                continue
            if abs(mins(ht["fired_il"]) - mins(lt["il"])) <= 6.0:
                m = k; break
        if m is not None:
            used.add(m); ht = htr[m]
            cat["both"].append((d, lt, ht, ""))
        else:
            # the harness routed it but did not take it? find the route at that time
            why = "harness: not detected"
            for r in j.get("routes") or []:
                if r.get("direction") == lt["dir"] and base(r.get("classification")) == base(lt["pat"]) \
                        and abs(mins(r["il"]) - mins(lt["il"])) <= 6.0:
                    ex = (r.get("exec") or {}).get("live") or {}
                    why = "harness: blocked_by=%s live_blocked_by=%s cmd_rejected=%s" % (
                        r.get("blocked_by"), r.get("live_blocked_by"), (ex.get("command") or {}).get("rejected"))
                    break
            cat["live_only"].append((d, lt, None, why))
    for k, ht in enumerate(htr):
        if k in used:
            continue
        why = "live: not in ledger"
        for il, row in led.get(d, []):
            if row.get("direction") == ht["direction"] and base(row.get("pattern")) == base(ht["classification"]) \
                    and abs(mins(il) - mins(ht["fired_il"])) <= 6.0:
                why = "live: %s blocked_by=%s outcome=%s live_blocked_by=%s" % (
                    row.get("event_type"), row.get("blocked_by"), row.get("outcome"), row.get("live_blocked_by"))
                if row.get("blocked_by") or row.get("live_blocked_by"):
                    break
        cat["harness_only"].append((d, None, ht, why))

def hp(ht):
    return float(ht.get("pnl_usd") or 0)

print("REF=%s · live sessions %d (%s..%s)%s" % (REF, len(sessions), sessions[0], sessions[-1],
      " · missing ref: " + " ".join(missing_ref) if missing_ref else ""))
sess_ok = [d for d in sessions if d not in missing_ref]
L = sum((t["pnl"] or 0) for t in live if t["d"] in sess_ok)
LB = sum((t["pnl_b"] if t["pnl_b"] is not None else (t["pnl"] or 0)) for t in live if t["d"] in sess_ok)
H = sum(float(load(d)["daily_pnl_harness"] or 0) for d in sess_ok)
nl = sum(1 for t in live if t["d"] in sess_ok and t["pnl"] is not None)
nh = sum(len(load(d)["trades"]) for d in sess_ok)
print("Σ live books %+.2f$ (broker-priced %+.2f$, %d trades) · Σ replay %+.2f$ (%d trades) · GAP books−replay %+.2f$" % (L, LB, nl, H, nh, L - H))
both = cat["both"]
d_fill = sum((1 if lt["dir"] == "LONG" else -1) * (float(ht["fill_price"]) - lt["entry"]) * 5 for _, lt, ht, _ in both)
d_pnl = sum((lt["pnl"] or 0) - hp(ht) for _, lt, ht, _ in both)
print("\n[1] BOTH took (%d): Σ live %+.2f$ vs Σ replay %+.2f$ → Δ %+.2f$ · of which entry-fill Δ %+.2f$ (live entry vs replay fill, sign = cost to live)" % (
    len(both), sum((lt["pnl"] or 0) for _, lt, _, _ in both), sum(hp(ht) for _, _, ht, _ in both), d_pnl, -d_fill))
ex = collections.Counter()
for _, lt, ht, _ in both:
    ex[(lt["exit_reason"], "/".join(l["exit"] or "" for l in ht["legs"]))] += 1
print("    exit pairs (live, replay):", dict(ex))
lo = cat["live_only"]; ho = cat["harness_only"]
print("\n[2] LIVE only (%d): Σ %+.2f$" % (len(lo), sum((lt["pnl"] or 0) for _, lt, _, _ in lo)))
for w, n in collections.Counter(x[3] for x in lo).most_common():
    print("    %2d  %s" % (n, w))
print("\n[3] REPLAY only (%d): Σ %+.2f$ (what live missed)" % (len(ho), sum(hp(ht) for _, _, ht, _ in ho)))
for w, n in collections.Counter(x[3] for x in ho).most_common():
    print("    %2d  %s" % (n, w))
print("\n[4] broker-rejected live rows: %d" % len(cat["live_rejected"]))
print("\nidentity: GAP %+.2f = both Δ %+.2f + live-only %+.2f − replay-only %+.2f" % (
    L - H, d_pnl, sum((lt["pnl"] or 0) for _, lt, _, _ in lo), sum(hp(ht) for _, _, ht, _ in ho)))
if DETAIL:
    for k in ("both", "live_only", "harness_only", "live_rejected"):
        print("\n--", k)
        for d, lt, ht, why in cat[k]:
            a = "live #%d %s %s %s e=%.2f s=%.2f t1=%.2f x=%s %s pnl=%s" % (lt["id"], lt["il"][:5], lt["pat"], lt["dir"], lt["entry"], lt["stop"], lt["t1"], lt["exit_il"][:5] if lt["exit_il"] else "-", lt["exit_reason"], lt["pnl"]) if lt else "-"
            b = "replay %s %s %s e=%.2f fill=%.2f s=%.2f t1=%s x=%s %s pnl=%.2f" % (ht["fired_il"][:5], ht["classification"], ht["direction"], ht["entry"], ht["fill_price"], ht["stop_initial"], ht.get("t1_target"), ht["exit_il"], "/".join(l["exit"] or "" for l in ht["legs"]), hp(ht)) if ht else "-"
            print("  %s | %s | %s | %s" % (d, a, b, why))
