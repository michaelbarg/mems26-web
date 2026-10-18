#!/bin/bash
# T-597 lesson (18.10): a session that crashes leaves "done <session> <tag> rc=1" in the run logs and NO json — and nobody
# counted. Census of rc!=0 lines across all run logs + json/session-list coverage per tag. usage: check_runs.sh [TAG ...]
cd /Users/michael/Downloads/mems26_web_git || exit 1
H=/Users/michael/mems26_hist
echo "== rc!=0 lines (all logs)"
cat $H/hist_runs.log $H/chain*.log harness_out/t586/day.out 2>/dev/null | grep -h "^done" | grep -v "rc=0" | sort | uniq -c | sort -rn
echo "== coverage per tag (json count vs list)"
for t in "$@"; do
  for L in hist_sessions sessions70 hist_sessions_old; do
    n=0; miss=""
    for s in $(cat $H/$L.txt); do if [ -f harness_out/t466/${t}_${s}.json ]; then n=$((n+1)); else miss="$miss $s"; fi; done
    tot=$(wc -l < $H/$L.txt | tr -d ' ')
    [ $n -gt 0 ] && echo "$t $L: $n/$tot${miss:+  missing:$miss}"
  done
done
