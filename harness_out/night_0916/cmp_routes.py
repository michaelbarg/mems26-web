#!/usr/bin/env python3
"""A3 gate: compare routes/would_write of a night run vs the T-367 baseline.
Field-scoped on purpose: a whole-file checksum would break on wall-clock
fields that carry no decision meaning."""
import json, sys

def load(p):
    with open(p) as f:
        return json.load(f)

def canon(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False)

ok_all = True
for sess in sys.argv[1:]:
    base = load("harness_out/t367/head_%s.json" % sess)
    new = load("harness_out/night_0916/head_%s.json" % sess)
    print("\n===== session %s =====" % sess)
    for field in ("routes", "would_write"):
        b, n = base.get(field), new.get(field)
        same = canon(b) == canon(n)
        print("%s: baseline_len=%d new_len=%d IDENTICAL=%s" % (field, len(b), len(n), same))
        if not same:
            ok_all = False
            if len(b) != len(n):
                print("  !! LENGTH DIFF %d -> %d" % (len(b), len(n)))
            for i, (bi, ni) in enumerate(zip(b, n)):
                if canon(bi) != canon(ni):
                    keys = sorted(set(bi) | set(ni))
                    diffs = [k for k in keys if canon(bi.get(k)) != canon(ni.get(k))]
                    print("  idx %d: keys differing = %s" % (i, diffs))
                    for k in diffs:
                        print("     %s: base=%r  new=%r" % (k, bi.get(k), ni.get(k)))
print("\n==================================")
print("A3 VERDICT:", "IDENTICAL (zero behaviour change)" if ok_all else "DIFFERENT -> BLOCKING FINDING")
sys.exit(0 if ok_all else 1)
