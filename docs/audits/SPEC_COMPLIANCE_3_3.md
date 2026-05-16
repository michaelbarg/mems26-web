# Spec Compliance — COMMIT 3.3 (A2 + A4 + A5 + A7 Touch-Points + Universal)

## Stage A2 — Day Type Query (Touch-Point)
Spec source: Decision Tree V1 (Drive 1nuLAh8T...) § Section 4 · A2

Spec items:
- ✅ TREND_DAY → prefer ZLR, TT, TLB, GB100 → `a2_day_type_query.py:17`
- ✅ RANGE_DAY → prefer HFE, FAMIR → `a2_day_type_query.py:19`
- ✅ REVERSAL_DAY → prefer VEGAS, GHOST, FAMIR → `a2_day_type_query.py:20`
- ✅ GAP_FILL → bias INITIATIVE (empty prefs, handled in A6) → `a2_day_type_query.py:21`
- ✅ BROAD_CHANNEL → REACTIVE preference → `a2_day_type_query.py:22`
- ✅ NEUTRAL → no preference → `a2_day_type_query.py:23`
- ✅ Degraded mode: no preference, proceed normal → `test_a2.py:47-49`
- ✅ NEVER vetoes (RULE 14) → `test_a2.py:53-57` (no veto/block field)

Terminal states emitted: None (advisory only) ✅ matches § Section 6
Status: 8/8 ✅ · 0 deferred · 0 missing

---

## Stage A4 — POC + Suffering Side Query (Touch-Point)
Spec source: Decision Tree V1 (Drive 1nuLAh8T...) § Section 4 · A4

Spec items:
- ✅ Price within 3pt of IB/VA edge → REACTIVE hint → `a4_poc_suffering_query.py:69-72`
- ✅ Near middle + POC migrating → INITIATIVE hint → `a4_poc_suffering_query.py:76-80`
- ✅ Suffering matches entry direction → warning → `a4_poc_suffering_query.py:87-91`
- ✅ UFL/UFH bypass → warning cleared → `a4_poc_suffering_query.py:58-63`
- ✅ Degraded mode: INITIATIVE default, skip suffering → `test_a4.py:81-87`
- ✅ Advisory only (RULE 14) → `test_a4.py:90-98` (no veto/entry_blocked)

Terminal states emitted: None (advisory only) ✅ matches § Section 6
Status: 6/6 ✅ · 0 deferred · 0 missing

---

## Stage A5 — OTF Clarity Query (Touch-Point)
Spec source: Decision Tree V1 (Drive 1nuLAh8T...) § Section 4 · A5

Spec items:
- ✅ BOTH_CLEAR → safe → `a5_otf_clarity_query.py:54`
- ✅ SELLERS_CLEAR + LONG → safe → `a5_otf_clarity_query.py:58`
- ✅ BUYERS_CLEAR + SHORT → safe → `a5_otf_clarity_query.py:62`
- ✅ UNCLEAR → NO_CLARITY warning → `a5_otf_clarity_query.py:66`
- ✅ Direction mismatch → DIRECTION_MISMATCH → `a5_otf_clarity_query.py:69`
- ✅ Degraded mode: skip, UNAVAILABLE → `test_a5.py:45-48`
- ✅ Advisory only (RULE 14) → `test_a5.py:51-60` (no veto)

Terminal states emitted: None (advisory only) ✅ matches § Section 6
Status: 7/7 ✅ · 0 deferred · 0 missing

---

## Stage A7 — Universal Pre-Entry Checks
Spec source: Decision Tree V1 (Drive 1nuLAh8T...) § Section 4 · A7

Spec items:
- ✅ news_window_check (±5min) → `a7_universal_checks.py:63-65`
- ✅ cool_down_active → `a7_universal_checks.py:68-69`
- ✅ daily_loss_cap_hit ($200) → `a7_universal_checks.py:72-73`
- ✅ stop_within_3_to_8_pts (D-001) → `a7_universal_checks.py:76-77`
- ✅ bridge_status healthy → `a7_universal_checks.py:80-81`
- ✅ eod_distance > 60min → `a7_universal_checks.py:84-85`
- ✅ All pass → entry_approved=TRUE → `test_a7.py:18-26`
- ✅ Any fail → skip with reason → 6 test classes verify each

Terminal states emitted: SKIP (universal block), BUY, SELL ✅ matches § Section 6
Status: 8/8 ✅ · 0 deferred · 0 missing

---

## Total: 29/29 ✅ · 0 deferred · 0 missing
