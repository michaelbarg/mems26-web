#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stage5_context_root_wf.py — T-543 stage 5 (CC_ORDER_2026-10-05_DAILY_DALTON §3, BRIEF §2.4), read-only.

The variant: in phases C and D the ROOT is the context (IB structure, hour bucket, entry kind) and the day-type
label is information only. Phases A/B keep the live tree's leaf untouched. Measured WALK-FORWARD against t529b
(the live-config replay, 65 sessions): for session t the cell table is built from sessions < t only — a cell
(structure, hour, kind) is TAKE when it has n >= N_MIN prior candidates and their summed score is > 0, else SKIP.
Nothing is fitted on the session being scored; the first WARMUP sessions only feed the table.

Both sides are scored with the same fixed candidate model as scripts/context_table.py (own stop, 1.5R target,
first touch on the 5-min bars, EOD close, $5/pt, 2.60$ commission) so the comparison is like-for-like: the tree's
TAKE pool on the session vs the variant's TAKE pool on the SAME candidates. Pools, not slots (no one-trade-at-a-time
simulation) — stated, not hidden. The harness-executed t529b trades are printed beside it for reference only.

usage: python3 scripts/stage5_context_root_wf.py [--tag t529b] [--nmin 10] [--warmup 10] [--cutoff 22]
       --cutoff applies the live 3.4.0 rule (no NEW entries from 22:00 IL) to BOTH sides; 0 = none.
"""
import collections, glob, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
ARG = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d  # noqa
TAG = ARG("--tag", "t529b"); N_MIN = int(ARG("--nmin", "10")); WARMUP = int(ARG("--warmup", "10")); CUTOFF = int(ARG("--cutoff", "22"))
LIVE_ONLY = "--live-only" in sys.argv      # drop shadow-only producers (they never fire live on either side)
GATED = "--gated" in sys.argv              # drop candidates a post-tree gate blocked (entry_not_confirmed, chaser, ELQ, rr, eod…)
DEDUP = int(ARG("--dedup", "0"))           # minutes: one candidate per (pattern, direction) per window — the re-detection duplicates
COMM = 2.60; PT = 5.0; RR = 1.5


def q(sql):
    out = subprocess.run('%s -d mems26 -Atc "%s"' % (PSQL, sql.replace('"', '\\"')), shell=True, capture_output=True, text=True, timeout=180).stdout
    return [r.split("|") for r in out.splitlines() if r]


def fl(x):
    try:
        return float(x)
    except Exception:
        return None


bars = collections.defaultdict(list)
for r in q("select to_char(ts at time zone 'Asia/Jerusalem','YYYY-MM-DD'), to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), high, low, close "
           "from v9_bars_5min_woodies where symbol='MES' and ts>='2026-06-01' and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '22:55' order by ts"):
    if len(r) == 5:
        bars[r[0]].append((r[1], fl(r[2]), fl(r[3]), fl(r[4])))


def score(day, t_il, direction, entry, stop):
    """Fixed candidate model (identical to context_table.py): own stop, 1.5R, first touch, EOD close."""
    risk = abs(entry - stop); tgt = entry + RR * risk if direction == "LONG" else entry - RR * risk
    seq = [b for b in bars.get(day, []) if b[0] > t_il]
    if not seq:
        return None
    for _, h, l, c in seq:
        if direction == "LONG":
            if l <= stop: return (stop - entry) * PT - COMM
            if h >= tgt: return (tgt - entry) * PT - COMM
        else:
            if h >= stop: return (entry - stop) * PT - COMM
            if l <= tgt: return (entry - tgt) * PT - COMM
    c = seq[-1][3]
    return ((c - entry) if direction == "LONG" else (entry - c)) * PT - COMM


def hbucket(h):
    """The reference table's buckets (WALK_FORWARD_2026-10-05 §6): 16h · 17h · 18-19h · 20h+."""
    return "16h" if h <= 16 else ("17h" if h == 17 else ("18-19h" if h <= 19 else "20h+"))


# ── candidates of the live-config replay, scored once ─────────────────────────────────────────────────────
sessions = {}   # day -> {"cands": [...], "harness_pnl": float}
for p in sorted(glob.glob("harness_out/t466/%s_2026-*.json" % TAG)):
    d = os.path.basename(p)[len(TAG) + 1:len(TAG) + 11]
    try:
        j = json.load(open(p))
    except Exception:
        continue
    cands = []
    for r in (j.get("routes") or []):
        tv = r.get("tree_v3")
        if not isinstance(tv, dict):
            continue
        ep = fl(r.get("entry")); stp = fl(r.get("stop")); direction = r.get("direction")
        if not (ep and stp and 1.0 <= abs(ep - stp) <= 30):
            continue
        t_il = (r.get("il") or "00:00:00")[:5]
        sc = score(d, t_il, direction, ep, stp)
        if sc is None:
            continue
        v = tv.get("vec") or {}
        blocked = str(r.get("blocked_by") or "")
        if LIVE_ONLY and r.get("shadow_only"):
            continue
        if GATED and blocked and not blocked.startswith("tree:"):
            continue                                   # a gate after the tree said no — on either root it would
        if DEDUP:
            mins = int(t_il[:2]) * 60 + int(t_il[3:5]); k2 = (r.get("classification"), direction)
            last = cands and [c for c in cands if c["k2"] == k2]
            if last and mins - last[-1]["mins"] < DEDUP:
                continue
        cands.append({"day": d, "hour": int(t_il[:2]), "hb": hbucket(int(t_il[:2])), "kind": v.get("kind") or "?",
                      "structure": v.get("structure") or "?", "phase": v.get("phase") or "?", "dt": v.get("day_type") or "?",
                      "leaf": str(tv.get("leaf") or "SKIP").upper(), "score": sc,
                      "k2": (r.get("classification"), direction), "mins": int(t_il[:2]) * 60 + int(t_il[3:5])})
    hp = 0.0
    for t in (j.get("trades") or []):
        hp += fl(t.get("pnl_usd")) or 0.0
    sessions[d] = {"cands": cands, "harness_pnl": hp}

days = sorted(sessions)
print("T-543 stage 5 — context root (structure · hour · kind) for phases C/D, walk-forward vs %s" % TAG)
print("sessions %d (%s → %s) · N_MIN %d · warm-up %d · cutoff %s · scorer = context_table fixed model (own stop, 1.5R, first touch, EOD)"
      % (len(days), days[0], days[-1], N_MIN, WARMUP, ("%d:00 IL on both sides" % CUTOFF) if CUTOFF else "none"))
print("candidate filter: live-only=%s · gated=%s · dedup=%s" % (LIVE_ONLY, GATED, ("%d min per (pattern, direction)" % DEDUP) if DEDUP else "off"))
ncd = sum(1 for d in days for c in sessions[d]["cands"] if c["phase"] in ("C", "D"))
print("candidates %d · phase C/D %d · phase A/B %d (A/B keep the tree's leaf on both sides)"
      % (sum(len(sessions[d]["cands"]) for d in days), ncd, sum(len(sessions[d]["cands"]) for d in days) - ncd))


def cell(c):
    return (c["structure"], c["hb"], c["kind"])


def tree_take(c):
    return c["leaf"] == "TAKE" and (not CUTOFF or c["hour"] < CUTOFF)


def variant_take(c, table):
    """Phases A/B: the tree decides. Phases C/D: the context cell decides from PRIOR sessions only."""
    if CUTOFF and c["hour"] >= CUTOFF:
        return False
    if c["phase"] not in ("C", "D"):
        return c["leaf"] == "TAKE"
    n, s = table.get(cell(c), (0, 0.0))
    return n >= N_MIN and s > 0


# ── walk-forward ──────────────────────────────────────────────────────────────────────────────────────────
table = collections.defaultdict(lambda: [0, 0.0])     # cell -> [n, sum score]  (phase C/D candidates only)
rows = []                                              # per scored session
print("\n%-10s %-6s %6s %4s %9s %4s %9s %9s" % ("session", "label", "harness", "tT", "tree$", "vT", "variant$", "delta$"))
for i, d in enumerate(days):
    cs = sessions[d]["cands"]
    if i >= WARMUP:
        frozen = {k: (v[0], v[1]) for k, v in table.items()}
        t_pool = [c for c in cs if tree_take(c)]
        v_pool = [c for c in cs if variant_take(c, frozen)]
        ts, vs = sum(c["score"] for c in t_pool), sum(c["score"] for c in v_pool)
        label = collections.Counter(c["dt"] for c in cs if c["phase"] in ("C", "D")).most_common(1)
        rows.append({"day": d, "label": label[0][0] if label else "?", "harness": sessions[d]["harness_pnl"],
                     "tn": len(t_pool), "tree": ts, "vn": len(v_pool), "variant": vs, "delta": vs - ts})
        r = rows[-1]
        print("%-10s %-6s %+8.0f %4d %+9.1f %4d %+9.1f %+9.1f" % (d, r["label"][:6], r["harness"], r["tn"], ts, r["vn"], vs, vs - ts))
    for c in cs:                                       # the session joins the table AFTER it was scored
        if c["phase"] in ("C", "D"):
            table[cell(c)][0] += 1; table[cell(c)][1] += c["score"]


# ── the verdict (BRIEF §2 d: holdout-10 >= 0 AND delta > 0 on the whole set AND every month >= 0) ─────────
def tot(rs, k):
    return sum(r[k] for r in rs)


hold = rows[-10:]
print("\nTHE NUMBERS (walk-forward sessions %d, %s → %s; pools, not slots)" % (len(rows), rows[0]["day"], rows[-1]["day"]))
print("  tree TAKE pool ........ %+9.1f$  (%d candidates taken)" % (tot(rows, "tree"), tot(rows, "tn")))
print("  variant (context root)  %+9.1f$  (%d candidates taken)" % (tot(rows, "variant"), tot(rows, "vn")))
print("  delta ................. %+9.1f$   better %d / worse %d / same %d sessions"
      % (tot(rows, "delta"), sum(1 for r in rows if r["delta"] > 0.005), sum(1 for r in rows if r["delta"] < -0.005),
         sum(1 for r in rows if abs(r["delta"]) <= 0.005)))
print("  holdout-10 (%s → %s): tree %+8.1f$ · variant %+8.1f$ · delta %+8.1f$"
      % (hold[0]["day"], hold[-1]["day"], tot(hold, "tree"), tot(hold, "variant"), tot(hold, "delta")))
bym = collections.defaultdict(lambda: [0.0, 0.0])
for r in rows:
    bym[r["day"][:7]][0] += r["tree"]; bym[r["day"][:7]][1] += r["variant"]
print("  by month (tree / variant / delta): " + " · ".join("%s %+.0f / %+.0f / %+.0f" % (m, v[0], v[1], v[1] - v[0]) for m, v in sorted(bym.items())))
print("  harness-executed %s on the same sessions (reference, slot-aware, real exits): %+.2f$" % (TAG, tot(rows, "harness")))
ok = tot(hold, "delta") >= 0 and tot(rows, "delta") > 0 and all(v[1] - v[0] >= 0 for v in bym.values())
print("  acceptance rule (holdout >= 0 AND delta > 0 AND every month >= 0): %s" % ("PASSES" if ok else "does NOT pass"))

# the final table, for the eye: what the context root would take today (all sessions, n >= N_MIN)
print("\nthe context table after all %d sessions (phase C/D; TAKE = n >= %d and sum > 0):" % (len(days), N_MIN))
print("  %-10s %-7s %-11s %5s %9s %7s  %s" % ("structure", "hour", "kind", "n", "sum$", "per$", "verdict"))
for k, (n, s) in sorted(table.items(), key=lambda kv: -kv[1][1]):
    if n >= N_MIN:
        print("  %-10s %-7s %-11s %5d %+9.0f %+7.1f  %s" % (k[0], k[1], k[2], n, s, s / n, "TAKE" if s > 0 else "SKIP"))
print("report: docs/reports/T543_STAGE5_CONTEXT_ROOT_%s.md" % days[-1])
