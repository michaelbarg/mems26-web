# -*- coding: utf-8 -*-
"""T-635 per-trade read of the harness days: python3 harness_out/t635/per_trade.py <ref_tag> <tag> [tag …] [--days D …]

For every day: the reference trades vs the variant trades (fired time · pattern · dir · entry · $ · exit), what the
variant BLOCKED that the reference took (mid_value_no_edge_test / wait_for_test …), and the day totals. Then the
quick_cmp aggregate (Δnet, better/worse, by month, biggest days). Michael 22.10: per trade, not per 78 days.
"""
import json, glob, os, sys, collections
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "days")
args = [a for a in sys.argv[1:]]
days_sel = None
if "--days" in args:
    k = args.index("--days"); days_sel = args[k + 1:]; args = args[:k]
ref_tag, tags = args[0], args[1:]


def load(tag):
    out = {}
    for p in glob.glob(os.path.join(DIR, f"{tag}_*.json")):
        d = os.path.basename(p)[len(tag) + 1:-5]
        try:
            out[d] = json.load(open(p))
        except Exception:
            continue
    return out


def tsum(j):
    tr = j.get("trades") or []
    return round(sum((t.get("pnl_usd") or 0) for t in tr), 2), len(tr)


def tline(t):
    legs = t.get("legs") or []
    ex = ",".join(str(l.get("exit") or "-") for l in legs)
    tight = ";".join("%s→%s" % (x.get("il"), x.get("to")) for x in (t.get("tightened") or [])[:3])
    return "%s %-26s %-5s @%-8s %+8.2f$ mfe %5s mae %5s exit %s %s" % (
        t.get("fired_il", "?")[:5], t.get("classification"), t.get("direction"), t.get("entry"), float(t.get("pnl_usd") or 0),
        t.get("mfe_pts"), t.get("mae_pts"), ex, ("tight " + tight) if tight else "")


ref = load(ref_tag)
for tag in tags:
    v = load(tag)
    days = sorted(set(ref) & set(v))
    if days_sel:
        days = [d for d in days if d in days_sel]
    print("=" * 100)
    print("%s vs %s — %d common days" % (tag, ref_tag, len(days)))
    for d in days[-4:] if not days_sel else days:
        r, x = ref[d], v[d]
        rs, xs = tsum(r), tsum(x)
        print("\n## %s   ref %+.2f$ (%d)   →   %s %+.2f$ (%d)   Δ %+.2f" % (d, rs[0], rs[1], tag, xs[0], xs[1], xs[0] - rs[0]))
        print("  ref:")
        for t in r.get("trades") or []:
            print("    " + tline(t))
        print("  %s:" % tag)
        for t in x.get("trades") or []:
            print("    " + tline(t))
        blocks = [g for g in (x.get("gateway_decisions") or []) if str(g.get("blocked_by") or "").startswith(
            ("mid_value_no_edge_test", "wait_for_test", "opening_half_range", "edge_failed_ext"))]
        if blocks:
            print("  %s blocked (new gates):" % tag)
            seen = set()
            for g in blocks:
                key = (str(g.get("ts", ""))[11:16], g.get("pattern") or g.get("classification"), g.get("direction"), g.get("blocked_by"))
                if key in seen:
                    continue
                seen.add(key)
                print("    %s %s %s [%s] %s" % (key[0], key[1], key[2], key[3], str(g.get("reason") or "")[:110]))
    # aggregate
    dn = [(d, tsum(v[d])[0] - tsum(ref[d])[0]) for d in sorted(set(ref) & set(v))]
    tot = sum(x for _, x in dn); better = sum(1 for _, x in dn if x > 0.01); worse = sum(1 for _, x in dn if x < -0.01)
    bym = collections.defaultdict(float)
    for d, x in dn:
        bym[d[:7]] += x
    last10 = sum(x for _, x in sorted(dn)[-10:])
    print("\n%s vs %s: Δnet %+9.2f  days %d  better %d / worse %d / same %d  last10 %+8.2f" % (
        tag, ref_tag, tot, len(dn), better, worse, len(dn) - better - worse, last10))
    print("   by month Δ:", {k: round(x, 1) for k, x in sorted(bym.items())})
    print("   biggest:", [(d, round(x, 1)) for d, x in sorted(dn, key=lambda t: abs(t[1]), reverse=True)[:6]])
