# Woodies V1 Production Inventory

Date: 2026-05-15
Spec: docs/MEMS26_WOODIES_DECISION_TREE_V1.md (LOCKED May 9)
Code: backend/v9/systems/woodies/ (1,742 lines, 17 files)

## T1: YAML Configuration Block

| Item | Location | Status |
|---|---|---|
| YAML config file | compliance_manifest.yaml (4,440B) — NOT a runtime config | 🔴 MISSING |
| Loader function | No YAML→engine loader found | 🔴 MISSING |
| Validation logic | No runtime validation | 🔴 MISSING |
| `enabled: false` skip | Not implemented | 🔴 MISSING |
| `reorder_priority` | Not implemented | 🔴 MISSING |

Evidence: `grep -rn "yaml\|YAML\|config.*loader\|load_config\|enabled.*false\|reorder_priority" backend/v9/systems/woodies/` → 0 results (excluding compliance_manifest.yaml which is a static doc, not runtime config).

Engine determines order via hardcoded `detect_all_patterns()` call in `woodies_system.py:166`.

**Summary: 0/5 🟢 | 0/5 🟡 | 5/5 🔴**

---

## T2: Entry Phase A1-A7

| Stage | Spec ID | File | Function | Wired? | Status | Notes |
|---|---|---|---|---|---|---|
| A1 | strategic_gate | cci_calc.py:121 | calc_trend_state() | ✅ | 🟢 | Returns BLUE/RED/GRAY/YELLOW matching spec |
| A2 | day_type_query | — | — | ❌ | 🔴 | No cross-system query to /day_type/current from Woodies |
| A3 | pattern_detection | pattern_engine.py + patterns/*.py | detect_all_patterns() | ✅ | 🟢 | 8 patterns scanned (HFE missing — see T4) |
| A4 | poc_suffering_query | — | — | ❌ | 🔴 | No POC/suffering query from Woodies |
| A5 | otf_clarity_query | — | — | ❌ | 🔴 | No OTF clarity query from Woodies |
| A6 | entry_classification | woodies_system.py:188 | classification logic | 🟡 | 🟡 | Uses TACTICAL/STRATEGIC, not REACTIVE/INITIATIVE per spec |
| A7 | universal_checks | — | — | ❌ | 🔴 | No news/cooldown/cap/stop-range/bridge/EOD checks in Woodies |

**Summary: 2/7 🟢 | 1/7 🟡 | 4/7 🔴**

---

## T3: Active Phase B1-B14

| Stage | Spec ID | Priority | File | Status | Notes |
|---|---|---|---|---|---|
| B1 | stop_check | ABSOLUTE_EXIT | — | 🔴 | Not in Woodies (handled by TradingGateway) |
| B2 | eod_check | ABSOLUTE_EXIT | — | 🔴 | Not in Woodies |
| B3 | color_flip | STRATEGIC_EXIT | — | 🔴 | No color flip detection in active trade mgmt |
| B4 | poc_migration_query | ADVISORY_EXIT | — | 🔴 | No TP#4 query |
| B5 | otf_mid_trade_query | ADVISORY_EXIT | — | 🔴 | No TP#5 query |
| B6 | news_window | ABSOLUTE_EXIT | — | 🔴 | Not in Woodies |
| B7 | time_stop | TIME_EXIT | — | 🔴 | Not in Woodies (in targets_table.py for Day Type) |
| B8 | counter_pattern | TIGHTEN | — | 🔴 | No counter-pattern tighten logic |
| B9 | market_state_query | PARTIAL | — | 🔴 | No TP#6 query |
| B10 | t1_milestone | TARGET | — | 🔴 | Not in Woodies (in trade_manager) |
| B11 | t2_milestone | TARGET | — | 🔴 | Not in Woodies |
| B12 | t3_milestone | TARGET | — | 🔴 | Not in Woodies |
| B13 | trail_check | TRAIL | — | 🔴 | No Vegas EMA-169 trail in Woodies |
| B14 | hold | NO_ACTION | — | 🔴 | No explicit hold state |

**Summary: 0/14 🟢 | 0/14 🟡 | 14/14 🔴**

Note: B1/B2/B6/B7/B10-B12 are handled by trade_manager/gateway, NOT inside Woodies. The spec expects them IN the Woodies decision tree. This is an architectural mismatch.

---

## T4: 9 Patterns

| # | Pattern | Category | File | DLL Export | JSON Field | Status |
|---|---|---|---|---|---|---|
| 1 | ZLR | TREND_CONFIRMING | patterns/zlr.py | zlr_detected, zlr_direction | ✅ in JSON | 🟢 |
| 2 | TT | TREND_CONFIRMING | patterns/tt.py | — (computed in Python) | — | 🟢 |
| 3 | TLB | TREND_CONFIRMING | patterns/tlb.py | — | — | 🟢 |
| 4 | GB100 | TREND_CONFIRMING | patterns/gb100.py | — | — | 🟢 |
| 5 | VEGAS | NEW_TREND | patterns/vegas.py | — (uses ema_34) | — | 🟢 |
| 6 | GHOST | NEW_TREND | patterns/ghost.py | — | — | 🟢 |
| 7 | FAMIR | NEW_TREND | patterns/famir.py | — | — | 🟢 |
| 8 | HTLB | NEW_TREND | patterns/htlb.py | — | — | 🟢 |
| 9 | HFE | NEW_TREND | — | ⚠️ NOT IN DLL | — | 🔴 MISSING |

Evidence for HFE: `grep -rn "HFE\|hook_from_extreme\|Hook.*Extreme" backend/v9/` → 0 results. `grep -rn "hfe\|hook.*extreme" sc_study/` → 0 results.

**Summary: 8/9 🟢 | 0/9 🟡 | 1/9 🔴 (HFE)**

---

## T5: 6 Touch-Points

| TP | Stage | Endpoint | Production Route | Status | Notes |
|---|---|---|---|---|---|
| #1 | A2 | /day-type/current | /api/v9/day_type/current (exists) | 🔴 | Endpoint exists but Woodies doesn't call it |
| #2a | A4 | /poc/current | /api/v9/tpo/current (exists) | 🔴 | Endpoint exists but Woodies doesn't call it |
| #2b | A4 | /suffering-side/check | /api/v9/veto/state (exists) | 🔴 | Endpoint exists but Woodies doesn't call it |
| #3 | A5 | /otf-clarity/state | — | 🔴 | No OTF clarity endpoint |
| #4 | B4 | /poc/migration | /api/v9/tpo/current (has poc_migration) | 🔴 | Data available but Woodies doesn't consume |
| #5 | B5 | /otf-clarity/state | — | 🔴 | Same as #3 |
| #6 | B9 | /market-state | /api/v9/layer0/state (exists) | 🔴 | Endpoint exists but Woodies doesn't consume |

**Summary: 0/7 🟢 | 0/7 🟡 | 7/7 🔴**

---

## T6: 18 Terminal States

| State | String Literal | Logged To | Status |
|---|---|---|---|
| SKIP_color_veto | — | — | 🔴 |
| SKIP_no_pattern | — | — | 🔴 |
| SKIP_universal_block | — | — | 🔴 |
| BUY | — | — | 🔴 |
| SELL | — | — | 🔴 |
| STOP_LOSS | — | — | 🔴 |
| EOD_FORCE | — | — | 🔴 |
| STRATEGIC_EXIT | "STRATEGIC" in woodies_system.py:188 | current_state | 🟡 (classification, not terminal emit) |
| SUFFERING_EXIT | — | — | 🔴 |
| CLARITY_EXIT | — | — | 🔴 |
| NEWS_EXIT | — | — | 🔴 |
| TIME_STOP | — | — | 🔴 |
| TIGHTEN | — | — | 🔴 |
| PARTIAL | — | — | 🔴 |
| SUCCESS_Reactive | — | — | 🔴 |
| SUCCESS_Initiative | — | — | 🔴 |
| SUCCESS_Trail | — | — | 🔴 |
| HOLD | — | — | 🔴 |

**Summary: 0/18 🟢 | 1/18 🟡 | 17/18 🔴**

---

## T7: Priority Hierarchy

No dispatcher/router implementing the 9-class priority order found in Woodies.

Evidence: `grep -rn "ABSOLUTE\|ADVISORY\|priority.*class\|dispatch.*priority" backend/v9/systems/woodies/` → only STRATEGIC/TACTICAL classification, not the 9-tier priority.

Trade management priorities exist in `services/layer4/` and `services/trade_manager/` but are NOT integrated into the Woodies decision tree.

**Status: 🔴 MISSING**

---

## T8: D-Series Rules

| Rule | Location | Status |
|---|---|---|
| D-001 Stop 3-8pt | — in Woodies | 🔴 (exists in trade_manager) |
| D-002 NO BE on T1 | — in Woodies | 🔴 (exists in trade_manager) |
| D-055 Smart BE on T2 | — in Woodies | 🔴 (exists in trade_manager) |
| 30min cool-down | — | 🔴 |
| $200 daily cap | — | 🔴 |
| 60min time stop | targets_table.py (Day Type, not Woodies) | 🟡 |
| Vegas EMA-169 trail | — | 🔴 |

**Summary: 0/7 🟢 | 1/7 🟡 | 6/7 🔴**

---

## T9: 11 DLL Studies in woodies_30min.json

| # | Field | In Sample | Status |
|---|---|---|---|
| 1 | cci_14 | 0.0 | 🟢 |
| 2 | cci_6_tcci | -102.57 | 🟢 |
| 3 | ema_34 | 7464.18 | 🟢 |
| 4 | lsma_value | 0.0 | 🟢 |
| 5 | lsma_above_price | False | 🟢 |
| 6 | swi_value | 0.0 | 🟢 |
| 7 | czi_value | -224.94 | 🟢 |
| 8 | trend_state | GRAY | 🟢 |
| 9 | predictor_next_cci | 0.0 | 🟢 |
| 10 | zlr_detected | False | 🟢 |
| 11 | zlr_direction | NONE | 🟢 |

**Summary: 11/11 🟢**

---

## T10: UFL/UFH Bypass Zones

| Item | Location | Status |
|---|---|---|
| UFL/UFH computation | tpo/levels.py:191 detect_ufl_ufh() | 🟢 (in TPO, not Woodies) |
| A4 consumption | — | 🔴 (Woodies A4 doesn't exist) |
| B4 consumption | — | 🔴 (Woodies B4 doesn't exist) |

**Summary: 1/3 🟢 | 2/3 🔴**

---

## GRAND TOTAL

| Category | Found 🟢 | Partial 🟡 | Stub ⚫ | Missing 🔴 |
|---|---|---|---|---|
| T1 YAML Config (5) | 0 | 0 | 0 | 5 |
| T2 Entry A1-A7 (7) | 2 | 1 | 0 | 4 |
| T3 Active B1-B14 (14) | 0 | 0 | 0 | 14 |
| T4 9 Patterns (9) | 8 | 0 | 0 | 1 |
| T5 6 Touch-Points (7) | 0 | 0 | 0 | 7 |
| T6 18 Terminal States (18) | 0 | 1 | 0 | 17 |
| T7 Priority Hierarchy (1) | 0 | 0 | 0 | 1 |
| T8 D-Series Rules (7) | 0 | 1 | 0 | 6 |
| T9 DLL Studies (11) | 11 | 0 | 0 | 0 |
| T10 UFL/UFH (3) | 1 | 0 | 0 | 2 |
| **TOTAL (82)** | **22** | **3** | **0** | **57** |
