# Claude Code Detailed Status Report Request — MEMS26 P30

**For:** Claude Code (CC)
**Source:** Michael's `~/Downloads/05_CC_DETAILED_REPORT_REQUEST.md`
(uploaded 2026-05-19) — request for a per-system status report (S1–S6) in
Hebrew, covering code paths, spec compliance, what changed from spec,
tests, blockers, and next steps.

**Deliverable:** **one** consolidated report at
`docs/reports/P30_CONSOLIDATED_STATUS.md`. Do **not** scatter six new
files; CC's reporting workflow per `CLAUDE.md` is to produce one
canonical report and link out to existing artefacts.

---

## Why this is CC's task, not Cursor's

`CLAUDE.md` reporting workflow:

> For every completed prompt, bug fix, UAT, or phase gate, ask Claude Code
> to prepare or update the relevant report before moving to the next task.
> Prefer Claude Code for structured reports because it is efficient at
> turning test output, diffs, and UAT evidence into concise handoff docs.

The Cursor agent is currently focused on code edits in
`backend/v9/api/v9/`, `frontend/v9/src/v9/components/chart/`, and the
inbox in `docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md`. Status reports are
CC's lane.

---

## Existing material to consolidate (do not rewrite, link or summarise)

CC should read these existing reports and produce **one** consolidated
view, not duplicate their content:

| System | Existing report(s) |
|--------|--------------------|
| All / index | `docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md` (current source of truth) |
| All / phase log | `docs/reports/PROMPT30_0_DESIGN_INGESTION.md` through `PROMPT30_10b_PLAN_LIVE.md` (21 PROMPT30_* reports) |
| S1 Day Type | `backend/v9/systems/day_type/` + `docs/handoff/INVESTIGATE_DAY_TYPE_NONTREND_2026-05-19.md` (pending investigation) |
| S2 5-min Patterns | `backend/v9/systems/five_min/` + `docs/reports/PROMPT30_9b_CVD_PANE.md`, `PROMPT30_9c_CHART_SIERRA_ALIGNMENT_CC.md` |
| S3 Footprint+VAP | `backend/v9/systems/chart_5min/` + `docs/runbooks/SIERRA_DLL_OPS.md` |
| S4 Woodies CCI | `docs/reports/PROMPT30_10_WOODIES_PANEL.md` + `docs/audits/WOODIES_V1_PRODUCTION_INVENTORY.md` + `docs/v9/woodies_audit.md` + `docs/handoff/P30_WOODIES_PANEL_AGENT_HANDOFF.md` + `docs/handoff/WOODY_CCI_PANEL_HANDOFF_DOCX.md` + `docs/architecture/Woody_CCI_System_Architecture.docx` |
| S5 TPO Charts | `docs/reports/PROMPT30_10b_TPO_LEVELS_FIX.md` + `backend/v9/systems/tpo/` |
| S6 Killzone | `backend/v9/systems/day_type/` (D-061 override) + `docs/audits/SPEC_COMPLIANCE_3_3.md` |
| Active gaps | `docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md` §3 (G1–G6) |
| Roadmap | `docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md` §6 (L0–L8) |
| Order of work | `docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md` §8 |
| Live status | `docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md` §9 |

---

## Required structure for `docs/reports/P30_CONSOLIDATED_STATUS.md`

Per Michael's template (Hebrew labels, English code paths):

```markdown
# P30 — דוח ביצוע מאוחד (P30 Consolidated Status Report)

תאריך: <YYYY-MM-DD HH:MM ET>
מקור אמת: docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md
מודל הדיווח: per Michael's 05_CC_DETAILED_REPORT_REQUEST.md template

## TL;DR (5 שורות)
- מה ירוק
- מה צהוב
- מה אדום
- מה הבא להיום
- מה הבא ל-LIVE

## S1: Day Type — סטטוס, קוד, ספק, טסטים, בלוקרים, next steps
## S2: 5-min Patterns — ...
## S3: Footprint + VAP — ...
## S4: Woodies CCI — (9-Study Architecture: S1/S6/S7/S9/S10/S11/S12/S13)
## S5: TPO Charts — ...
## S6: Killzone — ...

## Data Flow Diagram
(Sierra DLL → JSON → Backend → Cockpit, with current latencies)

## בסוף הדוח
1. מה עבד כמתוכנן?
2. מה לא עבד?
3. מה שונה מהspec?
4. מה הבלוקרים למצב הבא?
5. ETA לתיקון כל issue?
```

For each system follow Michael's per-system structure verbatim (code
file paths, lines of code count, functions list, how-it-works summary,
changes-from-spec, blockers, tests passing/failing, next steps).

---

## Acceptance criteria

1. `docs/reports/P30_CONSOLIDATED_STATUS.md` exists, ≤ 6 KB compressed
   (one screen full per system, not a wall of text).
2. Each of S1–S6 has an explicit status (✅ WORKING / ⚠ PARTIAL / ❌ BLOCKED)
   matching the `docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md` §3 truth.
3. Code paths cited are real (CC must `grep` to confirm) — no
   hallucinated module names.
4. "Changes from spec" section explicitly enumerates which spec field /
   behaviour was modified and why, with a link to the spec line in
   `docs/spec_authority/`.
5. Test totals match a real `pytest -q` run captured the same day.
6. The bottom "בסוף הדוח" section answers all five of Michael's questions
   in three sentences each.

---

## Guardrails (same as the rest of pre-LIVE)

- Do **not** edit `bridge/`, `sc_study/`, LaunchAgent, `.cursor/`.
- Do **not** restart services.
- Do **not** commit or push unless Michael says so.
- Do **not** invent test results — run them, capture, paste.
- If a system is in BLOCKED state, list the blocker by ID
  (G1/G2/G3/G4/G5/G6 from inbox §3) — do not paraphrase.

---

## How Cursor agent will consume this report

Once CC ships `P30_CONSOLIDATED_STATUS.md`:

1. Cursor agent reads it as the new ground truth for what's where.
2. Cursor agent updates inbox §1 row D8 status from "Handoff prepared"
   to "CC report shipped @ <date>".
3. Any new bugs surfaced by CC's audit become new G-IDs in inbox §3.
4. Any "next steps" CC proposes get added to inbox §8 order-of-work.

CC does not have to update the inbox itself — Cursor agent owns that
file.
