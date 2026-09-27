#!/bin/bash
# T-494 (27.09 15:47) — the package: every split that passed alone (net Σ ≥ 0 and ≥ 15 trades added vs live0927,
# rule 24.09) replayed TOGETHER, because branches measured alone interact through the single live slot.
# S1 and S5 passed; S6/S7 join only if their own day-total passes the same rule (decided here, from the files).
cd /Users/michael/Downloads/mems26_web_git || exit 1
while ! grep -q "QUEUE4 DONE" harness_out/t494/run_queue4.out 2>/dev/null; do sleep 15; done
PARTS=$(python3 - <<'EOF'
import glob, json, os
D = "harness_out/t466"
def load(tag):
    out = {}
    for p in glob.glob(f"{D}/{tag}_*.json"):
        d = os.path.basename(p)[len(tag) + 1:len(tag) + 11]
        try:
            j = json.load(open(p)); out[d] = (float(j.get("daily_pnl_harness") or 0), len(j.get("trades") or []))
        except Exception:
            pass
    return out
ref = load("live0927"); parts = ["tree_s1.yaml", "tree_s5.yaml"]
for tag, f in (("t494s6", "tree_s6.yaml"), ("t494s7", "tree_s7.yaml")):
    v = load(tag); common = set(v) & set(ref)
    d_usd = sum(v[d][0] - ref[d][0] for d in common); d_n = sum(v[d][1] - ref[d][1] for d in common)
    net = d_usd - 2.60 * d_n
    if len(common) >= 55 and net >= 0:
        parts.append(f)
print(" ".join(parts))
EOF
)
echo "package parts: $PARTS $(date)"
python3 harness_out/t494/compose_pkg.py tree_pkg.yaml $PARTS || exit 1
bash harness_out/t466/run_variant.sh t494pkg "DECISION_TREE_V3=1 DECISION_TREE_V3_PATH=harness_out/t494/tree_pkg.yaml" harness_out/t493/sessions.txt > harness_out/t494/run_t494pkg.out 2>&1
echo "t494pkg done $(date)"
echo "QUEUE5 DONE $(date)"
