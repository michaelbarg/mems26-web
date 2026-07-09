# CC — חבילת תיקוני-אמת מתקרית 333 (LIVE, 2026-07-09 ערב)

**חוזה:** `docs/handoff/CC_HANDOFF_CONTRACT.md` מחייב — טסטים אנטי-טאוטולוגיים (חייבים
להיכשל על הקוד הישן, הוכחה via `git stash`), Rule 5 (פקודה+פלט גולמי), סעיף NOT-DONE חובה.
**פריסה: אסור ריסטארט בלי אישור מייקל** — יש פוזיציה חיה (333). לקודד, לבדוק, לקמט,
לדווח READY; אני (Cowork) מתזמן את הריסטארט.

## הקרייה (ראיות מלאות, כולן אומתו בלוג/DB)

יום דרייב-אפ ‏+50 נק'. 25+ מועמדי-תבנית → עסקה אחת (333) — והיא נולדה מורעלת:

1. ‏18:45 ‏S2 ‏REACTIVE_LONG entry=7576.75 stop=7572.25 (rung r1, dist 4.5) — נשלח, מולא
   **2 חוזים אמיתיים** (אקטיביטי: 0→1→2; מייקל אימת בסיירה: 2 פעילים, 0 מימושים).
2. ‏TP-1 clamp צימד את **כל** t1/t2/t3 ל-IB-High 7566.5 — **מתחת לכניסה** בלונג.
3. שער ‏R:R (gateway:782) עבר כי `abs()` — יעד בצד הלא-נכון נראה מרחק כשר.
4. ילדי-היעד (sell-limits מתחת לשוק) לא התקבלו/לא עומדים בסיירה → פוזיציה בלי יעדים.
5. ‏BarLevelDetector (bar_level_detector.py:322) "הסיק" ‏C1+C2 ‏HIT_TARGET ‏@7566.5
   (‏pnl ‏−$51.25 כ"א) — **פיקציה**: ‏low מאז הכניסה 7573.25. הרשומה שיקרה, סיירה לא.
6. בנוסף (בלתי-תלוי): ‏cont_trend_filter חסם 13 ‏CONT כולל לונגים בעליה — `sustained_lsma_side`
   בודק צד-מול-LSMA בלבד; ברי-פולבק בעליה נסגרים מתחת ל-LSMA העולה → ‏"DOWN" מול ‏trend BLUE.
7. בשעה הראשונה: יעדי-מבנה (‏#68 structural + clamp) השתמשו ב-IB **מתהווה** (= שיא-הסשן הרץ)
   → ‏C1 במרחק 1.25 נק' (16:40, ‏"was t1=7564.15") → ‏R:R ‏0.05 → חסימה. ‏IB ננעל רק 17:30.

## התיקונים (סדר עדיפות)

### FIX-1 — שער R:R חתום (gateway ~:776)
`_t1_dist = abs(...)` → מרחק **חתום** לפי כיוון: ‏LONG ‏`t1-entry`, ‏SHORT ‏`entry-t1`.
‏`<= 0` → ‏block חדש `blocked_by="t1_wrong_side"` + לוג ‏WARNING (SYS-2). זה באג בשער
פסוק-ON — אין דגל חדש.

### FIX-2 — target_structure_clamp מוגן (backend/v9/systems/target_structure_clamp.py)
א. פרמטר `ib_locked` (המחשוב בשער: דקות-מאז-08:30 ‏America/Chicago ‏≥ 60; ‏TZ מפורש — Rule 4).
   ‏not locked → ‏passthrough + ‏note ‏"ib_forming_no_clamp".
ב. שפיות-צד: יעד מצומד חייב להישאר מעבר לכניסה בכיוון העסקה (‏LONG: ‏edge > entry+0.25;
   ‏SHORT: ‏edge < entry−0.25). אחרת — **לוותר על הצימוד לאותו יעד** (להשאיר מקור) + ‏WARNING.
ג. לא לגעת ב-BEYOND_IB_ALLOWED (פסיקת Variation-with-extension = פסיקה נפרדת של מייקל — לא לממש).

### FIX-3 — BarLevelDetector שפוי (bar_level_detector.py ~:314)
לפני היסק-מימוש: ‏LONG דורש ‏target > entry_price; ‏SHORT ‏target < entry_price.
הפרה → ‏CRITICAL ‏"[BarLevelDetector] INSANE TARGET GEOMETRY trade=%d %s target=%.2f entry=%.2f — inference disabled"
ולא קוראים ‏on_target_hit. (הסקת-סטופ ללא שינוי.)

### FIX-4 — #68 structural targets pre-lock skip (gateway ~:603)
אותו `ib_locked`: לא ‏locked → דלג על ‏resolve_structural_targets (יעדי-הסולם נשארים) + לוג INFO.

### FIX-5 — cont_trend_filter: הסמכת-מגמה (direction_context_live.py)
דגל חדש **CONT_TREND_STATE_CERT_V1 (default OFF — פסיקת מייקל להדלקה)**:
‏dir_sustained="UP" גם כאשר ‏K הברים האחרונים ‏trend_state=='BLUE' **וגם** ‏lsma_slope>0
(סימטרי ל-DOWN/RED). שאילתת ‏_srows כבר בטבלה הנכונה — להוסיף ‏trend_state ל-SELECT.
משאיר את דחיית-הצ'ופ (מצבים מעורבים/שיפוע-שטוח → NEUTRAL).

### FIX-6 — נתיב-סיירה-פתוח (SYS-3, דרישת מייקל המפורשת הערב)
"למערכת חייב להיות נתיב פתוח לסיירה שתדע תמיד מה הולך שם."
‏reconciler רץ (ב-fill_poller או task נפרד, כל ≤30 שנ'):
- ‏qty-אמת מ-‏trade_activity_events.jsonl (‏POSITION_CHANGE אחרון) + ‏fills journal.
- השוואה מול ‏TM (עסקאות פתוחות × ‏contracts שלא-נסגרו).
- סטייה → ‏WARNING רועש + ‏banner ‏(BannerStack) + הקפאת פעולות-אוטו על אותה עסקה.
  אימוץ-אוטומטי = שלב הבא (פסיקת מייקל), לא עכשיו.
- ‏DoD: להרוג את מחלקת "records≠reality" — ‏333 הייתה מתגלה תוך ≤30 שנ'.

## טסטים (אנטי-טאוטולוגיים — chaque one fails-on-old)
- ‏rr: ‏LONG ‏t1<entry → ‏blocked ‏t1_wrong_side (נכשל-על-ישן: עובר בגלל ‏abs).
- ‏clamp: (א) ‏ib_locked=False → לא-מצומד; (ב) ‏edge≤entry → יעד מקורי נשאר + ‏note.
- ‏detector: ‏LONG ‏target<entry → אין ‏on_target_hit (mock TM) + ‏CRITICAL בלוג.
- ‏structural: ‏pre-lock → ‏setup ללא ‏C1/C2/C3 מבניים.
- ‏cert: ‏closes מתחת-LSMA + ‏BLUE×K + ‏slope>0 → ‏UP רק עם הדגל; ‏OFF → ‏DOWN (ישן).
- ‏reconciler: ‏TM אומר 1 פתוח, אקטיביטי אומר 2 → ‏WARNING+freeze.

## אחרי מיזוג
`python3 scripts/gen_flag_index.py` (דגל חדש) + עדכון ‏RULED_FLAGS.yaml ‏(CONT_TREND_STATE_CERT_V1:"unset_or_0"
עד פסיקה) + שורת ‏STATUS_BOARD. ‏NOT-DONE מפורש על כל מה שלא הושלם.
