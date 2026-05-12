# HOTFIX V9.0.5.2 — Session Classifier (Architectural)

**Date:** 2026-05-12
**Authority:** GAP-014, D-083

## Problem
System reported "MARKET_CLOSED" during Globex overnight hours.
MES trades 23/5 — only WEEKEND and MAINTENANCE are truly closed.

## Solution
Created `SessionClassifier` as shared module (D-083):
- 8 session types: OVERNIGHT, PRE_MARKET, CASH_OPEN, FIRST_HOUR, CASH_HOURS, AFTER_HOURS, MAINTENANCE, WEEKEND
- `is_trading_active`: True for everything except WEEKEND + MAINTENANCE
- `is_globex()` / `is_cash()` helpers

Updated FiveMinSystem to use SessionClassifier instead of raw time checks.
Mode now correctly shows OVERNIGHT_MODE during Globex hours.

## Self-QA Results
- Check 1 (Module exists): **PASS**
- Check 2 (Not MARKET_CLOSED): **PASS** — returns OVERNIGHT
- Check 3 (5-min uses classifier): **PASS** — 5 references
- Check 4 (Status session field): **PASS** — session=OVERNIGHT
- Check 5 (Session-aware mode): **PASS** — mode=OVERNIGHT_MODE
- Check 6 (Tests): **PASS** — 22 session classifier tests
- Check 7 (Layer0Strip session): **PASS** — 3 session mode refs
- Check 8 (Regression): **PASS** — 75 tests pass

GAP-014 closed: Session classifier added.
D-083 locked: SessionClassifier is single source of truth for trading sessions.
Principle 8 NEW: SESSION-AWARE-NOT-TIME-AWARE.
