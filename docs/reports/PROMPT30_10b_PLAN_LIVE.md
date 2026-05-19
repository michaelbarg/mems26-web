# P30.10b — Plan Tab Live (§5.8)

**Status:** GREEN (API + UI code) · browser visual sign-off pending Michael  
**Last updated:** 2026-05-19  
**Replay head:** `2026-05-18 10:30:00 ET`

## Scope

Live Plan tab for all six systems (S1–S6) in the side Lens:

- **STATE** — lifecycle badge (SCANNING / APPROACHING / BLOCKED / READY)
- **BUILDING** — forming pattern/context + progress bar
- **TO FIRE** (FIRING) or **CONTEXT** (OBSERVER) — pre-fire rows from `systems-snapshot` raw
- **DATA HEALTH** — poll age + health dot
- Tap any section/row → Hebrew RTL detail panel (what it measures, not approve/disapprove)
- Static spec collapsed under `<details>Spec</details>`

## Files

| Area | Path |
|------|------|
| Live UI | `frontend/v9/src/v9/components/sidepanel/lens/plan/systemPlanLive.tsx` |
| Hebrew help | `frontend/v9/src/v9/components/sidepanel/lens/plan/planHelp.ts` |
| Per-system wrappers | `frontend/v9/src/v9/components/sidepanel/lens/plan/*Plan.tsx` |
| Lens wiring | `SidePanel.tsx` → `*LensContent.tsx` Plan tab |
| Woodies raw | `backend/v9/systems/woodies/woodies_system.py` — `failed_stages` / `pending_stages` on `current_state` |

## Live API UAT (2026-05-19)

```text
GET /api/v9/cockpit/systems-snapshot
  systems[4] Woodies: state=NEUTRAL, ready_to_route=false
  decision_tree.pre_fire: 7 rows (A1–A7)
  failed_stages: ['A5']  → Plan STATE=BLOCKED
```

| Axis | Result |
|------|--------|
| Quality | pre_fire rows present; failed stage surfaced |
| Recency | snapshot from in-process systems (not stale HTTP fan-out) |
| Cardinality | 7 pre_fire stages returned for Woodies |
| Latency | curl < 500ms local |

## Browser UAT (2026-05-19, local)

Automated snapshot on `http://127.0.0.1:3000` — S4 Plan tab:

- Lifecycle **BLOCKED** when `failed_stages=['A5']`; later poll **READY** + `VEGAS LONG` when tree passed
- TO FIRE rows: A1–A7 with PASS/FAIL/SKIP + message (e.g. `A5 calculate_size=reject FAIL`)
- DATA HEALTH: `Feeds OK` + poll age

## Browser checklist (Michael)

1. Side panel → S4 Woodies → **Plan**
2. Badge **BLOCKED** when `failed_stages` non-empty; tap badge → Hebrew RTL explanation
3. Tap **A5** row → auxiliary alignment help (RTL)
4. S2/S3 Plan shows mode/buffer/COT rows
5. S1/S5/S6 Plan shows CONTEXT rows (no fire wording)

## Deferred

- Full §5.3 Woodies designer 1:1 panel
- P30.11 full 12-stream bridge (Michael approval)
- LIVE trading

## Bridge / stack note

Plan reads `useSystemStateStore` ← `systems-snapshot`. Woodies **decision tree** updates when `woodies_system` processes bars (full bridge or `woodies_5min` stream). CCI chart panel still reads Sierra `woodies_5min.json` directly (P30.10).
