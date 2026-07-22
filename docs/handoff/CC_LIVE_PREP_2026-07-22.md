# CC — הכנה ללייב היום (2026-07-22) · רשימת-משימות מחייבת

**מייקל 10:45 IL:** רשימה לקלוד לתקן — כולל משימות-אתמול + תיקון סוג-פתיחה/סוג-יום בפרונט +
שינוי כניסת-S4 לטקטיות רק במיקום שמתאים לסוג-יום. **הכנה ללייב היום.**

**מצב כניסה (cursor 10:45, חוק-5):** `git pull` → HEAD `509ca2c8`. משימות-לילה 1–4 **לא בוצעו**
(אין קומיטים אחרי 22:45; `.env`: `LSMA_FLAT_GATE_V1=0`, `DAYTYPE_LOCATION_GATE=0`). pre-open:
`opening_panel` n_bars=0 / opening=null · `day_type/live`=null · status day=UNKNOWN — צפוי לפני 09:30 ET.
**אפס-קוד תוך-מסחר אחרי 09:30 ET.** בנייה עכשיו → אימות → ריסטארט-אחד לפני פתיחה.

---

## סדר-ביצוע (חובה — מהקריטי ללייב קודם)

| # | משימה | דגל / משטח | סטטוס | מקור-פסיקה |
|---|---|---|---|---|
| **A** | **מקור-יחיד סוג-יום + סוג-פתיחה בפרונט** | G5 / Task#5 · OpeningTypePanel · TopBar | 🔴 פתוח | מייקל 10:45 + G5 |
| **B** | **S4 טקטי רק במיקום שמתאים לסוג-יום** | `DAYTYPE_LOCATION_GATE` v2 | 🔴 פתוח | מייקל 22:18 + 10:45 |
| **C** | T1 = סוף-מבנה-הכניסה | `T1_STRUCTURE_END_V1` | 🔴 מפרט מאושר, לא נבנה | מייקל 18:15 |
| **D** | סטופ מאחורי קיצון-המבנה | `STOP_STRUCTURE_EXTREME_V1` | 🔴 מפרט, לא נבנה | מייקל 22:22 |
| **E** | המתן כשהמחיר תקוע (LSMA שטוח) | `LSMA_FLAT_GATE_V1=1` | 🔴 בנוי OFF — להדליק | מייקל 07-08 + 22:36 |
| **F** | הידרציית PnL/הפסדים מתאפסת ב-09:30 ET | hydration | 🔴 פתוח | מייקל 21:10 |
| **G** | C4_TREND_FLATTEN + T2T3_NO_STOMP | כבר ON אתמול | ✅ | מייקל 11:19 |
| **H** | TS_OFFSET_INGEST_GATE + IB_BREAK_ANY | כבר ON | ✅ | מייקל 07-21 |

מפרט מלא למשימות C/D/E/B: `docs/handoff/CC_T1_STRUCTURE_END_2026-07-21.md` (אל תשכתב — הרחב בלבד).

---

## A — סוג-פתיחה + סוג-יום בפרונט (מייקל 10:45: "שיתקן")

**כאב (אתמול, אומת):** פיצול-4-מקורות — `opening_panel.live=Normal` · שער/פלייבוק=`Variation` ·
`/day_type/live`=null · `classify_replay` מתהפך. מייקל ראה "Normal" וסחר על תווית-שגויה.

**תיקון (smallest):**
1. **מקור-תצוגה = אותו מקור כמו השערים:** `get_live_day_type` (override-aware). `classify_replay` =
   audit/EOD בלבד — לא תווית-חיה ב-TopBar / OpeningTypePanel / DayTypeLens.
2. `OpeningTypePanel`: סוג-פתיחה נשאר מ-`classify_replay` (זה נכון — opening type נקבע פעם אחת),
   אבל שורת-`live` / `effective_day_type` / פסיקי-התבניות = מ-`get_live_day_type` + playbook על אותה תווית.
3. כש-`get_live_day_type`=None → UI מציג **"—" / FORMING** בכנות (Rule 1) — לא נופל ל-Normal מדומה.
4. אחרי restart: `curl …/opening_panel` + `curl …/day_type/live` + צילום-TopBar — אותה תווית ב-3 המקומות.
5. טסט-רגרסיה: mock live=Variation → panel+TopBar מציגים Variation; live=None → לא מציגים Normal.

**קבצים:** `daytype_classify_routes.py` (opening_panel) · `OpeningTypePanel.tsx` · `TopBar.tsx` ·
store שמזין DayTypeLens. הצלב G5 / `GAP_REGISTER` G-16.

---

## B — S4 טקטי רק במיקום שמתאים לסוג-יום (מייקל 10:45, standing)

**הפסיקה (בכתב):** *"לשנות את הכניסה של מערכת 4 שתבצע עסקאות טקטיות אלא אם הן נמצאות במיקומים
שמתאימים מבחינת סוג היום."*

**פירוש-ביצוע (cursor — אם סטייה, שאל מייקל לפני קוד):**
- S4 = עסקאות-תבנית **טקטיות** (ZLR/GB100/TT/… לפי הפלייבוק).
- **ירי מותר רק כשהמיקום תואם סוג-יום** (Dalton): למשל Variation-UP → שורט נגד-הרחבה רק ב-VAH
  אחרי בדיקה; לונג-עם-הרחבה במיקומי-CONT לגיטימיים. אמצע-value נגד-הרחבה = **BLOCK**.
- זה **משימת-לילה 2** (`DAYTYPE_LOCATION_GATE` v2) + ודא ש-S4 עובר את אותו שער (לא רק S2).
- Fixtures אתמול: ‎#449/452/456 BLOCK · fixture חיובי 19:55 VAH-test ALLOW · S4 mid-POC SHORT על Variation-UP = BLOCK.
- הדלקה: `DAYTYPE_LOCATION_GATE=1` + RULED (פסיקת 22:18 **מחליפה** כיבוי-07-20) בריסטארט לפני פתיחה.

**אל תבלבל עם:** `LAYER0_CHOP_GATE` / `S2_CHOPPINESS_GATE` — נשארים STANDING-OFF.

---

## C+D — T1 מבני + סטופ קיצון-מבנה (אתמול, לא נבנה)

קרא + בצע לפי `CC_T1_STRUCTURE_END_2026-07-21.md`:
- **C:** `T1_STRUCTURE_END_V1` — כולל 3 תוספות-חובה של cursor (דורסי-T1 בגייטוויי, מונוטוניות סולם, RULED supersedes-07-10).
- **D:** `STOP_STRUCTURE_EXTREME_V1` — מחליף `breakout_bar/window:1` (פסיקת-06-30). אותו מזהה-מבנה ל-T1 ולסטופ.
- לבנות **יחד** · טסטי-rr על הצירוף · OFF עד ריסטארט-בוקר → אז ON + RULED.

אם הזמן לפני פתיחה לא מספיק ל-C+D המלאים: **A+B+E+F קודם** (חוסמים את ההפסדים של אתמול), C+D אחרי-שוק / לפני מחר.

---

## E — LSMA_FLAT_GATE_V1=1

בנוי. הדלק + RULED (ציטוט 07-08 + אשרור 22:36) + טסט-fixture על ‎#449/452/456=BLOCK, ‎#444=pass.
**לא** להדליק Layer0/S2 chop.

---

## F — הידרציה

`hydrate_live_pnl` / consecutive_losses לא נמשכים מסשן-אתמול אחרי 09:30 ET (או אחרי restart בוקר-אחרי-פתיחה).
אתמול: cap אפקטיבי $675 במקום $800 בגלל hydration. טסט: restart לפני 09:30 → מונים=0 או "pre-session"; אחרי עסקה-היום בלבד.

---

## שער-פתיחה ללייב (לפני שמייקל מחמש)

```bash
git pull
python3 scripts/flag_guard.py          # חייב PASS
curl -s localhost:8000/api/v9/day_type/live | jq .
curl -s localhost:8000/api/v9/day_type/opening_panel | jq .opening,.live,.effective_day_type
# TopBar == live == opening_panel.live  (אותה תווית)
# DAYTYPE_LOCATION_GATE=1 · LSMA_FLAT_GATE_V1=1 · (T1/STOP אם הספיקו)
# MEMS26_MODE=live · LIVE_TRADING_ARMED=1 · is_sim=0 · position=0
```

חוק-5: כל משימה = פקודה + פלט-גולמי ב-LIVE_CHANNEL. cursor מאמת; אף סוכן לא סוגר משימה של עצמו.

---

## להדבקה לקלוד קוד (בלוק אחד)

```
git pull. קרא docs/handoff/CC_LIVE_PREP_2026-07-22.md + docs/handoff/CC_T1_STRUCTURE_END_2026-07-21.md.

מייקל 10:45 — הכנה ללייב היום. סדר:
A) תקן סוג-פתיחה + סוג-יום בפרונט: מקור-תצוגה = get_live_day_type (כמו השערים);
   classify_replay = audit בלבד; None → "—" בכנות; OpeningTypePanel+TopBar אותה תווית.
B) S4 טקטי רק במיקום שמתאים לסוג-יום — DAYTYPE_LOCATION_GATE v2 (משימת-לילה 2),
   fixtures #449/452/456 BLOCK + 19:55 VAH ALLOW; הדלקה בריסטארט.
C+D) T1=סוף-מבנה + סטופ=קיצון-מבנה (אם יש זמן לפני פתיחה; אחרת אחרי-שוק).
E) הדלק LSMA_FLAT_GATE_V1=1 (פסיקה עומדת).
F) תיקון hydration consecutive_losses/PnL ב-09:30 ET.

כל דגל חדש: בנה→אמת→RULED→הדלק בריסטארט-אחד לפני פתיחה.
אפס-קוד תוך-מסחר אחרי 09:30 ET. חוק-5 ל-LOG. cursor מאמת.
```
