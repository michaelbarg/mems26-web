#!/usr/bin/env bash
# t563_plist_footprint_fix.sh — T-563 (cowork 08.10): let S3 run in SHADOW under the LaunchAgent.
#
# Finding (thread 07.10 23:30): ~/Library/LaunchAgents/com.mems26.backend.plist exports 16 keys
# AFTER `source .env`, so .env is dead for them. `export FOOTPRINT_DISABLED=true` makes
# FootprintSystem.process_bar return at once ⇒ System 3 is fully OFF in the live process although
# .env says FOOTPRINT_DISABLED=0 ("shadow only") — the blocker for 358a4610, not the tick table.
#
# This script REMOVES exactly that one export from the plist. It leaves TICK_REVERSAL_DISABLED=true
# (persist stays off: 1.5M duplicate rows/day until the DLL emits bar_start_ts and the handler
# inserts only new bars) and every other key untouched. S3 stays shadow: it is not registered to
# live/demo (backend/main.py enables systems [2,4] only) — this changes journal/measurement, no order.
#
# Usage:
#   scripts/t563_plist_footprint_fix.sh            # dry-run: show what would change (default)
#   scripts/t563_plist_footprint_fix.sh --apply    # snapshot → edit plist → lint → print next steps
#   scripts/t563_plist_footprint_fix.sh --apply --restart
#                                                   # ...and bootout/bootstrap the agent (a changed plist
#                                                   # needs bootstrap, kickstart alone keeps the old env)
# RULES: only on Michael's written ruling ("לבצע"), only outside 16:00–23:05 IL on weekdays,
#        position 0. Rollback: scripts/mems26_restore.sh <snapshot-dir> (printed below).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST="$HOME/Library/LaunchAgents/com.mems26.backend.plist"
KEY="FOOTPRINT_DISABLED"
APPLY=0; RESTART=0
for a in "$@"; do case "$a" in --apply) APPLY=1;; --restart) RESTART=1;; *) echo "unknown arg $a"; exit 2;; esac; done

dow=$(TZ=Asia/Jerusalem date +%u); hm=$(TZ=Asia/Jerusalem date +%H%M)
if [ "$dow" -le 5 ] && [ "$hm" -ge 1600 ] && [ "$hm" -lt 2305 ]; then
  echo "REFUSED: $(TZ=Asia/Jerusalem date +%H:%M) IL is inside RTH (16:00–23:05 weekdays) — no LaunchAgent change now."; exit 2
fi

echo "== plist: $PLIST"
/usr/libexec/PlistBuddy -c "Print :ProgramArguments:2" "$PLIST" | tr ';' '\n' | grep -n "export $KEY=" || { echo "export $KEY= not present — nothing to do"; exit 0; }
echo "== .env says: $(grep -E "^$KEY=" "$ROOT/.env" || echo "$KEY unset")"
pid=$(launchctl print "gui/$(id -u)/com.mems26.backend" 2>/dev/null | awk '/^[[:space:]]*pid = /{print $3}' | head -1)
[ -n "${pid:-}" ] && echo "== live backend pid $pid sees: $(ps -E -p "$pid" -o command= -ww | tr ' ' '\n' | grep -E "^$KEY=" || echo "$KEY unset")"
echo "== change: remove 'export $KEY=true' from ProgramArguments[2]; keep TICK_REVERSAL_DISABLED and the other 15 keys."

if [ "$APPLY" -ne 1 ]; then
  echo "DRY-RUN — nothing changed. Re-run with --apply on Michael's 'לבצע'."; exit 0
fi

# ── apply ──
pos=$(python3 -c "
import json,time,os
p=os.path.expanduser('~/SierraChart_Data/v9_export/sierra_state.json')
d=json.load(open(p)); age=time.time()-float(d.get('ts') or 0)
print(d.get('position_qty','?') if age < 120 else 'stale(%ds)' % age)
" 2>/dev/null || echo "?")
echo "== position before change: ${pos}"
if [ "${pos}" != "0" ]; then echo "REFUSED: position is '${pos}', not 0 — not touching the LaunchAgent with a position open."; exit 2; fi

snap=$("$ROOT/scripts/mems26_snapshot.sh" "t563-plist-footprint" 2>&1 | tail -1); echo "== snapshot: $snap"
cp -p "$PLIST" "$HOME/mems26_launchagent_backup_$(date +%Y%m%dT%H%M%S).plist"
python3 - "$PLIST" "$KEY" <<'EOF'
import plistlib, re, sys
p, key = sys.argv[1], sys.argv[2]
with open(p, "rb") as fh: d = plistlib.load(fh)
args = d["ProgramArguments"]
before = args[2]
after = re.sub(r'\s*export %s=[^;]*;' % re.escape(key), '', before, count=1)
assert after != before, "export not found"
assert 'TICK_REVERSAL_DISABLED=true' in after and 'source .env' in after
args[2] = after
with open(p, "wb") as fh: plistlib.dump(d, fh)
print("== plist rewritten; removed: export %s=…" % key)
EOF
plutil -lint "$PLIST"
/usr/libexec/PlistBuddy -c "Print :ProgramArguments:2" "$PLIST" | tr ';' '\n' | grep -c "export " | sed 's/^/== exports now: /'

if [ "$RESTART" -ne 1 ]; then
  cat <<EOT
== plist changed, agent NOT restarted. The running backend still has $KEY=true until a bootstrap.
   Next (restart protocol, outside RTH, position 0):
     launchctl bootout gui/\$(id -u)/com.mems26.backend
     launchctl bootstrap gui/\$(id -u) $PLIST
     sleep 30; grep -a "\[boot\] logging OK" /tmp/backend.err.log | tail -1
     grep -a "FootprintSystem hydrated" /tmp/backend.err.log | tail -1
     python3 scripts/flag_guard.py | tail -4        # PLIST REPORT must no longer flag $KEY
     scripts/post_restart_verify.sh && python3 scripts/fire_drill.py --no-live
   Rollback: scripts/mems26_restore.sh <snapshot-dir above> + the same bootout/bootstrap.
EOT
  exit 0
fi

echo "== restarting the LaunchAgent (bootout → bootstrap)…"
launchctl bootout "gui/$(id -u)/com.mems26.backend" || true
sleep 3
launchctl bootstrap "gui/$(id -u)" "$PLIST"
for i in $(seq 1 30); do
  sleep 2
  npid=$(launchctl print "gui/$(id -u)/com.mems26.backend" 2>/dev/null | awk '/^[[:space:]]*pid = /{print $3}' | head -1)
  if [ -n "${npid:-}" ] && curl -s --max-time 2 http://127.0.0.1:8000/health >/dev/null 2>&1; then break; fi
done
echo "== new pid: ${npid:-?}  $KEY in process: $(ps -E -p "${npid:-0}" -o command= -ww 2>/dev/null | tr ' ' '\n' | grep -E "^$KEY=" || echo "unset (good)")"
grep -a "\[boot\] logging OK" /tmp/backend.err.log | tail -1
python3 "$ROOT/scripts/flag_guard.py" | tail -4
"$ROOT/scripts/post_restart_verify.sh" || true
python3 "$ROOT/scripts/fire_drill.py" --no-live || true
echo "== done. Watch: v9_footprint_journal must start receiving rows during the next RTH (S3 shadow)."
