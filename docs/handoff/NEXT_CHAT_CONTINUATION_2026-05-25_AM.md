# NEXT CHAT CONTINUATION · 2026-05-25 AM

**Purpose:** continuation prompt for the next Cursor session. Read this first, then proceed.

**Previous session ended:** 24/5 22:00 IL · Phase A 11/15 packages done · 3b-3 + 3b-3.1 hotfix folded · Sierra research artifact attached.

**Previous transcript:** [3b-3 G3 + 3c contract split + Sierra research attach](e4169318-9990-42bb-96c6-4ad8066bdf0e)

---

## TL;DR · אתה ממשיך מאיפה שעצרנו

המערכת בדרך ל-LIVE futures trading של MES (CME). Phase A (Pre-SHADOW Build) כמעט סגור — 11/15 packages עברו G3. הצעד הבא תקוע על 3 החלטות אסטרטגיות שצריך לקבל לפני draft של handoff חדש.

**אל תתחיל draft של Pkg 4a לפני שמייקל יענה על שאלה 1 למטה.**

---

## 🔴 3 שאלות פתוחות למייקל (קריטי לפני קוד)

### 1️⃣ Pkg 4a scope · `risk_rules.py`

לפי `docs/plans/PRE_LIVE_PIPELINE_2026-05-23.md` line 102+191-192 · Pkg 4a בונה `backend/v9/services/risk_rules.py` עם 2 EXIT classes: `TCCIExitRule()` + `DirectionChangeRule()`.

**הבעיה:** אחרי 3b-3 ה-Layer 4 services כבר חיים ב-TrailEngine. `tcci_cross_exit.evaluate()` כבר רץ כ-#3 ב-`_apply_layer4` (line 608 of `backend/v9/services/trail_engine.py`) ו-EXIT short-circuits. `direction_change_event` כבר זורם מ-`WoodiesSystem.get_layer4_context()` ונצרך ע"י TCCI service.

**3 אופציות:**

- **(A) Wrapper architecture** · Pkg 4a בונה `RiskRule` base class + 2 concrete classes שעוטפות את Layer 4 services הקיימים. Classes יושבות עד Pkg 6 שיטעין אותן. **תפקיד:** preparation ל-Pkg 6 plugin system. **CC time:** ~30min · zero functional change.
- **(B) Reduce ל-DirectionChangeRule בלבד** · TCCI כבר חי. נשאר 1 service חדש שצורך `direction_change_event` ישירות (אם זה רעיון שונה מ-TCCI שכבר משתמש בו). **CC time:** ~20min · pending Michael clarification אם DirectionChange ≠ TCCI logic.
- **(C) Defer 4a ל-Pkg 6 (merge)** · 4a ריק מתוכן functional. **CC time:** 0 · משפיע על Pkg 6 scope.

**🎯 שאלה למייקל:**
> האם `DirectionChangeRule` הוא:
> (1) **identical** ל-TCCI service (שמטפל ב-direction_change_event פנימית) → אופציה C
> (2) **different** rule שעובד על S1 (DayType) direction changes (לא Woodies) → אופציה B
> (3) **wrapper architecture** שמכין ל-Pkg 6 plug-in system → אופציה A

---

### 2️⃣ D-093 re-locks (Sierra research artifact)

`docs/research/SIERRA_ORDER_ROUTING_RESEARCH_2026-05-24.md` (615 lines · נוסף 24/5 22:00) מציע **3 spec corrections** ל-D-093 locked items:

| Locked item נוכחי | Research תיקון | Severity |
|---|---|---|
| ACSIL bracket = `sc.SubmitOCOOrder()` | `sc.BuyEntry()`/`sc.SellEntry()` עם Attached Orders (`Target1Offset`/`Stop1Offset`) | **🔴 קריטי** · `sc.SubmitOCOOrder` שמור ל-3 native OCO parent types בלבד · השימוש המוצע יוצר wrong-API ב-P5-1 |
| Modify = `sc.CancelOrder() + new sc.SubmitOrder()` | `sc.ModifyOrder()` ישיר · `sc.SubmitOrder()` **לא קיים בכלל** ב-ACSIL | **🔴 קריטי** · ה-fix חוסך naked-position race + queue priority |
| Heartbeat 30s stale → alert | 5s emit · 30s WARN if flat / KILL if open · 120s critical | 🟡 enhancement |

D-093.Q1 (gateway canonical) · research recommends `backend/v9/services/trading_gateway/` (W11 TradeManager + W14 RiskValidator pre-integrated). **Pending Michael lock.**

**🎯 שאלה למייקל:**
> מאשר את 3 ה-re-locks ו-D-093.Q1? (אם כן · אפשר לפתוח Pkg 0 P5-0 ל-CC עם spec מתוקן)

---

### 3️⃣ P5-1..P5-8 alignment עם research §1-6 (optional)

ה-research מכיל gotchas checklist מפורט (§6) · 18 פריטים critical/important/operational. הכי קריטי:

- `sc.SendOrdersToTradeService` MUST match global `Trade Simulation Mode On` · mismatch = silent rejection
- `sc.AllowOnlyOneTradePerBar` default = 1 → second BuyEntry within a bar silently skipped · **חייב לאפס**
- `sc.SubmitOrder()` does NOT exist (חוזר על נקודה 2)
- 8-second position resync window (DRIFT_ALERT threshold ≥10s)
- 20-minute auto-clear of non-working orders → snapshot terminal state at status transition

**🎯 שאלה למייקל:**
> רוצה שנעדכן את ה-Pkg specs (P5-0..P5-8) ב-D-093 עם §6 checklist verbatim, או שזה ייכנס לתוך mega-prompts מאוחר יותר?

---

## 📊 State snapshot (24/5 22:00)

### Git
- Branch: `stabilize/mems26-local-truth-2026-05-16`
- HEAD: `1e01c4a feat(s2): Pkg 3b-3 · D-094 retrofit + Layer 4 wiring · TrailEngine v3`
- 17 commits ahead of origin · NOT pushed
- 3b-3 commit הוא `git commit --amend` של `6b2b7cc` (אותו parent `31e493e`) · scope expanded beyond reorder (legitimate per LOCK 5 part B)

### Phase A progress · 11/15 done

| Pkg | Status | Commit |
|---|---|---|
| 0 (Path B+X) | ✅ G3 PASS 23/5 18:47 | (no SHA shown) |
| 1 (Adaptive Stop) | ✅ G3 PASS 23/5 19:30 12/12 | `dd5e2f2` |
| 2a (OFA Entry) | ✅ G3 PASS 23/5 19:55 12/12 | `847bb40` |
| 2bc (OFA Config+Validators) | ✅ G3 PASS 23/5 20:50 10/10 | `dfdf91f` |
| 3a Stream 1 (EXIT_V6) | ✅ G3 PASS 23/5 21:00 14/14 | `dd9c34f`→`a58ee61`→`689ac41` |
| 3a Stream 1.5 (prev_day) | ✅ G3 PASS 23/5 21:18 10/10 | `548f1f6` |
| 3a Stream 2 (day-type targets) | ✅ G3 PASS 23/5 22:15 | `cf6383e` |
| 3b Stream 1 (trail infra) | ✅ G3 PASS 24/5 18:57 8/8 | `6dfce93` |
| 3b Stream 2 (TrailEngine v1) | 🔴 G3 STRATEGIC STOP 24/5 20:15 · superseded by 3b-3 | `23c8456` |
| 3b Stream 3 (D-094 retrofit + Layer 4) | ✅ G3 PASS 24/5 21:45 14/14 · 59 tests · 3b-3.1 folded via amend | `6b2b7cc`→`1e01c4a` |
| 3c (contract split) | ✅ G3 PASS 24/5 19:50 10/10 | `c917d42` |
| 5a (Inv H&S + H&S Top) | ✅ G3 PASS 24/5 17:45 10/10 · G4 scaffolding 21:00 | `7ffab50` |
| 5b (Double BT) | ✅ G3 PASS 24/5 18:50 10/10 · G4 scaffolding 21:00 | `2c001a2` |
| 5c (Flags · Q5 Path C) | ✅ G3 PASS 24/5 19:30 12/12 | `427d687` |
| **4a (Risk Rules · Critical)** | ⬜ **NEXT** · pending scope decision | — |
| **4b (Risk Rules · Tightening)** | ⬜ deps 4a | — |
| **8 (Quality V2)** | ⬜ | — |
| **6 (TradeManager extensible · LAST)** | ⬜ deps ALL | — |

### Test baseline (24/5 21:45)
- `tests/v9/services/test_trail_engine.py` · **59/59 PASS in 0.27s**
- Full suite (`backend/v9/systems/five_min/tests` + `tests/v9/services` + `tests/v9/systems`): **42 failed · 1114 passed · 1 skipped** in ~6s
- Pre-3b-3 baseline: 43 failed/1083 passed · 3b-3 הוסיף 31 passing + הפחית 1 failure · **zero new regressions**
- F4 failures pre-existing (test_five_min_day_type_wiring · test_woodies_dedup) · לא קשור לעבודה הנוכחית

### זמן · המסלול ל-LIVE
- Estimated CC time saved vs original plan: ~70-80h (87% under estimate)
- Per-Pkg CC turnaround average: **~25min** vs ~3h estimated
- Phase A wall-clock: 23/5 18:25 → 24/5 22:00 · ~28h elapsed (10-12h focused work · רוב הזמן Michael ישן)
- Projection to Phase A done: **+10-15h more** (4a/4b/8/6 + UAT)
- Projection to LIVE: **2-3 ימים נוספים** מהנקודה הזו (Phase B SHADOW soak + Phase C DEMO smoke + LIVE micro)

---

## 🚫 CRITICAL: pre-LIVE protocol rules (קרא לפני כל פעולה)

קובצי rules: `.cursor/rules/mems26-pre-live-protocol.mdc` + `.cursor/rules/mems26-stability.mdc` + `CLAUDE.md`

**הכי חשוב:**

1. **Diagnose first, fix second.** קודם DB query / log read / probe · אחר כך נוגעים בקוד.
2. **Read the current code** לפני כל הצעת שינוי. אסור edit מהזיכרון.
3. **Audit existing surfaces.** לפני יצירת component חדש · classify KEEP/ADAPT/REPLACE/DEFER (זה בדיוק מה שהתקיע אותנו על Pkg 4a — `tcci_cross_exit` כבר חי).
4. **One thread at a time.** סיים + report לפני פתיחת thread חדש.
5. **Smallest correct change.** No "while I'm here" refactors.
6. **Verify 4 UAT axes** (Quality · Recency · Cardinality · Latency).
7. **Strategic stop** ב-phase gates · ב-contradictions · לפני שינויי trading logic.
8. **Update reports immediately** כש-state משתנה. אל תתן ל-`docs/reports/PROMPT_*.md` להישאר stale.
9. **Bridge local-only** · `CLOUD_URL=http://localhost:8000` קבוע · לעולם לא לcloud/render.
10. **לא להריץ `npm run dev` או `scripts/start_all.sh`** ב-stability audits בלי לבדוק לכל הפחות `127.0.0.1:3000` ו-`127.0.0.1:8000`.

---

## 📂 Key files · know where to look

### Decisions
- `docs/decisions/D-090_PATH_A_CANONICAL.md` · Pkg 0 + Path A
- `docs/decisions/D-091_S2_LIVE_SCOPE.md` · S2 patterns scope (Q1/Q2/Q4/Q5)
- `docs/decisions/D-092_S4_WOODIES_UPDATE.md` · Woodies methodology
- `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md` · **רענן · 3 re-lock proposals 24/5 22:00**
- `docs/decisions/D-094_PKG3B_TRAIL_DECISIONS.md` · §3.A-D trail spec (3b-1/2/3 source of truth)

### Spec authority (locked)
- `docs/spec_authority/S2_EXIT_DEFINITION_V6.md`
- `docs/spec_authority/S4_WOODIES_PATTERN_TABLES_V1.xlsx`
- `docs/spec_authority/S4_WOODIES_TABLE_A_Pattern_Setup.csv`
- `docs/spec_authority/S4_WOODIES_TABLE_B_DayType_Matrix.csv`
- `docs/spec_authority/S4_WOODIES_TABLE_C_Strategy_Caveats.csv`

### Plans + status
- `docs/plans/PRE_LIVE_PIPELINE_2026-05-23.md` · V2 full plan (15 Phase A packages + Phase B-D)
- `docs/plans/STATUS_BOARD.md` · **חי · עדכן כל פעם ש-state משתנה**

### Research
- `docs/research/SIERRA_ORDER_ROUTING_RESEARCH_2026-05-24.md` · **חדש · 615 lines · ACSIL deep-dive + gotchas**

### Templates
- `docs/templates/MEGA_PROMPT_TEMPLATE.md`
- `docs/templates/SPEC_LOCK_TEMPLATE.md`

### Handoffs (recent)
- `docs/handoff/MEGA_PROMPT_PKG3B_STREAM3.md` · 3b-3 prompt (v3 · used)
- `docs/handoff/DESKTOP_PKG3C_CONTRACT_SPLIT_HANDOFF.md` · 3c (delivered)
- `docs/handoff/CC_PROMPT_PHASE_A_G3_REPORT.md`

### Source code · trail engine (3b-3 final state)
- `backend/v9/services/trail_engine.py` · TrailEngine v3 · 813 lines · LOCK 1-9 + v4 Patch A
- `backend/v9/systems/woodies/woodies_system.py:512` · `get_layer4_context()` provider
- `backend/v9/services/layer4/` · 5 services (tcci_cross_exit · mfe_peak_tighten · cci_flat_tighten · swi_tighten · day_type_targets_verify)
- `tests/v9/services/test_trail_engine.py` · 59 tests · 9 test classes

---

## 🛠️ Working pattern (פרוטוקול הסשן)

1. **קרא TODO** של הסשן הקודם (יש למעלה תחת "3 שאלות פתוחות").
2. **בדוק status** עם `git log --oneline -10` + `cat docs/plans/STATUS_BOARD.md`.
3. **המתן לתשובות מייקל** על 3 השאלות לפני draft של handoff חדש.
4. **כש-Michael עונה:** עדכן STATUS_BOARD · נסח handoff (אם נדרש) · שלח ל-CC.
5. **כש-CC מסיים:** `git log --oneline -3` → G3 review (4 axes + spec compliance) → STATUS_BOARD update.
6. **רעיון תשובה למייקל:** תמיד עם data (4-axes verification · regression baseline · tests count) · לא הצהרות.

### Cursor delegation policy
- **Cursor (אתה):** קוד reading + edits · strategic decisions + stop/go · G3 reviews + UAT analysis · handoff drafting.
- **Claude Code (CC):** service bring-up · kill -9 · screen sessions · launchctl · live measurement · soak runs · **report drafting** מ-test/UAT output.
- אם sandbox חוסם פעולה 2× (screen · pgrep · pkill · process spawn) → delegate to CC מיד.

---

## 🎯 צעד ראשון מומלץ בסשן

```text
שלום! המשך מה-handoff. ראיתי את 3 השאלות הפתוחות.
לפני שאני שואל אותך 3 שאלות לאיזה מסלול ללכת:
ראית את ה-Sierra research artifact ב-docs/research/?
האם אתה רוצה (a) לענות על 3 השאלות הפתוחות עכשיו ולהתקדם
או (b) לעבור על אחד הנושאים לעומק לפני שמחליטים?
```

---

**Last update:** 25/5 07:55 IL · drafted by Cursor at end of session 24/5 22:00.
**File:** `docs/handoff/NEXT_CHAT_CONTINUATION_2026-05-25_AM.md`
