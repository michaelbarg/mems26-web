# MEGA PROMPT · Pipeline 2 (S4 Woodies) · P-W Decisions Intake

**Owner:** Cursor agent (Claude Desktop)
**Consumer:** Claude (Desktop / Code · whichever assistant Michael uses next)
**Reviewer:** Michael Barg
**Goal:** Lock 10 open Woodies questions (P-W1..P-W10) so Pipeline 2 can move from `⏳ pending` → `G0 spec`.

---

## ⚠️ Instructions for the assistant reading this

1. **Do NOT propose code.** This intake is doctrine-level. Code design starts after locks.
2. **Ask one question at a time.** Wait for Michael's answer before moving to the next.
3. **Echo back his choice in your words** before recording it — confirm understanding.
4. **Record every locked answer** verbatim in a new section `## Locked Decisions` at the bottom of this file (you append, you don't overwrite).
5. **If Michael picks "other / hybrid"**, ask for the exact rule he wants and write it as prose, not a multiple-choice letter.
6. **Use the trading examples below** — they're tied to MES 5-min CCI-14 reality. Don't invent fresh examples.
7. **When all 10 are locked,** generate a 1-page summary table and stop. Cursor will take it from there (audit + Pipeline 2 package list).

---

## Authority reference (verbatim, locked)

- `docs/decisions/D-092_S4_WOODIES_UPDATE.md` — D-092 LOCKED 2026-05-23
- `docs/spec_authority/S4_WOODIES_PATTERN_TABLES_V1.xlsx` — 9 patterns canonical
- `docs/spec_authority/S4_WOODIES_TABLE_C_Strategy_Caveats.csv` §6.7 — researcher's reads per P-W

**Domain context Michael already locked:**

- 9 patterns: ZLR · TLB · TT · GB100 (CONT) · VEGAS · GHOST · FAMIR · HTLB · HFE (REV)
- Stop = ATR-14 based · NOT today_typical (differs from S2)
- 4 trend states: BLUE / RED / YELLOW / GRAY
- Day-type matrix: 9 × 7 = 63 cells (xlsx Sheet B)
- 9 anti-patterns (AP1..AP9) — block fires
- Existing code: `backend/v9/systems/woodies/` (17 .py files · audit TBD)

---

# 10 שאלות — שאל את מיכאל בסדר הזה

---

## P-W1 · DTV1 verbatim paste · 📋 ADMIN

**השאלה:** היכן מקור ה-DTV1 (Woodies Decision Tree V1) המקורי?  
ה-Master Index מצביע על `docs/MEMS26_WOODIES_DECISION_TREE_V1.md` שאינו קיים בריפו · אני (Cursor) חיפשתי ולא מצאתי. צריך לדעת אם:

**אופציות:**

- **A · Canvas mirror:** ה-DTV1 חי ב-Cursor Canvas / ChatGPT Canvas · מיכאל ידביק verbatim עכשיו
- **B · External doc:** קובץ Drive / Notion / PDF — מיכאל ישלח path / URL
- **C · Memory only:** אין מקור כתוב · מיכאל יכתיב את 9 הענפים ל-Claude עכשיו (יקח ~20 דק')
- **D · Defer:** לדלג כרגע · להמשיך בלי DTV1 · ב-Stage 3 לעשות reconciliation

**משמעות אסטרטגית:**  
DTV1 הוא הקובץ שמגדיר את 9 ה-decision branches של dispatcher (איזה pattern fires במה ביום). בלעדיו אנחנו בונים את ה-dispatcher (`P-W6`) מתוך המלצת חוקר בלבד · בלי authority של מיכאל. סיכון: dispatcher יעשה החלטות שלא תואמות את הכוונה המקורית.

---

## P-W2 · HFE dual-path · 🔴 ARCHITECTURE

**השאלה:** HFE (Hook & Failure Extreme) — ה-pattern היחיד ללא Wood/Rensink doctrine. כיום קיימים 2 נתיבי זיהוי:

1. **DLL** — Sierra Chart C++ study מחשב `hfe_detected` ושולח דרך bridge
2. **Python** — `backend/v9/systems/woodies/patterns/hfe.py` (אם קיים) מחשב מקומית

**דוגמת trading:**  
> בר 14:32 · MES @ 5825.50 · BLUE trend · 7 ברים מעל ZL  
> **DLL exports:** `hfe_detected=true` · `bars_since_extreme=4`  
> **Python computes:** `hfe_detected=false` · `bars_since_extreme=6`  
> מה לעשות?

**אופציות:**

- **A · DLL only · Python מבוטל:** סומכים על Sierra · Python disabled. סיכון: אם DLL crashes / רב-שני chart isn't loaded → אין HFE כלל
- **B · DLL primary · Python audit-only** (המלצת חוקר): מבצעים trade לפי DLL. Python רץ במקביל ומלוגג divergences ב-SHADOW. אם DLL down → no trade
- **C · DLL primary · Python fallback:** DLL down → Python מחליף · trade ממשיך (סיכון: שני implementations יכולים להיות שונים בקצוות)
- **D · Python canonical · DLL diagnostic:** ההפך — Python היחיד · DLL רק כ-cross-check לוג

**משמעות אסטרטגית:**  
HFE הוא ה-pattern עם הכי פחות doctrine backing. בחירת A/B דורשת אמון ב-DLL · בחירת C/D מחייבת לתחזק 2 implementations. B = רוב הזמן trader-safe וגם data-collecting ל-SHADOW.

---

## P-W3 · 39 ZLR test failures · 🔴 DIAGNOSTIC

**השאלה:** ב-Master Index 16/5 דווחו **39 כשלי tests של ZLR**. שורש הבעיה לא ידוע.  
המלצת חוקר: רוב הסיכויים זה fixtures לא שלמות — declared BLUE state אבל אין בר עם CCI >+200 (דרישת Liran Stage-1).

**דוגמה:**  
> Fixture: 8 ברים · CCI = [55, 60, 75, 110, 90, 70, 65, **trigger**]  
> Declared trend = BLUE  
> ❌ Stage-1 דורש ≥1 בר עם CCI >+200 — אין כזה! → detector דוחה → fixture חושב שיש fire → test fails

**אופציות:**

- **A · Audit-first:** Claude Code ירוץ על 39 ה-fixtures · ידווח per fixture: האם יש בר >+200? · אז מחליטים אם זה fixture bug או detector bug. **אין שינוי קוד עד שיש diagnostic.**
- **B · Mass-fix fixtures:** מניחים שזה fixture bug · CC יוסיף בר >+200 לכל 39 ה-fixtures. סיכון: יכסה bug אמיתי ב-detector
- **C · Detector fix:** מניחים שזה detector bug · CC ירכך את דרישת Stage-1. סיכון: יחליש את ZLR מול ה-doctrine
- **D · Disable temporarily:** מסמנים 39 tests כ-`@pytest.mark.skip` · ZLR ללא test coverage עד SHADOW. **לא מומלץ pre-LIVE.**

**משמעות אסטרטגית:**  
ZLR הוא ה-pattern הכי חשוב לפי Wood ("could be the only Woodies trade for your career"). אם הוא שבור — pipeline 2 כולו מסתכן. A הוא היחיד שמתאים ל-mems26-pre-live-protocol ("Diagnose first, fix second").

---

## P-W4 · JSON 18s bug · 📋 INTERNAL

**השאלה:** דווח באירוע ש-`gateway._persist_trade` נחסם 18 שניות עקב datetime serialization issue. **האם זה תוקן בפרודקשן?**

**דוגמה:**  
> trade fires at `14:32:01.045` · _persist_trade blocks 18s → trade row visible at `14:32:19.103` · UI shows trade באיחור · alert sounds מאוחרים

**אופציות:**

- **A · Verify-first:** CC יריץ probe חד-פעמי על gateway · ימדוד latency של `_persist_trade` ב-100 trades אחרונים. אם > 1s → bug · אם < 100ms → תוקן
- **B · Assume fixed:** מסמנים P-W4 = closed · No-action
- **C · Assume broken:** CC ייכנס לתוך gateway ויתקן datetime serialization (`isoformat()` במקום default JSON)

**משמעות אסטרטגית:**  
זה bug של latency, לא של doctrine. אבל ב-LIVE 18s = entry שונה לגמרי (MES יכול לעוף 2-3 ticks). A הוא הבחירה הבטוחה לפי pre-LIVE protocol.

---

## P-W5 · YELLOW state · 🔴 GATING LOGIC

**השאלה:** מצב YELLOW = "5th opposite bar" — הbar החמישי בכיוון הפוך אחרי trend מבוסס. המלצת חוקר: **BLOCK ALL 9 PATTERNS**.

**דוגמה:**  
> BLUE trend מבוסס · CCI עלה 8 ברים: [120, 140, 165, 210, 180, 150, 130, 105]  
> בר 9: CCI = 60 (1st opposite)  
> בר 10: CCI = 30 (2nd opposite)  
> בר 11: CCI = 10 (3rd opposite)  
> בר 12: CCI = -5 (4th opposite)  
> **בר 13: CCI = -25 (5th opposite ← YELLOW)**  
> ZLR Long signal forms (CCI bounced from -25 back). **Fire או block?**

**אופציות:**

- **A · BLOCK ALL 9** (Wood "WSI" · Liran "next bar flip" · המלצת חוקר): גם CONT וגם REV נחסמים ב-YELLOW. A1 gate מורחב
- **B · Block CONT only:** REV (VEGAS/GHOST/FAMIR/HTLB/HFE) יכולים לירות — צופים reversal. סיכון: REV מוקדם מדי
- **C · Block REV only:** CONT (ZLR/TLB/TT/GB100) יכולים לירות — רוכבים על trend שגוסס. סיכון: late-trade
- **D · Pass-through · reduced confidence × 0.5:** הכל יכול לירות אבל confidence מצונח. dispatcher יבחר רק if confidence > threshold
- **E · No change:** YELLOW = treat as BLUE/RED. ההמלצה הקיימת בקוד הנוכחי (אם זו ההתנהגות הנוכחית)

**משמעות אסטרטגית:**  
זאת ההחלטה הכי גדולה ל-doctrine. A הכי שמרני ($$$ הכי בטוח · ❌ הכי הרבה skips). E הכי aggressive. D היחיד שמשאיר ל-data להחליט (SHADOW יראה אם YELLOW-fires נצברים שלילי).

---

## P-W6 · Priority Dispatcher · 🔴 ARCHITECTURE

**השאלה:** כש-**2+ patterns** יורים באותו bar — איזה מנצח?

**דוגמה 1 · same-direction:**  
> בר 14:32 · BLUE · ZLR Long fires (conf 0.85) + TLB Long fires (conf 0.70) · אותו כיוון, שניהם CONT

**דוגמה 2 · opposite-direction:**  
> בר 14:32 · BLUE · ZLR Long fires (conf 0.80) + GHOST Short fires (conf 0.75) · כיוונים מנוגדים

**אופציות:**

- **A · max(confidence) plain:** הגבוה ביותר תמיד מנצח. דוגמה 1 → ZLR · דוגמה 2 → ZLR. **פשוט אבל יוצר bias** (P-W8)
- **B · DTV1 hierarchical** (המלצת חוקר):
  - **same-direction** → max(confidence) · ZLR בדוגמה 1
  - **opposite-direction** → Stage-1 trend gate breaks tie · BLUE → CONT wins · ZLR בדוגמה 2 (כי הכיוון תואם BLUE)
- **C · Parallel trades:** 2 firings → 2 separate trades · risk doubles
- **D · Cancel both:** קונפליקט = no trade. שמרני אבל מבטל הזדמנויות
- **E · Pattern priority list:** static order — ZLR > GHOST > VEGAS > TLB > TT > FAMIR > GB100 > HTLB > HFE (לא תלוי confidence)

**משמעות אסטרטגית:**  
B הוא היחיד שמשתמש ב-trend gate כ-tiebreaker (תואם Wood doctrine). A פשוט אבל יכול לבחור REV ב-BLUE strong = lose. C מסוכן לסיכון. D מבטל value.

---

## P-W7 · 6th touch-point · 📋 DOC RECONCILIATION

**השאלה:** Master Index אומר 6 touch-points · Canvas A4 מראה 5: `day_type` · `tpo` · `veto` · `killzone` · `layer0`. **מה ה-6th?**

**אופציות:**

- **A · CCI state** הוא ה-6th (BLUE/RED/YELLOW/GRAY → gate נפרד)
- **B · SWI** (sidewinder) — gate נפרד מ-trend state
- **C · Canvas correct · Master Index שגוי:** הם 5 בלבד
- **D · בדוק git log:** אולי היה 6th היסטורית שהוסר — CC יחפש ב-history

**משמעות אסטרטגית:**  
Doc reconciliation. אם A → צריך לוודא ש-CCI state gate ממומש בקוד. אם C → לעדכן Master Index. **לא חוסם build אבל חוסם compliance manifest.**

---

## P-W8 · Confidence normalization · 🔴 DISPATCHER FAIRNESS

**השאלה:** 9 ה-patterns מחזירים confidence ב-**יחידות שונות**:

- **5 dynamic** (ZLR/TLB/TT/GB100/HFE): normalized [0, 1] floats
- **4 fixed** (VEGAS/GHOST/FAMIR/HTLB): raw point values (e.g., CCI depth)

**דוגמה:**  
> בר 14:32 · ZLR confidence = `0.85` · GHOST confidence = `175` (CCI cup depth)  
> `max(0.85, 175)` → GHOST תמיד מנצח. **dispatcher bias עיוור.**

**אופציות:**

- **A · Normalize all to [0,1] · min-max per pattern** (המלצת חוקר): כל pattern מתחזק טווח היסטורי (min, max) · `normalized = (raw - min) / (max - min)`. דורש SHADOW data לכייל
- **B · Normalize all to [0,1] · z-score:** `normalized = (raw - μ) / σ` · משווה כמה הסיגנל "מיוחד" מול ה-mean
- **C · Don't normalize · explicit tiers:** REV outranks CONT (or vice versa) · max() רק בתוך tier
- **D · Relative ranks 1-9:** לכל pattern fire ניתן rank 1-9 לפי quality · dispatcher בוחר rank #1
- **E · Keep as-is:** מודעים ל-bias · מנצלים אותו (REV "natural priority")

**משמעות אסטרטגית:**  
A/B דורשים calibration data → לא ניתן ב-V1 build בלי SHADOW. C/D פתרונות סטטיים שעובדים מיידית. E מסוכן (dispatcher לא הוגן). **ייתכן צריך hybrid:** סטטי ב-V1 → A אחרי SHADOW.

---

## P-W9 · YAML config loader · 🔧 INFRA

**השאלה:** ערכי סף ספציפיים-לpattern (TT 3-9 bars · FAMIR ±50 zone · VEGAS ≥3 handle bars וכו') — איפה שומרים?

**אופציות:**

- **A · YAML-driven** (המלצת חוקר): `backend/v9/systems/woodies/config/thresholds.yaml` · loader ב-init · "Liran baseline" profile. שינוי = edit YAML + reload (אין deploy)
- **B · Python constants:** קבועים ב-`detector.py` · שינוי = code edit + deploy + test rerun
- **C · DB-stored:** טבלת `woodies_thresholds` · admin UI לעדכון runtime · most flexible but most risky pre-LIVE
- **D · Per-day-type YAML profiles:** `thresholds_tn.yaml` · `thresholds_nv.yaml` etc. — different baseline per day type
- **E · YAML override on top of Python defaults:** Python = ברירת מחדל · YAML = override יחיד-משימה (e.g., SHADOW experiments)

**משמעות אסטרטגית:**  
A הכי גמיש ובטוח (Git tracks YAML changes). C מוקדם מדי לפני LIVE. D מוסיף 7 קבצים — over-engineering ל-V1. E מצוין ל-SHADOW experimentation אבל מסבך init.

---

## P-W10 · All-9 keep policy · 📋 POLICY

**השאלה:** האם להשאיר את כל 9 ה-patterns דרך V1 SHADOW · או לאפשר drop מוקדם ל-pattern עם ביצועים גרועים?

**דוגמה:**  
> אחרי 200 SHADOW trades:  
> HFE: N=23 · E[R] = -0.45 · hit-rate T1 = 18%  
> VEGAS: N=31 · E[R] = +0.12 · hit-rate T1 = 38%  
> ZLR: N=87 · E[R] = +0.55 · hit-rate T1 = 52%  
> **שמור hfe או דרופ?**

**אופציות:**

- **A · Keep all-9 through V1 SHADOW** (המלצת חוקר): drop threshold = `N≥500 AND E[R]<0 AND hit-rate T1<35%` · promote 🔴→🟢 = `N≥500 AND E[R]>0 AND hit-rate T1>40%`
- **B · Early drop:** N≥100 (לא 500) · אם E[R]<-0.30 → mute pattern · faster pivots
- **C · Never drop:** 9 patterns canonical · Liran taxonomy יציבה · רק בעבר calibrate thresholds
- **D · Aggressive drop:** N≥50 · E[R]<0 → mute · over-fitting risk גבוה אבל מהיר

**משמעות אסטרטגית:**  
A הכי שמרני (500 trades = ~3-4 חודשי SHADOW במחיר 1-2 trades/day). B/D מאיצים learning loops אבל מסכנים over-fit ל-data מוגבל. **לא חוסם build · מחליטים אחרי P-S0 SHADOW gate.** ניתן לדחות עד אחרי SHADOW launch.

---

# Closing the intake

## ✅ When all 10 are locked, output the summary table

צור section בתחתית הקובץ הזה:

```markdown
## Locked Decisions · 2026-MM-DD

| P-W | Decision | Letter | Verbatim rule (if other/hybrid) |
|---|---|---|---|
| P-W1 | ... | A/B/C/D | ... |
| P-W2 | ... | ... | ... |
...
| P-W10 | ... | ... | ... |
```

ואז עצור. אל תיגע בקוד · אל תכתוב Pipeline 2 package list. Cursor יקבל את ה-locks ויקדם משם.

## 🛑 Stop signals — אל תמשיך אם:

- מיכאל אומר "לא יודע · תחזור אלי" לשאלה כלשהי → תשאיר אותה ב-`⏳ pending` ותעבור לבאה
- מיכאל מבקש "תן לי קוד דוגמה" → סרב · אמור "doctrine first · code later"
- מיכאל מבקש Pipeline 2 package list → סרב · אמור "P-W locks first"
- אתה לא בטוח על אופציה → אל תמציא · קרא מ-D-092 / Sheet C verbatim

---

## Authority & references

- **Spec authority:** `docs/decisions/D-092_S4_WOODIES_UPDATE.md`
- **Pattern tables:** `docs/spec_authority/S4_WOODIES_PATTERN_TABLES_V1.xlsx` (Sheet A · B · C)
- **Strategic caveats:** `docs/spec_authority/S4_WOODIES_TABLE_C_Strategy_Caveats.csv` §6.7
- **Status board:** `docs/plans/STATUS_BOARD.md` line 107 (P-W resolution blocks Pipeline 2 build queue)
- **Pre-LIVE protocol:** `.cursor/rules/mems26-pre-live-protocol.mdc`
- **Constitution V3:** §T2 Woodies behavior

---

**END OF MEGA PROMPT · Hand back to Cursor when all 10 are locked.**

---

# ✅ Locked Decisions · 2026-05-25 IL

**Intake run:** Claude Desktop · 2026-05-25
**Reviewer:** Michael Barg
**Status:** ✅ All 10 P-W locks closed · ready for Cursor audit + Pipeline 2 package list

| P-W | Decision | Letter | Verbatim rule (where hybrid / prose) |
|---|---|---|---|
| **P-W1** | DTV1 source · file uploaded as `MEMS26_WOODIES_DECISION_TREE_V1.md` (1085 LOC · v1.0 · 2026-05-09 · STANDALONE architecture · Entry A1-A7 + Active B1-B14) | **B** | External doc · uploaded 25/5 · Cursor commits to `docs/` and updates Master Index pointer |
| **P-W2** | HFE detection · DLL primary · Python audit-only · DLL down → no HFE (8 patterns continue) | **B** | DLL exports `hfe_detected` via bridge · Python `hfe.py` runs in parallel and logs divergences to SHADOW events · trade decisions consume DLL signal only |
| **P-W3** | 39 ZLR test failures · diagnose first · no code changes until per-fixture probe report | **A** | CC runs probe on all 39 fixtures · reports per fixture whether ≥1 bar has CCI >+200 (Liran Stage-1 requirement) · only then decide fixture-bug vs detector-bug |
| **P-W4** | `gateway._persist_trade` 18s latency · verify-first · measure before fix | **A** | CC runs one-shot probe over last 100 trades · measures p50/p95/max latency of `_persist_trade` · if max >1s → bug confirmed · if max <100ms → close P-W4 no-action |
| **P-W5** | YELLOW trend state (5th opposite bar) · BLOCK ALL 9 patterns · both CONT and REV | **A** | DTV1 Stage A1 (Strategic Gate) extended with `if trend_state == 'YELLOW': reject_all_patterns`. No pass-through · no reduced-confidence override. Wood "WSI" + Liran "next bar flip" doctrine. SHADOW frequency hit acceptable risk for V1; revisit in Phase B if too restrictive |
| **P-W6** | Priority dispatcher · DTV1 hierarchical · trend gate as universal cross-family tiebreaker | **B** (extended) | Two-tier dispatcher: **(1)** within same family (CONT vs CONT · REV vs REV) → `max(R_t1)` per P-W8 · **(2)** cross-family (CONT + REV) → Stage-1 trend gate breaks (BLUE → CONT wins · RED → REV wins · GRAY → `max(R_t1)` cross-family fallback). YELLOW already blocks all per P-W5 (not reached). Edge cases (GRAY cross-family, all-tied) documented in dispatcher spec doc (Cursor follow-up) |
| **P-W7** | 6 touch-points · DTV1 §3 verbatim · Canvas A4 mis-attributed | **other / doc-reconciliation** | The 6 are: **A2** (Day Type · Entry) · **A4** (POC + Suffering Side · Entry) · **A5** (OTF Clarity · Entry) · **B4** (POC migration · Active) · **B5** (OTF Clarity mid-trade · Active) · **B9** (Market State · Active). All ADVISORY · none blocks/exits. Canvas A4 list (`day_type / tpo / veto / killzone / layer0`) confused S2 vocab (`veto/killzone/layer0` are S2: `pre_fire_validator/first_hour_buffer/q0_dispatcher`). Master Index "6 total" is correct. **Cursor follow-ups (non-blocking):** (a) update or replace Canvas A4 with DTV1 §3 snapshot · (b) update S4 `compliance_manifest.yaml` to enumerate A2/A4/A5/B4/B5/B9 as canonical IDs |
| **P-W8** | Confidence normalization · V1 = R_t1 comparator · SHADOW logs full data for Phase B re-decision | **hybrid prose** | V1 dispatcher comparator = **R_t1 = (t1_price − entry) / (entry − stop)**. Within-family (CONT vs CONT · REV vs REV) → `max(R_t1)`. Cross-family → P-W6 trend gate breaks (BLUE → CONT · RED → REV · GRAY → `max(R_t1)` cross-family fallback). SHADOW logs `raw_confidence` + `realized_R per leg` (T1/T2/T3 hit/miss/stopped) for all 9 patterns to enable Phase B re-decision (W1→W3 weighted · or empirical E[R] with hit-rate · or rank-based · per data) |
| **P-W9** | Threshold config storage · Python defaults + optional YAML override | **E** | Python detector files (`patterns/*.py`) define `THRESHOLDS = {...}` as default constants. Optional `backend/v9/systems/woodies/config/thresholds.yaml` loaded at init · merged on top of Python defaults (YAML wins). If YAML missing/corrupt → fall back to Python defaults (no silent failure · no init crash · WARN log). SHADOW experiments can load alternate YAML via env var without touching baseline. All YAML diffs Git-tracked |
| **P-W10** | All-9 keep policy through V1 SHADOW · empirical thresholds for drop/promote | **A** | All 9 patterns active through V1 SHADOW. **Drop threshold:** `N≥500 AND E[R]<0 AND hit-rate T1<35%`. **Promote 🔴→🟢:** `N≥500 AND E[R]>0 AND hit-rate T1>40%`. ~3-4 months SHADOW at ~1-2 trades/day. Non-blocking for build · decision happens post-SHADOW launch |

## Cursor follow-ups (non-blocking on build)

1. **P-W1** · commit `MEMS26_WOODIES_DECISION_TREE_V1.md` to `docs/` · update Master Index pointer
2. **P-W7** · update Canvas A4 to mirror DTV1 §3 OR annotate Canvas A4 as deprecated/historical
3. **P-W7** · update `backend/v9/systems/woodies/compliance_manifest.yaml` to enumerate A2/A4/A5/B4/B5/B9 as canonical touch-point IDs
4. **P-W3** · audit-first probe (deferred to Pipeline 2 G0 spec)
5. **P-W4** · latency probe (deferred to Pipeline 2 G0 spec)

## Lock dependencies (for audit reference)

- **P-W5** (YELLOW block) — referenced by P-W6 (dispatcher path: YELLOW reached → no decision)
- **P-W6** (hierarchical dispatcher) — references P-W8 (`max(R_t1)` comparator within-family) · references P-W5 (YELLOW pre-filtered)
- **P-W7** (6 touch-points) — independent of doctrine locks · doc-reconciliation only
- **P-W8** (R_t1 comparator) — referenced by P-W6 (tier-1 within-family rule)
- **P-W9** (YAML override) — independent infra · enables SHADOW experimentation cited in P-W8 + P-W10
- **P-W10** (drop policy) — depends on SHADOW data per P-W8 logging contract

No circular dependencies. Build can proceed with P-W locks closed.

## Stop signals encountered during intake

None. All 10 questions answered cleanly. No "I don't know · come back later" deferrals. No code-proposal requests. No Pipeline 2 package list requests.

---

## Cursor audit · 2026-05-25 IL

**Verifier:** Cursor agent
**Method:** Read 10 locks · cross-check internal consistency · verify formulas direction-agnostic · spot-check follow-up file existence

| Check | Result |
|---|---|
| All 10 P-W locked (no `⏳ open` remaining) | ✅ |
| No circular dependencies in lock graph | ✅ |
| R_t1 formula direction-agnostic (Long + Short produce positive R) | ✅ verified — signs cancel in both numerator and denominator |
| P-W5 (YELLOW block) consistent with P-W6 (dispatcher never reaches YELLOW) | ✅ |
| P-W6 cross-family GRAY fallback specified (`max(R_t1)`) — no undefined edge | ✅ |
| P-W8 R_t1 comparator referenced by P-W6 within-family rule | ✅ |
| P-W2 (DLL down → no HFE) does NOT block other 8 patterns | ✅ |
| P-W9 YAML missing → Python defaults + WARN log (no silent failure per pre-LIVE protocol) | ✅ |
| P-W3 + P-W4 diagnose-first comply with mems26-pre-live-protocol | ✅ |
| `backend/v9/systems/woodies/compliance_manifest.yaml` exists | ✅ |
| `MEMS26_WOODIES_DECISION_TREE_V1.md` present in repo | ❌ NOT YET — Michael must hand off the file content (it lives in Claude Desktop intake session) |
| `docs/spec_authority/MEMS26_MASTER_INDEX_V2.markdown` exists (target for P-W1 pointer update) | ✅ |

**Audit verdict:** ✅ Lock set is internally consistent and ready to drive Pipeline 2 G0. **One blocker remains:** DTV1 file body not in repo. P-W1 metadata is locked but the canonical doctrine document (1085 LOC) needs to be pasted/uploaded before Cursor can commit it under `docs/MEMS26_WOODIES_DECISION_TREE_V1.md`.

---

*End of P-W Decisions Intake · 2026-05-25 IL · locks closed · audit passed · pending DTV1 file body before G0 audit kickoff*

---

# ✅ v2 FINAL · 2026-05-25 IL · DTV1 DELIVERED · ALL GAPS RESOLVED

**Supersedes:** v1 above (3 specific rows only — see "What changed from v1" table)
**Intake run:** Claude Desktop · v2 final
**Status:** ✅ All 10 P-W locks closed + 3 post-intake gap questions resolved · **G0 audit unblocked**

## What changed from v1 (focused diff · all other 8 P-W rows unchanged)

| Section | v1 → v2 change | Reason |
|---|---|---|
| **P-W6 row** | "RED → REV wins" → **"RED → CONT wins"** (with direction = CONT-SHORT) | Typo in v1. D-092 §Trend State + Gate A1 already block REV in RED · therefore "RED → REV wins" is unreachable. The doctrinally-correct mirror of "BLUE → CONT wins" is "RED → CONT wins" (CONT-SHORT, with-trend). Confirmed by Michael 25/5 |
| **P-W8 row** | Added clarification on 9 confidence formulas: code-as-truth · KEEP · do NOT participate in V1 dispatcher (V1 uses R_t1) | P-W8 already determined R_t1 is the V1 comparator. The 9 raw_confidence formulas in `patterns/*.py` are kept solely to feed `v9_trades.raw_confidence` for SHADOW · Phase B re-decision. Documentation mirror exists in Registry §5 (verified) |
| **Cursor follow-ups list** | Added item 6: Registry §5 row 9 (HFE) needs update — still said "decide DLL only or keep Python fallback" — P-W2 already closed (B · DLL primary · Python audit-only) | Discovered during gap-3 verification when reading Registry §5 |

## Locked Decisions · 2026-05-25 · v2 (corrected rows only · others unchanged from v1 above)

| P-W | Decision | Letter | Verbatim rule (v2) |
|---|---|---|---|
| **P-W6** | Priority dispatcher · DTV1 hierarchical · trend gate as universal cross-family tiebreaker | **B** (extended · v2 typo fix) | Two-tier dispatcher: **(1)** within same family (CONT vs CONT · REV vs REV) → `max(R_t1)` per P-W8 · **(2)** cross-family (CONT + REV) → Stage-1 trend gate breaks: **BLUE → CONT wins · RED → CONT wins · GRAY → `max(R_t1)` cross-family fallback**. YELLOW already blocks all per P-W5 (not reached). Direction follows trend (BLUE → CONT-LONG · RED → CONT-SHORT). **v2 NOTE:** v1 said "RED → REV wins" — that was a typo. D-092 §Trend State + Gate A1 already block REV in RED · therefore the rule is unreachable and the typo'd rule would never have fired wrong code; nevertheless the prose is corrected here for doctrinal consistency. D-092 unchanged · REV remains blocked in RED via Gate A1 |
| **P-W8** | Confidence normalization · V1 = R_t1 comparator · SHADOW logs full data for Phase B re-decision | **hybrid prose · v2 clarified** | V1 dispatcher comparator = **R_t1 = (t1_price − entry) / (entry − stop)**. Within-family (CONT vs CONT · REV vs REV) → `max(R_t1)`. Cross-family → P-W6 trend gate breaks. SHADOW logs `raw_confidence` + `realized_R per leg` (T1/T2/T3 hit/miss/stopped) for all 9 patterns to enable Phase B re-decision (W1→W3 weighted · or empirical E[R] with hit-rate · or rank-based · per data). **v2 NOTE:** the 9 `raw_confidence` formulas in `backend/v9/systems/woodies/patterns/*.py` are **code-as-truth** · classify **KEEP** in G0 audit · they feed `v9_trades.raw_confidence` for SHADOW analysis · they do **NOT** participate in V1 dispatcher decisions. Documentation mirror in `MEMS26_SYSTEMS_DECISIONS_REGISTRY_2026-05-23.md` §5 (table of 9 patterns · column "confidence formula" · all verified "כולם מאומתים בקוד" per row 108). No separate spec doc required |

## Post-intake gap questions (Cursor 25/5 · resolved)

### Gap 1 · DTV1 body — ✅ RESOLVED · file saved

`MEMS26_WOODIES_DECISION_TREE_V1.md` committed to `docs/MEMS26_WOODIES_DECISION_TREE_V1.md` (1085 LOC · MD5 verified byte-identical to Michael's 25/5 upload).

**What DTV1 contains:** §1 Core Principles · §2 Configuration Block · §3 Six Touch-Points Reference · §4 Entry Phase (Stages A1–A7) · §5 Active Phase (Stages B1–B14) · §6 Terminal States Catalog · §7 Editing Guide.

**What DTV1 does NOT contain:** Liran-specific Stage-1 / Stage-2 / Stage-3 bar-by-bar detection criteria for ZLR. §A3 (Pattern Detection) only describes each of the 9 patterns in one line each. Bar-by-bar criteria live in:
- (a) `S4_WOODIES_PATTERN_TABLES_V1.xlsx` Sheet A (entry recipes per pattern)
- (b) The existing detector code `backend/v9/systems/woodies/patterns/zlr.py` (code-as-truth per Gap 3)
- (c) Registry §5 table (documentation mirror)

### Gap 2 · P-W6 RED — ✅ RESOLVED · α (typo) · LOCKS row P-W6 corrected above

**Decision:** α (typo · meant CONT).

Verbatim fix applied in P-W6 v2 row above:
- **v1:** `"BLUE → CONT wins · RED → REV wins · GRAY → max(R_t1) cross-family fallback"`
- **v2:** `"BLUE → CONT wins · RED → CONT wins · GRAY → max(R_t1) cross-family fallback"`

D-092 §Trend State stays as-is (REV remains blocked in RED via Gate A1). No code impact (the unreachable branch never fired).

### Gap 3 · Confidence formulas — ✅ RESOLVED · code-as-truth · KEEP · documented in Registry §5

**Decision:** classify `backend/v9/systems/woodies/patterns/*.py` confidence formulas as **KEEP** in G0 audit. They are code-as-truth · feed `v9_trades.raw_confidence` for SHADOW analysis · they do **NOT** participate in V1 dispatcher (V1 uses R_t1 per P-W8).

Registry §5 table (rows 112-122) · Cursor-verified content:

| Pattern | Formula | Type |
|---|---|---|
| ZLR | `min(0.9, 0.5 + cci/400)` | dynamic |
| TLB | `min(0.85, 0.4 + abs(curr-pred)/200)` | dynamic |
| TT | `0.7` | fixed |
| GB100 | `min(0.85, 0.5 + (curr-100)/200)` | dynamic |
| VEGAS | `0.75` | fixed |
| GHOST | `0.7` | fixed |
| FAMIR | `min(0.8, 0.5 + (200-max)/100)` | dynamic |
| HTLB | `0.65` | fixed |
| HFE | `min(0.8, 0.5 + hook/400)` | dynamic |

The mixed-units bias that P-W8 originally worried about (5 dynamic [0,1] vs 4 fixed point values) is **solved by P-W8's R_t1 comparator decision**, not by normalizing `raw_confidence`. SHADOW will collect raw_confidence + realized_R per leg for all 9 to enable Phase B re-decision.

## Cursor follow-ups v2 (non-blocking on G0 audit)

1. **P-W1** · ✅ DONE 25/5 16:50 — committed `MEMS26_WOODIES_DECISION_TREE_V1.md` to `docs/` · Master Index pointer was forward-declared at line 89 (`repo: docs/MEMS26_WOODIES_DECISION_TREE_V1.md`) and now actualized
2. **P-W7** · update Canvas A4 to mirror DTV1 §3 OR annotate Canvas A4 as deprecated/historical (deferred to Pipeline 2 G0 spec)
3. **P-W7** · update `backend/v9/systems/woodies/compliance_manifest.yaml` to enumerate **A2/A4/A5/B4/B5/B9** as canonical touch-point IDs (deferred to G0)
4. **P-W3** · audit-first probe on 39 ZLR fixtures (deferred to Pipeline 2 G0 spec)
5. **P-W4** · `_persist_trade` latency probe (deferred to Pipeline 2 G0 spec)
6. **P-W2 / Registry §5** · ✅ DONE 25/5 16:50 — Registry §5 row 9 (HFE) updated · "להחליט: DLL only או keep Python fallback" replaced with "🔒 **P-W2 lock 25/5 · B** · DLL primary · Python runs audit-only · logs divergences to SHADOW · DLL down → no HFE"

## Audit verdict · v2

✅ **All blockers cleared. G0 audit can proceed immediately.**

| Check | v1 (16:30) | v2 (16:50) |
|---|---|---|
| All 10 P-W locked (no `⏳ open` remaining) | ✅ | ✅ |
| No circular dependencies in lock graph | ✅ | ✅ |
| R_t1 formula direction-agnostic | ✅ | ✅ |
| P-W5 ↔ P-W6 consistency | ✅ | ✅ |
| P-W6 cross-family GRAY fallback specified | ✅ | ✅ |
| P-W6 RED branch doctrinally consistent | ❌ (typo) | ✅ (corrected to "RED → CONT wins") |
| P-W2 (DLL down → no HFE) doesn't block other 8 | ✅ | ✅ |
| P-W9 YAML missing → Python defaults + WARN | ✅ | ✅ |
| P-W3 + P-W4 diagnose-first | ✅ | ✅ |
| `compliance_manifest.yaml` exists | ✅ | ✅ |
| **DTV1 file body present in repo** | ❌ | ✅ (1085 LOC saved) |
| Master Index pointer to DTV1 valid | ✅ (forward) | ✅ (actualized) |
| Registry §5 row 9 (HFE) reflects P-W2 lock | ❌ | ✅ (updated) |

*v2 final · 2026-05-25 16:50 IL · all blockers cleared · G0 audit can proceed*
