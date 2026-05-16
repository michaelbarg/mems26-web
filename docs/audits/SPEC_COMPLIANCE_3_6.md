# Spec Compliance — COMMIT 3.6 (B4+B5+B9+B10+B11+B12+B14)

## Stage B4 — POC Migration (ADVISORY_EXIT)
Spec source: Decision Tree V1 § Section 5 · B4

Spec items:
- ✅ LONG + price < POC → SUFFERING_FLIP → `b4_poc_migration_query.py:62-63`
- ✅ SHORT + price > POC → SUFFERING_FLIP → `b4_poc_migration_query.py:65-66`
- ✅ UFL/UFH bypass → `b4_poc_migration_query.py:55-60`
- ✅ Default action: TIGHTEN (NOT auto-exit) → `test:23` (RULE 14)
- ✅ NEVER returns CLOSE_ALL → `test:38-41` (RULE 14)
- ✅ Degraded mode: skip → `test:33-34`

Status: 6/6 ✅

## Stage B5 — OTF Mid-Trade (ADVISORY_EXIT)
Spec source: Decision Tree V1 § Section 5 · B5

Spec items:
- ✅ UNCLEAR → NO_CLARITY_MID_TRADE → `b5_otf_mid_trade_query.py:48`
- ✅ Default action: TIGHTEN (NOT exit) → `test:49` (RULE 14)
- ✅ NEVER returns CLOSE_ALL → `test:58-60` (RULE 14)
- ✅ Degraded mode: skip → `test:53-54`

Status: 4/4 ✅

## Stage B9 — Market State (PARTIAL)
Spec source: Decision Tree V1 § Section 5 · B9

Spec items:
- ✅ EXPANDING→SEARCHING = momentum LOST → `b9_market_state_query.py:53`
- ✅ T1 hit → PARTIAL_CLOSE suggestion → `b9_market_state_query.py:55`
- ✅ NEVER returns CLOSE_ALL → `test:91-94` (RULE 14)
- ✅ Degraded mode: skip → `test:85-86`

Status: 4/4 ✅

## Stage B10 — T1 Milestone (TARGET)
Spec source: Decision Tree V1 § Section 5 · B10

Spec items:
- ✅ LONG: price >= T1 → CLOSE_C1 → `b10_t1_milestone.py:43-44`
- ✅ SHORT: price <= T1 → CLOSE_C1 → `b10_t1_milestone.py:46-47`
- ✅ D-002: DO NOT move BE on T1 → `b10_t1_milestone.py:50` (be_moved=False)
- ✅ D-002 verified in test → `test:109-112`
- ✅ Already hit → skip → `test:114-118`

Status: 5/5 ✅

## Stage B11 — T2 Milestone (TARGET)
Spec source: Decision Tree V1 § Section 5 · B11

Spec items:
- ✅ REACTIVE → CLOSE_ALL (no runner) → `b11_t2_milestone.py:51`
- ✅ INITIATIVE → CLOSE_C2 + Smart BE (D-055) → `b11_t2_milestone.py:54`
- ✅ D-055 Smart BE verified → `test:127-131` (be_moved=True)
- ✅ Already hit → skip → `test:133-136`

Status: 4/4 ✅

## Stage B12 — T3 Milestone (TARGET)
Spec source: Decision Tree V1 § Section 5 · B12

Spec items:
- ✅ T3 hit → CLOSE_C3 → `b12_t3_milestone.py:39-40`
- ✅ Terminal: SUCCESS Initiative Full Win → action=CLOSE_C3

Status: 2/2 ✅

## Stage B14 — Hold (NO_ACTION)
Spec source: Decision Tree V1 § Section 5 · B14

Spec items:
- ✅ Always returns HOLD → `b14_hold.py:30`
- ✅ Always last (NO_ACTION priority) → `test:153`

Status: 2/2 ✅

---

## RULE 14 Verification (Advisory Touch-Points):
- ✅ B4: suffering_flip → TIGHTEN, not CLOSE_ALL
- ✅ B5: NO_CLARITY → TIGHTEN, not CLOSE_ALL
- ✅ B9: momentum LOST → PARTIAL_CLOSE suggestion, not CLOSE_ALL
- ✅ All 3 TPs: degraded mode works (endpoint unavailable → HOLD)

## Total: 27/27 ✅ · 0 deferred · 0 missing
