# CC Handoff — #68 Direction-Context: בניית החלקים-החסרים (Michael אישר 2026-06-21)

**מטרה:** לבנות את "מוח-הכיוון" המאוחד — קביעת-כיוון רציפה מ-**4 הגורמים** (מיקום + CVD + נקודות + סוג-יום) דרך מודל **קבלה/דחייה של פריצת-IB**, + שני השערים החסרים (Nontrend, chop). התבניות = טריגרים; זו סמכות-הכיוון היחידה שהן מתייעצות בה.
**מצב:** spec לאישור-Michael פר-החלטה-פתוחה (§5). **flag-gated default-OFF · SHADOW · לא commit עד הוראה.**

---

## 0. מה כבר קיים (שימוש-חוזר — לא לבנות מחדש)
מ-`CC_S68_DIRECTION_CONTEXT_CHECKLIST_2026-06-21.md`, חי ב-SHADOW:
- `daytype_position_gate` (מיקום+סוג-יום) · `structural_targets` (3-חוזים) · all-patterns (C2) · `session_high/low` מוזרם (C3).
- נתונים קיימים: **`sides`** (S1, קבלת-פריצה ≥8% ווליום מוחזק≥2) · **`cumulative_delta`** (`v9_bars_5min` + טבלה) · נקודות-TPO.

## 1. `direction_context` resolver — מודול חדש `backend/v9/systems/direction_context.py` (flag `DIRECTION_CONTEXT`, default-OFF)
**קלט:** `day_type, entry_price, tpo_ctx(poc/vah/val/ibh/ibl/session_high/session_low), cvd_now, cvd_session_min/max, sides(S1)`.
**פלט:** `{breakout_state, auction_direction, allowed:set(LONG/SHORT), cvd_confirm, reason}`.
**לוגיקה (המודל של Michael):**
- **breakout_state** מ-`sides` + קצוות-סשן מול IB:
  - `up_accepted` = נשבר IBH **וגם** sides-up (קבלה) → "התרחבות מעלה".
  - `up_rejected` = חרג מעל IBH אך **בלי קבלה / חזר פנימה** → "פריצה-מעלה-שנכשלה".
  - מראה-מראה למטה; אף-אחד → "איזון / בתוך-IB".
- **auction_direction:**
  - `up_accepted` → **לך-עם-מעלה** → LONG (בפולבק); חסום SHORT.
  - `up_rejected` בקצה-עליון → **דהה** → SHORT בקצה; חסום LONG בקצה.
  - מראה למטה. **איזון** (אין פריצה) → דהה-קצוות לפי מיקום (SHORT≥POC, LONG≤POC).
- **cvd_confirm:** `cvd_pos = (cvd_now − min)/(max − min) ∈ 0..1`. LONG דורש `cvd_pos` לא ≤0.25 (לא מכירה-חזקה); SHORT לא ≥0.75. CVD סותר-חזק → veto/הקטנה.

## 2. לחווט את ה-resolver כסמכות-הכיוון
- להחליף את כללי-ה-per-day-type ב-`daytype_position_gate` בקריאה ל-`direction_context` (הגייט הופך ל-wrapper דק, או ה-resolver נקרא בשרשרת-הגייטוויי). S4 דרך פרמטר `context` (המת-המוכן); S2 דרך `cross_context`.
- **Neutral: לבטל את 'שני הצדדים'** — כיוון לפי breakout-state במיקום (כשל-עליון→שורט-בלבד בקצה; כשל-תחתון→לונג-בלבד).

## 3. צנרת CVD לזמן-ירי
- לחשוף `cumulative_delta` + min/max-סשן (ל-cvd_pos) ב-`cross_context` בזמן-ירי (מ-`v9_bars_5min.cumulative_delta` / הטבלה הייעודית). זה הקלט החסר ל-§1.

## 4. שער Nontrend (לתת לו בית)
מאחר ש-C2 גרם ל-playbook להחזיר FULL, אף אחד לא חוסם Nontrend. לאכוף **stand-aside** ב-resolver/position-gate: `day_type==Nontrend` → לחסום הכל (או חוזה-1 סקאלף לפי הטבלה — §5).

## 5. 🔴 שלוש החלטות שצריכות אותך (proposed defaults — לאשר/לשנות)
1. **סדר-עדיפויות כשהגורמים סותרים:** *proposed* — breakout-state+מיקום קובעים כיוון-ראשי; CVD = אישור/veto; סוג-יום = מסגרת-הרמות.
2. **מנגנון chop-guard** (כשל 06-11): *proposed* — בימי-איזון/Neutral, veto ל-fade אחרי K עצירות-רצופות **או** טווח<X עם CVD-שטוח. (Layer-0 chop כבוי בהחלטתך — זה guard ממוקד-fade, נפרד.)
3. **Nontrend:** *proposed* — stand-aside מלא (לא לסחור). חלופה: חוזה-1 סקאלף-קצה.

## 6. ניקוי
- לתקן את **5 טסטי-playbook-legacy** (לבודד `DAYTYPE_POSITION_GATE=0` / טסטים-חדשים ל-all-fire).
- **commit** של כל #68 + מסווג-S1 (untracked) — אחרי אישור-Michael.

## 7. אימות (Rule 5)
- טסטים אנטי-טאוטולוגיים פר-חלק (RED-on-revert): breakout up_accepted→LONG/block-SHORT · up_rejected→SHORT/block-LONG · CVD-סותר→veto · Neutral כבר-לא-שני-צדדים · Nontrend→block.
- **להריץ מחדש את הסימולציה** (`SIM_NEW_STACK`) עם ה-resolver → לצפות: 06-11 (chop) **לא** מחמיר; ימי-טרנד מחזיקים.
- הדלקה ב-SHADOW + אימות-חי. CC בונה, Cowork מאמת.

## 8. NOT-DONE
- לא לגעת ב-opening_type / S3 / Standing-OFF flags.
- לא להדליק ב-DEMO/LIVE — SHADOW בלבד עד צבירת-ראיה.
- ה-resolver לא מחליף את ה-classifier (S1) — רק צורך ממנו `sides`/day_type.
