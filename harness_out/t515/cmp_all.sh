#!/bin/bash
# T-515: every variant of 29.09 against the SAME-DAY reference t515ref (history tables drift between days).
cd /Users/michael/Downloads/mems26_web_git || exit 1
for t in t514tbr t514xs t514zlr t514p17 t515a t515am t515amw t515amwe t515x "$@"; do
  [ -n "$(ls harness_out/t466 | grep "^${t}_.*json$" | head -1)" ] || continue
  PYTHONIOENCODING=utf-8 python3 harness_out/t494/cmp_vs_live.py "$t" t515ref 2>&1 | head -3
  python3 - "$t" <<'EOF'
import json, os, sys
t = sys.argv[1]
for d in ("2026-09-28",):
    p = f"harness_out/t466/{t}_{d}.json"
    if os.path.exists(p):
        j = json.load(open(p))
        print(f"   28.09: {j['daily_pnl_harness']:+.2f}$ ", [(x.get('classification'), x.get('direction'), x.get('entry'), x.get('outcome'), round(float(x.get('pnl_usd') or 0), 2)) for x in j['trades']])
EOF
  echo
done
