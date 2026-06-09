# CC Prompt — B-13 Remediation (FULL) + clean SHADOW-from-0 run · 2026-06-05

**Authority:** Michael approved this scope in chat (2026-06-05). These are
trading-surface + session changes — implement, verify (Rule 5 raw output), then
**strategic-stop and report to Michael BEFORE the multi-day run is declared
trusted and before ANY demo/live**. Per CLAUDE.md: smallest correct change,
full-pipeline wiring (a flag/gate must reach EVERY affected branch — no
partial/dead wiring), add a regression for every fix, no "while I'm here"
refactors. Do NOT touch `CLOUD_URL`, LaunchAgent `KeepAlive`, or risk dollar
VALUES beyond the session gate. Diagnosis is DONE (see
`CC_PROMPT_B13_DIAGNOSE_ONLY_2026-06-05.md` + `BUG_LOG_2026-06-04_05.md`).

## Root cause (verified — code + live API + CC psql)
The phantom S2 fires (id 7 @7341.00, id 9 @7365.75, 16:18–16:20 CT, after close)
were NOT synthesized — they are **real OLD bars from May 6** (exact-tick match to
`v9_bars_5min` closes `2026-05-06 16:30+03`=7341, `20:20+03`=7365.75), residuals
the PG migration's "started fresh" never purged. They reached S2 because:
- **Ingestion has a FUTURE guard but no PAST/staleness guard.** `bars.py:308`
  rejects `ts > now+2m`; there is no symmetric reject for stale/old bars. A
  structurally-valid old bar (range 14pts) whose *time-of-day* lands in the RTH
  window passes `bar_is_valid` + `_is_within_rth`, gets written, and
  `bars.py:345` routes it to S2 as `last_valid_bar`.
- **S2 never returns to OVERNIGHT after close.** `five_min_system.process_bar`
  transitions only OVERNIGHT→FIRST_HOUR→DAY_TYPE (L760–779); OVERNIGHT/
  MAINTENANCE are set ONLY in `hydrate()` (L141/L181). Once intraday it enters
  DAY_TYPE_MODE it stays armed through the close.
- **No price-sanity.** `pre_fire_validator` checks only internal consistency.
- **SHADOW bypasses `risk_checks`** (`risk_checks.py:38`).

S1 (day_type) and S6 (killzone) have **0 trades / 0 fires** in DB — the "6,1,2"
report is not in the persisted trades; reconcile separately (UI/signals?).

---

## DECISIONS TO IMPLEMENT (sequence matters)

### D1 · Mute S3 (footprint) — reversible, no code change
Use the existing flag. Add `export S3_MUTE=1` to `scripts/start_all.sh` next to
the other exports (do NOT touch CLOUD_URL/KeepAlive), restart the backend.
`footprint_system._fire` already early-returns on `S3_MUTE` (observability stays).
**Reverse later** = set 0/unset + restart. Verify: log line
`[Footprint] S3_MUTE active — skipping fire` on a footprint signal, and no new
`firing_system=3` row in `/api/v9/trades/recent`. Paste raw.

### D2 · Ingestion staleness/off-market guard (THE root fix)
In `bars.py` POST `/api/v9/bars/5min` (and audit the other POST bar endpoints
that call `_route_bar`: tick_reversal/woodies/tpo), add — mirroring the existing
`now+2m` future guard — a reject when:
  (a) `ts` is older than the latest already-ingested bar by more than one bar
      interval (monotonic/staleness), AND/OR
  (b) bar price deviates from the live market price by more than `STALE_PRICE_BAND`.
Rejected bars are NOT written and NOT routed to any system. This makes the
unproven historical-replay delivery path irrelevant — old bars die at the door.
**Regression (RED→GREEN):** feed a May-6-style stale bar (old ts, price ~220pts
below live) → assert it is rejected, not in DB, and `_route_bar` not called.
Prove RED by removing the guard → bar is accepted+routed.

### D3 · Canonical session = America/Chicago 08:30–15:00 (single source of truth)
Per CLAUDE.md Rule 4 (no TZ ambiguity). Trading window is **08:30–15:00 CT**.
- Define it once, explicitly in `America/Chicago`, and have the session
  classifier + RTH gate + firing gate all reference that single definition.
  (Note: 08:30–15:00 CT == 09:30–16:00 ET; today the code is ET-based and
  `bars.py:33` extends the ingest close to 17:00 ET = 16:00 CT — **one hour past
  the 15:00 CT trading close**. A small post-close DATA buffer is OK, but FIRING
  must never use it.)
- **No firing outside 08:30–15:00 CT in ANY system and ANY mode (incl. SHADOW).**
  Add the session gate where it applies to all modes (not behind the
  `risk_checks.py:38` shadow bypass).
- Add the missing **DAY_TYPE→OVERNIGHT transition at 15:00 CT** in
  `five_min_system.process_bar`, and **audit S3/S4 and the other systems** for
  the same missing close→overnight edge (S3/S4 also fired after 16:00 ET).
- **entry_ts:** store UTC, display CT — stop persisting server-local `+03:00`.
**Regression:** a bar/setup at 15:01 CT → no fire in any mode; a fire's
`entry_ts` persists as UTC and renders as CT.

### D4 · Price-sanity band in pre_fire_validator — ❌ DEFERRED (Michael declined 2026-06-05)
Do NOT implement now. The staleness guard (D2) is the approved root fix; the
extra fire-time price band is deferred. Re-open only on Michael's request.

### D5 · Reset to clean 0 (after D2/D3 are in + green)
Purge the 8 residual rows (May 6–12) and, for a true fresh start, truncate
`v9_bars_5min`, `v9_bars_5min_continuous`, `v9_bars_5min_woodies`, `v9_trades`,
`v9_five_min_state` (+ related state). CLAUDE.md: past data is disposable.
Then restart with `S3_MUTE=1` → fresh Sierra ingestion from 0.

### Config VALUES needing Michael's sign-off (do NOT invent risk numbers)
`STALE_PRICE_BAND` and the staleness interval tolerance (D2). Propose defaults in
the report; Michael approves before they go live. (`FIRE_PRICE_BAND` not needed —
D4 deferred.)

---

## EXECUTION ORDER
1. D2 + D3 code + regressions green (RED proven). [D4 deferred — skip]
2. D5 data reset.
3. Restart backend with `S3_MUTE=1` (D1).
4. **Verify (Rule 5 — paste command + raw output):**
   - Regressions: raw pytest RED→GREEN.
   - Concurrent soak ≥10 min, 0 errors / 0 deadlocks (PG GO criteria) — paste.
   - Live: `/api/v9/trades/recent` shows no firing_system=3; no fire with
     entry far from live price; DB clean (`SELECT COUNT(*),MIN(ts),MAX(ts)` per
     bar table); five_min mode = OVERNIGHT after 15:00 CT.
5. **STRATEGIC STOP → report to Michael.** Do not declare the multi-day run
   trusted, and do not enable any demo/live, until he signs off.

## NOT-DONE (mandatory — list anything skipped/partial)
State explicitly: which systems were audited for the close→overnight edge and
which weren't; whether tick/woodies/tpo ingest endpoints got the staleness
guard; whether D4 was included or deferred; the exact band VALUES used and that
they are pending Michael's approval.

## Board updates (after GO, per CLAUDE.md Reporting Workflow)
`STATUS_BOARD.md` (finding + fix + raw verification, dated) and
`ROADMAP_TO_LIVE.html` (mark B-13 items, refresh "אתה כאן" + "עודכן").

## Separate track (do NOT bundle — one thread at a time)
**B-11** (`bridge_inspector` `rowid`→`{ts_col}`) is ready in
`CC_PROMPT_B11_BRIDGE_INSPECTOR_ROWID_2026-06-05.md` — dashboard false-OFFLINE,
non-trading. Run it as its own thread.
