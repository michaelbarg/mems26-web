# P30 — תזמור ביקורת ירי/חסימה (6 סוכנים + CC)

**תאריך:** 2026-05-20  
**מזמין:** Michael  
**מטרה:** 6 סוכנים (אחד לכל S1–S6) מאמתים מול **האפיון האסטרטגי** מה קובע **ירי** ומה קובע **חסימה** — גם תרחישי "אמור לירות" וגם "אמור לא לירות". תוצאות מסונכרנות עם דוח Claude Code.

---

## A. מה חוסם את המערכת **עכשיו** (הודעה ל-Claude Code)

העתק ל-CC לפני כל עבודה:

```text
MEMS26 — מצב חסימות מערכת (2026-05-20, Cursor)

1) ירי Woodies (S4) — העץ A1–A7 יכול להיות ready_to_route=true אבל TradingGateway מחזיר blocked_by לפני רישום SHADOW:
   - cluster_guard (D-037): 5+ route_setup attempts ב-60s → חסימה 5 דקות
   - cooldown (2 סטופים רצופים → 30 דק)
   - suffering_side_veto (SSV)
   - chop_searching (Layer 0 chop_score ≥ 75)
   קוד: backend/v9/gateway/trading_gateway.py (return לפני _execute_shadow)

2) שער תהליך Pre-LIVE: L4 risk audit (#14) לא בוצע → L5 paper WAIT. LIVE לא בתור.

3) DLL / Sierra (אל תפרוס בלי Michael): G1 proj_hi/lo, G2 previous_session — סטטוס לא מאומת live; G3/G4 — Michael אומר בוצע — CC רק VERIFY (ראה CC_STATUS_REQUEST).

4) תשתית: bridge 12/12 לא מאומת בסשן זה; Woodies A4 touch-point עומס אפשרי על snapshot.

5) שוק: OVERNIGHT_MODE / gate סגור — לא חלון ירי RTH (הגיוני, לא באג).

CC: מלא docs/handoff/CC_STATUS_REQUEST_2026-05-20.md §4 + אשר/הפרך סעיף 1–5 עם evidence.
```

---

## B. כללי מחייבים (כל הסוכנים + CC + Cursor)

| איסור | סיבה |
|--------|------|
| **שינוי עיצוב / UI / CSS / designer** | אין אישור Michael |
| **שינוי הגדרות נתונים Sierra / DLL / `sc_study/` / bridge** | Michael ביצע POC (כולל Woodies); נתוני זמן אמת מ-Sierra בלבד — §7a inbox |
| **Refactor, commit, push, launchctl, start_all** | ללא "go" מפורש |
| **סינתזת OHLC/TPO/CVD** ב-backend/frontend | אסור |

| מותר | |
|------|--|
| קריאת קוד, curl, jq, pytest, לוגים, דפדפן read-only | |
| דוח PASS/FAIL מול `compliance_manifest.yaml` + אפיון אסטרטגי | |
| השוואה ל-`CC_STATUS_REQUEST` §4 אחרי ש-CC מילא | |

---

## C. מפת 6 הסוכנים

| # | שם סוכן (פרויקט) | סוג | קובץ פרומפט | דוח יעד |
|---|------------------|-----|-------------|---------|
| S1 | **DayType-Observer-Spec-Agent** | OBSERVER — לא יורה | [`agents/AGENT_S1_DAYTYPE_OBSERVER_SPEC.md`](agents/AGENT_S1_DAYTYPE_OBSERVER_SPEC.md) | `docs/reports/AGENT_S1_DAYTYPE_FIRE_SPEC_AUDIT.md` |
| S2 | **FiveMin-T1-Fire-Spec-Agent** | FIRING T1 | [`agents/AGENT_S2_FIVEMIN_T1_FIRE_SPEC.md`](agents/AGENT_S2_FIVEMIN_T1_FIRE_SPEC.md) | `docs/reports/AGENT_S2_FIVEMIN_FIRE_SPEC_AUDIT.md` |
| S3 | **Footprint-T3-Fire-Spec-Agent** | FIRING T3 | [`agents/AGENT_S3_FOOTPRINT_T3_FIRE_SPEC.md`](agents/AGENT_S3_FOOTPRINT_T3_FIRE_SPEC.md) | `docs/reports/AGENT_S3_FOOTPRINT_FIRE_SPEC_AUDIT.md` |
| S4 | **Woodies-T2-Fire-Spec-Agent** | FIRING T2 (POC Michael) | [`agents/AGENT_S4_WOODIES_T2_FIRE_SPEC.md`](agents/AGENT_S4_WOODIES_T2_FIRE_SPEC.md) | `docs/reports/AGENT_S4_WOODIES_FIRE_SPEC_AUDIT.md` |
| S5 | **TPO-Observer-Spec-Agent** | OBSERVER — לא יורה | [`agents/AGENT_S5_TPO_OBSERVER_SPEC.md`](agents/AGENT_S5_TPO_OBSERVER_SPEC.md) | `docs/reports/AGENT_S5_TPO_FIRE_SPEC_AUDIT.md` |
| S6 | **Killzone-Gate-Observer-Spec-Agent** | OBSERVER — gate | [`agents/AGENT_S6_KILLZONE_OBSERVER_SPEC.md`](agents/AGENT_S6_KILLZONE_OBSERVER_SPEC.md) | `docs/reports/AGENT_S6_KILLZONE_FIRE_SPEC_AUDIT.md` |

**סדר הרצה מומלץ:** CC ממלא §4 → S4 Woodies + S3 Footprint (ירי) → S2 FiveMin → S1/S5/S6 (הקשר) → Michael מרכז.

---

## D. פרומפט מקיף — Claude Code (העתק מלא)

ראה [`CC_STATUS_REQUEST_2026-05-20.md`](CC_STATUS_REQUEST_2026-05-20.md) §5 + סעיף A למעלה.

**תוספת אחרי מילוי §4:**

```text
TASK-2: For each firing system S2/S3/S4, document whether live behavior matches:
  - compliance_manifest.yaml (FIRE_ROUTE, pre_fire, gateway)
  - Plan tab BLOCKED chain (PROMPT30_10b_PLAN_LIVE.md)
  - trading_gateway.py blockers (cluster_guard, cooldown, SSV, chop)

Deliverable addendum: docs/reports/P30_CC_FIRE_BLOCKERS_SUMMARY.md (1 page)
  - Table: System | Spec says fire when | Code path | Live blocked_by | GAP
Do NOT change DLL/UI. Michael approval required for any Sierra time-axis change.
```

---

## E. פרומפט מקיף — מנהל / Cursor (תזמור 6 סוכנים)

```text
ORCHESTRATOR: Launch 6 parallel read-only agents (one per S1–S6).

Read first:
  docs/handoff/P30_ORCHESTRATION_FIRE_AUDIT_2026-05-20.md (this file)
  docs/handoff/CC_STATUS_REQUEST_2026-05-20.md §4 (after CC fills)
  docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md §7a

For each agent N in 1..6:
  - Open docs/handoff/agents/AGENT_S{N}_*.md
  - Run that prompt only in that agent's scope
  - Collect report to docs/reports/AGENT_S{N}_*_AUDIT.md

Merge into: docs/reports/P30_SIX_SYSTEM_FIRE_SPEC_MATRIX.md
  - Rows: S1..S6
  - Cols: Spec fire rule | Spec block rule | Code implements? | Plan UI matches? | Live evidence | GAP | Owner

Stop conditions:
  - Any agent proposes DLL/UI change → mark DEFER, do not implement
  - Contradiction with CC §4 → strategic stop, ask Michael

Michael constraints:
  - No design changes
  - No Sierra data config changes (POC Woodies just done by Michael)
  - Firing rules must trace to strategic spec + compliance_manifest
```

---

## F. קישורים

| מסמך | תוכן |
|------|------|
| `docs/reports/P30_SIERRA_STUDY_PROTOCOL.md` | **חובה** — Sierra = מקור אמת; subgraph IDs; אישור Michael לכל שינוי |
| `docs/reports/P30_SYSTEM_GAP_AUDIT.md` | פערים per subsystem; **טבלת עדיפויות LIVE** — Michael ממלא |
| `CC_STATUS_REQUEST_2026-05-20.md` | מטריצת בוצע/לא + תבנית CC |
| `PROMPT30_10b_PLAN_LIVE.md` | Plan tab BLOCKED chain |
| `PROMPT30_10b_PLAN_LIVE_FULL_REPORT_HE.md` | GAPs + המלצות |
| `docs/architecture/for_designer/02_SYSTEMS_SPEC.md` | אפיון מוצר S1–S6 |
| `backend/v9/systems/*/compliance_manifest.yaml` | אפיון אסטרטגי per system |
| `backend/v9/gateway/trading_gateway.py` | שכבת חסימה משותפת ל-FIRING |

---

*Michael — העתק סעיף A ל-CC; הפעל 6 פרומפטים מ-`docs/handoff/agents/`.*
