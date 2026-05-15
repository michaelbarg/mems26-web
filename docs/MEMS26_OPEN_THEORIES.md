# MEMS26 Open Theories

Unresolved spec questions awaiting user decision. Each entry has a
skipped test guarding it.

## 1. NONTREND Playbook Sizing

- **Date:** 2026-05-15
- **Code:** `PLAYBOOK_TEMPLATES[DayType.Nontrend]["sizing"] = "MIN"`
- **Test:** `tests/v9/systems/test_day_type/test_day_type.py::TestPlaybookTemplates::test_nontrend_playbook` expects `"SMALL"`
- **Spec:** No authoritative source found for Nontrend sizing value
- **Status:** Test skipped pending decision
- **Options:** (a) trust code "MIN", (b) trust test "SMALL", (c) check Zohar/Mind Over Markets
