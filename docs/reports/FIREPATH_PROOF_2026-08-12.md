# FIREPATH PROOF — רפליי 35 האיתותים של 08-11 תחת הקונפיג החי של 08-12

**סוכן:** firepath-proof-agent (READ-ONLY — 0 שינויי קוד/דגל/ריסטארט) · **זמן:** 2026-08-12 ~15:50 IL, לפני פתיחת 16:30
**שאלת מייקל:** "להוכיח שמה שקרה אתמול (35 איתותים אמיתיים, כולם נחסמו, אפס עסקאות) לא יכול לחזור היום."

---

## 0. השורה התחתונה — בקול רם

**התשובה הכנה: זה כן יכול לחזור — וברפליי קפדני זה חוזר: 0 מתוך 35 יורים גם תחת הקונפיג של היום.**
השער החוסם זז: אתמול `extreme_chase_guard` (tip-revocation); היום — **`rr_entry_gate` × סולם-המדרגה F3** שהודלק הבוקר 08:09.

- **מה כן תוקן באמת:** ביטול-הפטור מת-בקוד — כל 14 חסימות-הרדיפה של אתמול **עוברות היום את שער-הרדיפה** (מוכח מהלוגים של אתמול עצמם: הפטור נִתן 14/14 — LEG_RIDE×6, TREND-BYPASS×8 — ורק ה-revocation ביטל; ההוכחה: `/tmp/backend.err.log` שורות 18:15–19:25 IL).
- **מה הורג אותם עכשיו:** F3 בונה סטופ 4pt (רצפה) עם T1 = 0.5×מדרגה. המדרגה-החציונית האמיתית של אתמול (פונקציית-הייצור `compute_median_session_step`, לא הערכה) = **2.0–3.0pt לשורט** — לא 10.4 — ⇒ T1 = 1.0–1.75pt ⇒ **RR שער = 0.25–0.44 < 0.65** ⇒ `rr_entry_gate` חוסם את כל 10 השורדים.
- **מתמטיקה קשיחה:** תקרת ה-RR של הסולם = 0.5/0.6 = **0.833 לנצח** ⇒ על תווית `Trend_*` (rr_min=1.0) הסולם **לא יכול לעבור את שער-ה-RR אף פעם**. על תוויות-רוטציה (0.65) נדרשת מדרגה ≥ 5.2pt.
- **שלישיית ה-+$540 (awaiting_release):** גם עם סף-12 החדש — **0 מתוך 3 יורות היום**: 10:40+10:45 נהרגות מוקדם יותר ב-`ZLR SKIP on Normal` (היפוך-פלייבוק F4, conf=1.0), ו-10:25 נשארת ב-release (תזוזת-close −11.5 < 12, פספוס של 0.5pt).

---

## 1. שיטה (Rule-5: ניתן-לשחזור)

- **איתותים:** הארכיון האמיתי `~/SierraChart_Data/v9_export/decisions_archive/gateway_decisions.2026-08-11.jsonl`
  (הקובץ שבמשימה — `gateway_decisions_until_0812.jsonl.bak` — הוא **כולו** 510 שורות-pytest מ-07:00, trade_id=t1..t5/T-TEST; אומת ונפסל).
  44 שורות 08-11 (אחרי סינון fixtures entry=7600) → דדופ `(בר, מערכת, תבנית, כיוון)` → **35 ייחודיים** — זהה ל-QUALITY_BLOCKS §3.
- **קונפיג היום = אמת-קרקע מאומתת:** `.env` הנוכחי (235 שורות; diff מול snapshot 08-11: scope CONT+REV→CONT · +LEG_EXEMPT_LSMA_FLAT_V1=1 · +RELEASE_TREND_BYPASS_PTS=12 · +STEP_SCALED_LADDER_V1=1) + `config/daytype_playbook.yaml` (F4) + קוד ה-gateway הנוכחי. התהליך הרץ PID 89926 עלה 08:09:42 **אחרי** snapshot `enable-step-ladder` ⇒ הכול טעון (env_loader "applied 222 vars"; uptime 7.6h; `flag_guard.py` → **PASS — all 166 ruled flags match**).
- **תוויות סוג-יום פר-בר:** `v9_day_type_state` (ts גולמי=UTC; מעוגן מול שתי התוויות שנרשמו בהחלטות עצמן — Normal@16:40Z, Trend_Normal@17:20Z).
- **רגל (leg):** `leg_state.detect_leg` האמיתי על 10 הברים הסגורים עד כל איתות; **מוצלב מול שורות LEG_RIDE של אתמול בלוג** — התאמה.
- **תזוזה (release/chase):** close אחרון − פתיחת-RTH ‏7791.5 (בדיוק כמו `release_gate.trend_bypass`).
- **סולם:** `build_step_ladder` האמיתי (יובא מהמודול). **סימולציה:** מודל-הביקורת (סטופ-לפני-טרגט, BE אחרי T1, אופק 12 ברים, $5/pt, $1.5/חוזה), חוזים לפי פסק-פלייבוק (FULL=3 / REDUCED=2).
- סקריפטים: `/tmp/firepath_replay.py`, `/tmp/firepath_scenario2.py` (חד-פעמיים, מחוץ לריפו).

---

## 2. טבלת-פסק — כל 35 (ET · אתמול→היום)

| ET | תבנית | כיוון | entry | נחסם אתמול | **פסק היום** | שער-היום | הערה |
|---|---|---|--:|---|---|---|---|
| 09:30 | GB100 | L | 7791.50 | lsma_flat | 🚫 חסום | lsma_flat | slope .2467<.25; 0 ברים ⇒ אין רגל. אתמול חסך $166 — מוצדק |
| 10:00 | REACTIVE | L | 7782.50 | direction_context | 🚫 חסום | direction_context | נגד-יום; אין פטור-responsive (label UNKNOWN/Trend) — flat ⚪ |
| 10:00 | FAMIR | L | 7781.75 | direction_context | 🚫 חסום | direction_context/playbook | FAMIR=SKIP-בכל-מקום ממילא |
| 10:05 | FAMIR | L | 7784.25 | awaiting_release | 🚫 מוחזק | awaiting_release | LONG נגד-תזוזה (−6.5) — חסך $166 |
| 10:10 | ZLR | L | 7784.75 | cont_trend_filter | 🚫 חסום | cont_trend_filter | disp −6.75<12, אין רגל-UP — חסך $166 |
| 10:15 | ZLR | L | 7784.00 | cont_trend_filter | 🚫 חסום | cont_trend_filter | חסך $166 |
| 10:20 | ZLR | L | 7783.25 | lsma_flat | 🚫 חסום | lsma_flat | אין רגל-UP (structure net=no) — חסך $111 |
| 10:25 | ZLR | S | 7779.75 | awaiting_release | 🚫 מוחזק | awaiting_release | **disp close −11.5 < 12 — פספוס 0.5pt**; per-sig אתמול +$152 |
| 10:30 | GHOST | L | 7785.25 | lsma_flat | 🚫 חסום | lsma_flat | close איבד LSMA — חסך $166 |
| 10:38 | ZLR | S | 7779.75 | cont_trend_filter | 🚫 חסום | **daytype_playbook** | **ZLR SKIP on Normal (conf 1.0)** — per-sig +$208 הולך לאיבוד |
| 10:40 | ZLR | S | 7779.25 | awaiting_release | 🚫 חסום | **daytype_playbook** | release-12 היה עוזר (disp −12.25) — **הפלייבוק הורג קודם** |
| 10:45 | ZLR | S | 7779.25 | awaiting_release | 🚫 חסום | **daytype_playbook** | כנ"ל (disp −12.0) — שלישיית ה-+$540 = 0/3 |
| 10:50 | REACTIVE | L | 7785.00 | awaiting_release | 🚫 מוחזק | awaiting_release | LONG נגד-תזוזה — חסך $166 |
| 11:15 | INITIATIVE | S | 7772.00 | chase (revoked) | 🚫 חסום | **rr_entry_gate** | ✅עובר-chase (bypass חי) → מדרגה 2.0 ⇒ RR 0.25<0.65 |
| 11:30 | REACTIVE | S | 7769.50 | chase (revoked) | 🚫 חסום | **rr_entry_gate** | REV מחוץ-לסקופ-chase → מדרגה 3.25 ⇒ RR 0.41<0.65 |
| 11:35 | BEAR_FLAG | S | 7764.75 | chase (revoked) | 🚫 חסום | **rr_entry_gate** | RR 0.44<0.65 |
| 11:55 | ZLR | S | 7763.75 | chase (revoked) | 🚫 חסום | **rr_entry_gate** | תווית Trend_DD ⇒ rr_min=1.0; תקרת-סולם 0.833 — בלתי-עביר |
| 11:55 | REACTIVE | S | 7763.75 | chase (revoked) | 🚫 חסום | **rr_entry_gate** | כנ"ל |
| 12:05 | ZLR | S | 7765.50 | chase (revoked) | 🚫 חסום | **rr_entry_gate** | כנ"ל (per-sig +$162) |
| 12:11 | ZLR | S | 7766.00 | chase (revoked) | 🚫 חסום | **rr_entry_gate** | כנ"ל (+$217) |
| 12:15 | ZLR | S | 7765.50 | chase (revoked) | 🚫 חסום | **rr_entry_gate** | כנ"ל (+$193) |
| 12:20 | ZLR | S | 7766.75 | chase (revoked) | 🚫 חסום | **rr_entry_gate** | אתמול משבצת-פנויה +$192 — היום מת ב-RR |
| 12:25 | REACTIVE | S | 7761.00 | chase (revoked) | 🚫 חסום | **rr_entry_gate** | כנ"ל |
| 12:30 | FAMIR | L | 7763.50 | awaiting_release | 🚫 חסום | daytype_playbook | FAMIR SKIP (conf .62) — חסך $166 |
| 12:40 | FAMIR | L | 7763.75 | awaiting_release | 🚫 מוחזק | awaiting_release | חסך $166 |
| 12:40 | GHOST | S | 7762.25 | location_gate | 🚫 חסום | location_gate | אין רגל חיה בבר הזה (close מעל LSMA+2.5) — per-sig +$92 אבוד |
| 13:20 | FAMIR | L | 7753.00 | daytype_playbook | 🚫 חסום | daytype_playbook | זהה לאתמול — מוצדק |
| 13:25 | REACTIVE | L | 7754.25 | daytype_playbook | 🚫 חסום | daytype_playbook | counter-trend על Trend_Normal — חסך $111 |
| 13:25 | FAMIR | L | 7754.25 | daytype_playbook | 🚫 חסום | daytype_playbook | מוצדק |
| 14:10 | INITIATIVE | S | 7752.50 | lsma_flat | 🚫 חסום | lsma_flat | **אין רגל** (LSMA לא חד-כיווני) ⇒ הפטור-החדש לא נדלק; per-sig +$97 אבוד |
| 14:50 | FAMIR | L | 7749.00 | awaiting_release | 🚫 מוחזק | awaiting_release | flat ⚪ |
| 15:00 | REACTIVE | S | 7746.00 | lsma_flat | 🚫 חסום | lsma_flat | אין רגל — חסך $166 |
| 15:50 | REACTIVE | S | 7749.50 | eod_entry_cutoff | 🚫 חסום | eod | מבני — מוצדק |
| 15:55 | VEGAS | L | 7750.00 | eod_entry_cutoff | 🚫 חסום | eod | VEGAS=SKIP ממילא |
| 16:00 | ZLR | L | 7751.25 | session_gate | 🚫 חסום | session_gate | מבני |

**סה"כ: 0 יורים · NET מוקרן $0.00** (אתמול-בפועל: 0 יורים; ההפסד-שנחסך/הרווח-שאבד נטו חד-משבצת אתמול = +$239 לפי QUALITY_BLOCKS).

**פסק-איכות:** 25 מהחסימות מוצדקות-או-ניטרליות גם היום (לונגים-נגד-מגמה, FAMIR/VEGAS, EOD). **10 החסימות הלא-מוצדקות הן כולן `rr_entry_gate`** — כל אשכול-השורטים-עם-המגמה 11:15→12:25 שהשתחרר מ-chase נהרג שער-אחד-אחריו.

---

## 3. שורש חדש-מהיום: `rr_entry_gate` × `STEP_SCALED_LADDER_V1` (F3)

```
build_step_ladder(7772.0,'SHORT', bars<15:15Z) →
{'stop': 7776.0, 't1': 7771.0, 't2': 7770.0, 't3': 7769.0, 'median_step': 2.0, 'stop_dist': 4.0}
⇒ T1_dist=1.0, stop_dist=4.0 ⇒ RR=0.25 < 0.65  ⇒ BLOCKED
compute_median_session_step(08-11, SHORT): 15:15Z→2.0 · 15:30Z→3.0 · 16:20Z→3.0 · 16:40Z→2.5 · 18:10Z→2.5
```

- הנחת-העבודה "מדרגה ~10.4pt" **אינה נכונה ל-08-11** (Rule 2 — נבדק מול פונקציית-הייצור עצמה). המדרגה-כ-extreme-advance היא 2–3pt.
- **גבולות מתמטיים:** RR-סולם = 0.5×step / max(4, 0.6×step) ⇒ מקסימום 0.833 (step≥6.67). ⇒
  על `Trend_*` (rr_min=1.0): **חסום תמיד**. על רוטציה (0.65): נדרש step ≥ 5.2pt.
- ה-replay של F3 (73 עסקאות/15 ימים) דיווח בעצמו "RR טיפוסי 0.31" — כלומר **הרפליי לא אכף את `rr_entry_gate`**; בצנרת החיה השער כן נאכף אחרי הסולם (`trading_gateway` F3 ‏@2357 → RR ‏@2613, קורא `setup['t1']`/`setup['stop']` שהסולם דרס).
- גם בלי שער-RR (תרחיש-B): הסולם הזעיר מרוויח כמעט-כלום על הטייפ של אתמול — 10 מועמדים, חד-משבצת **+$25.88** (T1=1.5pt נבלע בעמלות), מול ~+$300 בגאומטריית-הביקורת. **F3 פוגע בדיוק באשכול שהוא נועד לתפוס בימי-מדרגה-קטנה.**

## 4. ממצא #2: היפוך-הפלייבוק מנטרל את פסיקת-release-12

השלישייה שהניעה את הפסיקה (10:25/10:40/10:45 ET, +$540 per-signal): התווית הפכה `Normal` conf=1.0 ב-14:30Z ⇒ `ZLR: Normal=SKIP` (F4) חוסם את 10:40+10:45 **לפני** שער-ה-release; 10:25 נשאר מוחזק (disp −11.5 < 12). **פסיקת ה-12 לא לוכדת אף אחת משלוש העסקאות שהצדיקו אותה.** (לתשומת-לב לפסיקה עתידית: ענף-הנפח של release, או ZLR-Normal=REDUCED-עם-מגמה.)

## 5. בדיקות-היום (16:30)

| בדיקה | מצב |
|---|---|
| CPI 15:30 IL | חלון-red = ‏−10/+5 דק' ⇒ 15:20–15:35 IL בלבד — **לא נוגע ב-RTH**; אין אירועי-red נוספים היום (calendar 01:09 ET) |
| פוזיציה ידנית | **flat** — `sierra_state.json` טרי (14:54): position_qty=0, orders=[], working=0 ⇒ F1 guard לא חוסם |
| cold-start | backend רץ מ-08:09 (uptime 7.6h), פיד חי ⇒ bars_processed≥3 מזמן; ריסטארט <15 דק' לפני איתות = יחסום 3 ברים ראשונים |
| flag_guard | PASS — 166/166 |
| health | 200 OK (uptime_s 27490) |

## 6. סיכון-שיורי — בקול רם

**אם היום ייראה כמו אתמול (מדרגות 2–3pt) — שוב 0 עסקאות, הפעם בגלל `rr_entry_gate` על סולם-F3.**
ועל כל דקה שהתווית `Trend_*` — הסולם חסום-מתמטית (0.833<1.0) גם במדרגות גדולות.
אופציות לפסיקת-מייקל (לא בוצע דבר — READ-ONLY): (א) F3=OFF עד תיקון; (ב) פטור-RR לברקטים שהסולם ייצר (הסולם הוא מודל-הסיכון); (ג) אכיפת-קונסיסטנטיות בסולם עצמו: T1 ≥ rr_min×stop מבנית + rr_min=0.65 גם ל-Trend כשהסולם פעיל. שנית: ZLR-Normal=SKIP מול ענף-release — ר' §4.

חתום: firepath-proof-agent · 2026-08-12 ~15:55 IL
