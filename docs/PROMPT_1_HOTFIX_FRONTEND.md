# HOTFIX — Frontend LeftTabs + API Unreachable

**Date:** 2026-05-11

## Bug 1: LeftTabs crash — "Element type is invalid: got undefined"

**Root cause:** `TAB_COMPONENTS[activeTab]` returned `undefined` when
`activeTab` was a stale value from localStorage (Zustand `persist`
middleware stores layout state under key `mems26-v9-layout`). If the
persisted `activeTab` didn't match any key in the map, `ActiveComponent`
was `undefined` and React crashed on `<ActiveComponent />`.

**Fix:** Added fallback guard in `LeftTabs.tsx` line 47:
```ts
// Before:
const ActiveComponent = TAB_COMPONENTS[activeTab];
// After:
const ActiveComponent = TAB_COMPONENTS[activeTab] ?? TAB_COMPONENTS.trader;
```
Plus a safety check in the JSX: `{ActiveComponent ? <ActiveComponent /> : null}`

**File:** `frontend/v9/src/v9/components/sidebar/LeftTabs.tsx`

## Bug 2: "API unreachable for /api/v9/bars/5min"

**Root cause:** Not a code bug. The backend (`uvicorn`) was not running
when the frontend loaded. The `catch` block in `api.ts:20` logs
"API unreachable" and returns `[]` as fallback — the dashboard renders
with empty data, which is correct behavior.

**No code change needed.** `.env.local` already has
`NEXT_PUBLIC_API_URL=http://localhost:8000`.

**To resolve:** Start the backend before/alongside the frontend:
```bash
cd /Users/michael/Downloads/mems26_web_git
source .env && python3 -m uvicorn backend.main:app --reload --port 8000
```

## Verification

- `npx next build` passes with zero errors
- Dashboard renders without crash even with stale localStorage
- PriceDebugConsole visible bottom-right
