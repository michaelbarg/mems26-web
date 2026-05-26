# D-095 · Defer Pkg 4a + 4b · Scope Absorbed by 3b-3

**Status:** 🔒 LOCKED · 2026-05-25 11:18 IL
**Owner:** Michael Barg
**Decided by:** Michael (chat 25/5 11:18) after Cursor audit of Pkg 3b-3 final state
**Supersedes (partial):** `docs/plans/PRE_LIVE_PIPELINE_2026-05-23.md` lines 102, 103, 115, 116 · Pkg 4a + 4b queue entries
**Related:** `docs/decisions/D-094_PKG3B_TRAIL_DECISIONS.md` (which expanded 3b-3 scope to include all 5 Layer 4 services)

---

## TL;DR

`Pkg 4a` (Risk Rules · Critical · 2 EXIT rules) and `Pkg 4b` (Risk Rules · Tightening · 3 rules) are **deferred**. Their entire functional scope is already implemented in `backend/v9/services/trail_engine.py` v3 (3b-3 final commit `1e01c4a`) via the 5 Layer 4 services wired into `_apply_layer4()`.

Phase A sequence collapses from `4a → 4b → 8 → 6` to `8 → 6`. The `RiskRule` interface wrapping all 5 Layer 4 services is consolidated into Pkg 6 (TradeManager extensible · LAST).

---

## Background

The V2 plan (23/5 17:30) split Risk Rules into two packages:

- **Pkg 4a** · `risk_rules.py` · 2 EXIT classes: `TCCIExitRule()` + `DirectionChangeRule()`
- **Pkg 4b** · 3 tightening classes: `SWITightenRule()` + `CCIFlatRule()` + `MFETightenRule()`

When the plan was written, Layer 4 services were "5 of 8 existing as DEAD CODE in `backend/v9/services/layer4/`" with zero imports outside tests (D-094 §3.B Cursor audit · 24/5 17:30).

Pkg 3b-3 (D-094 §3.B Option C+ · 24/5 19:00) wired all 5 services into the TrailEngine via `_apply_layer4()` per the §3.B.3 evaluation order (mfe → cci → tcci → swi → day_type_targets). This was committed as `6b2b7cc` → amended to `1e01c4a` on 24/5 21:42.

The audit on 25/5 11:00-11:18 (this chat) confirmed that **the entire functional scope of Pkg 4a + 4b is now live in TrailEngine v3**.

---

## Audit findings · Pkg 4a + 4b mapping to live code

| Original plan | Live in TrailEngine v3 | Evidence |
|---|---|---|
| `TCCIExitRule` · EXIT on TCCI × CCI14 cross against trade direction | ✅ `tcci_cross_exit.evaluate()` at `_apply_layer4` step 3 | `backend/v9/services/trail_engine.py:608-622` · consumes `direction_change_event` from `WoodiesSystem.get_layer4_context()` |
| `DirectionChangeRule` · S1 reports change → EXIT | ⚠️ **PARTIAL** · only `NO_TRADE` reclass closes trade · other reclasses log WARN | `_handle_day_type_action` at `backend/v9/services/trail_engine.py:687-728` (`DAY_TYPE_TARGETS_MISMATCH` + `no_trade` gate) |
| `SWITightenRule` · SWI red → tighten 25% | ✅ `swi_tighten.evaluate()` at `_apply_layer4` step 4 | `backend/v9/services/trail_engine.py:624-631` · tightest-stop wins via `_apply_tightest_stop` |
| `CCIFlatRule` · CCI flat 3+ bars → tighten | ✅ `cci_flat_tighten.evaluate()` at `_apply_layer4` step 2 | `backend/v9/services/trail_engine.py:599-606` · gated on `cci_history >= 3` |
| `MFETightenRule` · MFE ≥ 80% of T2 → tighten | ✅ `mfe_peak_tighten.evaluate()` at `_apply_layer4` step 1 | `backend/v9/services/trail_engine.py:591-597` |

**Net:** 4 of 5 rules are 1:1 live. The 5th (`DirectionChangeRule`) is partially live — the NO_TRADE escalation is wired, but per-Day-Type reclass (e.g., `Trend_Normal` → `Variation`) only logs WARN and does NOT close the trade.

---

## Decision

### 1. Defer Pkg 4a

`Pkg 4a` is **deferred**. No new `risk_rules.py` file is created in Phase A.

- `TCCIExitRule` functional equivalent = `tcci_cross_exit.evaluate()` (live).
- `DirectionChangeRule` functional equivalent = `_handle_day_type_action()` partial behavior (live for NO_TRADE only). **Michael accepted** (25/5 11:18) that the existing 7-layer defense (Adaptive Stop · Time Stop · TCCI cross · CCI Flat · SWI · MFE peak · NO_TRADE reclass) is sufficient · no additional EXIT on non-NO_TRADE day-type reclass is required pre-LIVE. Stop-loss is the floor.

### 2. Defer Pkg 4b

`Pkg 4b` is **deferred**. All 3 tightening rules are already live in `_apply_layer4()`.

### 3. NEXT = Pkg 8 (Quality V2)

Phase A queue updated:

```
Was: 3c → 4a → 4b → 5a → 5b → 5c → 8 → 6
Now: 3c (done) → 5a (done) → 5b (done) → 5c (done) → 8 (NEXT) → 6 (LAST)
```

**Pkg 8 is blocked on G0 spec** — the Auth Table is still pending Michael delivery (`STATUS_BOARD.md` line 80 · `⬜ (Auth Table)`). Until the Auth Table is provided, Pkg 8 cannot start.

### 4. Pkg 6 absorbs RiskRule interface

Pkg 6 (TradeManager extensible · LAST) was originally planned to wrap 2 Pkg 4a classes + 3 Pkg 4b classes (5 RiskRule subclasses total). The deferred scope shifts to Pkg 6:

- Pkg 6 will define the `RiskRule` base class
- Pkg 6 will wrap all 5 live Layer 4 services in `RiskRule` subclasses for the plug-in registry
- Zero functional change · refactor only (same evaluate logic, same order)

This consolidates the wrapping into a single coherent pass instead of split across 3 packages.

### 5. `DirectionChangeRule` future extension (post-LIVE)

If post-LIVE SHADOW + LIVE soak reveals that per-Day-Type reclass (Trend_Normal → Variation, etc.) regularly hurts P&L on open trades, we revisit. For now: WARN log only · stop-loss + TCCI cross handle the risk.

---

## Implications

### Time saved

- Pkg 4a estimated CC time: ~4h
- Pkg 4b estimated CC time: ~4h
- **Total: ~8h saved** (plus Cursor handoff drafting + G3 review · ~2h)

### Pkg 6 scope adjustment

Pkg 6 grows by ~30-60 minutes (wrap 5 services instead of 2). Net effect on total Phase A wall-clock: -7h.

### Risk surface reduction

5 fewer new classes + 1 fewer new file (`risk_rules.py`) means fewer surfaces for bugs pre-LIVE. Consistent with `mems26-pre-live-protocol.mdc` · "smallest correct change".

### Plan amendments

- `docs/plans/PRE_LIVE_PIPELINE_2026-05-23.md` table (lines 102-103) · mark 4a/4b as DEFERRED with pointer to this doc
- `docs/plans/PRE_LIVE_PIPELINE_2026-05-23.md` sequencing block (lines 115-117) · drop Weeks 3-4 4a/4b parallel rows · collapse to Week 5 = Pkg 8 → Pkg 6
- `docs/plans/STATUS_BOARD.md` build queue · mark 4a/4b cells DEFERRED · add D-095 reference

---

## Audit trail

| Date | Event |
|---|---|
| 23/5 17:30 | V2 plan locked Pkg 4a + 4b with 5 rule classes (when Layer 4 services were dead code) |
| 24/5 19:00 | D-094 §3.B Option C+ locked · Pkg 3b-3 to wire 5 Layer 4 services into TrailEngine |
| 24/5 21:23 | Pkg 3b-3 committed as `6b2b7cc` · all 5 services wired in `_apply_layer4()` |
| 24/5 21:42 | Pkg 3b-3 amended to `1e01c4a` (3b-3.1 hotfix folded) · Layer 4 wiring order finalized per D-094 §3.B.3 |
| 24/5 21:45 | Pkg 3b-3 G3 PASS · 59/59 trail_engine tests green · zero regressions |
| 25/5 11:00 | Cursor audit (this chat) confirmed 4 of 5 Pkg 4a+4b rules live in TrailEngine v3 |
| 25/5 11:16 | Michael accepted (chat 11:18) that the 7-layer defense is sufficient · `DirectionChangeRule` extension deferred |
| 25/5 11:18 | **D-095 LOCKED** · 4a + 4b deferred · NEXT = Pkg 8 (blocked on Auth Table) |
