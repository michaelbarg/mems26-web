# CC Prompt — Reactive 3-Variant Shadow Harness · 2026-06-01

**מאת:** Cowork agent → **אל:** Claude Code
**רקע:** `docs/reports/DECISION_BRIEF_REACTIVE_VOLUME_THRESHOLD_2026-06-01.md` · `DAY1_DEEP_ANALYSIS_2026-06-01.md` §3
**מטרה (Michael):** להריץ את 3 הוריאציות של גייט ה-volume ל-Reactive **במקביל, כצופים**, לתייג כל ירי לפי וריאציה, ולרכז בסוף השדאו דוח השוואתי שעליו Michael יחליט מה הכי טוב.

> **משמעת Pre-LIVE (CLAUDE.md) — חובה:**
> 1. **Diagnose/read first.** קרא את `five_min_system.py::_detect_reactive` והקבועים לפני כל הצעה.
> 2. **Audit existing.** בדוק אם כבר קיים A/B harness או טבלת variant — אם לא, סווג את כל רכיב חדש. אל תכפיל.
> 3. **Rule 5.** כל "עובד" = command + raw output.
> 4. **Strategic stop** לפני כל נגיעה ב-live fire path.
> 5. **אל תזהם stats.** ירי וריאציה הוא **observational בלבד** — לא עובר ב-gateway/route_setup, לא נרשם בטבלת ה-fires/trades הראשית, מסומן בנפרד (CLAUDE.md §synthetic="TEST").

---

## עיקרון-על: צופים, לא מחליפים

- **ה-live S2 Reactive נשאר ללא שינוי** — `DROP_THRESHOLD_PCT=0.10` כמו שהוא. אנחנו **לא** משנים מה שירה בפועל.
- שלוש הוריאציות רצות **במקביל על אותם ברים** דרך evaluator נפרד (observer), וכותבות אותות **מתויגים** לטבלה ייעודית. אפס השפעה על risk surface, אפס זיהום ל-SHADOW stats הקיימות.
- **apples-to-apples:** כל 3 הוריאציות מריצות את **אותו setup 4-ברי מלא** (b1 sellers/buyers, b3 belly, b4 confirm+close, COT/AMT, lookback_quiet) ונבדלות **אך ורק בגייט בר 2**.

## שלוש הוריאציות (גייט בר 2 בלבד)

| Variant | גייט בר 2 | תשתית |
|---------|-----------|--------|
| **A · VSA** | `b2_vol < b1_vol AND b2_vol < b0_vol` **וגם** `b2_vol ≤ 0.7 × rolling_avg_20(vol)` | ממוצע-vol מתגלגל 20 |
| **B · RVOL-TOD** | `b2_vol ≤ 0.6 × baseline_TOD(clock_time)` (ממוצע אותה שעת-שעון על 10–20 sessions) | baseline TOD מ-`v9_bars_5min` |
| **C · Strict** | `b2_vol ≤ 0.5 × rolling_avg_20(vol)` | ממוצע-vol מתגלגל 20 |

> overlay אופציונלי (לתעד, לא חובה לגרסה 1): "narrow spread" — `b2_range < 0.7 × _current_atr_5m` (משתמש ב-ATR הקיים). תייג בנפרד כדי שנראה את ההשפעה.

## ארכיטקטורה מבוקשת

1. **Refactor בטוח של הגייט:** הוצא את גייט בר 2 מ-`_detect_reactive` ל-callable מוזרק, עם **default זהה-בייט** להתנהגות הנוכחית (0.10). הרץ את הטסטים הקיימים → חייבים לעבור ללא שינוי (הוכחה שה-live לא זז). זה ה-strategic-stop הראשון: הצג diff + פלט טסטים **לפני** המשך.
2. **Variant evaluator (observer):** מודול חדש שמקבל את אותו `_bar_buffer`, מריץ את ה-setup המלא ל-A/B/C, וכשוריאציה "יורה" — כותב שורה ל-`v9_reactive_variant_signals`.
3. **טבלה חדשה `v9_reactive_variant_signals`** (read/write נפרד מ-fires):
   `id, ts, variant_id(A/B/C), direction, entry_price, b0_vol, b1_vol, b2_vol, rolling_avg_20, rvol_tod, gate_value, other_conditions_json (cot,amt,belly,lookback pass/fail), atr_5m, session_date, created_at`.
4. **Forward-outcome labeler (job בסוף-session, read-only על bars):** לכל אות וריאציה — מ-entry, בתוך חלון ה-time-stop (90 דק' ≈ 18 ברים): האם הגיע ל-**T1 = entry ± 12 ticks** לפני **stop = entry ∓ 8 ticks**? רשום: `outcome(T1_HIT/STOP_HIT/TIME_EXPIRED), mfe_ticks, mae_ticks, bars_to_resolution`. שמור ל-`v9_reactive_variant_outcomes`.

## דוח השוואתי בסוף השדאו (לא לבחור מנצח אוטומטית)

סקריפט `scripts/reactive_variant_report.py` שמפיק טבלה פר-וריאציה — **כל המדדים זה לצד זה**, ההכרעה של Michael:

| מדד | מה הוא אומר |
|-----|------------|
| `fires_per_day` | תדירות — האם ריאלי (~5–10) או רועש/0 |
| `gate_alone_pass_rate` | כמה ברים עברו את גייט ה-volume לבדו (יעד 5–18%) |
| `full_setup_fires` | כמה הפכו ל-setup 4-ברי מלא |
| `win_rate` | % T1-לפני-stop |
| `avg_mfe_ticks` / `avg_mae_ticks` | איכות תנועה |
| `expectancy_proxy` | (win%×12 − loss%×8) ticks — אינדיקציה, לא החלטה |

הדוח מציג את שלושתן + הפניה ל-DECISION_BRIEF. **אל תכריז מנצח** — Michael בוחר את המדד וההכרעה בסוף השדאו.

## דרישות מימוש
- read-only על `v9_bars_5min` ל-baseline TOD ול-labeler (sqlite `mode=ro`).
- כתיבה רק לשתי הטבלאות החדשות. **לא** ל-`route_setup`, **לא** לטבלת trades.
- **edge-cases** (מהמחקר): טפל/החרג 2 הברים הראשונים אחרי 09:30, בר 15:55–16:00, ו-roll/half-days — מעוותים baseline.
- טסט regression: (א) default-gate זהה-בייט (live לא זז), (ב) כל וריאציה יורה על fixture ידוע, (ג) labeler מסווג T1/STOP/TIME נכון על fixtures.
- **Rule 5:** הדבק — diff ה-refactor + טסטים ירוקים · 3 שורות variant מטבלה אחרי session · פלט הדוח ההשוואתי.

## Strategic stops (עצור ושאל Michael)
1. אחרי ה-refactor הבטוח של הגייט + הוכחת live-unchanged (diff + טסטים) — **לפני** בניית ה-evaluator.
2. אחרי ריצת session ראשונה — הצג 3 שורות variant גולמיות לאימות שהתיוג עובד, **לפני** שסומכים על הצבירה.

## בסיום
עדכן `ROADMAP_TO_LIVE.html` + `STATUS_BOARD.md` (root→fix→verification, Rule 5): פריט "Reactive variant shadow harness" כ-SHADOW, עם תאריך תחילת איסוף.

---

## הקשר קוד (לעיגון CC)
- `backend/v9/systems/five_min/five_min_system.py`: `DROP_THRESHOLD_PCT=0.10` (ש'30), `LOOKBACK_MAX_VOL_RATIO=0.6` (ש'36), `_detect_reactive` (≈ש'469–543, גייט בר 2 ב-`b2_drop` ≈ש'499), `_current_atr_5m` כבר מחושב (ש'767).
- `v9_bars_5min` — מקור הברים ל-baseline TOD ול-labeler.
- `V9FiveMinSetup` — **דוגמה** לפרסיסטנס, **לא** ליעד הווריאציות (להפריד).
