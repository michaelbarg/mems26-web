# Expected Outcome — After CC Executes the 2 Updated Prompts · 2026-05-28 EVENING

**Author:** Cursor agent (Claude Opus 4.7)
**Owner:** Michael
**Source prompts (updated 2026-05-28 evening):**
1. `docs/handoff/MEGA_PROMPT_CC_AUDIT_IB_TIMESTOP_2026-05-28.md`
2. `docs/handoff/CC_MEGA_PROMPT_7_FIXES_2026-05-28.md`

**Authoritative decisions baked in (Michael 2026-05-28 evening):**
- IB: Sierra Initial Balance Study only. Delete `_ib_from_bars()`.
- W-10 Registry #11 = sole TIME_STOP authority. 90min flat all patterns.
- Fix bugs A and D in code (not via YAML kill switch).
- Layer 4 (`TIME_STOP_BY_DAY_TYPE` + `_check_time_stop`) removed completely.

This document tells you the **end-state** you'll observe after CC finishes
both prompts. Use it as the audit checklist when you accept CC's work.

---

## §1 · What changes — file-by-file end-state

### 1.1 · Modified files (logic changes)

| File | What changes | Verify by |
|---|---|---|
| `backend/v9/api/v9/tpo_routes.py` | `_ib_from_bars()` function DELETED entirely. `_normalize_sierra_tpo()` `else:` branch returns `ib_high=None, ib_low=None, ib_source="missing"`. The `"Restored with Michael's explicit approval (2026-05-28 18:31 IDT)"` comment block is GONE. | `rg -n "_ib_from_bars\|v9_bars_5min_09_30_10_30_ET" backend/` → 0 hits |
| `backend/v9/api/v9/key_levels_routes.py` | Any switch on `ib_source == "v9_bars_5min_..."` removed. Consumer correctly handles `ib_high=None`. | `rg -n "v9_bars_5min_09_30" backend/` → 0 hits |
| `backend/v9/systems/woodies/woodies_system.py` | (a) `_bar_count` increments only when `bar.ts` is new (Bug A fix). (b) `_check_time_stops()` sets `exit_price = self._closes[-1]` BEFORE `close_trade(..., "TIME_STOP")` (Fix #5). (c) Defensive guard: skip close + log WARNING when `self._closes` is empty. (d) Kill-switch comment block on `_check_time_stops` REPLACED with a restoration note. | `rg -n "_last_bar_ts_for_count" backend/v9/systems/woodies/woodies_system.py` → 2 hits (init + process_bar). `rg -n "exit_price = float\(self._closes\[-1\]\)" backend/v9/systems/woodies/woodies_system.py` → 1 hit. |
| `backend/v9/systems/woodies/config/dispatcher_config.yaml` | `time_stop_minutes: null` → `time_stop_minutes: 90`. Comment block replaced with restoration note pointing to `AMENDMENTS_LOG`. | `grep "time_stop_minutes" backend/v9/systems/woodies/config/dispatcher_config.yaml` → `90` |
| `backend/v9/services/trade_manager/bar_level_detector.py` | Three regions DELETED: `TIME_STOP_BY_DAY_TYPE` constant (~lines 21-29), the time-based exit block in `on_bar` (~lines 116-124), `_check_time_stop` method (~lines 131-165). Stop/target hit logic and `_parse_ts` STAY. | `rg -n "TIME_STOP_BY_DAY_TYPE\|_check_time_stop" backend/` → 0 hits in `bar_level_detector.py`. `rg -n "on_stop_hit\|on_target_hit" backend/v9/services/trade_manager/bar_level_detector.py` → unchanged. |

### 1.2 · Modified files (TZ — only if Michael confirms ET)

| File | What changes | Verify by |
|---|---|---|
| `bridge/v9_streams/base_stream.py` | `America/Chicago` → `America/New_York` (only if Sierra UI confirmed ET). | Read line near `ZoneInfo(...)` (was `:73`). |
| `backend/v9/api/v9/woodies_chart_routes.py` | Hardcoded `ts_unix += 5 * 3600` REPLACED with bridge's `_chicago_to_utc()` (or whatever TZ helper applies post-fix). | `rg -n "5 \* 3600" backend/` → 0 hits |

**If Sierra is confirmed CT — these two files do NOT change in this round.**
The +1h drift has a different cause and CC must diagnose further before patching.

### 1.3 · S2 day_type — depends on diagnosis (Group C)

CC must run the SQL probe in §2.Fix #6 of `CC_MEGA_PROMPT_7_FIXES` first.
Outcome depends on which case (a/b/c) reproduces:
- Case (a): table empty pre-RTH → no fix, no file change.
- Case (b): UTC vs local date mismatch → `five_min_system.py` `hydrate()` WHERE clause changed to a 24h sliding window.
- Case (c): state machine wrote NULL → `backend/main.py:_day_type_on_bar` patched to never persist NULL.

---

## §2 · New files you'll receive

### 2.1 · New regression tests

| Path | Purpose |
|---|---|
| `tests/v9/api/test_tpo_routes_no_ib_synthesis.py` | Asserts `_normalize_sierra_tpo` returns `ib_source="missing", ib_high=None` when DLL silent. Anti-regression for the bars-synthesis revocation. |
| `tests/v9/systems/woodies/test_w10_bar_count_per_close.py` | Pushes same bar 5× with same `ts` → `_bar_count` increments only once. Anti-regression for Bug A. |
| `tests/v9/systems/woodies/test_w10_time_stop_sets_exit_price.py` | Two tests: (1) `exit_price = self._closes[-1]` set BEFORE `close_trade`. (2) Empty `_closes` → close skipped + WARNING (no NULL exit_price). |
| `tests/v9/systems/woodies/test_w10_time_stop_enabled.py` | INVERSION of the previous `test_w10_time_stop_disabled.py`. Asserts YAML=90 and enforcer fires at `bars_open >= 18`. |
| `tests/v9/services/trade_manager/test_bar_level_detector_no_time_stop.py` | Asserts a long-running open trade does NOT trigger `close_trade("TIME_STOP")` from Layer 4 (because Layer 4 is removed). Stop/target tests must still pass. |
| `tests/v9/systems/five_min/test_<case_specific>.py` | Name depends on which case (a/b/c) Group C identifies. |

### 2.2 · Deleted tests

| Path | Reason |
|---|---|
| `tests/v9/services/trade_manager/test_layer4_time_stop_authority.py` | Layer 4 removed. The "table is complete" assertion is moot. |

### 2.3 · Renamed tests

| Old path | New path | Reason |
|---|---|---|
| `tests/v9/systems/woodies/test_w10_time_stop_disabled.py` | `tests/v9/systems/woodies/test_w10_time_stop_enabled.py` | YAML restored to `90`. Assertions inverted. |

### 2.4 · Un-skipped tests

| Path | Notes |
|---|---|
| `tests/v9/systems/test_time_stop.py` | 6 tests un-skipped. All must pass against restored 90min YAML. |
| `tests/v9/systems/test_woodies_rth_gate.py` | 1 test un-skipped. |

### 2.5 · New documentation entries

| File | Entry |
|---|---|
| `docs/reports/AMENDMENTS_LOG.md` | Two new entries (timestamp + reason): (1) "IB bars-synthesis revocation" — revokes the 18:31 IDT same-day approval. (2) "W-10 Option B REVERSED" — documents the morning Layer-4-sole-authority decision being reversed in favour of Registry #11. |
| `docs/reports/IB_PACKAGE_A_LANDED_2026-05-28.md` | Final report from CC: diff summary per fix, UAT 4-axis results, deferred items. |
| `docs/reports/FIX_REPORT_7_BUGS_2026-05-29.md` | (or 28-evening date) Final report on the 7-bugs prompt: per-fix table, Sierra TZ confirmation evidence, full pytest output, UAT 4-axis evidence, remaining open items. |
| `docs/plans/STATUS_BOARD.md` | One line per landed group (A1, A2, B if applied, C). |
| `docs/handoff/OPEN_ITEMS_PRE_LIVE_2026-05-28.md` | Items #14–18 marked RESOLVED with citations to the new reports. |
| `docs/reports/CC_AUDIT_IB_TIMESTOP_CONSULTATION_2026-05-28.md` | CC's Phase 2 consultation document — pushback on subagent claims, re-ranked fix order, open questions for you. **You receive this BEFORE Phase 3 implementation.** |

### 2.6 · Optional script (Group B only — if TZ flip happens)

| Path | Purpose |
|---|---|
| `scripts/probe_tz_assumptions.py` | Side-by-side dry-run that prints how the latest 5 bars look under CDT / CST / ET interpretations vs Sierra wall-clock. CC writes this BEFORE flipping `base_stream.py` TZ. |

---

## §3 · What you'll observe live (post-restart UAT)

### 3.1 · IB endpoint behaviour

```bash
curl -s http://localhost:8000/api/v9/tpo/current | jq '{ib_high,ib_low,ib_source,ib_found}'
```

Expected, depending on Sierra Study state:
- DLL reporting IB → `{"ib_high": <Sierra value>, "ib_low": <Sierra value>, "ib_source": "sierra_live", "ib_found": true}`
- DLL silent → `{"ib_high": null, "ib_low": null, "ib_source": "missing", "ib_found": false}`
- **NEVER** `"ib_source": "v9_bars_5min_09_30_10_30_ET"` again.

### 3.2 · `/api/v9/key_levels`

- `previous_day.ib_*` and `today.ib_*` cleanly render `null` when DLL silent.
- UI strips render "—" instead of crashing.
- `sources.ib` no longer contains the synthetic source string.

### 3.3 · TIME_STOP behaviour after S4 fire

- TIME_STOP fires after **18 closed 5-min bars (= 90 real minutes)**, not at 52s.
- `v9_trades.exit_price` populated on TIME_STOP close (no longer NULL).
- `v9_trades.pnl_usd` is the actual P&L, not zero.
- `v9_trades.exit_reason = "TIME_STOP"` only fired by Woodies path (Registry #11), never by `bar_level_detector` (Layer 4 removed).

Anti-regression you can run:
```sql
-- After a S4 fire, push the same bar 30× over 90s. No close should appear:
SELECT id, exit_reason, exit_ts FROM v9_trades
WHERE entry_ts > datetime('now', '-2 minute')
  AND exit_reason = 'TIME_STOP';
-- Expected: 0 rows during the first 90 minutes.
```

### 3.4 · Day-type hydrate (Group C — only if a fix lands)

```bash
curl -s http://localhost:8000/api/v9/five_min/current | jq '.current_day_type'
```

Expected: matches the latest row in `v9_day_type_state` for the current
trading day, immediately after restart, without needing a day_type event
to fire.

### 3.5 · TZ — bars endpoint (Group B — only if TZ flip happens)

```bash
sqlite3 data/mems26_local.db "SELECT MAX(ts) FROM v9_bars_5min WHERE symbol='MES'"
date -u +"%Y-%m-%d %H:%M:%S"
```

Expected: delta between the two < 10 minutes (not +1 hour).

---

## §4 · Process you'll go through (not invented — straight from prompt §3 / §4)

### Step 1 — CC delivers Phase 2 consultation

CC produces `docs/reports/CC_AUDIT_IB_TIMESTOP_CONSULTATION_2026-05-28.md`
with:
- Per-claim verification verdicts (W-10: 11 claims; IB: 5 bugs).
- Push-backs vs subagent claims.
- Re-ranked fix order if CC disagrees.
- Open questions for you (especially DLL subgraph indices, Sierra TZ).

**You decide:** Phase 3 go / no-go / amendments.

### Step 2 — Phase 3 ASK — Sierra TZ

CC asks you (per `CC_MEGA_PROMPT_7_FIXES §3 Phase 1`):
> "Sierra Chart → Global Settings → General → Time Zone tab. Screenshot."

Group B (TZ flip) is GATED on your answer. The IB and W-10 packages
(A1, A2) can land WITHOUT this answer.

### Step 3 — Phase 3 implementation order

```
A1 (IB cleanup)         — backend only, no DLL, ~1-2h
A2 (W-10 restoration)   — backend only, no DLL, ~2-3h
B  (Chicago TS)         — gated on TZ confirmation, off-RTH window, ~1h
C  (S2 day_type)        — gated on diagnosis (Step 0 SQL probe), variable
```

### Step 4 — Per-fix UAT (4-axis, mandatory)

Per pre-LIVE protocol (`.cursor/rules/mems26-pre-live-protocol.mdc`):
- Quality (specific bug condition gone)
- Recency (`endpoint.latest_ts == DB.MAX(ts)`)
- Cardinality (`len(rows) == requested_limit`)
- Latency (under threshold)

CC pastes raw `curl + jq` output for each axis, per fix. Per CLAUDE.md
Rule 5: "verification quote, not assertion" — no "should work" claims.

### Step 5 — Backend restart

CC coordinates with you (do not restart mid-trade). After restart, all
five §3 axes are verified live before declaring done.

---

## §5 · What stays UNCHANGED (intentional — to bound blast radius)

These were considered and explicitly left alone:
- `sc_study/*.cpp` and `*.h` — DLL changes need Sierra Remote Build, deferred to Package B (Bug #1).
- `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt` — V3 says "Layer 4 per-Day-Type". Registry #11 says "90min flat all patterns". You chose Registry #11. CC will ASK whether to edit V3 directly or write a constitution amendment doc — does NOT decide unilaterally.
- `frontend/v9/src/v9/components/strips/KeyLevelsStrip.tsx` — already reads `ib_high` as nullable. Verify rendering on `null` is graceful but no patch unless a crash surfaces.
- W-6 patterns / W-8 dispatcher / W-1 ATR stop — frozen per `§4 Forbidden surface` of the 7-fixes prompt.

---

## §6 · Risk register — what could still go wrong

| Risk | Mitigation in the prompts |
|---|---|
| Layer 4 removal breaks a hidden caller | §2.1 pushback: `rg -n "_check_time_stop" backend/` MUST return 0 hits outside the deleted region. CC verifies before delete. |
| W-10 re-enable + Bug A fix doesn't actually limit per-bar (subtle race in `_last_bar_ts_for_count`) | New regression test `test_w10_bar_count_per_close.py` covers identical-ts pushes. Live UAT: push 30× same bar over 90s, assert no close. |
| `_closes` empty when TIME_STOP fires (defensive case) | Fix #5 guard: skip close + log WARNING. New test asserts this branch. |
| IB delete breaks day_type seed silently | All 5 consumer-side guards re-confirmed in §2.2 IB Bug #2 push-back list before delete commit. |
| TZ flip breaks every bars-consumer at once | Group B is OFF-RTH only. Probe script runs first. CC must dry-run before flipping. |
| CC adds a third day_type fallback path (sibling-prompt regression) | Fix #6 is now diagnose-first. Step 0 SQL is mandatory. No code change before identifying the case. |
| Constitution V3 deviates from implementation silently | A1.1 + A2.1 AMENDMENTS_LOG entries make the deviation explicit. Constitution amendment doc is a separate item; CC asks before writing. |

---

## §7 · One-line acceptance criteria

You can call this "done" when ALL of these are true:

```
[ ] curl /api/v9/tpo/current.ib_source ∈ {"sierra_live","missing"}
[ ] rg -n "_ib_from_bars\|v9_bars_5min_09_30" backend/ → 0 hits
[ ] cat backend/v9/systems/woodies/config/dispatcher_config.yaml | grep time_stop_minutes → "90"
[ ] rg -n "TIME_STOP_BY_DAY_TYPE\|_check_time_stop" backend/v9/services/trade_manager/bar_level_detector.py → 0 hits
[ ] After live S4 fire and 90 real minutes: v9_trades has exit_reason='TIME_STOP', exit_price IS NOT NULL, pnl_usd != 0
[ ] After bridge pushes same bar 30× in 90s: no TIME_STOP fired
[ ] All 969+ existing tests pass + 5 new tests added pass
[ ] AMENDMENTS_LOG has 2 new entries (IB synthesis revocation + W-10 Option B reversal)
[ ] CC delivered the consultation doc + final report (per §2.5)
```

If any box is unchecked, ask CC to paste the failing command + raw output
and either fix or revert before LIVE.
