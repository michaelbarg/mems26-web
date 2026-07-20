# ביקורת-דלתון מקיפה — 2026-07-20 (סוכן-אבחון, קריאה-בלבד, חוק-5)

## הממצא הגדול: תיקון-הסטופ כבר קיים בקוד — פשוט כבוי
נתיב-הסטופ של S2 (`five_min_system.py:1268-1352`) — **שני תיקונים בנויים אך OFF:**
- **`STRUCTURAL_STOP_ORIGIN_V1`** (unset/OFF) → שורה 1277 **זורק את עוגן-הסווינג האמיתי** של התבנית (`structural_anchor` = שיא b1..b3 = אזור-ההיצע 7521-7527) ומשתמש בקצה-בר-הכניסה במקום. ההערה ב-:1271 **מצטטת את #420 מפורשות.**
- **`STOP_WINDOW_COMPLETED_V1=0`** (OFF) → שורה 1308 קורא את ה-buffer-החי שהבר-האחרון בו חלקי (range≈0) → מרחק-מבני קורס ל-~3T → רצפת-ATR נכנסת → סטופ **בתוך** המבנה. זה בדיוק #420.
- ה-gateway resolver (`STOP_RESOLVER_V1=1`) **דוחה** מבנה רחב-מהתקרה ומשאיר את הסטופ-הצר — סותר את חוזה `compute_stop_v2` ("מבנה תמיד גובר").
→ **תיקון = להדליק את 2 הדגלים + לתת ל-resolver להרחיב-למבנה (לא לדחות). enable+test+verify, לא build-מאפס.**

## שורש-על (מאומת-קוד): 2 מקורות
(א) **הסטופ לא מעוגן לקצה-המבנה** (התיקונים כבויים) → הפסד-מוקדם **וגם** R:R מנופח → rr_entry_gate/pre_fire חוסמים.
(ב) **סיגנלים רגעיים** (trend_state/LSMA/day_type-מסונתז) מחליפים את **כיוון-היום/הרחבה של דלתון**.

## rr_entry_gate (חשד-מייקל אומת)
הסטופ-הממוקם-שגוי נכנס לחישוב-R:R → risk מנופח → R:R<0.65 → חסימה. **לא לכבות את rr — לתקן את הסטופ** (ואז R:R נכון לבד). אותו סטופ מזין גם את `pre_fire_validator` (R:R≥1 מול T2).

## require_with_trend (5a — פאולט חי)
`daytype_playbook.py:132-137`: על Variation, SHORT+trend_state=BLUE (באונס רגעי) → "counter-trend" SKIP → חוסם fade-בתקרה בכיוון-היום. **תיקון: להשוות מול כיוון-היום/הרחבה, לא trend_state רגעי; לפטור responsive-REV לפי מיקום (VAH/VAL).** אותו עיקרון ל-cont_trend_filter/direction_context על CONT.

## יעדים T0-T4 (חשד-מייקל אומת)
מיקוד-מבני **דלוק ונכון** (`structural_targets.py`, DAYTYPE_TARGETS_STRUCTURAL=1) — אבל **`pattern_t1_points` רץ אחריו (שורה 1176>1115) ודורס אותו** ב-T1=pts, T2=2×T1, T3=3×T1 שרירותי, בדיוק לתבניות שיורות ב-Variation. **תיקון: T1 אמפירי בסדר; T2/T3 מבניים (VAL/measured-move/קצה-VA-נגדי), או להריץ pattern_t1 לפני structural.** + הכל תלוי בסוג-יום נכון (#420 תוייג Trend_Normal → יעדים שגויים).

## שער-דלתון הנכון קיים אך כבוי
`DAY_DIRECTION_DOCTRINE_V1` (OFF) = השער הנכון (כיוון-הרחבה + halt-proof) — כבוי, בעוד השערים-הרגעיים דלוקים במקומו.

## רשימת-תיקונים ממוינת (להכשרה לדלתון)
1. **P0 · עיגון-סטופ-למבנה** — הדלק `STRUCTURAL_STOP_ORIGIN_V1`+`STOP_WINDOW_COMPLETED_V1` + resolver-widen-to-structure (מבנה גובר גם מעבר לתקרת-ATR; ATR→חיתוך-חוזים). טסט #420. **מתקן גם את rr/pre_fire.**
2. **P0 · require_with_trend/cont על כיוון-היום** (לא trend רגעי); REV-fade לפי מיקום.
3. **P1 · מקור-יחיד לסוג-יום + גלאי-הרחבה** (כל-פריצת-IB=הרחבה) → מבטל את ה-override הידני + מחזיר את השערים-הנכונים.
4. **P1 · T2/T3 מבניים** (לא ×2/×3).
5. **P1 · אזור-מת 10:00→נעילה** (ירי פר-סוג-פתיחה כל השעה).
6. **P0-אמון · רקונסיליאציה-סיירה** (trade_fills.json ריק — P&L לא-אמיתי).
7. **P1 · גיוס-buffer-בבוט.**

**מפתחות:** trading_gateway.py · five_min_system.py:1254-1352 · daytype_playbook.py:132-137 · structural_targets.py · trade_context.py:520-780 · pre_fire_validator.py · daytype_playbook.yaml · targets.yaml
