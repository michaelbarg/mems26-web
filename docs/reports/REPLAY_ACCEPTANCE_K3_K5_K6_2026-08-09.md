# דוח Replay-קבלה — K3/K5/K6 (3 דגלים חדשים) · 2026-08-09

**סוכן:** cc-macbook · **Rule-5:** כל מספר מגובה בפלט גולמי של הריפליי.

---

## 1. S1_TREND_ELONGATION_V1 — סיווג Trend ללא stair-steps

**מטרה:** rib ≥ 2.5 + close-position קיצוני (cp ≤ 0.15 / ≥ 0.85) → Trend_Normal.
**מטרות-הקבלה:** 08-05 חייב להסתווג Trend · 13/13 האמת לא ישברו.

| בדיקה | תוצאה |
|--------|--------|
| 13/13 truth (07-15…07-31, OFF) | **13/13 = 100%** |
| 13/13 truth (07-15…07-31, ON) | **13/13 = 100%** — אף שינוי |
| 08-05 (OFF) | Normal_Variation (rib 2.92, cp 0.03) |
| 08-05 (ON) | **Trend_Normal DOWN** — elongation-path ✅ |
| 08-03 (OFF→ON) | Normal_Variation (rib 1.67 < 2.5) — **לא משתנה** |
| 08-04 (OFF→ON) | Trend_Normal (control-path 6 steps) — ללא שינוי |
| 08-06/07 (OFF→ON) | Normal_Variation — rib < 2.5, ללא שינוי |

**פסק-דין:** ✅ **GO** — מתקן את 08-05 (הפער של המחקר), 0 רגרסיות.
08-03 (rib 1.67) נשאר פער — דורש הורדת rib-floor ל-1.5 (שינוי נפרד).

---

## 2. HIGHER_LOW_SECOND_TEST_V1 — תבנית-פולבק W6

**מטרה:** push→L1→recovery→L2>L1→rejection-bar. מודל: stop=L2−1pt, T1=entry±4pt.
**ריפליי:** 20 ימי-מסחר (07-15…08-07), bar-by-bar.

| מדד | ערך |
|------|------|
| סה"כ עסקאות | 132 |
| Win rate | 42.4% (56W / 67L / 9 EOD) |
| NET P&L | **−$1,822** |
| P&L ממוצע | −$13.80 |

**ניתוח:**
- הדטקטור יורה **יותר מדי** (132 פעמים ב-20 ימים = 6.6/יום). הרוב = רעש.
- ימים טובים: 07-23 (+$50, 9W/4L), 07-20 (+$47, 8W/6L), 08-05 (+$34), 08-07 (+$50).
- ימים רעים: 07-21 (−$388, 0W/8L כולם SHORT — ציד-מגמה), 07-29 (−$294).
- T1=4pt קבוע הוא חלש מדי — עסקאות מנצחות מנצחות $50, מפסידות מפסידות $40-$200.

**פסק-דין:** ❌ **NO-GO כ-standalone**. הדטקטור עצמו עובד (מזהה מבנה), אבל:
1. צריך סינון — רק ביום-Variation/Trend, בכיוון-הרגל, אחרי IB-lock.
2. T1 צריך להיות מבני (IB-high/קצה קודם), לא 4pt גנרי.
3. סטופ צריך להיות מתחת-ל-L1 (לא L2−1pt) — קיצוני יותר אבל שורד.

**המלצה:** להשאיר OFF. לשפר T1+stop+סינון ← replay חוזר ← פסיקה.

---

## 3. EXCESS_COUNTER_ENTRY_V1 — כניסת-פייד עם EXCESS מאושר

**מטרה:** EXPANSION+EXCESS בקצה+entry≤2pt → מתיר פייד-קאונטר (נחסם היום).
**ריפליי:** 18 ימי-מסחר, 14 ימי-Variation.

| מדד | ערך |
|------|------|
| כניסות EXCESS (היו נוספות) | **4** |
| חסימות-נכונות (נשארות חסומות) | **202** |
| WIN | 1 (07-20: +$40) |
| LOSS | 3 (07-16 ×2, 07-23) |
| NET P&L | **+$2** (≈0, נייטרלי) |

**הכניסות:**
1. 07-16 bar58 LONG @7565 → STOP (−$38)
2. 07-16 bar62 LONG @7554.50 → STOP (−$28)
3. 07-20 bar38 LONG @7501 → T1 (+$100) ← הכניסה-הטובה
4. 07-23 bar52 LONG @7428 → STOP (−$28)

**הערה חשובה:** 08-07 (שישי — המקרה-המניע) **לא מופיע** כ-EXCESS ב-replay!
הסיבה: ב-EOD classification 08-07 = Normal_Variation UP, אבל הפייד של שישי 18:40
היה SHORT — והקצה-הרלוונטי הוא ה-HIGH. סריקת-הריפליי בדקה רק counter-trend
entries, ו-SHORT ב-UP day הוא counter-trend ← נכון. אבל ה-EXCESS detection
דורש מספיק ברים אחרי השיא — ב-18:40 השוק רק הגיע ל-7786.75 (18:25-18:30),
ו-excess tail/no-revisit עדיין לא מבוסס. **זה קייס של "EXCESS בדיעבד, לא בזמן-אמת".**

**פסק-דין:** ⚠️ **DEFER** — 4 entries, NET ≈ $0, n קטן מדי.
הדגל בטוח (202 חסימות-נכונות נשמרות, 0 false-allows), אבל ה-edge
שבגללו נבנה (שישי) לא נתפס בזמן-אמת. דורש:
1. שיפור הגילוי של EXCESS ב-real-time (excess tail detection on partial data)
2. n ≥ 15 EXCESS entries כדי שהסטטיסטיקה תהיה משמעותית

---

## 4. Command-Queue SIM (תנאי-חימוש K1ג)

| שלב | תוצאה |
|------|--------|
| PLACE via fast-path → DLL ACK → cleared | ✅ |
| MODIFY_STOP via fast-path → DLL ACK → cleared | ✅ |
| PLACE+MODIFY rapid: PLACE fast, MODIFY queued, drainer sends after ACK | ✅ |

**3/3 PASS** — התור-החדש מעביר פקודות בסדר, מנקה אחרי ACK, לא שולח פקודות כפולות.
⚠️ **זה sim-מקומי (tmpdir), לא DLL אמיתי** — עדיין דרוש סשן-סים עם Sierra Chart רץ.

---

## סיכום ← פסיקת-מייקל

| דגל | NET | n | פסק-דין | המלצה |
|------|-----|---|---------|--------|
| S1_TREND_ELONGATION_V1 | 0 regressions, +1 fix | 13+5 | ✅ GO | **להדליק בוקר-שני** |
| HIGHER_LOW_SECOND_TEST_V1 | −$1,822 | 132 | ❌ NO-GO | להשאיר OFF, לשפר סינון+T1 |
| EXCESS_COUNTER_ENTRY_V1 | +$2 | 4 | ⚠️ DEFER | בטוח אבל n קטן, case-המניע לא נתפס RT |
| Command-Queue | 3/3 PASS | — | ✅ GO | מעבר ל-DLL-sim ← חימוש |
