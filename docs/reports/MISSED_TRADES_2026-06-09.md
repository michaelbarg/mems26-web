# חוקר עסקאות-שלא-בוצעו · 2026-06-09 (ריצה אוטונומית — Cowork)

**שער-זמן:** America/Chicago = **15:20 CDT** בעת הריצה → RTH סגור, ממשיכים.
**מצב יומי** (`/api/v9/day_type/current`): `day_type=Variation` · confidence **38** (נמוך) ·
opening **OPEN_DRIVE** · IB **7390.75–7417** (range 26.25, WIDE) · stage C3.
**readiness** (`/api/v9/build/pattern-status`): verdict **DEGRADED** · reason `trend_state=GRAY`
(post-close; `s4_trend_not_stuck_gray=false`, `in_rth=false`).
*הערה:* readiness מדווח `day_type=Trend_Normal` בעוד `/day_type/current`=Variation — **פער-instance** (I-1/C-2, ידוע).

> ✅ **שינוי מהותי מ-06-08:** היום המערכת **כן ירתה** — `/api/v9/trades/recent` מראה **2 עסקאות-shadow היום**
> (אתמול: 0). שתיהן בבוקר:
> - **#20 · S4 Woodies `HTLB` · SHORT** · entry **08:50 CT @ 7489.25** → exit **10:20 CT @ 7383.25** → **+106 נק'**
>   (תפסה את כל ה-OPEN_DRIVE היורד של הבוקר). **stop=7489.0 ≈ entry** → סטופ מנוון (**I-3**), R לא-מוגדר.
> - **#22 · S2 5-Min `BEAR_FLAG` · SHORT** · entry **11:00 CT @ 7313.5** · stop 7349.75 → exit **11:26 CT @ 7313.5**
>   (**breakeven/scratch**) — הרגל המשיכה ל-7247 (11:40) אז החזקה הייתה ≈+66 נק'; **היציאה-השטוחה קטעה רווח** (exit-logic, לא gate-כניסה).

> ⚠️ **מגבלת-דאטה (מקור-אמת, Rule 1 — זהה ל-06-08):** ה-export החי מחזיק **50 ברים** (`woodies`) /
> 80 ברים (`bars5min`) בלבד — חלון **~11:15→15:20 CT**. **אין CCI/ZLR/HFE/trend לבוקר-RTH (08:30–11:10 CT).**
> בנוסף `bars5min` מכיל ברים **עתיד-מתוארכים (06-10 22:40 IDT)** — **I-15/I-18 חי**. לכן הניתוח-מעוגן-signal מכסה
> רק את חצי-היום השני; הבוקר משוחזר רק עקיפות דרך `/trades/recent`. **הצלבת Sierra ל-CCI עדיין חובה — סימון ל-CC.**

---

## טבלת ה-setups — lookback מתגלגל 6-ברים (חלון signal 11:15–15:20 CT)

החוק: SHORT → entry=close הבר, stop=max(high הבר, high הקודם)+tick; LONG → mirror. risk=|stop−entry|,
T1=1.5R, T2=2.5R, replay קדימה עד hit-stop / hit-T1 / סוף-סשן (timeout = mark-to-last).
כל ה-signals היום הם **ZLR/S4** (אין HFE-flag בחלון). אף אחד לא ירה (העסקאות היו 08:50 + 11:00, לפני החלון).

| זמן(CT) | תבנית(שלנו) | מערכת | זוהה?(flag) | entry | stop | T1 | R-נגד | gate-שחסם | I-# |
|---------|-------------|-------|-------------|-------|------|----|-------|-----------|-----|
| 11:35 | ZLR-DOWN | S4 | ✅ `zlr=DOWN` (RED) | 7254.75 | 7308.0 | 7174.9 | **−1R** (stop) | risk=53נק' (סטופ-רחב, פסגת-דחייה) → לא-איכותי | I-3 |
| 12:50 | **ZLR-UP** | S4 | ✅ `zlr=UP` (BLUE) | 7346.5 | 7330.75 | 7370.1 | **+1.5R** ✅T1 | לא-בבאפר; trend=BLUE → צריך-לרוט | I-13/route |
| 12:55 | **ZLR-UP** | S4 | ✅ `zlr=UP` (BLUE) | 7347.25 | 7333.0 | 7368.6 | **+1.5R** ✅T1 | כנ"ל | I-13/route |
| 13:05 | **ZLR-UP** | S4 | ✅ `zlr=UP` (BLUE) | 7357.5 | 7342.25 | 7380.4 | **+1.5R** ✅T1 | כנ"ל | I-13/route |
| 13:15 | **ZLR-UP** | S4 | ✅ `zlr=UP` (BLUE) | 7365.75 | 7346.75 | 7394.25 | **+1.5R** ✅T1 | כנ"ל | I-13/route |
| 13:45 | **ZLR-UP** | S4 | ✅ `zlr=UP` (BLUE) | 7377.25 | 7364.5 | 7396.4 | **+1.5R** ✅T1 | כנ"ל | I-13/route |
| 13:50 | ZLR-UP | S4 | ✅ `zlr=UP` (BLUE) | 7378.5 | 7364.75 | 7399.1 | −1R (stop) | פסגת-הרגל, entry מאוחר | — |
| 13:55 | ZLR-UP | S4 | ✅ `zlr=UP` (BLUE) | 7389.5 | 7372.75 | 7414.6 | −1R (stop) | פסגת-הרגל (CCI 121, extended) | — |
| 14:35 | ZLR-DOWN | S4 | ✅ `zlr=DOWN` (GRAY) | 7357.75 | 7372.25 | 7336.0 | −1R (stop) | trend=GRAY → לא-איכותי, אי-ירי **רצוי** | — |
| 14:50 | ZLR-UP | S4 | ✅ `zlr=UP` (GRAY) | 7383.75 | 7347.25 | 7438.5 | +0.03R (timeout) | trend=GRAY (risk 36נק') | — |
| 14:55 | ZLR-UP | S4 | ✅ `zlr=UP` (GRAY) | 7391.75 | 7352.5 | 7450.6 | −0.17R (timeout) | trend=GRAY | — |
| 15:00 | ZLR-UP | S4 | ✅ `zlr=UP` (GRAY) | 7399.0 | 7382.0 | 7424.5 | −0.82R (timeout) | trend=GRAY (פסגה) | — |
| 15:15 | ZLR-UP | S4 | ✅ `zlr=UP` (BLUE) | 7383.25 | 7382.75 | 7384.0 | −1R (stop) | **risk=0.5נק' → סטופ מנוון (I-3)** | I-3 |

**`/api/v9/missed-trades`** = **50 candidates**, כולם `type=blocked_signal · ZLR · S4 · LONG`,
`why_not="ready_to_route=False"`, חלון **15:20–15:22 CT** בלבד (buffer מתגלגל cap=50, `hypothetical_r=null`).
אלה ה-ZLR-LONG של **אחרי-הסגירה ב-GRAY** — נגד-trend-נקי, אי-הירי שלהם **תקין**. הבאפר **אינו** מכיל את
ה-cluster של 12:50–13:45 (BLUE) — ולכן ה-gate המדויק שלהם **לא נלכד** (ראה פער #2 למטה).

---

## סיכום כמותי

- **signals שזוהו-ולא-ירו (חלון 11:15–15:20):** **13** (כולם ZLR/S4; 0 HFE-flag).
- **תוצאות replay:** 5×T1 · 5×stop · 3×timeout · **ΣR(הכל) ≈ +1.54R** · **ΣR(trend-aligned) ≈ +3.50R**.
- **ה-setup האיכותי שפוספס היום = ה-cluster של ZLR-UP ברגל-ה-BLUE 12:50→13:45:** 5 signals, **5/5 →T1 = +7.5R גרוס**
  (כולם trend=BLUE, CCI 77–111, סטופים-הדוקים 12–19נק'). זו הרגל הנקייה היחידה שזוהתה-ולא-נותבה.
- **עסקאות שכן ירו (בוקר, מחוץ-לחלון):** **2 shadow** — S4 HTLB (+106נק', תפסה את ה-down-drive) + S2 BEAR_FLAG
  (scratch ב-breakeven; exit-logic קטע ≈+66נק').
- ה-stops של 11:35 (53נק') ו-15:15 (0.5נק') הם **מנוונים (I-3)** — ה-−1R שלהם רעש, לא setup-אמיתי שפוספס.
- ה-ZLR ב-GRAY (14:35–15:00) — אי-הירי שם **רצוי** (אין trend נקי ביום Variation conf=38).

### פירוק לפי gate
| gate / blocked_by | כמה | מקור-ראיה | סטטוס |
|-------------------|-----|-----------|-------|
| `ready_to_route=False` (S4, ZLR-LONG post-close) | 50 buffer | `/api/v9/missed-trades` `why_not` | **תקין** — GRAY/נגד-trend אחרי-סגירה, לא תקלה |
| BLUE-cluster ZLR-UP 12:50–13:45 — נותב? לא-נלכד | 5 (+5.5R נטו) | woodies flags; **באפר לא מכסה** | **פתוח** — צריך S4 route-log מ-CC לאותם ברים |
| סטופ מנוון (risk 0.25–0.5נק') | #20,#22,11:35,15:15 | `/trades/recent` + replay | **פתוח (I-3)** — סטופ≈entry; ה-bottleneck המרכזי |
| exit-logic scratch (BEAR_FLAG breakeven) | 1 (#22) | `/trades/recent` exit=entry | **פתוח** — יציאה-שטוחה קטעה רווח-המשך |
| S2 5-Min fires | 1 (#22 ירה) | `/trades/recent` | פעיל (לעומת 0 אתמול) |

**הערה על choppiness:** לפי Standing Decisions (CLAUDE.md 2026-06-08) **שני שערי-ה-chop כבויים** + **COT/AMT לא נדרש**
(S2⟂S3). לכן אי-ירי ה-cluster של 12:50–13:45 **אינו** choppiness. ה**חוסם המוביל** היום הוא **I-3 (סטופ/target מנוון)** —
הוא שנגע בשתי העסקאות שכן ירו (סטופ≈entry) ובשני ה-signals המנוונים — ולא חסימת-route.

---

## שורת-BENCHMARK (5 העסקאות של Michael, ground-truth מ-MISSED_TRADES_ANALYSIS_2026-06-05)

ה-benchmark הוא ground-truth של **06-05** (8:35–10:00 CT, כולן SHORT/reversal ב-open יורד). היום 06-09 הבוקר
היה גם הוא **OPEN_DRIVE יורד** (7489→7383, ‎−106נק' עד 10:20) — מבנה **דומה** ל-benchmark, אך הדאטה החי לא מכסה
08:30–10:05 כך שאימות-בר-לבר אינו אפשרי.

| # | שעה(CT) | סוג benchmark | אותר/ירה היום? | הערה |
|---|---------|---------------|-----------------|------|
| 1 | 8:35 | REVERSAL (S2/FHB) | ❓ אין-דאטה | חלון signal מתחיל 11:15 CT |
| 2 | 9:00–9:05 | LONG טקטי (S2) | ❓ אין-דאטה | — |
| 3 | 9:20 | SHORT (S2/S4) | 🟡 **חלקית** | S4 HTLB **ירה** 08:50 SHORT והוחזק עד 10:20 — מכסה את חלון השורטים 9:20–10:00 |
| 4 | 9:35 | SHORT (S2/S4) | 🟡 כנ"ל (אותה החזקה) | |
| 5 | 10:00 | SHORT (S2/S4) | 🟡 יצאה 10:20 | יציאת ה-HTLB ב-10:20 @ 7383 ≈ benchmark #5 |

**benchmark: ~1/5 אותרו-וירו ישירות** (S4 HTLB short כיסה את ה-window של trades 3–5). trades 1–2 (8:35 reversal,
9:00 long) — **לא ניתן לאמת** (פער-חלון-export). **שיפור מ-06-08** (אז 0/5, כי 0 עסקאות + מבנה-בוקר הפוך).
**המלצה ל-CC (חוזרת):** הרחב `woodies`/`bars5min` export ל-≥80 ברים מ-08:30 CT לאימות-benchmark אמיתי בבוקר.

---

## פערים פתוחים שזוהו בריצה זו (סימון ל-CC)
1. **I-3 (סטופ/target מנוון)** — ה-bottleneck המוביל: סטופ≈entry בשתי העסקאות שירו (#20: 7489 vs 7489.25; #22: ok)
   וב-signals 11:35/15:15. ה-HTLB תפס +106נק' אבל עם סטופ 0.25נק' → R לא-מוגדר; ה-BEAR_FLAG יצא breakeven.
2. **חלון export = 50/80 ברים** → לא מכסה בוקר-RTH (08:30–11:10) → אי-אפשר benchmark-בוקר. בקשה: ≥80 ברים מ-08:30.
3. **`missed-trades` buffer רדוד** (cap=50, מחזיק רק 15:20–15:22) → לא לוכד את ה-gate של ה-cluster 12:50–13:45.
   בקשה: שמירת `why_not` היסטורי לכל signal-בר (לא רק 3 הברים האחרונים).
4. **bars5min ברים עתיד-מתוארכים** (06-10 22:40 IDT) — **I-15/I-18 חי**. הצלבת Sierra חובה.
5. **exit-logic scratch** (#22 BEAR_FLAG יצא ב-entry בדיוק) — חוקר אם זו יציאה-לספק/breakeven-stop שקוטעת המשך-רגל.
6. **I-23** (counters לא סופרים shadow fires) + **I-25** (`limit=200`→422, תקרה 100) — אומתו עצמאית בריצה זו.

*אנליזה בלבד — לא שונה קוד. `MEMS26_ISSUES_REGISTER.md` עודכן בבלוק-יומן מתוארך. ROADMAP/STATUS_BOARD לא נגעו
(אין שינוי-קוד/phase-gate בריצה זו).*
*מקורות API (localhost:8000): `/api/v9/woodies/chart?limit=80` (50 ברים), `/api/v9/chart/bars5min?limit=80`,
`/api/v9/trades/recent`, `/api/v9/build/pattern-status`, `/api/v9/day_type/current`, `/api/v9/missed-trades`.*
