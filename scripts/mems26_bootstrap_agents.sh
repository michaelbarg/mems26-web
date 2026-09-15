#!/usr/bin/env bash
# mems26_bootstrap_agents.sh — the nine mems26 LaunchAgents, in ONE place.
#
# WHY THIS EXISTS (T-259, twice measured, same 6/9 split both times):
#   Every macOS reboot leaves six of the nine agents UNREGISTERED in launchd —
#   06.09, and again 15.09 after the 10:01 reboot. Among them `mobile_relay`,
#   which is the ONLY writer of Michael's phone messages into
#   docs/handoff/PHONE_THREAD.jsonl. A dead relay makes the inbox look empty:
#   "no pending messages" becomes a FALSE NEGATIVE.
#   The permanent fix was proposed 06.09 and never written, so every session
#   rediscovered it by hand and bootstrapped one plist at a time.
#   Worse: mems26_verify.sh checked 3 of the 9 (backend/bridge/export_promoter),
#   so it returned full green at 10:07 on 15.09 while the phone path was dead.
#   That is green measured on the wrong set — this script defines the right set.
#
# MODES
#   --check      (default) read-only census of all nine. Starts nothing.
#                rc=0 everything as designed · rc=1 drift found.
#   --bootstrap  idempotent — bootstraps ONLY what is not registered.
#                Already-registered agents are left completely alone
#                (no kickstart, no restart, no unload).
#
# SAFETY — the 06.09 precedent, re-proven every run and never assumed:
#   `mobile_relay` relays /cmd from the phone to the machine that trades, so a
#   stale queued command could in principle be pulled the moment it comes up.
#   It is therefore bootstrapped only when all three hold, measured seconds
#   before the call:
#       /cmd/pending == null   ·   position_qty == 0   ·   working_orders == 0
#   If ANY of them cannot be proven (no key, stale export, curl failure) the
#   relay is SKIPPED and the reason is printed — CLAUDE.md Rule 1, honest
#   failure beats a synthetic "probably fine". The script then prints the exact
#   one-line command, so the operator decides deliberately instead of a flag
#   quietly bypassing a trading-safety gate.
#   The other eight carry no trade-execution path and are bootstrapped freely.
#
# NEVER: touches .env, flags, positions, orders, or the command queue ·
#        never restarts/kickstarts a live agent · never unloads anything.
set -uo pipefail

REPO="${MEMS26_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
LA_DIR="$HOME/Library/LaunchAgents"
EXPORT_DIR="${MEMS26_SIGNALS_DIR:-$HOME/SierraChart_Data/v9_export}"
MOBILE_HOST="${MEMS26_MOBILE_HOST:-https://mems26-mobile.onrender.com}"
DOMAIN="gui/$(id -u)"

# The roster. One list, one source of truth — extend HERE, nowhere else.
#   ALWAYS_ON  — KeepAlive, must be `state = running`
#   SCHEDULED  — calendar / interval / one-shot: registered is enough,
#                `not running` is the correct state between firings
ALWAYS_ON=(backend bridge frontend export_promoter activity_feed mobile_relay)
SCHEDULED=(eod_handoff startup_check update_check)
# Needs the trade-safety preconditions above before it may be bootstrapped.
GUARDED=(mobile_relay)

MODE="check"
case "${1:-}" in
  ""|--check) MODE="check" ;;
  --bootstrap) MODE="bootstrap" ;;
  -h|--help) sed -n '2,40p' "${BASH_SOURCE[0]}"; exit 0 ;;
  *) echo "unknown arg: $1 (use --check | --bootstrap)" >&2; exit 2 ;;
esac

drift=0
registered(){ launchctl print "$DOMAIN/com.mems26.$1" >/dev/null 2>&1; }
is_running(){ launchctl print "$DOMAIN/com.mems26.$1" 2>/dev/null | grep -q "state = running"; }
in_list(){ local n="$1"; shift; local x; for x in "$@"; do [ "$x" = "$n" ] && return 0; done; return 1; }

# ── trade-safety preconditions for the GUARDED agents ────────────────────────
# Prints one line of evidence per fact, then PROVEN / UNPROVEN. Read-only.
guard_ok(){
  local ok=1
  local key
  key="$(grep -m1 '^MOBILE_ACCESS_KEY=' "$REPO/.env" 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')"
  if [ -z "$key" ]; then
    echo "      · /cmd/pending    UNPROVEN — no MOBILE_ACCESS_KEY in $REPO/.env"
    ok=0
  else
    local body
    body="$(curl -s -m 8 "$MOBILE_HOST/cmd/pending?key=$key" 2>/dev/null)"   # key never echoed
    if [ -z "$body" ]; then
      echo "      · /cmd/pending    UNPROVEN — no response from $MOBILE_HOST"
      ok=0
    elif printf '%s' "$body" | grep -q '"cmd"[[:space:]]*:[[:space:]]*null'; then
      echo "      · /cmd/pending    null  ✅"
    else
      echo "      · /cmd/pending    NOT null ⇒ a command is queued: ${body:0:120}"
      ok=0
    fi
  fi

  local st="$EXPORT_DIR/sierra_state.json"
  local pos
  pos="$(python3 - "$st" <<'PY' 2>/dev/null
import json,os,sys,time
p=sys.argv[1]
try:
    age=time.time()-os.path.getmtime(p)
    d=json.load(open(p))
except Exception as e:
    print("ERR %s" % type(e).__name__); raise SystemExit
q=d.get("position_qty"); w=d.get("working_orders")
print("%.0f %s %s" % (age, q, w))
PY
)"
  if [ -z "$pos" ] || [ "${pos%% *}" = "ERR" ]; then
    echo "      · sierra_state    UNPROVEN — unreadable: $st"
    ok=0
  else
    set -- $pos
    local age="$1" qty="$2" work="$3"
    if [ "$age" -gt 120 ]; then
      echo "      · sierra_state    UNPROVEN — stale by ${age}s (pos=$qty working=$work)"
      ok=0
    elif [ "$qty" = "0" ] && [ "$work" = "0" ]; then
      echo "      · sierra_state    position_qty=0 · working_orders=0 (age ${age}s)  ✅"
    else
      echo "      · sierra_state    position_qty=$qty · working_orders=$work (age ${age}s) ⇒ not flat"
      ok=0
    fi
  fi
  [ $ok -eq 1 ]
}

echo "──── mems26 LaunchAgents · ${MODE} · $(date '+%Y-%m-%d %H:%M:%S %Z') ────"
guard_checked=0; guard_pass=1

for a in "${ALWAYS_ON[@]}" "${SCHEDULED[@]}"; do
  plist="$LA_DIR/com.mems26.$a.plist"
  if [ ! -f "$plist" ]; then
    printf "  🔴 %-17s plist MISSING (%s)\n" "$a" "$plist"; drift=$((drift+1)); continue
  fi

  if registered "$a"; then
    if in_list "$a" "${ALWAYS_ON[@]}"; then
      if is_running "$a"; then
        printf "  ✅ %-17s registered · running\n" "$a"
      else
        printf "  🔴 %-17s registered but NOT running (KeepAlive agent is down)\n" "$a"
        drift=$((drift+1))
      fi
    else
      printf "  ✅ %-17s registered · idle between firings (by design)\n" "$a"
    fi
    continue
  fi

  # not registered — this is the T-259 failure mode
  printf "  🔴 %-17s NOT REGISTERED in launchd\n" "$a"
  drift=$((drift+1))
  [ "$MODE" = "bootstrap" ] || continue

  if in_list "$a" "${GUARDED[@]}"; then
    if [ $guard_checked -eq 0 ]; then
      echo "     ↳ trade-safety preconditions (measured now, not assumed):"
      guard_ok && guard_pass=1 || guard_pass=0
      guard_checked=1
    fi
    if [ $guard_pass -eq 0 ]; then
      echo "     ↳ SKIPPED — preconditions not proven. Decide deliberately, then run:"
      echo "          launchctl bootstrap $DOMAIN $plist"
      continue
    fi
  fi

  if launchctl bootstrap "$DOMAIN" "$plist" 2>/dev/null; then
    sleep 1
    if registered "$a"; then
      st=$(is_running "$a" && echo running || echo "idle")
      printf "     ↳ bootstrapped ✅ now registered · %s\n" "$st"
      drift=$((drift-1))
    else
      printf "     ↳ bootstrap returned 0 but agent still not registered ⚠️\n"
    fi
  else
    printf "     ↳ bootstrap FAILED (rc=%s)\n" "$?"
  fi
done

total=$(( ${#ALWAYS_ON[@]} + ${#SCHEDULED[@]} ))
if [ "$drift" -eq 0 ]; then
  echo "──── all $total agents as designed ────"; exit 0
fi
echo "──── $drift of $total agents in drift ────"
[ "$MODE" = "check" ] && echo "     fix: $0 --bootstrap"
exit 1
