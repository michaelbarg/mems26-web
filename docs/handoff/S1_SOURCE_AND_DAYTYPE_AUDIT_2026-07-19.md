# S1 מקור-אמת + S2/S4×סוג-יום — ביקורת + תור-סגירה (G0–G8)

**תאריך:** 2026-07-19 · **מבצע:** cursor-agent · **מאמת:** cowork-dev (חוק-5)  
**מפרט:** [`CURSOR_S1_SOURCE_AND_DAYTYPE_MISSION_2026-07-19.md`](CURSOR_S1_SOURCE_AND_DAYTYPE_MISSION_2026-07-19.md)  
**תור-עבודה:** לוח **🔴 S124 GAPS** ב-[`LIVE_CHANNEL.md`](LIVE_CHANNEL.md) · הצלב [`GAP_REGISTER.md`](GAP_REGISTER.md) (G-01…G-18)  
**מפרט-CC:** [`CC_PROMPT_S124_GAPS_2026-07-19.md`](CC_PROMPT_S124_GAPS_2026-07-19.md)  
**הצלב:** [`PATTERN_BIBLE_2026-07-19.md`](PATTERN_BIBLE_2026-07-19.md) (לא נשכתב) · SoT · `S1_ACTIVE_CANONICAL.md`

**אין שינוי-קוד/.env במסמך הזה.** סגירת-פערים = אחרי פסיקת-מייקל → מפרט-CC → cc-macbook → אימות-cowork → סימון-cursor.

---

## תשובות ישירות (מייקל)

| שאלה | תשובה קצרה |
|---|---|
| האם ל-S1 יש מקור-אמת אחד? | **לא לגמרי.** לייב-מסחר אמור לעבור ב-`get_live_day_type()` (override→machine→antiflap). UI עדיין קורא `classify_replay` (בלי override/antiflap). S2 **detection** עדיין על `current_day_type` (hydrate מ-`v9_day_type_state`). S4 אחרי A6 קורא live ראשון, אבל נסיגה עדיין לטבלה-מתה/`"Normal"`. |
| האם S1 = דלתון? | **בערך ל-7(+1) הסוגים** (sides/IB/POC/vol ב-`daytype_classifier.py`). פערים: prelock לא-כנה (דגל OFF), escalation-only **לא** על המנוע החי, Neutral=שני צדדים (לא "בלי כיוון"). |
| האם S2 סוחר לפי סוג-יום? | **שער-playbook: כן** (SKIP עובד). **Detection/chart-gates: חלקית** — A2/A4 על `current_day_type` מפגר. Emit/sizing: live. **REDUCED בגודל: לא** (FIXED_4). |
| האם S4 סוחר לפי סוג-יום? | **שער + sizing אחרי A6: כן** (`S4_OVERRIDE_AWARE_V1=1`). **Paint/trend: עיוור** (B1 `current_bar` בלי `_trend_from_cci`). Fallback-מת עדיין בקוד. |

---

## חלק א' — מפת מנועים וצרכנים

### A1. מנועי סוג-יום

| מנוע | כותב | קורא | סטטוס |
|---|---|---|---|
| `classify_session` / `daytype_classifier.classify` | pure | `main.py` `_day_type_on_bar` → promote ל-machine | ✅ LIVE canonical (כש-`S1_ENGINE_NEW_CLASSIFIER=1`) |
| `classify_replay` | pure/API | UI TopBar/DayTypeLens · audits · G1 רק מחוץ-לסשן | ✅ UI/replay · ⛔ mid-session G1 (`trade_context.py:587-603`) |
| `day_type_machine` | promote מ-`classify_session` | `get_live_day_type` | ✅ LIVE shell ללייבל |
| `v9_day_type_state` | `main.py` write-on-change | S2 hydrate · S4 fallback | 🟡 נכתב · **לא SoT למסחר** |
| `get_live_day_type` | — | G1 · S2 emit · S4 (A6) · gates | ✅ SoT-helper למסחר |
| Shadow / `/day_type/current` | — | — | 🔴 מת |

**נתיב-לייב:** `_day_type_on_bar` → `classify_session` → map `Normal_Variation→Variation` → `day_type_machine` → `get_live_day_type`.

### A2. צרכני-מסחר (האם אותו מקור?)

| צרכן | מקור | מול `get_live_day_type` |
|---|---|---|
| Gateway playbook / G1 | `extract_g1_entry_context` → live כש-`S1_NEW_CLASSIFIER` | ✅ |
| S2 detection (NT skip, chart 5a/5c) | `self.current_day_type` (event + hydrate DB) | 🔴 G2 |
| S2 Flag T2 fork | `self.current_day_type` (`five_min_system.py:1551`) | 🔴 G3 |
| S2 emit / V2 sizing | `get_live_day_type` first | ✅ |
| S4 sizing/targets | `get_live_day_type` first (`woodies_system.py:650-657`) | ✅; נסיגה 🔴 G6 |
| UI badge / lens | `classify_replay` | 🔴 G5 (תצוגה ≠ שער) |

### A3. זיהוי 8 הסוגים (first-match ב-`daytype_classifier.py`)

| סוג | קריטריון בקוד (תמצית) | בערך |
|---|---|---|
| FORMING | `n_bars < 12` | ~271-283 |
| Nonconviction | flag + OA in-value + sides0 + mid | ~285-300 |
| Nontrend | sides0 + vol_low + rib≤1.15 | ~302-313 |
| Neutral_Extreme | sides2 + close extreme | ~316-318 |
| Neutral_Center | sides2 + close center | ~319-322 |
| Trend_DD | sides1 + dd_second_dist / neck | ~327-339 |
| Trend_Normal | sides1 + open held + one_tf + extreme + rib≥2.5 | ~340-407 |
| Variation | sides1 catch-all → map Variation | ~408-411 |
| Normal | sides0 contained rib/vol | ~413-431 |

### A4. פערים מול דלתון (קוד בלבד)

| פער | Cite | מפה ל-G# |
|---|---|---|
| Prelock לא-כנה — תווית ישנה לפני IB lock | `trade_context.py:559-573` · דגל OFF | **G4** |
| Escalation-only רק ב-shadow מת | `shadow_reclass.py:85-88`; live מדלג | **G8** |
| Neutral = שני צדדים, לא "נייטרלי=בלי כיוון" | `daytype_classifier.py:226-227` | **G8** |
| `ib_source=bars` fallback כש-TPO חסר | `daytype_classify_routes.py` / `classifier_core` sanity | דוקטרינה / לא בתור G |
| UI ≠ gates | `TopBar.tsx` / `DayTypeLensContent.tsx` → classify_replay | **G5** |

---

## חלק ב' — הצלב Bible (לא שכתוב)

מטרת-מייקל: תבנית נכונה + מיקום נכון → מימוש C1–C3.

| מקור-כאב (Bible) | קשר ל-G |
|---|---|
| B1 paint / current_bar | **G1** |
| S2 מאוחר (B4+FHB+VSA) | מחוץ לתור S124 (Bible B2) — לא נסגר כאן |
| FIXED_4 מול REDUCED | **G7** |
| A2/A4 stale detection | **G2** (+ **G3** Flag T2) |
| A6 S4 override | ✅ נסגר 07-19; נשאר G6 fallback |
| entry_not_confirmed | נפסק 07-19 — לא בתור |

**B2 מספרים (`audit_pattern_miss` על 15–17/07):** לא-מוכרע בסשן זה (Postgres trust). להריץ על MacBook-המסחר.

---

## תור-סגירה מדורג (G0–G8)

פרוטוקול: הסבר (כאן + LIVE_CHANNEL) → **פסיקת-מייקל** → מפרט-CC → cc-macbook → cowork אימות → cursor מסמן ✅.

| # | פער | הצעת-תיקון | סיכון |
|---|---|---|---|
| **G0** | מפת-מצב + סדר | אישור סדר G1→G8 | אין קוד |
| **G1** | `current_bar.trend_state` raw בלי `_trend_from_cci` | אותה פונקציה על הבר המנותב ל-S4; תחת `TREND_CCI_DIRECT_V1` הקיים או דגל-השלמה OFF | נמוך אם רק משלים דגל שכבר ON |
| **G2** | S2 A2/A4 על `current_day_type` | detection קורא `get_live_day_type` ראשון; None→log מפורש | בינוני — משנה מי יורה |
| **G3** | Flag T2 על `current_day_type` | אותו `_emit_day_type` | בינוני — יעדים |
| **G4** | `DAYTYPE_HONEST_PRELOCK_V1` OFF | פסיקה להדליק + RULED + ריסטארט | תצוגה/שערים יראו None פרה-IB |
| **G5** | UI = classify_replay | צרכן FE → אותו מקור כמו gates | נמוך-בינוני (תצוגה) |
| **G6** | S4/FiveMin נסיגה ל-`v9_day_type_state` / `"Normal"` | fail-honest None; דגל OFF | בינוני |
| **G7** | FIXED_4 בולע REDUCED | **פסיקה חובה** לפני קוד | **גבוה** — גודל פוזיציה |
| **G8** | Neutral / escalation דוקטרינה | פסיקה + מפרט; קוד רק עם חתימה | אסטרטגי |

---

## מה לא הצלחתי להכריע מהקוד

1. מספרי `audit_pattern_miss` / נקודות-כניסה ממוצעות על 15–17/07 (אין DB בסשן).
2. כמה פעמים בפועל S4 נפל ל-`v9_day_type_state` אחרי A6 (דורש OPS_LOG/grep חי).
3. האם `DAYTYPE_GATE_LIVE_V1` / `DAYTYPE_ANTIFLAP_V1` דלוקים עכשיו — לא קוראים `.env` כאן; cowork יאמת ב-`flag_guard`.
4. SoT עדיין כותב ש-machine הוא "OLD 3-type" — בפועל הלייבל מקודם מ-7-type כש-engine flag ON; **מסמך-SoT מפגר** (לא תוקן כאן).
5. מיקום-כניסה אידיאלי לפי דלתון לכל תבנית — חלקית ב-Bible; אין מספרים חיים לסגירת B2.

---

## למייקל — מה לעשות עכשיו

1. לקרוא **G0** ב-LIVE_CHANNEL ולאשר/לשנות את הסדר G1→G8.  
2. לכל פער: לכתוב בלוג **`לתקן` / `לדחות` / `לשנות-כך`**.  
3. אחרי `לתקן` על G1 — cowork כותב מפרט → cc-macbook מממש (דגל OFF עד פסיקת-הדלקה).
