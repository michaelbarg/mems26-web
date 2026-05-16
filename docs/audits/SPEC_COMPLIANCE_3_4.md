# Spec Compliance — COMMIT 3.4 (B1 + B2 + B6 Absolute Exits)

## Stage B1 — Stop Check
Spec source: Decision Tree V1 (Drive 1nuLAh8T...) § Section 5 · B1

Spec items:
- ✅ LONG: current_price <= stop_price → STOP_HIT → `b1_stop_check.py:37-38`
- ✅ SHORT: current_price >= stop_price → STOP_HIT → `b1_stop_check.py:40-41`
- ✅ Terminal: CLOSE ALL + cool-down → `test_b1_b2_b6.py:22` (action=CLOSE_ALL)
- ✅ Priority class: ABSOLUTE_EXIT → `b1_stop_check.py:33`
- ✅ No scoring (RULE 13) → binary stop_hit boolean

Status: 5/5 ✅ · 0 deferred · 0 missing

---

## Stage B2 — EOD Check
Spec source: Decision Tree V1 (Drive 1nuLAh8T...) § Section 5 · B2

Spec items:
- ✅ current_time_et >= 15:59 → EOD_FORCE → `b2_eod_check.py:44`
- ✅ Terminal: CLOSE ALL — EOD force (D-002 no overnight) → `test_b1_b2_b6.py:53`
- ✅ Priority class: ABSOLUTE_EXIT → `b2_eod_check.py:34`
- ✅ Time parsing handles HH:MM format → `b2_eod_check.py:40-41`

Status: 4/4 ✅ · 0 deferred · 0 missing

---

## Stage B6 — News Window
Spec source: Decision Tree V1 (Drive 1nuLAh8T...) § Section 5 · B6

Spec items:
- ✅ Tier 1 within ±5min → CLOSE ALL → `b6_news_window.py:42-43`
- ✅ Tier 2 within ±5min and size > 1 → reduce to 1 → `b6_news_window.py:46-48`
- ✅ Terminal: CLOSE ALL — News emergency → `test_b1_b2_b6.py:75`
- ✅ Priority class: ABSOLUTE_EXIT → `b6_news_window.py:34`
- ✅ No news → HOLD → `test_b1_b2_b6.py:93`

Status: 5/5 ✅ · 0 deferred · 0 missing

---

## Total: 14/14 ✅ · 0 deferred · 0 missing
