#!/bin/bash
# T-515 (29.09): adaptive queue after QUEUE2 — runs, one variant at a time (run_variant.sh itself keeps ≤2 sessions in
# parallel), the first "TAG|ENV" line of queue3b.list not yet attempted. The list is re-read before every run, so the plan
# can change after each result without killing anything. Replaces run_queue3.sh (amwx carried the range-mid veto, which
# measured −204.90$ net vs t515a: it removed 11 trades worth +193.10$).
cd /Users/michael/Downloads/mems26_web_git || exit 1
while ! grep -q "QUEUE2 DONE" harness_out/t515/run_queue2.out 2>/dev/null; do sleep 10; done
tried=" "
while true; do
  next=""
  while IFS='|' read -r tag env; do
    tag=$(echo "$tag" | tr -d ' '); [ -z "$tag" ] && continue
    case "$tag" in \#*) continue;; esac
    case "$tried" in *" $tag "*) continue;; esac
    next="$tag|$env"; break
  done < harness_out/t515/queue3b.list
  [ -z "$next" ] && break
  tag=${next%%|*}; env=${next#*|}; tried="$tried$tag "
  bash harness_out/t466/run_variant.sh "$tag" "$env" harness_out/t515/sessions.txt > "harness_out/t515/run_$tag.out" 2>&1
  echo "$tag done $(date)"
done
echo "QUEUE3B DONE $(date)"
