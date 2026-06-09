# Decision Brief — S1 Mid-Session Day-Type Re-Classification · 2026-06-01

**סטטוס:** 🟡 **ממתין להחלטת Michael** — שינוי trading-logic / **risk surface הגבוה ביותר** מ-3 הפריטים. **אפס קוד שונה.**
**מחבר:** Cowork agent · **מקור מחקר:** מחקר חיצוני שסיפק Michael (2026-06-01, AMT/Market Profile)
**רקע:** `DAY1_DEEP_ANALYSIS_2026-06-01.md` §2+§5 · `AGENT_FIRE_AUDIT_VISIBLE_WINDOW_2026-06-01.md` §2

> ⚠️ **למה זה הכי רגיש:** סיווג-מחדש של day type באמצע היום הופך את ה-Auth Table gating (Normal `SKIP` → NV/TN `FULL`) → **משנה ישירות אילו תבניות יורות**. זה לא רק S1 — זה משחרר את ה-Initiative של S2 (פריט #3 בדוח), ומשנה sizing/targets. לכן ההמלצה: **shadow-log-only קודם**, חיווט ל-gating רק אחרי שהתוויות תואמות קריאה ויזואלית. דרוש אישורך לפני כל שלב.

---

## 1 · ההחלטה הנדרשת

האם להוסיף ל-S1 שרשרת סיווג **monotonic, IB-relative**: Normal → Normal Variation → Trend, שמתעדכנת כל בר אחרי נעילת IB, עם gating על **value migration + acceptance + initiative (CVD)** — ולהכריע את ה-convention המספרי (total-range מול range-extension).

## 2 · מצב נוכחי בקוד (מעוגן — מתקן את DAY1)

`backend/v9/systems/day_type/state_machine.py` — מכונת 13 שלבים (A1→C3). **בניגוד לרמז ב-DAY1 ("אין re-evaluation"), מנגנון re-eval כן קיים** — אבל לא בצורה שהמחקר דורש:

| רכיב קיים | מה הוא עושה | הפער מול המחקר |
|-----------|-------------|-----------------|
| `_rescore_from_behavior` (ש'660) | behavior TRENDING_UP/DOWN → `Trend_Normal`/`Trend_DD` | מסתמך על `detect_behavior`, **לא** על מכפיל IB-extension |
| `_stage_b6` (ש'620) | re-score, מחליף type רק אם `new_conf − old_conf > 0.15` | סף ה-conf "דביק" → לא מטפס בקלות |
| `_check_reeval` (ש'781) | אחרי lock: Normal עם `range/ATR > 2.0` → unlock | **range/ATR**, לא **range/IB_w**; אין VA-breakout/value-migration |
| `classify_range`/`detect_behavior` | קטגוריות מ-extensions + `range_ratio = range/ATR` | denominator = ATR, לא רוחב ה-IB |
| `_stage_b2` (ש'573) | placeholders `pass` — סומך על `bar.extensions_up/down` upstream | אין IB-extension tracker שמודד `E = RE/IB_w` |

**מסקנה מדויקת:** המנגנון הגנרי קיים, אבל **אין סיווג-מחדש ספציפי שמודד IB-extension כיחס מרוחב ה-IB, ולא בודק VA-breakout acceptance או value-migration**. בדיוק הפער שהמחקר מצביע עליו. (כבר קיים רלוונטי: `_last_atr_daily` מתגלגל, `classify_ib_width_atr` ל-narrow/medium/wide, ודגלי shadow `S1_IB_WIDTH_ATR`/`S1_CVD_OPENING`/`S1_DAYTYPE_STAGING`.)

## 3 · מסקנת המחקר (תמצית)

1. **הבאג רעיוני, לא מספרי:** day type הוא **מצב מתפתח**, לא תווית חד-פעמית. Dalton/Steidlmayer: Normal (OTF נעדר) → Normal Variation (OTF מאריך צד אחד) → Trend (OTF שולט). תווית קפואה ב-10:30 = הטעות.
2. **פיצול ספרותי שצריך להכריע (החלטת design):**
   - **total-range (דומיננטי; Steidlmayer/CBOT/Aspen):** NV total ≈ 2× IB · Trend "considerably more than double", classically >3× IB.
   - **range-extension (חלק מהמחנכים):** קורא ל-extension עצמו >2× IB כ-NV.
   - **המלצה: total-range** (מקורות סמכותיים).
3. **ספים codeable** (R=range/IB_w, E=extension/IB_w): Normal R≈1.0–1.15 (≥85% בתוך IB) · NV R≈1.5–2.0 (E עד ~1.0) · Trend R>2 (classically >3, E>~1.0 וממשיך).
4. **VA-breakout + value migration = אישור מעבר** (לא רק שבירת IB). value migration (POC/VA נעים כיווני period-after-period) = המבדיל trend אמיתי מ-probe חוזר.
5. **Initiative vs responsive — מרכזי, ממופה ל-CVD.** initiative (extension בכיוון value) trend-confirming; responsive (fade באקסטרים) rotational. CVD = proxy לגיטימי (אך לא זהה — האפיון הראשוני הוא location מול prior value).
6. **תזמון:** extension מוקדם (bracket 2–3, אחרי IB) trend-confirming; שיא ב-bracket אחרון = **spike** לא-מאושר → לא לשדרג.

## 4 · הכרעת convention + נוסחאות (מומלץ)

לכל בר אחרי 10:30 ET: `IB_w=IBH−IBL` · `RE_up=max(0,hi−IBH)` · `RE_dn=max(0,IBL−lo)` · `E_up=RE_up/IB_w` · `E_dn=RE_dn/IB_w` · developing `VAH/VAL/POC` · `CVD`.

| מעבר | טריגר (defaults — tunable) |
|------|----------------------------|
| **Normal → Variation** | `E_dom ≥ 0.10–0.15` **accepted** (≥2 TPO / sustained, לא wick) · הצד הנגדי לא האריך (`E_opp < ~0.10`) · POC/value נע בכיוון · (אישור) CVD בכיוון |
| **Variation → Trend** | `E_dom ≥ ~1.0` (R≥~2.0) · one-timeframing שלם · VAH/VAL בצד הדומיננטי שבור **ומקובל** · אין acceptance חזרה ל-value הפותח · (אישור) CVD חזק כיווני |
| **→ Neutral (guard)** | אם **שני** הצדדים האריכו (`E_up≥~0.10` ו-`E_dn≥~0.10`) → Neutral (center/extreme לפי close). override לשדרוג trend |
| **false-breakout hold** | שבירה שנכשלת ב-acceptance (חזרה ל-IB תוך ~2 TPO / value לא נע / CVD מתהפך) → **אל תשדרג** |
| **late-session discount** | שדרוג מ-spike ב-bracket אחרון בלבד → דכא |

**Monotonic:** שדרוגים בלבד תוך-יום (לא לתנודד Normal↔NV בר-בר); דרוש שהמצב הגבוה יחזיק ≥bracket אחד; ירידה רק ל-Neutral דרך כלל הדו-צדדי.

## 5 · יישום על יום הדוגמה

IB 7576.0–7596.5 (w=20.5) · שיא 7632.75:
- `E_up = (7632.75−7596.5)/20.5 = ` **1.77** · `R = (7632.75−7576.0)/20.5 = ` **2.77**.
- שבירת IBH ~12:00 (RE up) · שבירת VAH ~12:30 (initiative) · value נע מעלה · CVD חיובי חזק · אין חזרה ל-value.

**ורדיקט:** היו צריכים **שני** מעברים — (1) ~12:00: **Normal → Variation up**. (2) ~12:30+ (כש-E_up עבר ~1.0, ≈ מחיר 7617): **Variation → Trend up**. הקפאה ב-Normal התעלמה מכל אחה"צ — וחסמה את ה-Initiative של S2.

## 6 · Rollout מדורג (תואם המלצת המחקר + תבנית ה-Reactive harness)

1. **Stage 1 — shadow-log-only:** הוסף את שרשרת ה-IB-relative ותעד "would-be transitions" לטבלה/לוג, **בלי** להשפיע על ה-day_type שמוזן ל-Auth Table. אפס סיכון. מאפשר להשוות תוויות מול קריאה ויזואלית.
2. **Stage 2 —** הוסף Neutral two-sided guard + CVD/initiative + acceptance gating. עדיין shadow.
3. **Stage 3 — חיווט ל-gating** רק אחרי שהתוויות תואמות את הקריאה ההיסטורית שלך. כאן זה נוגע ב-risk surface → **strategic stop + אישור**.

## 7 · תוכנית אימות

1. **backtest** `X∈[0.10,0.15]`, `Y∈[0.8,1.2]` על **MES ספציפית** (המיפוי IB→day-type instrument-specific).
2. **כייל IB_w** narrow/medium/wide לפי percentile מתגלגל של טווחי שעה-ראשונה (20.5pt "medium" רק יחסית למשטר ה-VIX/vol הנוכחי) — חלקית כבר קיים דרך `classify_ib_width_atr`.
3. **מדוד תדירות day-type על הנתונים שלנו** — אל תקבע priors ממקור יחיד (המחקר מראה פיזור עצום: Normal 2.4%–60% לפי הגדרה).
4. **תוויות תואמות קריאה ויזואלית** של sessions היסטוריים לפני חיווט.
5. **4 צירי UAT** + **Rule 5** (command + raw output) לכל מספר.
6. **late-session/edge:** דכא שדרוגי spike; טפל ב-roll/half-days.

## 8 · אופציות החלטה (Michael)

- **A — אשר Stage 1 (shadow-log) עכשיו** + backtest §7. רואים את התוויות בלי לגעת ב-gating. **מומלץ.**
- **B — המתן ל-backtest מלא** לפני כל קוד.
- **C — total-range מול range-extension:** הכרע convention (מומלץ total-range) לפני מימוש.
- **D — דחה / השאר סיווג חד-פעמי.**

**המלצתי: A + C** — Stage 1 shadow מתעד את שני המעברים שפוספסו (כמו ביום הדוגמה) ומאפשר כיול, בלי לגעת ב-risk surface. אפשר להריץ אותו במקביל ל-Reactive harness (אותה פילוסופיית "צופים").

## 9 · Caveats (מהמחקר — כמו שהם)

- המכפילים הם **convention, לא מספר קנוני יחיד:** NV ~1.5× (Firich) מול ~2× (Aspen/CBOT); Trend ">2×" מול ">3×". *Mind Over Markets* פרק 2 **איכותני** — המספרים מ-CBOT/Steidlmayer-Buyer (1986)/Aspen. התייחס ל-X/Y כפרמטרים tunable.
- **תדירויות לא עקביות בין מקורות** (Normal 2.4%–60%) — מדוד על נתוני MES שלנו, אל תקבע hard-code.
- **CVD = proxy** ל-initiative/responsive, לא זהה — העיגון הראשוני הוא location מול prior-day value; CVD כפילטר מאשר.
- **TPO/30-דק' מול 5-דק'+CVD** — היישום שלנו הוא **התאמה** של המקור (LDB), לא ציטוט מילולי. מיפוי acceptance≈trade מתמשך מעבר לרמה, initiative≈delta כיווני — תקין כהתאמה.
- Dalton עצמו **הפחית** את ה-IB הקבוע של שעה ב-markets אלקטרוניים 24ש' — ה-IB תקף למודול RTH-anchored כשלנו, אבל "שעה ראשונה" היא heuristic; אמת מול פרופיל הפעילות התוך-יומי של MES.

---

*אפס קוד שונה. מסמך החלטה בלבד. עם אישור → CC ממש Stage 1 shadow-log תחילה, עם raw verification (Rule 5) ועדכון roadmap/STATUS_BOARD. השינוי נוגע ב-Auth Table gating → strategic stop לפני Stage 3.*
