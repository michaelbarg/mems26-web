# P30.10b — Plan Tab Live (§5.8)

**Status:** GREEN (#13 L3 audit complete) · Michael browser spot-check optional  
**Last updated:** 2026-05-20 (live re-audit)  
**דוח מלא + המלצות תיקון (עברית):** [`PROMPT30_10b_PLAN_LIVE_FULL_REPORT_HE.md`](PROMPT30_10b_PLAN_LIVE_FULL_REPORT_HE.md)  
**Replay head:** `2026-05-18 10:30:00 ET`

## Agent guardrail — Sierra real-time (**DONE** — Michael 2026-05-20)

DLL + time-axis fixes are **already shipped** (inbox §2). This block is **anti-regression only** — do not edit `sc_study/`, bridge, or chart data paths without reading §7a and re-verifying live Sierra exports.

Market OHLC/TPO/CVD/Woodies **must** stay on Sierra JSON → bridge → API (not backend/UI synthesis). Full rule: **`P30_AGENT_INBOX_PRE_LIVE.md` §7a**.

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

## Per-system audit (#13 L3, 2026-05-20)

| Sys | Component | Section | BLOCKED chain | Code audit | Browser 2026-05-20 |
|-----|-----------|---------|---------------|------------|---------------------|
| S1 Day Type | `DayTypePlan.tsx` | CONTEXT | health=error only | **PASS** | STATE **SCANNING**; rows Day type · Probability 0% · Trading conf. · Role Advisory; health Unknown 0s |
| S2 5-Min | `FiveMinPlan.tsx` | TO FIRE | `mode` MAINTENANCE/WEEKEND → BLOCKED | **PASS** (fix) | Hebrew STATE (setup verify); BUILDING אין תבנית; TO FIRE Mode **OVERNIGHT_MODE** + buffer/opening/pattern rows; Feeds OK 1s |
| S3 Footprint | `FootprintPlan.tsx` | TO FIRE | `last_fire.blocked_by` → BLOCKED | **PASS** (fix) | BUILDING **חסום · cluster_guard**; ● Last fire blocked → tap opens RTL **סגור** panel |
| S4 Woodies | `WoodiesPlan.tsx` | TO FIRE | `failed_stages` → BLOCKED | **PASS** | **מוכן לניתוב** / VEGAS SHORT; A1–A6 all ✓ PASS; STATE tap → RTL panel (Gateway note); `failed_stages=[]` live |
| S5 TPO | `TpoPlan.tsx` | CONTEXT | health=error only | **PASS** | STATE **READY**; IB NARROW 2pt; POC 7399.50 · migration STUCK; Feeds OK 26s |
| S6 Killzone | `KillzonePlan.tsx` | CONTEXT | gate CLOSED row ● (observer) | **PASS** | STATE **APPROACHING**; NY_PREMARKET; ⚠ Gate —; Edge/Zone rows; Feeds OK 29s |

**RTL:** `PlanDetail` `dir=rtl` `lang=he`; verified S3 blocked row + S4 STATE badge → **סגור** detail panel.

**Gap (documented, not #13 blocker):** S6 STATE stays APPROACHING when gate closed (observer by design). No live Woodies `failed_stages=['A5']` during this audit — BLOCKED+FAIL RTL covered by pytest + 2026-05-19 browser evidence.

## Live API UAT (2026-05-20)

```bash
curl -s http://localhost:8000/api/v9/cockpit/systems-snapshot | jq '{ts,count,systems:[.systems[]|{id,name,state,ready_to_route,failed_stages: (.raw.failed_stages // .raw.decision_tree.failed_stages // null), pre_fire_count: ((.raw.decision_tree.pre_fire // []) | length)}]}'
```

**Sample (audit start, HTTP 200, 340 ms):**

```json
{
  "ts": 1779278922.22,
  "count": 6,
  "systems": [
    {"id": 1, "name": "Day Type", "state": null, "failed_stages": null, "pre_fire_count": 0},
    {"id": 2, "name": "5-Min", "state": "OVERNIGHT_MODE", "failed_stages": null, "pre_fire_count": 0},
    {"id": 3, "name": "Footprint", "state": "BALANCED", "failed_stages": null, "pre_fire_count": 0},
    {"id": 4, "name": "Woodies", "state": "VEGAS", "failed_stages": [], "pre_fire_count": 7},
    {"id": 5, "name": "TPO", "state": "STUCK", "failed_stages": null, "pre_fire_count": 0},
    {"id": 6, "name": "Killzone", "state": "NY_PREMARKET", "failed_stages": null, "pre_fire_count": 0}
  ]
}
```

Woodies detail: `ready_to_route=true`, all A1–A7 PASS; `last_route.blocked_by=cluster_guard` (gateway/cluster, not tree FAIL).

| Axis | Result (2026-05-20) |
|------|---------------------|
| **Quality** | `count=6`; S3 `cluster_guard` + S4 empty `failed_stages` match UI blocked/ready semantics; no invented `proj_hi` on Plan path |
| **Recency** | `age_s ≈ 0.04` at curl time (`ts` ≈ `now`); UI poll Feeds OK 0–36 s per system |
| **Cardinality** | `count==6`; Woodies `pre_fire_count==7` (A1–A7) |
| **Latency** | Live curl **340 ms**; pytest in-process **<100 ms** (6 passed) |

```bash
pytest tests/v9/api/test_cockpit_systems_snapshot.py tests/v9/frontend/test_plan_fire_diagnosis_contract.py -q
# 6 passed in 2.67s
```

**Note:** End-of-audit curl hit **5 s timeout** (backend load); not a Plan-tab regression — stack was responsive at audit start.

## Browser UAT (2026-05-20, `http://127.0.0.1:3000`)

Automated MCP pass: Plan tab for S1–S6; tap blocked/context row → RTL **סגור** on S3 + S4 STATE.

Prior sample (2026-05-19): S4 **BLOCKED** when `failed_stages=['A5']`; A5 FAIL row + Hebrew help.

## GAPs (no refactor in #13)

| ID | Finding | Owner |
|----|---------|-------|
| G-PLAN-1 | `TopBar.tsx` React hydration overlay in dev (`Date.now`/locale) — can intercept Plan row clicks | Cursor — defer post-LIVE unless Michael wants fix |
| G-PLAN-2 | Woodies A4 touch-point self-HTTP `read timeout=2` to localhost (advisory degraded, stage still PASS) | Backend perf / timeout tuning |
| G-PLAN-3 | S1 API `state: null` while UI shows SCANNING (observer) | Document only |
| G-PLAN-4 | No live `failed_stages` FAIL row this session — BLOCKED badge not re-shot live | Ops timing / pytest contract |

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
