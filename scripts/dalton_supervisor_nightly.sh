#!/bin/bash
# T-639 — nightly run of the Dalton supervisor (LaunchAgent com.mems26.dalton_supervisor, 23:12 IL weekdays).
# READ-ONLY against the DB; writes the day's report + the phone page, commits them by path, pushes. Never touches
# flags, the tree, .env or a trade. Michael 23.10 "מאשר".
set -u
export PATH=/Library/Frameworks/Python.framework/Versions/3.9/bin:/usr/local/bin:/usr/bin:/bin
export LC_ALL=en_US.UTF-8 PYTHONIOENCODING=utf-8
cd /Users/michael/Downloads/mems26_web_git || exit 1
D=$(date +%F)
LOG=/tmp/dalton_supervisor.log
echo "=== $(date '+%F %T') dalton_supervisor start" >> "$LOG"
mkdir -p docs/reports/dalton_supervisor harness_out
python3 scripts/dalton_supervisor.py --days 20 --mode demo \
  --md "docs/reports/dalton_supervisor/$D.md" \
  --html render_mobile_relay/static/docs/dalton.html \
  --json "harness_out/dalton_supervisor_$D.json" >> "$LOG" 2>&1
RC=$?
echo "rc=$RC" >> "$LOG"
if [ "$RC" -eq 0 ] && [ -s "docs/reports/dalton_supervisor/$D.md" ]; then
  git add -- "docs/reports/dalton_supervisor/$D.md" render_mobile_relay/static/docs/dalton.html >> "$LOG" 2>&1
  git commit -q -m "dalton-supervisor: $D (nightly, read-only)" >> "$LOG" 2>&1
  git pull --no-rebase -q >> "$LOG" 2>&1
  git push -q >> "$LOG" 2>&1
  echo "committed $(git log --oneline -1)" >> "$LOG"
fi
echo "=== $(date '+%F %T') dalton_supervisor end" >> "$LOG"
exit $RC
