# Retro — Prompt 1: Foundation Layer (Event Bus + Schema + live_price)

**Date:** 2026-05-11
**Duration:** ~14h (planned: 6-8h)
**Planned vs Actual:** 2x over estimate

## 1. What went well?

- Event Bus library built cleanly — 20 tests passing on first commit
- DLL already had live_price export — no C++ modification needed (saved hours)
- Existing bridge architecture (BaseV9Stream, watchdog) was solid foundation
- Frontend build (Next.js 16 + React 19) passed first try after one useRef fix
- Redis Streams via Upstash REST works well, consistent with existing bridge pattern
- WS endpoint registered and received live data on first connection test

## 2. What broke or took too long?

- **DLL Windows paths (AP-T03):** Defaults were C:\ paths — Michael had to manually fix 4 Study Inputs before automation caught it. 3 hotfix rounds.
- **Tick dedup bug:** DLL `ts` is seconds resolution, dedup filtered 4/5 ticks per second. Took a full UAT cycle to discover.
- **WS route "missing":** OpenAPI doesn't show WebSocket routes — false alarm but burned investigation time. Added `/api/v9/ws/status` diagnostic.
- **LeftTabs crash:** Zustand persist with stale localStorage caused undefined component. Defensive guard added.
- **Manual UAT:** 3+ hours manually verifying what should be 30 seconds automated.
- **.env not loaded in tests:** conftest.py needed explicit dotenv.load_dotenv. Wasted a test iteration.

## 3. What did we learn about the codebase?

- Sierra Chart `time(nullptr)` is seconds resolution — not suitable for sub-second dedup
- Upstash REST API doesn't support `(` exclusive XRANGE syntax — use sequence increment
- React 19 requires explicit initial values for `useRef()`
- `backend/main.py` (unified) has `/health`, `backend/v9/app.py` (standalone) only has `/api/v9/health`
- WebSocket routes never appear in `/openapi.json` — OpenAPI spec limitation

## 4. What anti-patterns did we hit (or almost hit)?

- **AP-T03 (Windows paths):** Hit directly. Fixed in hotfix.
- **AP-M04 (manual UAT):** Hit directly. Building UAT automation as Prompt 1.5 to prevent recurrence.
- **AP-C01 (asking Michael technical decisions):** Avoided — made all technical calls autonomously.
- **AP-C03 (asking obvious follow-ups):** Avoided — executed on approval.

## 5. What should change for next prompt?

- UAT automation MUST run before any commit is considered done
- Status endpoint (`/api/v9/status`) should be checked first in every prompt
- DLL changes need immediate Sierra rebuild + re-add Study (add to MANUAL_STEPS_QUEUE.md)
- Every test file needs conftest.py that loads .env
- Stream dedup should use sub-second timestamps or file mtime, never `time()`
