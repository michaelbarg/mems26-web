# CC Prompt — RTH diagnose: I-21 (export stall) + I-20/C-6 (TZ mask) + I-11 (footprint)

**Run at Monday 2026-06-08 RTH** (these are all RTH-only phenomena — on the
weekend the bridge is down and Sierra isn't exporting, so nothing reproduces).

**Mode:** diagnose-first, **read-only**. No code changes. Every claim = command
+ raw output (Rule 5). Follow `CC_HANDOFF_CONTRACT.md` + `CC_VERIFICATION_PROTOCOL.md`.
Consult `SYSTEM_INDEX.md` / `_INDEX.md` to locate files — do not grep blind.

**Goal:** isolate *where* the 5-min/study channel breaks (Sierra → bridge → DB),
and capture the per-stream raw `ts` strings so the I-20/C-6 TZ root can be fixed
correctly. Do NOT patch yet — report findings, then we scope fixes.

---

## Background (verified by Cowork 2026-06-07, weekend)
- Backend up; **bridge down on weekend** (`/api/v9/status` → `bridge.running:false`,
  `streams_active:0/11`). So the live stall must be observed during RTH.
- I-20/C-6 reproduced live even on the weekend: `/api/v9/build/pattern-status`
  showed **`footprint` ts = `2026-06-07T13:27:28+00:00`** while real UTC was `10:57`
  → IL-local stored as UTC (~+2.5h), displayed as **"FRESH 0s"**.
- Root of the *mask* localized to `bridge_inspector._parse_ts` (applies
  America/New_York to naive ts AND mishandles `+00:00` → naive `tzinfo=None`),
  compensated by `bridge_inspector.py:99-102` (`age<0 → FRESH`). The mask is
  **load-bearing** (removing it blind blocks the board — `volume_profile` is a
  critical stream that only shows FRESH because of it). Fix needs the per-stream
  raw ts (Step 3 below).
- Michael observed the **15-tick reversal** study live on **Sierra chart 1**.

## Step 1 — Sierra export files: which channel is frozen? (read-only)
List mtimes + tail of each export in `~/SierraChart_Data/v9_export/`:
```
ls -la --time-style=full-iso ~/SierraChart_Data/v9_export/
for f in 5min woodies_5min footprint tick_reversal_15 tick_reversal_12 \
         cumulative_delta_continuous volume_profile tpo live_price 5min_continuous; do
  echo "== $f.json =="; stat -f '%Sm %z bytes' ~/SierraChart_Data/v9_export/$f.json 2>/dev/null; \
  tail -c 300 ~/SierraChart_Data/v9_export/$f.json 2>/dev/null; echo; done
```
**Interpret:** if `woodies_5min.json` / `footprint.json` mtime is frozen while
`live_price.json` / tick files keep updating → the stall is **upstream of the
bridge** (Sierra/DLL not writing). If all files are fresh but the DB is stale →
the stall is **in the bridge or DB write**.

## Step 2 — bridge: running, pushing, local-only? (read-only)
```
tail -80 /tmp/bridge.err.log        # any "API push FAILED to https://..."? any stream DEAD/exception?
tail -40 /tmp/bridge.log 2>/dev/null
launchctl list | grep mems          # com.mems26.bridge present + last exit code
curl -s localhost:8000/api/v9/status | python3 -m json.tool | grep -A12 '"bridge"'
```
Confirm `streams_active` ≈ `streams_total`, `errors:0`, **local-only** (no render URL).

## Step 3 — DB freshness + RAW ts per stream (this settles I-20/C-6)
For each table, print MAX(ts) **as the raw stored string** and `now()`:
```
psql "$DATABASE_URL" -c "SELECT now() AT TIME ZONE 'UTC' AS now_utc;"
for t in v9_bars_5min v9_bars_5min_woodies v9_bars_footprint v9_bars_cumulative_delta \
         v9_bars_volume_profile v9_bars_tick_reversal v9_bars_imbalance v9_tpo_bars; do
  echo "== $t =="; \
  psql "$DATABASE_URL" -c "SELECT '$t' AS tbl, MAX(ts) AS max_ts_raw, pg_typeof(MAX(ts)) FROM $t;"; done
```
**Capture the exact `max_ts_raw` string + type per table.** For each, classify the
convention by comparing to `now_utc`: **UTC** (matches), **ET-naive** (≈ −4h),
or **IL-as-UTC** (≈ +3h, the footprint case). This per-table table of
conventions is the deliverable that lets us fix `_parse_ts` per-stream and then
safely remove the `age<0→FRESH` mask. Do **not** edit `_parse_ts` yet.

## Step 4 — tick_reversal / chart-1 (Michael's observation) + I-11 footprint
- In Sierra, confirm the 15-tick reversal study on **chart 1** has **Input 4
  "V9 Export Directory" = `/Users/michael/SierraChart_Data/v9_export/`** (this
  Input persists per chart — a wrong/empty value writes the file elsewhere and the
  bridge never sees it). Report the Input value.
- Cross-check Step 1: is `tick_reversal_15.json` updating? Does the bridge
  `tick_reversal_15` stream push? (`grep tick_reversal_15 /tmp/bridge.err.log`).
- **I-11 footprint** is Python-recomputed from SCID ticks (`vap_recompute.py`),
  not the Sierra `footprint.json`. Check `/api/v9/footprint/current`
  (`bars_processed_today`, `buffer_size`) during RTH and report whether the SCID
  tick read is producing bars. Suspect for the IL-as-UTC footprint ts:
  `vap_recompute.scid_ts_to_unix` uses a **naive `.timestamp()`** (line ~170) —
  capture one raw `bar_start_ts` it produces vs the SCID source time.

## NOT-DONE / report back, do not fix yet
- The deliverable is a **findings report**: (a) where the chain breaks for I-21,
  (b) the per-table ts-convention map for I-20/C-6, (c) the chart-1 Input value,
  (d) footprint recompute state. We scope the fixes from that — no blind edits.
- Paste raw command output for every step. If a step can't run (service down,
  permission), say so explicitly rather than inferring.
