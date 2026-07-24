# CC-MACBOOK — בניית-לילה לקראת מסחר 07-24 (פסיקת-מייקל 07-23: "שלושתם — #1→#3→#2")

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`** (anti-tautological · Rule-5 · NOT-DONE חובה).
**פסיקה:** מייקל 07-23 ערב — לבנות שלושה תיקונים, כל אחד flag-gated OFF → verify → cowork מאמת בבוקר ומדליק לפי הפסיקה. **אל תדליק בעצמך.**
**רקע-היום (07-23):** טרנד-יורד 7524→7411. המערכת ירתה שורטים בשפל (479 @7423.5 שפל-7411 · 481 ZLR @~7420 בתחתית) במקום בשיא-התיקון (7486 ב-16:40), וההפסדים נבעו גם מאי-מעבר-סטופ-ל-BE. יומי-לייב ‑$300.
**⚠ יש עכשיו שורט-לייב עירום ‑9 @7430.08 שמייקל פסק להשאיר (22:35) — אל תיגע בפוזיציה/פקודות-חיות. עבודת קוד בלבד, הכל flag-OFF.**

---

## Phase 0 — תיקון-מפתח קריטי (עצמאי, קטן)
`sierra_state.json` מכיל `position_qty` — אבל קוראים שונים בדקו `position_quantity` (שגוי → None → "flat" כוזב; cowork נפל על זה הערב וגם הדריל P8). **חובה:** `grep -rn "position_quantity" backend/ scripts/ --include="*.py"` — תקן כל קורא לקרוא `position_qty` (עם fallback ל-position_quantity אם קיים איפשהו ישן). AC: grep מחזיר 0 מופעים לא-מטופלים + טסט קטן שקורא את הקובץ האמיתי-פורמט.

## Phase 1 — 🔴 root-diagnose: למה Smart-BE לא רץ על 479 (לפני כל בנייה!)
**אבחון-לפני-תיקון (Pre-LIVE).** המנגנון קיים ומודלק: `BE_AFTER_REAL_T1_V1=1`, `ZLR_MGMT_V1=1`, `STOP_STRUCTURE_TRAIL_V1=1`; `_apply_smart_be_after_t1` (manager.py:~640) נקרא מ-on_target_hit T1 (line 541) ופולט MODIFY_STOP. **אבל על 479 (T0-fill 18:28 → real-T1-fill 18:30) אין בלוג אף שורת `Smart BE`/`SMART_BE`/`T0-remap`/`MODIFY_STOP` (0 בכל err.log), ואין `[FillPoller] T1 fill` — ובכל-זאת ה-DB עודכן (t1_hit, PnL).** מצא איפה השרשרת נשברת: (א) האם fill_poller באמת עיבד את ה-fills או שה-DB עודכן מנתיב אחר? (ב) האם ה-T17-remap שלח את ה-fill-השני ל-T1 והקריאה ל-_apply_smart_be_after_t1 זרקה חריגה שנבלעה? (ג) האם `_is_demo_mode(trade)` מחזיר False ל-mode='live' (שער ההפליטה ב-_emit_modify_stop:220) — קרא את המימוש! חשד-עיקרי: השם מרמז demo-only. (ד) 481=ZLR — למה גם ה-ZLR-BE (branch line 656) שתק? **תקן את השורש** (flag-gated אם משנה-התנהגות; אם זה באג-הפליטה ל-live — זה תיקון-באג להתנהגות שכבר נפסקה [ZLR-BE 07-14 + smart-BE קיים] → מותר לתקן ישר, עדיין OFF-אם-דגל-חדש). AC: טסט שמזרים T0+T1 fills על trade-mode=live ומוכיח פקודת MODIFY_STOP נכתבת עם stop=BE; "if reverted → RED because ___".

## Phase 2 — בניית #1: EXTREME_CHASE_GUARD_V1 (שער-גייטוויי, S2+S4)
דגל `EXTREME_CHASE_GUARD_V1` (default OFF). בגייטוויי (נקודת-חנק יחידה, ליד שאר השערים ב-route_fire): לפני אישור כניסה כיוונית —
- **מרחק-מקיצון:** SHORT רק אם `entry ≥ session_low + EXTREME_MIN_DIST_PTS` (default 6.0); LONG סימטרי מול session_high. session_low/high מ-RTH bars של היום (v9_bars_5min_woodies מאז 16:30-IL / דרך ה-tpo-context אם קיים day_low/day_high).
- **פולבק:** SHORT רק אם באחד מ-3 הברים האחרונים היה bounce-up ≥ `PULLBACK_MIN_PTS` (default 3.0) מהשפל (high של בר אחרון ≥ session_low + pullback); סימטרי ללונג.
- fail-open על חוסר-נתונים (אין ברים → אין חסימה). חל על משפחות המשך/יוזמה (INITIATIVE/ZLR/CONT) — REACTIVE כבר מכוסה ע"י RESPONSIVE_WITH_DAY_TREND_V1 (chasing-branch שלו).
AC: replay — 479 (SHORT @7423.5, שפל-נוכחי 7418, אין-פולבק) → BLOCKED; 481 (@7420 בשפל) → BLOCKED; שורט היפותטי @7466 אחרי שיא-7486 (מרחק-מהשפל גדול + פולבק) → ALLOW. טסטים + "if reverted → RED".

## Phase 3 — בניית #2: OPENING_TYPE_SEEDS_S1_V1 (סוג-פתיחה מניע S1 ב-15 דק')
דגל `OPENING_TYPE_SEEDS_S1_V1` (default OFF). לפי ה-spec הקבוע (S1 staging: opening_type@15min): בתוך 15 הדק' הראשונות של RTH, אם (א) נפתחנו מובהקות מעל/מתחת ל-value-אתמול (VAH/VAL קנוניים) או (ב) תנועת-פתיחה חד-כיוונית ≥ סף — S1 זורע מיד הטיית-יום (Trend-down-bias / Trend-up-bias) שנכנסת ל-`get_live_day_type`/`dir_bias` consumers, **נעולה escalation-only עד IB-lock** (אין קרטוע Variation↔Trend כל בר — היום קרטע 8×). זה נותן לזרועות כיוון בזמן-השיא-של-הפתיחה (היום: 16:40, כשעדיין UNKNOWN עד 17:00).
AC: replay ברי-היום — עד 16:45 ההטיה=DOWN (נפתחנו אחרי ‑74 לילי מתחת לערך); אסור flip אחרי הזריעה עד 17:30 אלא escalation. טסטים + revert→RED. **אם ההיקף גדול מדי ללילה — בנה את הזריעה בלבד ותשאיר את איחוד-הצרכנים כ-NOT-DONE מפורט.**

## Phase 4 — אימות-כולל
`pytest tests/v9/regression -q` (כל הסלקציה הירוקה הקיימת נשארת ירוקה) · flag_guard PASS (הדגלים החדשים לא ב-RULED עדיין — cowork יוסיף בהדלקה) · `gen_flag_index.py` + FLAG_REGISTRY entries · דוח לפי חלק-C של החוזה (טבלת phases + evidence + NOT-DONE) → `docs/reports/CC_OVERNIGHT_3FIXES_REPORT_2026-07-24.md` · commit+push · שורה ב-LIVE_CHANNEL.

**סדר: 0 → 1 → 2 → 3 → 4.** אם הזמן קצר — 0+1+2 הם החובה למחר; 3 יכול להיות חלקי עם NOT-DONE.


## Phase 5 (נוסף 23:35 — פסיקת-מייקל "מערכת-ירי סוג-פתיחה"): endpoint+פרונט+חלון-60
לפי `docs/plans/OPENING_FIRE_SYSTEM_PLAN_2026-07-23.md`:
1. **תקן `api/v9/open_type_routes.py`:** קורא v9_bars_5min (טבלה מזוהמת — הפרת-SoT) → `v9_bars_5min_woodies`; הסר את טריגר-10:00-בלבד — תצוגה מדורגת מ-16:35 IL (עדכון כל בר עד 17:30, ואז נעילה). השתמש ב-opening_detector_v2 (לא הישן).
2. **פרונט:** chip "Open type" בפאנל-הצד **מעל לשונית מערכת-2** — סוג+כיוון+confidence, צבע לפי כיוון, "PENDING" לפני 16:35. ניזון מ-`/api/v9/open_type/current`, polling **15000ms** (רצפות-P30 — אסור מהיר-יותר). קומפוננטה קטנה, אל תיגע בקיים.
3. **הרחב `opening_entry.py` לחלון-60-דק'** (ברים 2-12, WINDOW_LAST_BAR=12) + כניסת **PULLBACK-CONT** חדשה (פולבק ≥33% מהמהלך + בר-דחייה → כניסה עם-הכיוון, סטופ מאחורי קיצון-הפולבק 16T, T1=1.5R) — הכל תחת flag חדש `OPENING_FIRE_V1` (default OFF; כשכבוי — התנהגות-30-דק' הקיימת byte-identical). טסטים: replay 07-23 חייב לתפוס שורט-פולבק ~7466-7470 אחרי דחיית-7486; revert→RED.
