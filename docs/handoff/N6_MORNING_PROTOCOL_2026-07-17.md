# N6 — Hard morning protocol (16:00-16:25 ET), execute on cc-imac / iMac only

**100% live-dependent — cannot run from cowork-dev sandbox (no backend/Sierra/DB reachability).**
This is the compiled checklist from NIGHT_PROMPT_2026-07-17 §N6, ready to run verbatim. cc-imac
runs it, cowork-dev (or Michael) verifies in parallel, GO/NO-GO by 16:25.

## Checklist (all 7 must be green before the opening trade)

1. **bar_gap_monitor green on all 3 streams** (5min / woodies_5min / continuous):
   ```
   python3 scripts/bar_gap_monitor.py --window 60
   ```
   Expect 0 gaps on `v9_bars_5min_woodies` (the canonical live SoT per docs/SOURCE_OF_TRUTH.md).
   `v9_bars_5min`/`v9_bars_5min_continuous` may show gaps — known secondary-table issue, not a
   feed problem (see AGENT_SYNC history) — do not block on those two alone.

2. **post_restart_verify.sh GREEN**:
   ```
   bash scripts/post_restart_verify.sh
   ```
   **Known false-RED**: its bar-staleness check queries the legacy `v9_bars_5min` table (same
   root class as the feed_watchdog bug fixed this session in `backend/v9/services/feed_watchdog.py`
   — that fix only touched feed_watchdog, NOT this script). If this specific check is the only RED
   and `v9_bars_5min_woodies` is fresh, treat as a known false-RED, not a blocker — but say so
   explicitly, don't silently wave it through.

3. **S1 publishing on RTH bars within 30 min of open — NEW rule: otherwise no-trading.**
   ```
   curl -s localhost:8000/api/v9/mobile/data | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('day_type'))"
   ```
   Check at 10:00 ET (30 min after 09:30 open): must NOT be null/None if `DAYTYPE_HONEST_PRELOCK_V1`
   is on (expected None before IB lock at ~10:30 ET — if that flag is on, this check's 30-min window
   needs to move to ~10:30 ET / IB-lock time instead; confirm which is live before judging red/green).
   If still null past the *appropriate* window → NO-TRADING per Michael's new rule, escalate.

4. **S2-DL (decision log) shows activity on a live bar** — confirm the five_min system is actually
   evaluating, not silently stalled (this session's earlier "S2 blind" scare turned out to be a
   false alarm — verify with fresh evidence, don't assume from memory):
   ```
   curl -s localhost:8000/api/v9/gateway/decisions | python3 -m json.tool | head -40
   ```

5. **flag_guard + drill**:
   ```
   python3 scripts/flag_guard.py
   python3 scripts/fire_drill.py
   ```
   Expect PASS + GO. If NOT-GO, read the specific gate that failed — don't just retry.

6. **decisions-feed live** — same endpoint as #4, confirm timestamps are current (within the last
   few minutes at the time of the check, not stale from yesterday).

7. **OPENING_WINDOW active for the opening trade**:
   ```
   grep -i "OPENING_WINDOW" .env
   ```
   Confirm `OPENING_WINDOW_FIRE_V1=1` (or whatever the current flag name is per FLAG_INDEX.md —
   check there first, flags drift) is ON and not accidentally disabled by an overnight change.

## Also verify before declaring GO
- `DAY_TYPE_MANUAL_OVERRIDE` (set 07-16 21:35 for `2026-07-16:Neutral_Center`) **auto-expires at
  ET midnight** — confirm it is NOT still set for a new trading day (a stale override would silently
  re-apply yesterday's ruling to today). `grep DAY_TYPE_MANUAL_OVERRIDE .env` should show either
  nothing, or a date matching *today*.
- Tonight's 3 new flags (`S1_IB_SANITY_V1`, `S1_NEUTRAL_PRECEDENCE_V1`, `DAYTYPE_HONEST_PRELOCK_V1`)
  are all flag-OFF by default and were NOT sim-verified against a live Sierra feed (only pure-function
  unit tests, from a sandbox with no live access) — do not flip any of them on without a sim pass
  first, per the standing "sim before live" rule.
- The pending local commits (this session, cowork-dev) need to actually be pulled onto this machine
  first — `git log --oneline -8` should show `7187d990`/`03c11684`/`19de338f`/`764805bd`/`4e4bbc6d`
  at or near HEAD. If they're not there, the push blocker (AGENT_SYNC S-11) hasn't been resolved yet
  and none of tonight's N1/N4 work is actually live on this machine.

## GO / NO-GO
Record the verdict + raw command output for each of the 7 items in AGENT_SYNC by 16:25, per Rule 5
(paste the command + output, not "confirmed").

## ⚠️ חובה לפני-לייב (נוסף אוטומטית 07-17 07:03)
- `EOD_FLATTEN_V1=1` חזרה ב-.env (נוטרל לחלון-הסים-הלילי — מבטל-מיידית ברקטים מחוץ-ל-RTH) + ריסטארט.
