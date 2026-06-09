# CC MEGA PROMPT — Build Status Observability Overhaul (Live Inputs → Interpretation → Per-Setup Explanation) · 2026-06-01

**תווית החלטה:** `D-OBS` (ראה `docs/plans/DECISION_LEDGER.md`)
**מאת:** Cowork agent → **אל:** Claude Code

> **משמעת Pre-LIVE:** read-current-code · audit-existing (KEEP/ADAPT) · **read-only observability — אפס שינוי לוגיקת-מסחר/ירי/סיכון** · **Rule 5 (command+raw output)** · No silent failures · תווית `# D-OBS` בכל קובץ שנוגעים.

## מטרה (Michael)

ש-Build Status יהפוך ל**מסך אחד נוח לעיון** שבו, לכל מערכת, רואים:
1. **כל הנתונים החיים שהמערכת מקבלת** — כל שדה, ערך חי, וטריות (fresh/stale).
2. **לצד זה — מה המערכת מבינה מהנתון** (interpretation: מה גזרה/החליטה).
3. **לכל setup/תבנית — הסבר משוכלל** למה היא ARMED / FIRED / BLOCKED (ולא רק סטטוס).
4. **שיקוף כל התיקונים/ההחלטות הנוכחיים** — וריאציות D-RVX (אור ירוק למי שירה), שרשרת D-S1DYN (shadow), וכו'.

## ⚠️ Audit קודם — אל תכפיל

קיים כבר, לקרוא ולסווג KEEP/ADAPT:
- `backend/v9/systems/build_status/{types,aggregator,s2_inspector,woodies_inspector,day_type_inspector,bridge_inspector,footprint_inspector,build_status_routes}.py` — כבר מחזיר per-pattern armed/blocked + block-reasons (מ-`FIX_WIRING_PATTERNS_ARM`, `RELATIVE_ALWAYS`).
- בקשה קודמת חופפת: `docs/handoff/CC_PROMPT_RELATIVE_IN_PATTERNS_BRIDGE_INVENTORY_2026-06-01.md` — "Bridge Data Inventory (כל שדה→ערך-חי→מערכת→תבנית)". **ה-D-OBS הזה הוא ה-superset שלו** — אם נבנה חלקית, ADAPT; אל תיצור מסך שני.
- רכיב ה-Build Status בפרונט (CC לאתר: `frontend/v9/src/v9/components/.../BuildStatus*`).

## מבנה מבוקש — כרטיס פר-מערכת

לכל מערכת (S1 day_type · S2 five_min · S3 footprint · S4 woodies · bridge · — ועם **שם וסוג המערכת בכותרת**):

### א. Live Inputs (טבלה)
כל שדה גולמי שהמערכת צורכת: `field · value · source(stream/chart) · age(sec) · fresh?`. דוגמאות: S4 → cci_14/tcci/swi/czi/lsma/ema34/trend_state/predictor + OHLCV; S2 → OHLCV/COT/AMT/POC/VAH/VAL/IB/CVD; S1 → opening_bars/IB/PD-context/CVD. סמן stale באדום.

### ב. Interpretation (מה המערכת מבינה)
לצד ה-inputs — ה-derived state: S1 → opening_type+conf, IB-width class, day_type vote+lock+stage (+ shadow chain D-S1DYN); S4 → trend color + פירוש (BLUE=המשך-עלייה), CCI zone; S2 → mode, day_type gate, location_vs_POC; S3 → belly/stacked imbalance. **כל interpretation מצמיד "מאיזה input היא נגזרה".**

### ג. Patterns / Setups — הסבר משוכלל
לכל תבנית: `status ∈ {ARMED, FIRED, BLOCKED}` + **reasoning משוכלל**:
- ARMED → אילו תנאים מתקיימים ומה חסר ל-fire.
- BLOCKED → **בדיוק איזה gate חסם** (P-W5 GRAY/YELLOW · Auth Table SKIP · day_type · סף לא עבר) + הערך שנכשל.
- FIRED → התנאים שהתקיימו + entry/stop/targets.
מבוסס על ה-block-reasons הקיימים, **מורחב** לכלול את הערך החי שגרם.

### ד. שיקוף התיקונים/ההחלטות (D-RVX / D-S1DYN)
- **S2 → בלוק "Reactive Variants" (D-RVX):** A/B/C עם **אור ירוק** למי ש-`fired_today`, צהוב=armed, אפור=לא. (מסונכרן עם מגה-פרומפט Reactive Phase 3.)
- **S1 → בלוק "Dynamic Day-Type (shadow)" (D-S1DYN):** day_type חי לצד ה-shadow chain (would-be Normal→NV→Trend + הטריגר). (מסונכרן עם מגה-פרומפט S1 Phase 2.)
- מנגנון: כל החלטה/תיקון עתידי שמוסיף נתון → **חייב להופיע כאן**. תעד את הדפוס.

## דרישות
- read-only מוחלט (sqlite mode=ro; אפס self-HTTP בתוך aggregator — כמו §5.4 הקיים).
- כל inspector עוטף try/except + warning rate-limited; אף פעם לא 500; מערכת חסרה → `status:unknown`.
- UX: כרטיסים מתקפלים, חיווי טריות צבעוני, פריסה נוחה לעיון מהיר.
- **Rule 5:** הדבק JSON מלא של ה-endpoint המורחב + תיאור/צילום של כל כרטיס מערכת אחרי session חי.
- **4 צירי UAT** ל-endpoint: Quality/Recency/Cardinality/Latency (זה hot-path — לוודא latency<100ms, לא לחרוג מ-polling floors ב-CLAUDE.md).

## תלות / סדר
- **קודם** למגה-פרומפטים Reactive(Phase 3) ו-S1(Phase 2) — או במשולב: הם מזינים את בלוקים ד'. תאם כך שאין כפילות (הם מוסיפים את הנתון, ה-D-OBS מציג אותו). אם בונים בנפרד — D-OBS מגדיר את ה-schema, והם ממלאים.

## בסיום
עדכן ROADMAP (1c · D-OBS) + STATUS_BOARD + DECISION_LEDGER (D-OBS → 🟢 IMPLEMENTED). תווית `D-OBS` בכל קובץ.

---
*read-only observability. אפס נגיעה בלוגיקת ירי/סיכון/polling floors.*
