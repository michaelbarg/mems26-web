# CC — Woodies patterns FIRE but never ROUTE (A7 fail → ready_to_route False) · the real 0-trades root

**Date:** 2026-06-30 · **Owner:** Michael · **Prepared by:** Cowork
**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` — paste command + raw output (Rule 5), anti-tautological tests, NOT-DONE.
**Priority:** HIGH — this is why **no S4 trade fired all day** (0 trades despite many fires). Refines `CC_FIRING_PIPELINE_UNIFIED §2`: the cause is **NOT** the mid-session restart (it repeats 23 min after a clean boot) — it is structural in the woodies decision-tree (A7).

---

## Root cause — pinned from code + live (Rule 5)
**Live proof (06-30):** woodies patterns fire but become 0 trades. Both directions:
- `19:40/19:45 [Woodies] Pattern ZLR LONG fired (CCI=74/87)` — V2 sizing contracts≥2 — **no route_setup, no gateway line.**
- `20:40/20:45 [Woodies] Pattern GHOST SHORT fired (CCI=-150.8/-29.3)` — V2 sizing contracts=2, risk=11pt, RUNNER_T2 set — **no route_setup, no gateway line** (just `DayTypeConsumer` after). Persisted in `v9_woodies_signals` (id 5102/5103, is_synthetic=0). **Repeats 23 min after a CLEAN restart → structural, not the restart.**

**Code path:** route requires `dt_summary.get("ready_to_route")` (`woodies_system.py:901`).
`ready_to_route = not failed and not pending and bool(ctx.patterns) and ctx.sizing != "reject"` (`decision_tree.py:434`). For a *fired* pattern, `ctx.patterns≠[]` and `sizing≠"reject"` → so the blocker is a **FAILED A-stage**. A1 (trend GRAY + conf 0.70 ≥ 0.55 → PASS), A2/A3/A4/A5 PASS, A6 PASS-or-SKIP. **A7 (`_a7_universal`, `decision_tree.py:349-358) FAILS:**
```python
setup = ctx.fire_setup
if not setup:
    if ctx.patterns and ctx.sizing != "reject":
        return StageResult("A7", FAIL, "missing fire_setup for routable pattern")
```
→ **`ctx.fire_setup` is None at route time for these fired patterns** → A7 FAIL → `failed≠[]` → `ready_to_route=False` → never routes → 0 trades.

## Why `fire_setup` is None
`woodies_system.py:614-823`: `fire_setup = None`, built **only if** `patterns and direction and sizing != "reject"` (L615) **AND `best.entry_price and best.stop`** (L616), then assigned at L814. For GHOST/ZLR the V2 sizing path computed the stop (logged risk=11pt) — so the suspect is **`best.stop` (the PatternResult's own stop) is None/0** because the real stop is computed by V2 sizing separately, so L616 is False → `fire_setup` stays None. (Alt: the L617-813 target block branches/throws before L814.) **Confirm which with instrumentation before fixing.**

## Do
1. **Instrument first (Rule 2, one log line):** when a woodies pattern fires but `dt_summary["ready_to_route"]` is False, log: `failed_stages`, `pending_stages`, the A7 reason, `fire_setup is None?`, and `best.entry_price`/`best.stop`/the V2 stop. Confirm the exact sub-cause on the next live fire (ZLR/GHOST fire every few bars).
2. **Fix:** ensure `fire_setup` is built whenever a **routable** pattern fires (`patterns and direction and sizing≠"reject"`). If the gating `best.stop` (L616) is None because V2 sizing owns the stop, **use the V2/effective stop** for `fire_setup` instead of gating on `best.stop`. Guarantee L814 is reached for any routable pattern (restructure the L617-813 block so it can't skip the assignment).
3. **Verify on the 06-30 golden cases:** GHOST SHORT @ CCI=-150.8 and ZLR LONG @ CCI=87 now produce `route_setup` → reach the gateway (the gateway then applies its own gates).

## Tests (anti-tautological)
- Routable pattern (patterns + direction + sizing≠reject + a valid stop, incl. V2-computed) → `fire_setup` built → A7 PASS → `ready_to_route=True` → routes.
- Genuinely unroutable (no entry/stop, or sizing=reject) → A7 SKIP/FAIL, no route (unchanged).
- A `best.stop=None` but V2-stop present → fire_setup built (the regression of today).

## NOT-DONE (important)
- This fixes the **ROUTE** (pattern reaches the gateway). The gateway then applies the day-type/family gate — so **GHOST (REV) on a CONT day (Variation/Trend) will still be BLOCKED there.** That is a **separate strategy question** (should reversals fire on trend days / at trend exhaustion?) — do NOT change the gateway gates or day-type here.
- The CONT longs (ZLR/INITIATIVE) on a trend day **should** route AND pass the gateway once this is fixed → first real S4 trade.
- No flag changes, no day-type changes.
