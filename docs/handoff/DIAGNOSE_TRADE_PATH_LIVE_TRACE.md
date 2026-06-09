# Diagnose-First: Trade Path Live Trace

**Type:** diagnostic probe — **READ-ONLY, no fixes, no edits, no service restarts**
**Date:** 2026-05-31
**Author:** Cowork (for Michael)
**Trigger:** Michael 31/5 — "נתיב הטרייד שבור". `FULL_PATH_MEGA_TABLE_2026-05-31.md`
mapped the path statically (30 steps) but never traced it against live data. This
prompt closes that gap with evidence.
**Goal:** answer "are trades being created, and if not, **at which hop** does the path
break?" — as a survival funnel, every number backed by raw output.

---

## Prime directive (CLAUDE.md — read before starting)

- **Diagnose first, fix second.** This task makes **zero** code changes. Propose fixes
  in prose only, for Michael's approval.
- **Read the current code** before any claim. Re-open each file; do not trust the
  static audit's line numbers — confirm them (Rule 2: verify before you trust).
- **Rule 5 — verification quote, not assertion.** Every finding = command + raw output
  (SQL + rows, `rg` + matched lines, log excerpt). No bare claims.
- **Rule 1 — honest failure.** If a hop is not observable (e.g. SHADOW fills live only
  in an in-memory list, not the DB), write "not observable from DB" — do not invent a
  number to fill the funnel.
- **No silent failures.** A query returning 0 where you expected data IS a finding.
- **Service Bring-Up:** DB `data/mems26_local.db` (~10GB) is **read-only**. **Do not
  start or restart any service.** If the backend is already up, you may probe it; if
  it is down, fall back to DB + code + logs only and say so.

---

## The path under test

```
S2 setup_emitter ─┐
S3 footprint    ──┼─→ pre_fire_validator (7 checks) ─→ gateway.route_setup
S4 woodies      ─┘                                          │ 5 risk gates
                                          SHADOW: always → shadow_trades list (in-mem, cap 500)
                                          DEMO/LIVE: single slot
                                          ▼
                            TradeManager.accept_setup → V9Trade(PENDING)
                                          ▼ on_fill
                                       FILLED → BarLevelDetector → targets/stop → CLOSED
                                          ▼
                                    v9_trades (DB) → API → Frontend
```

Produce the **funnel** for the trace window:

```
generated → passed validator → passed gates → accept_setup → rows in v9_trades → closed
   N1            N2                 N3             N4              N5              N6
```

The first arrow that drops to ~0 (or that drops SHADOW silently) is the answer.

---

## WS-0 — Which gateway is live, and what window? (do this FIRST)

The mega table flagged **two** gateways (GAP-8): Legacy `backend/v9/gateway/` (wired)
and New `backend/v9/services/trading_gateway/` (unwired, has W14 RiskValidator). A
trace is meaningless until you know which one actually receives `route_setup`.

```bash
rg -n "route_setup|trading_gateway|import .*gateway|from .*gateway" backend/v9 --type py
```

1. From `backend/main.py` / app startup, trace the single gateway instance the running
   app constructs. Paste the import + construction line.
2. State KEEP/DEFER for the other gateway; confirm no live `route_setup` caller reaches
   it.
3. Define the window — the last RTH session with bar activity:
   ```sql
   SELECT date(ts) d, COUNT(*), MIN(ts), MAX(ts)
   FROM v9_bars_5min GROUP BY d ORDER BY d DESC LIMIT 5;
   ```

**Deliver:** live gateway (file:line) + trace window (date, bar count).

---

## Diagnostic steps (run in order, paste raw output)

### Step 1 — Rows in `v9_trades` (the funnel's end: N5/N6)

```sql
SELECT COUNT(*) total, mode, firing_system, state,
       MIN(created_at) oldest, MAX(created_at) newest
FROM v9_trades
WHERE created_at > datetime('now','-7 days')
  AND is_synthetic = 0
GROUP BY mode, firing_system, state
ORDER BY mode, firing_system, state;
```

**If zero non-synthetic rows:** the break is BEFORE persistence — continue to Steps 3→2.
**Note (Rule 1):** if SHADOW is recorded only to the in-memory `shadow_trades` list and
the SHADOW branch of `route_setup` does **not** call `TradeManager.accept_setup`, then
v9_trades will legitimately be empty for shadow — that is "behaving as coded, not as
expected," NOT a bug. **Confirm by reading the SHADOW branch of the live gateway's
`route_setup`** and paste it.

### Step 2 — Gateway block reasons (N2→N3)

```bash
rg -i "BLOCKED|slot occupied|SKIP|route_setup|cooldown|suffering|chop|cluster" /tmp/mems26_backend.log 2>/dev/null | tail -60
```

If logs are unavailable, read the 5 gates in the **live** gateway (cooldown / SSV /
chop / cluster-guard / LIVE-strict) and reason about which could silently zero the
funnel — especially the **chop gate** (Layer-0 `chop_state="SEARCHING"` → block). Paste
the chop_state for the window if available.

### Step 3 — Were setups emitted at all? (N1) — kill the "no patterns" trap

The 28/5 mistake: concluding "no patterns today" without querying. Do not repeat it.

```sql
SELECT COUNT(*), firing_system FROM v9_five_min_setups
WHERE date(created_at) >= date('now','-7 days') GROUP BY firing_system;   -- S2

SELECT COUNT(*) FROM v9_woodies_signals
WHERE date(created_at) >= date('now','-7 days');                          -- S4
```
For S3, find the footprint pre-gateway signal record/log:
`rg -n "fire|route_setup|SHADOW" backend/v9/**/footprint_system.py`.

```bash
rg -i "T1Setup emitted|T1Setup skipped|pre_fire.*REJECT|ready_to_route|SHADOW recorded" /tmp/mems26_backend.log 2>/dev/null | tail -40
```

**If zero setups but bars are flowing (Step 4):** the break is in detection
(thresholds, or day_type=Nontrend → Auth Table SKIP), not the gateway.

### Step 4 — Bar ingestion health (is there even input?)

```sql
SELECT MAX(ts) latest, COUNT(*) FROM v9_bars_5min WHERE date(ts)=date('now');
```
(If backend up:) `curl -s http://localhost:8000/api/v9/bars/latest | python3 -m json.tool`
**If no fresh bars during RTH:** bridge/Sierra issue — the trade path can't fire by
design; stop and report that as the root.

### Step 5 — S1 day_type context (gates Auth Table sizing)

(If backend up:) `curl -s http://localhost:8000/api/v9/day_type/v9/current | python3 -m json.tool`
or read `v9_day_type_history` for today's row.
**If day_type is Nontrend / unlocked:** Auth Table returns SKIP (0 contracts) → no S2
fire. That is a legitimate "no trade," not a broken path — distinguish it.

### Step 6 — Stuck-trade lifecycle (only if N5 > 0)

```sql
SELECT id, mode, firing_system, state, direction, entry_price, stop, t1, t2,
       created_at, entry_ts, exit_ts
FROM v9_trades
WHERE state IN ('PENDING','FILLED','PARTIAL')
  AND created_at > datetime('now','-3 days')
ORDER BY created_at DESC LIMIT 20;
```
- stuck **PENDING** → `on_fill` never called (no fill reported).
- stuck **FILLED** → BarLevelDetector not subscribed / bars not flowing
  (cross-check 30/5 fix: subscribes `5min`+`woodies_5min`).

### Step 7 — API surfacing — four UAT axes (only if N5 > 0 and backend up)

On `GET /api/v9/trades` and `/recent`: **Quality** (`is_synthetic=0` filter active,
`trades.py:331,357`), **Recency** (endpoint latest == `MAX(created_at)`), **Cardinality**
(returned count == DB count; watch the 200-row truncation flagged in the trades-page
checklist), **Latency**. If the API can't be hit and you must not start it — say so,
DB-side checks only.

---

## Decision tree

```
N5 (rows in v9_trades) == 0 ?
  ├─ YES → Step 4: bars fresh?
  │   ├─ NO  → bridge/Sierra (path can't fire — root)
  │   └─ YES → Step 3: setups emitted (N1)?
  │       ├─ NO  → detection (thresholds / day_type=NT→SKIP)   [check Step 5]
  │       └─ YES → Step 2: blocked at a gate (N2→N3)?
  │           ├─ cooldown / SSV / chop=SEARCHING / cluster → name it, cite count
  │           └─ none blocked → SHADOW recorded in-mem only, no accept_setup? (Step 1 note)
  └─ NO (rows exist) → Step 6: stuck PENDING (no fill) / stuck FILLED (detector) / closing OK
```

---

## Output

Write to `docs/reports/TRADE_PATH_LIVE_TRACE_2026-05-31.md`:

1. **Funnel table** N1→N6, with the command + raw output under each number.
2. **The break point(s):** hop, root-cause hypothesis, the evidence that confirms it,
   and whether it is "broken" vs "behaving as coded but not as Michael expects" (the
   SHADOW-in-memory case, or day_type=NT→SKIP).
3. **GAP-8 verdict:** KEEP/ADAPT/REPLACE/DEFER for the dual gateway, based on what you
   saw at runtime.
4. **Proposed fix(es) — described only, NOT implemented.** Flag anything touching
   order / risk / sizing / gateway routing as a **strategic stop** needing Michael's
   sign-off before any code.

Do not edit source. Do not restart services. Report back the report path + the
one-line funnel verdict, then stop — do not advance to implementation.

## Roadmap discipline (CLAUDE.md § Reporting Workflow)

On completion, fold the funnel verdict (finding + evidence, per Rule 5) into the
🟠HIGH "Trade path שבור" item in `docs/plans/STATUS_BOARD.md`, and refresh the matching
open item + dated line in `docs/plans/ROADMAP_TO_LIVE.html`.
