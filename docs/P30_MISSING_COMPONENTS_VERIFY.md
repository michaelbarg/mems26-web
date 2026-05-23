# P30 — Missing Components Verification

**Date:** 2026-05-20
**Mode:** READ-ONLY grep

---

## 1. SHADOW Analyst Agent

**STATUS:** 🔴 NOT_FOUND (code) | 🟡 MENTIONED in spec

**Files matching:**
- `docs/spec_authority/MEMS26_FIRST.md`

**Implementation level:** C) MENTIONED in docs only

**Evidence:**
- `MEMS26_FIRST.md:57` — "PROMPT 5: SHADOW Analyst Agent + Stepped POC build (post-data analysis)"
- `MEMS26_FIRST.md:353` — "[ ] SHADOW Analyst Agent (backend/v9/agents/shadow_analyst.py)"
- `MEMS26_FIRST.md:358` — "[ ] SHADOW Analyst Panel UI"
- No file `backend/v9/agents/shadow_analyst.py` exists
- No "shadow_analyst" directory or module found anywhere in backend/

**Verdict:** 🔴 NEEDS BUILDING — scoped in spec as PROMPT 5, but no code exists. The actual PROMPT 5 UAT report covers S2 FiveMin, not SHADOW Analyst.

---

## 2. LIVE Pre-flight UI

**STATUS:** 🟡 PARTIAL (docs exist, no dedicated UI)

**Files matching (excluding node_modules/.next):**
- `docs/reports/handoff/CHECKLIST_TO_LIVE.md` — actionable checklist from current state to LIVE
- `docs/reports/handoff/GANTT_TO_LIVE.md` — timeline with gates
- `docs/reports/handoff/PROMPT_LIST_TO_LIVE.md` — full prompt bodies
- `docs/design/MEMS26_COCKPIT_V5_DESIGN_SPEC.md` — Cockpit V5 spec (includes pre-flight concepts)
- `docs/spec_authority/MEMS26_FIRST.md` — references Cockpit V5 pre-flight

**Implementation level:** C) MENTIONED in docs / B) PARTIAL (checklist docs exist, no frontend UI)

**Evidence:**
- `CHECKLIST_TO_LIVE.md:1-15` — living checklist document with checkboxes and gate criteria
- Contains `🛑 STOP — ASK MICHAEL` decision points
- References companion docs: PROMPT_LIST_TO_LIVE, GANTT_TO_LIVE
- No dedicated pre-flight UI component found in `frontend/v9/src/`
- No `/api/v9/preflight` or similar endpoint

**Verdict:** 🟡 EXISTS BUT INCOMPLETE — docs/checklists exist for planning. No frontend pre-flight UI or backend readiness endpoint built. The checklist is a document, not a runtime gate.

---

## 3. LIVE Activation

**STATUS:** 🟡 PARTIAL (executor stubs exist, not connected)

**Files matching:**
- `backend/v9/gateway/live_executor.py` — "Currently a stub — logs intent but does not connect to Sierra live account. Full implementation deferred to post-DEMO validation."
- `backend/v9/services/trading_gateway/executors/live.py` — "Routes to Sierra live account APEX-125218-13. Runs W14 RiskValidator.check_setup() BEFORE creating trade."
- `backend/v9/services/risk_validator/validator.py` — W14 risk validator
- `docs/v9/W14_RISK_VALIDATOR_DESIGN.md` — risk validator design doc

**Implementation level:** B) PARTIAL (skeleton/stub)

**Evidence:**
- `gateway/live_executor.py:3-5` — "LIVE mode: single slot, strict risk checks required. Currently a stub — logs intent but does not connect to Sierra live account."
- `services/trading_gateway/executors/live.py:1-4` — "Routes to Sierra live account APEX-125218-13. Runs W14 RiskValidator"
- Risk validator exists and has design doc
- Gateway currently runs in SHADOW mode only (all trades are paper)
- No `LIVE_MODE` env var or activation switch found

**Verdict:** 🟡 EXISTS BUT INCOMPLETE — live executor stubs exist in two locations. Risk validator designed. No runtime switch to activate LIVE mode. Needs: activation gate + risk validator integration test + Michael's go-live decision.

---

## Cross-Component Summary

| Component | Code | Docs | UI | Verdict |
|-----------|------|------|----|---------|
| SHADOW Analyst | 🔴 None | 🟡 Spec only | 🔴 None | 🔴 NEEDS BUILDING |
| LIVE Pre-flight | 🔴 None | 🟢 Checklists | 🔴 None | 🟡 EXTEND (add UI + endpoint) |
| LIVE Activation | 🟡 Stubs | 🟢 Design doc | 🔴 None | 🟡 EXTEND (connect + activate) |
