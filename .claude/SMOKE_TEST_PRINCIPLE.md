# MEMS26 — END-TO-END SMOKE TEST PRINCIPLE (LOCKED)

Version: 1.0 · 2026-05-10 · 🔒 LOCKED
Trigger: Phase 3 Workers reported DONE with 185 tests, browser showed 3 bugs.

## THE PRINCIPLE

No Worker may report DONE on user-facing functionality until an end-to-end
smoke test against the real running stack confirms the user can actually use
the feature.

Unit tests passing is necessary but NOT SUFFICIENT.
The DONE bar is: real browser/CLI/API call against real running services succeeds.

## WHEN IT APPLIES

Required when:
1. Frontend code changes — must load actual page
2. API endpoint changes — must call from outside test process
3. WebSocket changes — must establish actual WS connection
4. Database schema changes — must round-trip through API
5. Bridge/data pipeline changes — must trace real data source to display
6. Authentication changes — must complete real auth flow

NOT required for: pure backend logic, algorithm functions, internal utilities.

## STANDARD SMOKE TESTS

### Frontend Worker — DONE requires:
- Start dev server, wait for "ready"
- curl localhost:3000 returns HTML (no error overlay)
- Check dev log for compilation errors
- Test API call with same headers frontend sends

### Backend Worker — DONE requires:
- Start service, health check passes
- Each new route returns expected status with auth
- WebSocket connection if applicable
- OpenAPI introspection confirms routes registered

### Bridge/Pipeline Worker — DONE requires:
- Bridge process alive
- Sample data flows through full pipeline within 5s
- Backend reads the data
- Frontend receives via WS (if applicable)

## ANTI-PATTERN #22 — "Unit Tests = DONE"

❌ "All 185 unit tests pass. DONE."
   User opens browser → 401 + infinite render loop

✅ "All 185 unit tests pass. E2E smoke:
   - curl localhost:3000 returns HTML ✓
   - apiFetch from browser succeeds (no 401) ✓
   - dashboard renders without console errors ✓
   - DONE."

## ROOT CAUSE (2026-05-10 incident)

Bug 1: apiFetch had no Authorization header → 401
Bug 2: Zustand .filter() in selector → new array → infinite re-render
Bug 3: Same as #2 → SSR hydration mismatch

ALL three caught by 30-second browser smoke test.

🔒 LOCKED. Modifications require explicit user approval.
