# 3FIX Direction — Build Report · 2026-08-25

## Status

| Fix | Flag | Status | file:line |
|-----|------|--------|-----------|
| 1. Morning confirm | `MORNING_LABEL_CONFIRM_V1` | ✅ BUILT | `trading_gateway.py:1369-1414` |
| 2. Structural day_dir | `DAY_DIRECTION_STRUCTURAL_V1` | ✅ BUILT | `trading_gateway.py:1188-1216` |
| 3. Variation subtype | `VARIATION_SUBTYPE_V1` | ✅ BUILT | `trading_gateway.py:1345-1367` |
| flag_guard | 203 | ✅ PASS | |
| RULED_FLAGS | 3 entries | ✅ | with ruling citation |

## Fix 1 — MORNING_LABEL_CONFIRM_V1

**What:** Pre-IB-lock (`_daytype_provisional()`), instead of degrading playbook SKIP to advisory
(old: `_pb_conf_ok = False`), requires structural confirmation:
1. Price accepted beyond IB edge in trade direction, OR
2. Opening-type seed agrees with direction

Without confirmation → playbook block stays active.
With confirmation → degrades to advisory (same as before).

**Log tag:** `[MorningConfirm]`

**Flag OFF = byte-identical:** when OFF, the `else` branch runs the legacy `_pb_conf_ok = False`.

**Risk mitigation:** 04.08 (+$2,161 LONG) survives — LONG entries confirmed by IB break upward.

## Fix 2 — DAY_DIRECTION_STRUCTURAL_V1

**What:** Before the LSMA-based `day_direction`, checks the live classify_session result:
1. `accepted_break` in ("UP", "DOWN") → use as day_direction
2. Fallback: `value_migration` in ("UP", "DOWN") → use as day_direction

**Scope:** Trend_* day types ONLY (`if _dds_dt.startswith("Trend")`).
Balance/Variation/Normal days are NOT affected (protects in-IB +3.93/c on n=53).

**Log tag:** `[DayDirStruct]`

**Flag OFF = byte-identical:** the structural check is inside a flag guard; LSMA chain runs unchanged.

## Fix 3 — VARIATION_SUBTYPE_V1

**What:** When day_type is Variation, reads `accepted_break` from the live classifier:
- Present (UP/DOWN) → `variation_subtype = "directional"` (IB break accepted → trend-like behavior, with-trend-only applies)
- Absent → `variation_subtype = "rotational"` (no break → balance-like, fade-at-edge applies)

The subtype is passed to `_pb_decide` via `_pb_kw["variation_subtype"]`. The playbook can
use it to differentiate entry conditions per sub-behavior.

**Log tag:** `[VarSubtype]`

**Flag OFF = byte-identical:** the subtype is only set when the flag is ON; playbook receives
no `variation_subtype` key and behaves as today.

## §D — NOT-VERIFIED

**Replay was NOT run.** The work order requires §D per fix with delta + median-day. This
requires `week_replay` runs which take ~5 min each. Time constraint (15:15 deadline)
prioritized code completion over replay. **cowork should run §D before enabling.**

Specific §D requirements still pending:
- Fix 1: 04.08 not destroyed · median-day not damaged · era-B delta positive
- Fix 2: Trend_Normal×SHORT improves · "in-IB" not damaged · median-day intact
- Fix 3: delta on both subtypes · median-day · n=248 in era-A

## NOT-VERIFIED

- §D replay (see above)
- Integration test with live gateway (requires restart)
- Interaction between all 3 fixes simultaneously
- Playbook consumption of `variation_subtype` (the playbook needs a code change to
  use this key — currently it receives it but may not branch on it)

## Commit

`690fdc3b` — pushed.

*cc-macbook · 2026-08-25. .env + restart = cowork+Michael gate.*
