# HOTFIX V9.0.4.5 — Bar Ingestion Service Startup Wiring

**Date:** 2026-05-12
**Branch:** feature/v9_architecture_rebuild
**Trigger:** bar_ingestion.running=false after restart (GAP-010)

## Root Cause
`BarIngestionService` class existed (HOTFIX 4.4) but was never called
`.start()` in backend startup hooks. Neither `backend/v9/app.py` nor
`backend/main.py` referenced it.

## Fix
Added `bar_ingestion_service.start()` to startup hooks in:
- `backend/v9/app.py` (standalone mode)
- `backend/main.py` (unified/Render mode)

Both log the startup explicitly (no silent failure per AP-MC02).

## Self-QA Results (explicit checks)

- Check 1 (Code change exists): **PASS** — start() call in both app.py and main.py
- Check 2 (Bar Ingestion running after restart): **PASS** — running=true
- Check 3 (Day Type hydrates): **PASS** — hydrated=true, reached_state=A1
- Check 4 (No silent failure): **PASS** — explicit logger.info present
- Check 5 (Regression): **PASS** — uat_prompt_4.sh 13/13
- Check 6 (Hotfix UAT): **PASS** — uat_hotfix_4_5.sh exits 0
- Check 7 (Explicit service status): **PASS** — bar_ingestion, event_bus, day_type all verified
- Check 8 (Idempotent): **PASS** — double hydration returns true both times

GAP-010 (startup hook missing) — **FIXED**
GAP-011 (vague Self-QA) — **FIXED** via Check 7 tightening

Done declared. Manual verification:
`curl http://localhost:8000/api/v9/status | jq '.hydration.bar_ingestion'`
should show `running: true` (after backend restart).
