# cursor — בדיקה: האם שורט-תקף (S2 INITIATIVE/REACTIVE + S4) צריך לירות עכשיו ונחסם? (מייקל 2026-07-20)

**מייקל:** *"אחד מהם [Initiative Short / Reactive Short] צריך להיות מוכן לשורט, וגם מערכת-4 — תבדוק עם cursor."*
מצב: Variation-DOWN (override) · price≈7503.5 **על VAL (7502.25)** · trend=RED · flags דלוקים (require_with_trend fix ON).
**מבצע: cursor · קריאה-בלבד · חוק-5.** ⛔ אין PLACE/.env/ריסטארט.

## ההבחנה הקריטית לבדוק
עם `REQUIRE_WITH_TREND_DAY_DIRECTION_V1=1`, `daytype_playbook.decide()` מחזיר **FULL** ל-REACTIVE **וגם**
INITIATIVE SHORT על Variation (בדקתי — FULL ל-RED וגם BLUE). אבל cursor מצא שהחסימה בפועל היא
**"responsive SHORT not at VAH (below_value)"** — כלומר בדיקת-ה**מיקום** של ה-responsive-fade.

**השאלה:** האם בדיקת-המיקום-responsive **תופסת גם שורט-INITIATIVE/CONT** (המשך עם-היום)?
- **REACTIVE** = responsive/fade → נכון שדורש VAH (לא לפייד ברצפה). חסימה ברצפה = **נכונה**.
- **INITIATIVE / S4-CONT (ZLR/TT/GB100)** = המשך עם-כיוון-היום → **צריך להיות מותר בפריצה מתחת ל-VAL**,
  לא לדרוש VAH. אם בדיקת-המיקום חוסמת גם אותם → **over-block אמיתי** של שורט-ההמשך.

## מה לבדוק (חוק-5, כל שורה פקודה+פלט)
1. **הבלוק של 13:15 (20:15 IL):** איזו תבנית בדיוק (REACTIVE responsive, או INITIATIVE)? day_type שנקרא? הסיבה המדויקת?
   (gateway/decisions + הלוג). אם REACTIVE-responsive-ברצפה → נכון. אם INITIATIVE/CONT → over-block.
2. **הלוגיקה:** ב-`daytype_playbook`/require_with_trend fix + `location_gate` — האם ה-location-check
   מבדיל family REV(responsive) מ-CONT/INITIATIVE? CONT/INITIATIVE צריך `with-day-direction=allow` בלי דרישת-VAH.
   הצלב מול החוזה `allow_responsive_fade` (test_dalton_require_day_direction_vah): "with-day-direction continuation
   always allowed" — האם זה מיושם בפועל ל-INITIATIVE/S4, או רק ל-REV?
3. **S4 (woodies) עכשיו:** האם ZLR/TT/GB100 SHORT מזוהה (price על VAL, trend RED)? אם כן — יורה או נחסם? ע"י מה?
4. **מצב-נוכחי:** אם price פורץ מתחת ל-VAL → שורט-INITIATIVE/CONT צריך לירות. עקוב setup-אמיתי דרך השרשרת.

## תוצר
`docs/handoff/SHORT_READY_CHECK_2026-07-20.md` — מסקנה: (א) הכל-נכון (responsive ברצפה נחסם, CONT יורה בפריצה) ·
(ב) **over-block: INITIATIVE/CONT-שורט נתפס ע"י responsive-location** → תיקון (family-aware: CONT/INITIATIVE עם-יום
לא דורש VAH), דגל-OFF+טסט, cowork מאמת. חוק-5. commit+push+LOG.
