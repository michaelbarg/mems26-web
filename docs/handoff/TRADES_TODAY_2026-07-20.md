# עסקאות היום — 2 תיקונים במקביל שפותחים את הטרייד (מייקל: עדיפות-עליונה)

**מצב:** ~12:30 ET, סגירה 16:00, סף-כניסה 15:30 → **~3 שעות.** הטרייד שמייקל רוצה = **שורט-Variation-בתקרה
(מחיר מעל VAH) עם סטופ-מבני.** שני חוסמים מונעים אותו — כל אחד בקובץ אחר → **cc ו-cursor במקביל, בלי התנגשות.**
כל תיקון: דגל-OFF + טסט-דטרמיניסטי על מקרה-אמת + byte-identical OFF + flag_guard. cowork מאמת → הדלקה → **ריסטארט אחד מתואם** כששניהם מוכנים.

## cc — תיקון-1 (P0): עיגון-הסטופ-למבנה  [קובץ: five_min_system.py + gateway resolver]
התיקון **כבר בנוי, רק כבוי:**
- הדלק `STRUCTURAL_STOP_ORIGIN_V1` (five_min_system.py:1277 — כרגע זורק את `structural_anchor` האמיתי ומשתמש בקצה-בר-הכניסה).
- הדלק `STOP_WINDOW_COMPLETED_V1` (כרגע=0 → קורא בר-חלקי → מרחק קורס → רצפת-ATR בתוך המבנה).
- `STOP_RESOLVER_V1`: כשמבנה רחב-מהתקרה → **להרחיב-למבנה, לא לדחות** (מבנה גובר; ATR→חיתוך-חוזים).
- **טסט:** ברי-#420 → REACTIVE_SHORT stop **> 7521.25+6T** (מעל השיא), לא 7514. מראה LONG.
- **מתקן גם את rr_entry_gate ו-pre_fire** (R:R נכון מסטופ-נכון).

## cursor — תיקון-2 (P0): require_with_trend = כיוון-היום  [קובץ: daytype_playbook.py]  ⭐ משימת-בנייה
**זו המשימה שפותחת את השורט שלך.** `daytype_playbook.py:132-137`:
- כרגע: `counter = (SHORT and trend_state==BLUE)` → חוסם שורט על באונס-רגעי.
- **תקן:** בימים-כיווניים (Variation/Trend) `require_with_trend` משווה מול **כיוון-היום/הרחבה** (get_live_expansion / dir_bias),
  **לא** trend_state הרגעי. **תבניות responsive-REV (REACTIVE/HNS) פטורות** — נשלטות לפי **מיקום** (SHORT מותר ליד VAH, LONG ליד VAL).
- אותו עיקרון ל-`cont_trend_filter`/`direction_context` על CONT (מול הרחבה, לא LSMA-רגעי) — אבל **התחל ב-require_with_trend** (זה החוסם החי).
- **טסט-דטרמיניסטי:** Variation-מטה + SHORT@VAH + trend_state=BLUE → **מותר** (verdict≠SKIP). LONG@VAH → נחסם. byte-identical כשהדגל OFF.
- דגל חדש: `REQUIRE_WITH_TREND_DAY_DIRECTION_V1` (default OFF) + RULED.

## cursor — תיקון-4 (P1, אחרי-2): T2/T3 מבניים  [targets.yaml / structural_targets.py]
`pattern_t1_points` (line 1176) דורס את המיקוד-המבני (1115) ב-T2=2×T1/T3=3×T1. **תקן:** T1 אמפירי בסדר;
T2/T3 = **מבניים** (VAL / measured-move / קצה-VA-נגדי), או הרץ pattern_t1 **לפני** structural. טסט: Variation-מטה → T2/T3 מטה למבנה.

## סדר להשגת-עסקה-היום
cc-1 + cursor-2 **במקביל** → cowork מאמת שניהם על מקרי-האמת → **ריסטארט-אחד** → אמת: (א) get_live=Variation,
(ב) short@VAH עובר require_with_trend, (ג) סטופ מעל-השיא, (ד) rr עובר. **אז השורט-בתקרה יורה עם סטופ-מבני.**
תיקון-3 (מקור-יחיד) ו-5/6/7 — אחרי, לא חוסמים את הטרייד-של-היום.

**גבול-בטיחות:** is_sim לפי מייקל · $ cap פעיל · בלי op=EXIT · לא לרסטרט חוזר (ריסטארט-אחד-מתואם בלבד).
