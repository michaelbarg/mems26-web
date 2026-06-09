# CC — FIX 7: Flag stop = בר-הפריצה + T1 יחסי (0.4–0.8R לפי מרחק) · 2026-06-09

**מבוסס על עסקה חיה #22 (BEAR_FLAG_SHORT) + החלטות-Michael מפורשות.** trading-logic → **STRATEGIC-STOP**: ממש בדיוק לפי ה-spec למטה, אל תשנה ערכים בלי הטבלה. Rule 5 (raw) · regression · §config-tunable (YAML, בלי קוד).

**הראיה (raw, עסקה #22):** `entry=7313.5 · stop=7349.75 → סיכון 36.25 נק'` · `t1=7259.375 (1.5R, 54נק') · t2=7205.25 (3R)`. הסטופ עוגן ל-`flag_high=7349.00` שזה **ה-wick של בר-הדחייה 18:50** (`O7341 H7349 L7331 C7333`). הברים: דגל 18:30–18:50 ~7326–7349, **בר-פריצה 18:55** `O7332 H7334.50 L7311 C7312.50`.

═══════════════════════════════════════════════
## FIX 7A — סטופ ל-Flag = בר-הפריצה (לא flag_high/wick)
═══════════════════════════════════════════════
**שורש:** `backend/v9/systems/five_min/patterns/flags.py:249` → `"structural_anchor": flag_high + TICK_SIZE` כאשר `flag_high = max(b["h"] for b in flag_bars)` (כולל wicks) → סטופ רחב מדי.

**ההחלטה (Michael):** הסטופ עוגן ל-**בר-הפריצה** — ב-`detect_bear_flag` זה `breakout = w[-1]` (השורט: `breakout["h"]`); סימטרי ב-`detect_bull_flag` (הלונג: `breakout["l"]`). 
- שנה `structural_anchor` ל-`breakout["h"] + TICK_SIZE` (bear) / `breakout["l"] - TICK_SIZE` (bull), במקום `flag_high/flag_low`.
- **או** (עדיף config) `config/stop_anchors.yaml:79` → `Flag: {type: breakout_bar, window: 1}` במקום `flag_low` — ה-resolver כבר תומך ב-`breakout_bar` (שורה 59). ודא שהוא בוחר `high` לשורט / `low` ללונג, +`anchor_offset_ticks` (3T).
- **אבחן-קודם** איזה משני המסלולים פעיל בירי (detector-anchor מול resolver-window) ותקן את הנכון, לא חצי-חצי (anti-partial-wiring).

**verify על #22:** סטופ צפוי ≈ `7334.50 + 3T = 7335.25` → סיכון ≈ **21.75 נק'** (במקום 36.25).

═══════════════════════════════════════════════
## FIX 7B — T1 יחסי: 0.4R (סטופ רחב) → 0.8R (סטופ הדוק), לפי מרחק
═══════════════════════════════════════════════
**ההחלטה (Michael, מספרים סופיים):** T1 יחסי לפי **מרחק-הסטופ בנק'**, בבָּנד **15→25 נק'** ממופה ל-`t1_r` **0.8→0.4** (ככל שהמרחק קטן, T1 **גדל**):
```
dist ≤ 15 נק'  → t1_r = 0.8   (clamp)
dist = 20 נק'  → t1_r = 0.6
dist ≥ 25 נק'  → t1_r = 0.4   (clamp)
t1_r = 0.8 − (dist − 15)/10 × 0.4   (לינארי, clamp [0.4, 0.8])
```
- **כל הפרמטרים ב-YAML (config-tunable, בלי קוד):** `t1_r_max: 0.8`, `t1_r_min: 0.4`, `dist_tight_pts: 15`, `dist_wide_pts: 25`. Michael מכוון בלי קוד.
- חל על **T1/המימוש**. T2/T3 — השאר מהטבלה (`targets_table`) אלא אם Michael יורה אחרת.

**verify על #22:** עם הסטופ החדש (בר-פריצה) ≈ **21.75 נק'** → `t1_r = 0.8 − (21.75−15)/10×0.4 ≈ 0.53` → T1 ≈ `7313.5 − 0.53×21.75 ≈ 7302` (במקום 7259.4). הרבה מוקדם יותר. ✓

═══════════════════════════════════════════════
## אימות + מעקות
═══════════════════════════════════════════════
1. **regression (RED-on-revert):** שחזר את קלטי #22 → assert `stop ≈ breakout_high+3T` (לא flag_high) **וגם** `t1_r ∈ [0.4,0.8]` לפי המרחק (לא 1R/1.5R). הוכח אדום-בהחזרה.
2. **אל תשבור תבניות אחרות:** Reactive/OFA/Double_BT/HnS stop-anchors + T1 שלהן לא משתנים אלא אם זה בכוונה. הרץ regression מלא, הדבק מספר.
3. **YAML-tunable** (§Standing — stop+exits tunable) · **S3 לא נוגעים** · אל תדליק דגל default-off.
4. **raw** לכל: diff (file:line/commit) · replay #22 (stop+T1 חדשים) · regression count. עדכן `STATUS_BOARD.md` + הפק סטטוס ל-Cowork.

**מה ש-Cowork יבדוק:** replay #22 מראה `stop≈7335` ו-`T1≈0.4R` · RED-on-revert של שני החלקים · אף תבנית אחרת לא נשברה.
