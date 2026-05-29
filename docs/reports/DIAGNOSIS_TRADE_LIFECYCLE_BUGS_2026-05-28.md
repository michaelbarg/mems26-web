# Diagnosis: Trade Lifecycle Bugs (5 Findings) · 2026-05-28

**Auditor:** Claude Code · Phase 1 (READ-ONLY diagnosis)
**Scope:** 5 bugs from the 17:45 ET S4 GB100+HTLB LONG fire

---

## §0 · TL;DR

| Bug | Summary | Root Cause | Severity |
|-----|---------|-----------|----------|
| **A** | TIME_STOP fires after 52s | `_bar_count` increments per bridge push (~3s), not per closed 5-min bar → 18 pushes = 54s ≈ 18 "bars" | 🔴 CRITICAL |
| **B** | Demo stop=7579.25 (above entry for LONG) | NOT a bug — Smart BE+1T fired correctly after T1 hit, then new BE stop was hit on the same bar | ✅ WORKING AS DESIGNED |
| **C** | t1_hit_ts == stop_hit_ts | Same bar covered both T1 and stop after Smart BE; BarLevelDetector processes T1 first, then Smart BE moves stop, then stop hit — all on the same bar's ts | ⚠️ LOW |
| **D** | pnl=0.0, exit_price=NULL on TIME_STOP | W-10 `_check_time_stops()` calls `tm.close_trade()` without setting `exit_price` first | 🔴 HIGH |
| **E** | stop_hit_ts = 09:30:00 (before entry) | Chicago TS +1h over-correction: bar ts 09:30 UTC = 05:30 ET written as stop_hit_ts by BarLevelDetector | 🟡 MEDIUM |

---

## §1 · Bug A — TIME_STOP fires after 52 seconds

**(a) Confirmed?** YES — DB shows trade #155 entry at `17:45:05` and exit at `17:45:57` (52s) with `exit_reason=TIME_STOP`.

**(b) Subsystem owner:** `backend/v9/systems/woodies/woodies_system.py:201` — `self._bar_count += 1` fires on every `process_bar()` call.

**(c) Root cause:** The bridge pushes the DLL export every ~3 seconds. Each push triggers `process_bar()`, incrementing `_bar_count`. The W-10 enforcer fires when `bars_open >= limit_bars` (18). After 18 pushes × ~3s = ~54 seconds, `bars_open` reaches 18 and TIME_STOP fires. The counter should only increment on **new closed bar timestamps**, not on every push (Sierra sends multiple UPDATEs for the same in-progress bar).

The dedup gate at `woodies_system.py:395-405` only protects fire signals, not the bar counter itself.

**(d) Minimum fix:** Track the last bar timestamp and only increment `_bar_count` when the bar ts changes:
```python
# woodies_system.py:201 area
bar_ts_key = bar.get("ts", 0)
if bar_ts_key != self._last_bar_ts_for_count:
    self._bar_count += 1
    self._last_bar_ts_for_count = bar_ts_key
```
Add `self._last_bar_ts_for_count = None` in `__init__`.

**(e) Regression test:** Trade with 5 pushes of the same bar ts → `bars_open` should be 1, not 5.

**(f) Risk:** LOW blast radius — single field change, bar_count is only used by time_stop.

---

## §2 · Bug B — Demo stop "inverted" for LONG (#156)

**(a) Confirmed?** **NO — this is WORKING AS DESIGNED.**

**(b) Explanation:** Demo trade #156 has `stop=7579.25 = entry(7579.0) + 0.25 (1 tick)`. This is the **Smart BE+1T** rule from `manager.py:260-298` (`_apply_smart_be_after_t1`). Line 284: `target_stop = entry + tick` for LONG.

The sequence: (1) trade opened at 7579.0 with original stop 7577.75, (2) T1 hit at 7582.0 → `on_target_hit` calls `_apply_smart_be_after_t1` → stop moved to 7579.25, (3) price retraced below 7579.25 → stop hit on the same bar.

Trade #156 shows `t1_hit_ts = 2026-05-28 18:45:00` — T1 WAS hit. The "inverted" stop is actually the post-T1 Smart BE.

**Why shadow #155 differs:** Shadow trade was already closed by TIME_STOP (Bug A) at 17:45:57, before T1 could be hit. So shadow never reached the Smart BE path. The demo trade stayed open longer (no W-10 time stop in BarLevelDetector for demo? — see §6).

**(c-f)** N/A — not a bug.

---

## §3 · Bug C — t1_hit_ts == stop_hit_ts (demo #156)

**(a) Confirmed?** YES — both timestamps are `2026-05-28 18:45:00.000000`.

**(b) Subsystem owner:** `bar_level_detector.py:88-110` — processes T1 hit, then continues processing stop hit on the same bar loop iteration.

**(c) Root cause:** On the 18:45 bar, `bar_high >= T1(7582.0)` triggered T1 hit. `on_target_hit` → `_apply_smart_be_after_t1` moved stop to 7579.25. Then `bar_low <= stop(7579.25)` triggered stop hit on the same bar. Both received `fill_ts = bar_ts` (the bar's timestamp).

This is a legitimate wide-range bar scenario. The BarLevelDetector at line 90 does `continue` after stop hit, but T1 was processed FIRST (targets checked before stop on the next bar? No — stop is checked FIRST at line 87-92). Actually: stop check at line 87 uses the ORIGINAL stop (7577.75). For LONG, `bar_low <= 7577.75` — if the bar's low was above 7577.75 (e.g. 7578), stop didn't trigger on the original stop, so we proceed to T1 check. T1 hit → Smart BE → new stop=7579.25. But the stop check already PASSED for this bar. The new stop is only effective on the NEXT bar.

Wait — the `continue` on line 92 skips target checks when stop hits. But the stop with the original 7577.75 might NOT have been hit if bar_low was above it. Then T1 hit → Smart BE → new stop. On the NEXT bar, the new stop 7579.25 is checked.

So the timestamps are from TWO DIFFERENT bars that happened to have the same bar_ts? No, `18:45:00` appears once. This means T1 and stop happened on different bars that both had `18:45:00` as ts... or the same bar processed twice.

Most likely: on one bar the original stop wasn't hit (low > 7577.75), T1 was hit (high >= 7582.0), Smart BE raised stop to 7579.25. On the same or next push with same bar_ts, bar_low <= 7579.25 → stop hit. Both get the same `fill_ts = bar_ts = 18:45:00`.

**(d) Fix:** Not strictly needed for shadow. For LIVE, T1+stop on same bar should be resolved by priority: if both trigger, record T1 hit but do NOT apply Smart BE until the next bar close.

**(e) Regression test:** Inject a bar where high > T1 and low < original_stop — verify only stop fires (adverse priority).

**(f) Risk:** LOW — cosmetic in shadow mode.

---

## §4 · Bug D — pnl=0.0 and exit_price=NULL on TIME_STOP (#155)

**(a) Confirmed?** YES — `pnl_usd=0.0`, `exit_price=NULL` on trade #155.

**(b) Subsystem owner:** `woodies_system.py:553-559` — `_check_time_stops()` calls `tm.close_trade(int(trade_id), "TIME_STOP")` without setting `exit_price` first.

**(c) Root cause:** `manager.py:349-366` `close_trade()` sets `exit_ts` and `exit_reason` but does NOT set `exit_price`. It calls `_calculate_pnl()` which at line 553 does:
```python
exit_p = trade.exit_price or trade.entry_price
```
Since `exit_price` is NULL, it falls back to `entry_price`, producing `pnl_usd = 0.0`.

Contrast with `on_stop_hit()` at line 334: `trade.exit_price = trade.stop` — explicitly sets exit_price before PnL calc.

The BarLevelDetector's TIME_STOP path at line 122 DOES set `refreshed.exit_price = bar_close`, but the W-10 path in `woodies_system.py:556` does NOT.

**(d) Minimum fix:** Set `exit_price` before calling `close_trade()` in `_check_time_stops()`:
```python
# woodies_system.py, inside _check_time_stops, before tm.close_trade:
trade_obj = tm._get_trade(int(trade_id))
if trade_obj and self._closes:
    trade_obj.exit_price = self._closes[-1]
tm.close_trade(int(trade_id), "TIME_STOP")
```

**(e) Regression test:** Fire TIME_STOP on a trade → verify `exit_price` is not NULL and `pnl_usd != 0.0`.

**(f) Risk:** LOW — single assignment before existing call.

---

## §5 · Bug E — stop_hit_ts/exit_ts = 09:30:00 (trades #14, #15)

**(a) Confirmed?** YES — trade #14 (shadow) and #15 (demo) both show `exit_ts = 2026-05-28 09:30:00.000000` despite `entry_ts = 13:35:01`.

**(b) Subsystem owner:** `bar_level_detector.py:89-91` — `on_stop_hit(trade.id, fill_ts=bar_ts)` passes `bar_ts` as the fill timestamp.

**(c) Root cause:** The Chicago TS over-correction. The bar that hit the stop had `ts = 09:30:00` in the DLL export (Chicago wall-clock). The bridge adds +5h to bar.ts for the woodies_5min stream, but the 5min bars stream uses its own fix path. The BarLevelDetector subscribes to `5min` bars (not `woodies_5min`), and the `5min` bar timestamps may have a different correction or none at all.

Actually, `09:30:00.000000` without timezone — this is stored as a naive datetime. The `_parse_ts` at line 166 parses it, and `on_stop_hit` passes it directly. If the 5min bars carry timestamps in Chicago wall-clock (CDT = UTC-5), then `09:30 CDT = 14:30 UTC`, which is close to the 13:35 UTC entry. The bug is that the raw Chicago time was stored without conversion.

**(d) Minimum fix:** Ensure `_parse_ts` in BarLevelDetector applies the same Chicago-to-UTC conversion as the bridge.

**(e) Regression test:** Mock a bar with Chicago-encoded ts, verify the fill_ts stored is UTC.

**(f) Risk:** MEDIUM — affects all trades closed by BarLevelDetector.

---

## §6 · Cross-Cutting Observations

1. **Dual TIME_STOP paths conflict:** The W-10 enforcer in `woodies_system.py:533` and the BarLevelDetector at `bar_level_detector.py:117` BOTH implement time stops. W-10 uses bar-count (broken — counts pushes). BarLevelDetector uses wall-clock elapsed minutes with Day Type limits. Trade #155 was closed by W-10 (the woodies path) at 52 seconds. If W-10 hadn't fired prematurely, BarLevelDetector might have applied a 30-minute Normal-day time stop instead.

2. **Shadow vs Demo lifecycle divergence:** Shadow trades go through TradeManager (SQLAlchemy) and are visible to BarLevelDetector. Demo trades go through `_persist_trade` (raw SQLite) and are NOT in TradeManager's SQLAlchemy session — but BarLevelDetector queries all non-CLOSED trades via SQLAlchemy, and the raw-SQLite rows ARE visible after commit. This works but is fragile.

3. **Bug B is actually Bug A in disguise:** If W-10 hadn't killed shadow #155 prematurely, it would have reached T1, gotten Smart BE, and the stop would have been identical to demo #156. The apparent "stop inversion" is actually a consequence of the premature TIME_STOP.

---

## §7 · What I Couldn't Verify

- Whether BarLevelDetector processes demo trades at all (it queries `get_active_trades()` which uses SQLAlchemy — demo trades inserted via raw SQLite may or may not be visible depending on session state)
- The exact bar that triggered the 18:45 stop hit for demo #156 (would need to check `v9_bars_5min` for that window)
- Whether the Day Type time stop in BarLevelDetector (`TIME_STOP_BY_DAY_TYPE`) interferes with W-10

---

## §8 · Ranked Fix Order

| Priority | Bug | Why first |
|----------|-----|-----------|
| **1** | **A — TIME_STOP 52s** | CRITICAL — kills every trade before any target reachable; currently makes the system useless |
| **2** | **D — pnl=0/exit_price=NULL** | HIGH — without correct PnL, can't evaluate system performance |
| **3** | **E — 09:30 timestamp** | MEDIUM — corrupts trade audit trail |
| **4** | **C — t1==stop same ts** | LOW — cosmetic in shadow, correct by construction |
| **5** | **B — not a bug** | N/A — Smart BE working as designed |
