# חוקר עסקאות-שלא-בוצעו · 2026-06-08 (ריצה אוטונומית — Cowork)

**שער-זמן:** America/Chicago = **15:20 CDT** בעת הריצה → RTH סגור, ממשיכים.
**מצב יומי (מאומת מ-`/api/v9/day_type/current`):** `day_type=Variation` · confidence **38** (נמוך) ·
opening **OPEN_DRIVE** · IB **7429–7469.5** (range 40.5, WIDE) · stage C3.
**עסקאות שירו היום (`/api/v9/trades/recent`):** **0** (העסקה האחרונה במערכת היא מ-2026-06-05).

> ⚠️ **מגבלת-דאטה קריטית (מקור-אמת):** ה-export החי של Woodies (`/api/v9/woodies/chart`) מחזיק
> **50 ברים בלבד** — חלון **11:15→15:20 CT**. **אין נתוני CCI/ZLR/HFE/trend לבוקר (08:30–11:10 CT).**
> לכן הניתוח-מעוגן-signal מכסה רק את חצי-היום השני. לבוקר קיים רק OHLCV (`/api/v9/chart/bars5min`).
> זה מדווח ככשל-כן (Rule 1) ולא מסונתז. **הצלבת Sierra ל-CCI עדיין חובה — סימון ל-CC.**

---

## טבלת ה-setups — lookback מתגלגל 6-ברים (חלון signal 11:15–15:20 CT)

החוק: SHORT → entry=close הבר, stop=max(high הבר, high הקודם)+tick, risk=stop−entry,
T1=1.5R, T2=2.5R, replay קדימה עד hit-stop / hit-T1 / סוף-סשן (timeout = mark-to-last).

| זמן(CT) | תבנית(שלנו) | מערכת | זוהה?(flag) | entry | stop | T1 / T2 | R-נגד | gate-שחסם | I-# |
|---------|-------------|-------|-------------|-------|------|---------|-------|-----------|-----|
| 11:30 | **ZLR-DOWN** | S4 | ✅ `zlr=DOWN` | 7441.75 | 7457.25 | 7418.5 / 7395.5 | **+1.5R** ✅T1 | ready_to_route=False | I-13/I-14 |
| 11:55 | **ZLR-DOWN** | S4 | ✅ `zlr=DOWN` | 7441.5 | 7449.75 | 7429.1 / 7420.9 | **+1.5R** ✅T1 | ready_to_route=False | I-13/I-14 |
| 12:00 | **CLEAN-DOWNLEG** | (אף-תבנית) | ❌ no flag | 7429.75 | 7447.5 | 7403.1 / — | +1.08R (timeout) | תנועה-נקייה שאף detector לא תפס | I-14/TCCI |
| 12:35 | ZLR-DOWN | S4 | ✅ `zlr=DOWN` | 7434.25 | 7446.75 | 7415.5 | −1R (stop) | ready_to_route=False | I-13 |
| 12:40 | ZLR-DOWN | S4 | ✅ `zlr=DOWN` | 7426.25 | 7439.75 | 7406.0 | −1R (stop) | ready_to_route=False | I-13 |
| 12:55 | ZLR-DOWN | S4 | ✅ `zlr=DOWN` | 7433.75 | 7440.0 | 7424.4 | −1R (stop) | ready_to_route=False | I-13 |
| 13:25 | ZLR-UP (long) | S4 | ✅ `zlr=UP` | 7442.0 | 7434.75 | 7452.9 | −1R (stop) | ready_to_route=False | I-13 |
| 13:35 | **CLEAN-DOWNLEG** | (אף-תבנית) | ❌ no flag | 7432.0 | 7447.5 | 7408.75 / — | **+1.5R** ✅T1 | leg-יוזמה חד (CCI +131→−36) שאף תבנית לא תפסה | I-14/TCCI |
| 14:10 | CLEAN-DOWNLEG | (אף-תבנית) | ❌ no flag | 7414.75 | 7434.5 | — | +0.18R (timeout) | extreme-bottom, אין המשך | — |
| 14:50 | ZLR-DOWN | S4 | ✅ `zlr=DOWN` | 7414.75 | 7422.5 | 7403.1 | +0.45R (timeout) | ready_to_route=False | I-13 |
| 14:55 | ZLR-DOWN | S4 | ✅ `zlr=DOWN` | 7415.5 | 7422.5 | 7405.0 | +0.61R (timeout) | ready_to_route=False | I-13 |
| 15:10 | ZLR-DOWN | S4 | ✅ `zlr=DOWN` | 7413.25 | 7419.25 | 7404.3 | +0.33R (timeout) | ready_to_route=False | I-13 |
| 15:15 | ZLR-DOWN | S4 | ✅ `zlr=DOWN` | 7411.25 | 7418.0 | 7401.1 | 0R (timeout) | ready_to_route=False | I-13 |

**גם 50 candidates ב-`/api/v9/missed-trades`** = כולם **HFE / S4 / LONG**, `why_not="ready_to_route=False"`,
חלון 14:23–14:25 CT (buffer מתגלגל, cap=50, `hypothetical_r=null`). אלה ה-hooks-מ-extreme (bounce
נגד-מגמה מ-CCI −243) — איכות-נמוכה, נגד-trend, ולכן **אי-הירי שלהם תקין**.

---

## סיכום כמותי

- **setups שזוהו-ולא-ירו (חלון signal):** 13 · מתוכם **9 זוהו ע"י detector (S4)** + **4 תנועות-נקיות שאף תבנית לא תפסה**.
- **תוצאות replay:** 3×T1 · 4×stop · 6×timeout · **ΣR ≈ +3.63R** (timeout = mark-to-last).
- **setups-איכות שפוספסו (trend-aligned, חיוביים):** **3** → 11:30 ZLR-DOWN (+1.5R), 11:55 ZLR-DOWN (+1.5R),
  13:35 CLEAN-DOWNLEG (+1.5R) = **+4.5R פוטנציאל פוסם**.
- ה-stops של 12:35/12:40/12:55 הם **chop של תחתית** ביום Variation (conf 38) — אי-הירי שם **רצוי**, לא תקלה.

### פירוק לפי gate
| gate / blocked_by | כמה setups | מקור-ראיה | סטטוס |
|-------------------|-----------|-----------|-------|
| `ready_to_route=False` (A-layer routing, S4) | 9 + 50 buffer | `/api/v9/missed-trades`, `why_not` | **פתוח** — שרשרת signal→route חסומה ל-S4 |
| אין-תבנית (CLEAN-DOWNLEG, gap-detector) | 4 | replay על woodies bars | **פתוח** — אין detector ל-leg-יוזמה ללא ZLR/HFE |
| S2 5-min: 0 fires כל היום | 10 תבניות | `/api/v9/build/pattern-status` | post-close=`Missing: data.mode_context` (OVERNIGHT_MODE); intraday לא ניתן לשחזר מ-snapshot סגור |

**הערה על choppiness:** לפי ה-Standing Decisions (CLAUDE.md, 2026-06-08) **שני שערי-ה-chop כבויים**
(`S2_CHOPPINESS_GATE` + `LAYER0_CHOP_GATE`) וגם **COT/AMT לא נדרש** (S2⟂S3). לכן ההיעדר-ירי של S4 היום
**אינו** choppiness — הוא `ready_to_route=False` (שרשרת routing/sizing, I-13/I-14). זה ה**חוסם המוביל**.

---

## שורת-BENCHMARK (5 העסקאות של Michael, ground-truth מ-MISSED_TRADES_ANALYSIS_2026-06-05)

| # | שעה(CT) | סוג benchmark | אותר היום? | למה לא |
|---|---------|---------------|------------|--------|
| 1 | 8:35 | REVERSAL (S2/FHB) | ❌ אין-דאטה | חלון signal של היום מתחיל 11:15 CT — **אין CCI/ZLR/HFE לבוקר** |
| 2 | 9:00–9:05 | LONG טקטי (S2) | ❌ אין-דאטה | כנ"ל (קיים רק OHLCV) |
| 3 | 9:20 | SHORT (S2/S4) | ❌ אין-דאטה | כנ"ל |
| 4 | 9:35 | SHORT (S2/S4) | ❌ אין-דאטה | כנ"ל |
| 5 | 10:00 | SHORT (S2/S4) | ❌ אין-דאטה | כנ"ל |

**benchmark: 0/5 אותרו בדאטה החי של היום** — לא בגלל gate אלא בגלל **פער-חלון-export** (woodies מחזיק 50 ברים
בלבד). בנוסף, מבנה-הבוקר של **היום** הפוך מ-06-05: 08:30→10:05 **עלה** 7445→7474 (לא ירידת-הפתיחה של
ה-benchmark), כך שה-setups של 06-05 ממילא לא חוזרים זהים היום. **המלצה ל-CC:** הרחב את חלון ה-woodies export
ל-≥80 ברים (כיסוי מלא של RTH מ-08:30) כדי לאפשר אימות-benchmark אמיתי בבוקר.

---

## פערים פתוחים שזוהו בריצה זו (סימון ל-CC)
1. **`ready_to_route=False`** חוסם 100% מ-signals-S4 (ZLR+HFE) — שרשרת signal→route. נתיב לאבחון: A1/sizing/day_type. (I-13/I-14)
2. **חלון woodies-export = 50 ברים** → לא מכסה בוקר-RTH → אי-אפשר benchmark-בוקר. בקשה: ≥80 ברים.
3. **אין gap-detector** ל-leg-יוזמה נקי ללא ZLR/HFE (2 setups חיוביים פוספסו: 12:00, 13:35). (I-14/TCCI)
4. **freshness שלילי נמשך:** `data_freshness.lag_seconds=-7229`, `fresh=true` (`/api/v9/build/pattern-status`). (I-20/I-24)
5. **footprint** disabled (S3_MUTE) — צפוי לפי standing decision, לא תקלה.

*אנליזה בלבד — לא שונה קוד. ROADMAP/STATUS_BOARD לא נגעו (אין שינוי-קוד/phase-gate בריצה זו).*
*מקורות API: `/api/v9/woodies/chart`, `/api/v9/chart/bars5min`, `/api/v9/trades/recent`, `/api/v9/build/pattern-status`, `/api/v9/missed-trades`, `/api/v9/day_type/current` (localhost:8000).*
