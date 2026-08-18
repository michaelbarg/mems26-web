# עסקאות שהוחמצו + דגלים שלא הודלקו — סשן 2026-08-17

**נכתב:** 2026-08-18 · **מכונה:** מק-1 (MacBook, LIVE) · **מצב:** READ-ONLY בלבד —
לא שונה דגל, לא בוצע restart, לא נכתב דבר ל-`~/SierraChart_Data`.
**עונה על:** *"תראה איתי זה עסקאות שפספסת אולי בגללי"* · *"מה היו התוצאות של דגלים
שלא הדלקנו והיו בבדיקות"*

---

## 0. ממצא-קדם שמשנה כל ספירה — `gateway_decisions.jsonl` מזוהם ב-replay

לפני שמצטטים מספר כלשהו מהפיד: **1,210 מתוך 1,267 השורות בקובץ אינן הסשן החי.**

```
$ python3 -c "... json.loads per line ..."
rows 1267 bad 0
min ts 2026-08-17T01:55:23+00:00 max ts 2026-08-17T19:50:47+00:00

pre-13:00UTC rows: 1210
entry price range: 5250 - 7601.25
trade_ids: [('None', 1003), ('t', 72), ('t2', 42), ('t1', 39), ('t3', 18)]
zone_limit_late_entry entries: [7600.0]
opening_type_gate entries: [7595]
```

MES ב-17.08 נסחר ב-**7764–7809**. שורות עם `entry=5250 / 5900 / 7405 / 7595 / 7600`
ו-`trade_id="L1"/"t"/"t1"` הן **replay/מעבדה** שנכתב לאותו קובץ (ה-backend היה למטה
באותן שעות — `cold_start_guard` ×776, ואין שורות-לוג ב-07:0x IDT). לכן:

- **ספירת "היום" הנכונה = 57 שורות בחלון-הירי 13:30–20:00 UTC** (08:30–15:00 CT):
  43 חסומות · 12 shadow_only · 2 live.
- כל `blocked_by` שמופיע **רק** לפני 13:00 UTC — `zone_limit_late_entry` (15),
  `opening_type_gate` (3), `chop_searching` (3), `duplicate_fire` (3),
  `pattern_loss_breaker` (3), `rr_entry_gate` (39 מתוך 41) — **לא קרה היום בשוק חי**.
  אימות-צולב: `grep -ic "zone_limit" /tmp/_m0817.log` → **0**, `grep -i "opening_type"` → **0**.

> זה חוב לפתוח: הפיד החי נכתב-אליו ע"י תהליך-replay. כל ניתוח-שערים שנשען על
> ספירה גולמית מהקובץ הזה שגוי. (ר' `backend/v9/tests/conftest.py` — אותה מחלקה
> בדיוק כבר טופלה לטסטים, אך לא ל-replay ידני.)

---

## PART A — עסקאות שהוחמצו

### A0. אימות שני המספרים שכבר רשומים בלוג-המשימות (כלל 2)

| טענה בלוג | אומת? | ראיה גולמית |
|---|---|---|
| `lsma_flat` חסם **13** | ✅ **נכון** | 13 שורות, כולן בחלון החי |
| "רובם SHORT ב-7792–7795" | ⚠️ **חלקית** | 9 SHORT / **4 LONG**; 7 מה-SHORT ב-7792.5–7795.5, 2 ב-7775 |
| `OPENING_DIR_FUSION`=None, נפל ב-3.5%, נפח 110,410 מול חציון 114,359 | ✅ **נכון במדויק** | ראה למטה |
| 5 מועמדי `DRIVE SHORT` נזרקו | ✅ **נכון** | 5 שורות |
| לייב **+$103.75** (3) · צל **+$690** (14) | ✅ **נכון** | `v9_trades` — סכום מדויק |

```
$ grep -iE "fusion" /tmp/_m0817.log
2026-08-17 17:00:01 [INFO] [OPENING_DIR_FUSION] SKIP: opening_vol 110410 < median 114359 — auction/low-conviction
2026-08-17 17:05:04 [INFO] [OPENING_DIR_FUSION] SKIP: opening_vol 110544 < median 114359 — auction/low-conviction
2026-08-17 17:05:04 [INFO] [FiveMin] OPENING_DIR_FUSION gate dropped DRIVE SHORT (fusion=None)
2026-08-17 17:10:03 [INFO] [FiveMin] OPENING_DIR_FUSION gate dropped DRIVE SHORT (fusion=None)
2026-08-17 17:15:03 [INFO] [FiveMin] OPENING_DIR_FUSION gate dropped DRIVE SHORT (fusion=None)
2026-08-17 17:20:01 [INFO] [FiveMin] OPENING_DIR_FUSION gate dropped DRIVE SHORT (fusion=None)
2026-08-17 17:25:02 [INFO] [FiveMin] OPENING_DIR_FUSION gate dropped DRIVE SHORT (fusion=None)
```
(חוסר: 110,410/114,359 = **3.45%** · 110,544/114,359 = **3.34%**. שעות הלוג הן IDT=UTC+3.)

```
$ psql -c "SELECT id,mode,pnl_usd FROM v9_trades WHERE entry_ts::date='2026-08-17'"
live:   693 +40.00 · 699 +63.75 · 708 0.00            = +$103.75  (n=3)
shadow: 692 +56.25 · 694 +28.75 · 695 +32.50 · 696 +67.50 · 697 −47.50 · 698 +72.50
        700 +57.50 · 701 +55.00 · 702 +57.50 · 703 +75.00 · 704 +70.00 · 705 +67.50
        706 +47.50 · 707 +50.00                        = +$690.00 (n=14)
```

### A1. כל 43 האיתותים שלא הפכו לעסקה (חלון חי בלבד)

| שער | n | דפוסים · כיוונים |
|---|---|---|
| `lsma_flat` | 13 | ZLR ×11, VEGAS ×1 · 9 SHORT / 4 LONG |
| `eod_entry_cutoff` | 8 | ZLR/GHOST/FAMIR/REACTIVE · 19:25–19:50 UTC |
| `awaiting_release` | 6 | ZLR ×4, GHOST, TREND_STEP, GB100 |
| `cont_trend_filter` | 5 | ZLR — "setup DOWN vs sustained UP/NEUTRAL" |
| `daytype_playbook` | 4 | VEGAS SKIP on Variation · FAMIR SKIP ×3 |
| `extreme_chase_guard` | 2 | ZLR SHORT 7793.50, dist 4.25 < 6.1 מ-session_low |
| `rr_entry_gate` | 2 | GHOST SHORT, R:R 0.36 / 0.32 |
| `rr_hard_floor` | 1 | GHOST SHORT, R:R 0.24 < 0.30 — un-rescuable |
| `location_gate` | 1 | S2 REACTIVE_SHORT — fade at near_val |
| `direction_context` | 1 | ZLR SHORT מול day-context UP |

**ועוד 5 שלא הגיעו בכלל לגייטוויי** — `OPENING_DIR_FUSION` הפיל 5 `DRIVE SHORT`
בתוך `FiveMin` ב-14:05–14:25 UTC, לפני שנרשמו לפיד. אלה **לא** בין ה-43.

### A2. האם הפוזיציה הידנית של מייקל עלתה למערכת עסקה? — **כן, 4 ירי-לייב. אבל היא לא עלתה כסף.**

הראיה חד-משמעית, `[CRITICAL]`, ארבע פעמים:

```
$ grep -n "BLOCKED pre-send" /tmp/_m0817.log
43631:2026-08-17 17:15:40 [CRITICAL] [Gateway] LIVE fire BLOCKED pre-send: standing position +10 on the
  account at fire time (live slot was free → not TM-managed). Sierra's recipe rejects opposite entries
  (AllowOppositeEntryWithOpposingPositionOrOrders=0) and stacking onto a foreign/manual position is the
  07-24 class — blocked pre-send — SHORT ZLR sys=4 — no trade row, no slot, no Sierra command
44361:2026-08-17 17:20:01 [CRITICAL] ... SHORT ZLR sys=4 ...
45251:2026-08-17 17:25:48 [CRITICAL] ... SHORT ZLR sys=4 ...
51892:2026-08-17 18:20:02 [CRITICAL] ... LONG GHOST sys=4 ...
$ grep -c "BLOCKED pre-send" /tmp/_m0817.log
4
```

ארבעת אלה ירדו ל-shadow והתוצאה שלהם **ידועה במדויק** (לא סימולציה — עסקאות-צל אמיתיות):

| UTC | דפוס | כיוון | כניסה | חוזים | תוצאת-הצל |
|---|---|---|---|---|---|
| 14:15:40 | ZLR | SHORT | 7796.25 | 2 | **+$28.75** |
| 14:20:01 | ZLR | SHORT | 7795.00 | 2 | **+$32.50** |
| 14:25:48 | ZLR | SHORT | 7792.75 | 2 | **+$67.50** |
| 15:20:02 | GHOST | **LONG** | 7798.50 | 2 | **−$47.50** |

- **סכום גולמי (בלי כלל עסקה-אחת-בכל-רגע): +$81.25** (n=4)
- **סכום ריאלי (עם עסקה-אחת-בכל-רגע): −$18.75** (n=2) —
  694 הייתה נכנסת 14:15 ויוצאת 14:35, ולכן 695 ו-696 היו נחסמות ממילא ב-`LIVE slot occupied`;
  נשארות 694 (+$28.75) ו-697 (−$47.50).

**המסקנה הישרה: הפוזיציה שלך חסמה 4 ירי-לייב — עובדה. אבל תחת כלל עסקה-אחת-בכל-רגע
שהמערכת באמת מריצה, היא חסכה ~$19 ולא עלתה כסף.** אין כאן "בגללך הפסדנו".

**מה שהיא כן עשתה, פעמיים, ולא נספר קודם** — דיכאה פעולת-יציאה על עסקת-לייב 699:

```
104998: 22:30:08 [WARNING] [BarLevelDetector] S6 TARGET APPROACH REALIZE: trade 699 — t1 approach-realize
104999: 22:30:08 [CRITICAL] [TARGET-APPROACH] SKIPPED for trade 699 — the account holds contracts this
        trade does not own (foreign=True); an account-wide FLATTEN would close them and cancel their stop.
112851: 22:53:04 [WARNING] ... trade 699 — t3 approach-realize ...
112852: 22:53:04 [CRITICAL] [TARGET-APPROACH] SKIPPED for trade 699 — ... (foreign=True) ...
```

עלות: **≈$0**. 699 כבר בנקה T2 ב-19:31 ו-T1 ב-19:32 (`v9_trade_management_log`), ו-
`pnl=63.75 = 6.25pt×$5 + 6.5pt×$5` בדיוק ⇒ שני החוזים מומשו, לא נשאר ראנר ש-t3 יכול היה להציל.

**מה שלא קרה (חשוב לומר במפורש):**
- **מרג'ין לא חתך כלום.** `MARGIN_AWARE_SIZING_V1=0` — הסייז שנפסק נשלח 1:1.
  היו 2 דחיות-מרג'ין ב-05:03/05:04 UTC, אבל הלוג עצמו אומר שהן **לא** של המערכת:
  `[FillPoller] FIX-10 ORDER_REJECT seen (Insufficient Account Value (NLV) ...) but no PENDING demo/live
  trade to correlate — manual order? logged only.` אף ירי-מערכת לא נדחה ולא הוקטן בגלל מרג'ין.
- **8 החסימות `LIVE slot occupied` הן של המערכת עצמה, לא שלך.** כולן ב-17:56–19:05 UTC,
  בדיוק בתוך חיי עסקת-לייב **699** (17:50:04→20:06:03). הן הפילו את 700–707 לצל:
  **$57.50+55+57.50+75+70+67.50+47.50+50 = $480** — זו העלות של כלל
  עסקה-אחת-בכל-רגע ביום הזה, לא של הפוזיציה הידנית.

### A3. מה כל אשכול חסום היה עושה — סימולציה

**מתודולוגיה + מגבלותיה (בגילוי מלא):** לאיתות חסום **אין** סולם — החסימה קודמת
ל-`StopResolver`/`STEP_SCALED_LADDER`. מה שכן קיים בלוג לכל איתות הוא **הסיכון-הגולמי
בנקודות** ו**מספר-החוזים אחרי `SIZE_CAP_CUT`**. לכן הסימולציה: כניסה במחיר-האיתות,
סטופ ויעד ב-±1R על הסיכון-הגולמי, **סטופ נבדק לפני יעד באותו בר**, ברי-5דק' מ-
`v9_bars_5min_woodies`, סגירה כפויה ב-20:00 UTC. 30 מתוך 43 שורות ניתנות-לסימולציה
(ל-13 אין שורת `V2Sizing` — מסלול S2/לא-woodies).
**חולשת-המודל:** הסיכון-הגולמי אינו הסטופ שהיה נשלח (ה-resolver הידק בכל 16 המקרים
הנצפים, למשל `stop 7811.25 → 7801.50, band [4.6,6.9]`). לכן מובאות **שתי גבולות**, לא מספר אחד.

**(א) גולמי, בלי תחרות-על-הסלוט (גבול עליון):**

| שער | n | $ |
|---|---|---|
| `rr_entry_gate` | 2 | **+123.50** |
| `eod_entry_cutoff` | 6 | +75.75 |
| `extreme_chase_guard` | 1 | +42.00 |
| `awaiting_release` | 3 | +38.75 |
| **`lsma_flat`** | **11** | **+5.50** |
| `cont_trend_filter` | 4 | −9.00 |
| `daytype_playbook` | 3 | **−202.00** |
| **סה"כ** | **30** | **+74.50** |

**(ב) עם עסקה-אחת-בכל-רגע (כל שער כובה לבדו; עסקאות-הלייב האמיתיות תופסות את הסלוט):**

| שער | גולמי | סטופ מהודק ל-[4.75,7.75] |
|---|---|---|
| `awaiting_release` | +128.75 | +38.75 |
| `extreme_chase_guard` | +42.00 | +47.50 |
| `rr_entry_gate` | +61.00 | +38.75 |
| `cont_trend_filter` | −3.00 | 0.00 |
| `eod_entry_cutoff` | 0.00 (n=0, סלוט תפוס) | 0.00 |
| **`lsma_flat`** | **−54.00** | **−90.75** |
| `daytype_playbook` | −140.00 | −116.25 |
| **סה"כ** | **+34.75** | **−82.00** |

**(ג) חסר-מודל לחלוטין — MFE/MAE בנקודות מהכניסה עד 20:00 UTC.** זה הנתון החזק ביותר
כי אינו תלוי בהנחת-סטופ:

| שער | n | MFE ממוצע | MAE ממוצע | MFE>MAE |
|---|---|---|---|---|
| `extreme_chase_guard` | 1 | 27.25 | 4.00 | 1/1 |
| `rr_entry_gate` | 2 | 25.38 | 5.88 | 2/2 |
| `cont_trend_filter` | 4 | 21.44 | 9.94 | 3/4 |
| **`lsma_flat`** | **11** | **15.23** | **12.34** | **7/11** |
| `eod_entry_cutoff` | 6 | 5.62 | 2.96 | 5/6 |
| `awaiting_release` | 3 | 9.42 | 16.50 | 1/3 |
| `daytype_playbook` | 3 | 2.58 | **21.17** | **0/3** |

### A4. שתי מסקנות שסותרות את מה שכתוב היום ב-T-32

1. **`lsma_flat` לא היה "השער היקר היום".** בכל שלוש השיטות הוא בין +$5.50 ל-−$90.75
   — אפס עד קצת-שלילי, לא הפסד גדול. הסיבה: הוא חסם בשעתיים שבהן המחיר **דשדש**
   ב-7792–7796 (זה בדיוק מה ש-LSMA-שטוח מודד), ורק אחר-כך השוק ירד. 4 מתוך 13
   החסימות היו **LONG** — כלומר הוא גם חסך. MFE 15.23 מול MAE 12.34 = שולי.
   **הצעד הנכון אינו לכבות אותו — אלא לכמת אותו על 20 סשנים.**
2. **`daytype_playbook` היה השער שהרוויח הכי הרבה היום** — חסם 3 (VEGAS LONG ×1,
   FAMIR LONG ×2) ביום יורד, MAE ממוצע 21.17 מול MFE 2.58, **0/3 טובות**.
   חסך $116–$202. הוא לא ברשימת-הבדיקה של אף אחד.

---

## PART B — הדגלים שלא הודלקו: מה הם היו עושים ב-17.08

מקורות-אמת: `.env` (`grep -E "^FLAG="`), `config/RULED_FLAGS.yaml` (178 דגלים),
`v9_s7_shadow_log`, `v9_tsf_shadow_log`, ו-`/tmp/backend.err.log`.
**"אין הזדמנות" ≠ "אין השפעה"** — מסומן במפורש.

| דגל | מצב | מה קרה ב-17.08 | תוצאה בדולרים |
|---|---|---|---|
| **`SYSTEM7_SCORE_V1`** | לא-מוגדר → קוד-ברירת-מחדל **OFF** | **פעל בצל ורשם 14 שורות.** ספים: `<40` חסום · `40–64` → 1c · `65–84` → 2c · `≥85` → 3c. כל 14 קיבלו **30 או 40 בלבד** | **ההשפעה הגדולה ביותר מכל הדגלים.** score=30 ⇒ **חסום**: 692 (התאום של לייב **693**) — כלומר היה **הורג את המנצח החי הראשון של היום, −$40**; וכן 694 (+$28.75), 695 (+$32.50). score=40 ⇒ **1 חוזה בלבד** ל-11 הנותרות ⇒ 699 הייתה יורה 1c במקום 2c: נשאר רק C1→T1 = 6.5pt×$5 = **$32.50** במקום $63.75 ⇒ **−$31.25**. **סה"כ על הלייב: מ-+$103.75 ל-+$32.50 — כלומר −$71.25** |
| **`ZONE_LIMIT_ENTRY_V1`** | `=0` | **אין הזדמנות.** 15 שורות `zone_limit_late_entry` בפיד — כולן ב-replay (entry=7600). `grep -ic zone_limit` בלוג החי = **0** | $0 · לא נבחן |
| **`OPENING_TYPE_GATE`** | `=0` | **אין הזדמנות.** 3 שורות — replay (entry=7595). `grep -i opening_type` בלוג = **0**. ממילא `OPENING_DIR_FUSION` כבר החזיר None כל הפתיחה | $0 · לא נבחן |
| **`S2_CHOPPINESS_GATE`** | לא-מוגדר → OFF (פסיקה קבועה 06-08) | **אין הזדמנות בירי.** מדד תצוגה/arming בלבד — מעולם לא ווטו על ירי-S2 אמיתי. `grep -ic choppiness` בלוג = **0** | $0 · חסר-מדידה מבנית |
| **`LAYER0_CHOP_GATE`** | לא-מוגדר → OFF (פסיקה קבועה 06-08) | **אין הזדמנות.** `chop_searching` ×3 — כולן replay. `grep -ic "chop_score\|chop_state"` בלוג החי = **0** — כלומר גם ה-observability שאמור לרוץ **לא נרשם**. חוב בפני עצמו | $0 · לא נמדד |
| **`MARGIN_AWARE_SIZING_V1`** | `=0` (פסיקת 13.08 "1:1") | **אין הזדמנות שהזיקה.** 2 דחיות-NLV ב-05:03/05:04 UTC — הלוג מסווג אותן `manual order? logged only`. אף ירי-מערכת לא נדחה | $0. **אבל** תנאי-החזרה בפסיקה ("אם יחזרו דחיות NLV אמיתיות") — לא התקיים; אלה לא היו של המערכת |
| **`SYSTEM6_REVERSAL_TIGHTEN_V1`** | `=0` (כובה 17.08) | **אין הזדמנות** אחרי הכיבוי. מה שכן נראה: `MODIFY_TARGET` נדחה **שוב ושוב** — `[System6] AUTO-CORRECT target_divergence_t2/t3 → rejected` + `needs manual handling (advisory)`. מאשר את נימוק-הכיבוי: חצי-הפסיקה אינו בר-ביצוע | $0 · הכיבוי מאומת-בשטח |
| **`S6_MAE_SCRATCH_V1`** | **`=1` (דלוק)** | **0 ירי.** `grep -cE "MAE.SCRATCH"` = **0**. כל עסקאות-הלייב הלכו לטובה מוקדם ולא הגיעו לסף-MAE | $0 · **אין הזדמנות**, לא "אין אפקט" |
| **`S6_TARGET_APPROACH_REALIZE_V1`** | **`=1` (דלוק)** | **ירה פעמיים** — לא "מעולם לא ירה" כפי שנרשם. 19:30:08 (t1) ו-19:53:04 (t3) על לייב 699. **שתיהן דוכאו** ע"י `foreign=True` (הפוזיציה הידנית) | **≈$0** — T1+T2 כבר מומשו 19:31/19:32; לא נשאר ראנר. הדגל **עדיין לא-נבחן בפועל** |
| **`TSF_V1`** | לא-מוגדר → OFF | פעל בצל: 14 שורות, **`would_apply=False` בכל 14** (`floor=6.0` מול `current_risk` 4.25–7.75, `delta_pts=0`) | **$0 מדוד** — הדגל היה אינרטי לחלוטין |
| `SSV_GATE_V1` | `=0` | אין הזדמנות — לא מופיע בלוג | $0 |
| `PATTERN_LOSS_BREAKER` | `=0` | 3 שורות בפיד — **כולן replay** | $0 |
| `DAYTYPE_POSITION_GATE` | `=0` | אין הזדמנות | $0 |
| `RISK_CONSECUTIVE_LOSS_LIMIT` | `=0` | **אין הזדמנות** — 0 הפסדי-לייב ברצף (3 עסקאות, 2 מנצחות + BE) | $0 |
| `STALL_EXIT` / `OPPOSITE_EXIT_V1` | קוד-ברירת-מחדל OFF (op=EXIT שבור) | אין הזדמנות · אסורים ממילא | $0 |

**תיקון לניסוח שהגיע איתי במשימה (כלל 2):** `SYSTEM7_SCORE_V1` **אינו** "מקבע כל
עסקה ל-≤3 חוזים". הקוד ב-`trading_gateway.py:1866-1871` הוא
`if _s7_contracts < result.get("contracts", 3): result["contracts"] = _s7_contracts`
— ה-`3` הוא רק ברירת-מחדל של `.get`, וההידוק הוא ל-**sizing של S7 עצמו (0–3)**.
ב-17.08 ה-sizing היה **1** בכל השורות שלא נחסמו ⇒ הידוק ל-**חוזה אחד**, לא ל-3.

---

## PART C — הסתייגות: כל מספר כאן הוא n<20 ודק

1. **סשן אחד.** כל שורה בטבלאות היא n=1..13.
2. **14 מתוך 16 ירי-הדפוסים היו ZLR SHORT מתואמים** לתוך אותה רגל-ירידה אחת
   (17:50–19:30 UTC). זו **תצפית אחת שנספרה 14 פעם**, לא 14 תצפיות. כל
   "win-rate 13/14" מהיום הזה הוא אשליה סטטיסטית.
3. **הסימולציה של האשכולות החסומים היא מודל**, לא replay — אין סולם לאיתות חסום.
   הפער בין הגבולות (+$74.50 גולמי מול −$82.00 מהודק+סלוט) **גדול מכל אפקט
   פר-שער שנמדד**. זה אומר: המודל אינו מספיק חד כדי להכריע שער.

### מה **אסור** להכריע לפני 20 סשנים
- **`lsma_flat`** — n=13 ביום-דשדוש-אחד; MFE≈MAE. גם הכיוון לא ברור.
- **`SYSTEM7_SCORE_V1`** — n=14, כל ה-scores 30/40 בלבד (טווח של 10 נק' מתוך 100).
  היום הוא נראה יקר (−$71.25) אבל זה על יום אחד שבו הוא בעיקר הידק סייז.
  T-17 (3 ימי-צל) הוא הסף הנכון — ואפילו הוא נמוך.
- **`daytype_playbook`** — n=3. נראה מצוין היום; זה 3 עסקאות.
- **`cont_trend_filter` · `awaiting_release` · `rr_entry_gate`** — n=2..6.

### מה **כן** אפשר להכריע כבר עכשיו (עובדה, לא סטטיסטיקה)
- **הפיד `gateway_decisions.jsonl` מזוהם ב-replay** — 1,210/1,267. באג, לא מדגם.
- **`S6_TARGET_APPROACH_REALIZE_V1` ירה ודוכא** — התיעוד ("מעולם לא ירה") שגוי.
- **`TSF_V1` היה אינרטי** — `would_apply=False` ב-14/14, `delta=0`. מדידה מלאה.
- **`LAYER0_CHOP_GATE` לא נרשם בכלל** — ה-observability שאמור לרוץ למרות הכיבוי אינו רץ.
- **הפוזיציה הידנית חסמה 4 ירי-לייב + 2 פעולות-יציאה** — מתועד `[CRITICAL]`.

---

## נספח — כל הפקודות (כלל 5)

```bash
# מקור-החלטות
python3 -c "json per line" ~/SierraChart_Data/v9_export/gateway_decisions.jsonl   # 1267 rows / 0 bad
# חיתוך הסשן מהלוג (שעות IDT=UTC+3, אומת מול trade 693)
awk '/^2026-08-17 /{p=1} /^2026-08-18 /{p=0} p' /tmp/backend.err.log > /tmp/_m0817.log   # 122,929 שורות
grep -c "BLOCKED pre-send" /tmp/_m0817.log            # 4
grep -c "foreign=True"     /tmp/_m0817.log            # 2
grep -c "LIVE slot occupied" /tmp/_m0817.log          # 8
grep -ic "zone_limit" /tmp/_m0817.log                 # 0
grep -i  "opening_type" /tmp/_m0817.log               # (ריק)
grep -icE "chop_score|chop_state|choppiness" /tmp/_m0817.log   # 0
grep -cE "MAE.SCRATCH" /tmp/_m0817.log                # 0
grep -cE "TARGET.APPROACH" /tmp/_m0817.log            # 4
grep -c  "ExitVerify" /tmp/_m0817.log                 # 0   (מאשר T-29)
grep -c  "SIZE_CAP_CUT" /tmp/_m0817.log               # 61  (מאשר T-30: 4→1/2 בכל ירי)
grep -c  "STOP_RESOLVER_V1" /tmp/_m0817.log           # 16
# DB
psql postgresql://localhost/mems26 -c "SELECT ... FROM v9_trades  WHERE entry_ts::date='2026-08-17'"  # 17
psql postgresql://localhost/mems26 -c "SELECT ... FROM v9_s7_shadow_log  WHERE ts::date='2026-08-17'" # 14
psql postgresql://localhost/mems26 -c "SELECT ... FROM v9_tsf_shadow_log WHERE ts::date='2026-08-17'" # 14
psql postgresql://localhost/mems26 -c "SELECT ... FROM v9_bars_5min_woodies WHERE ts BETWEEN ..."     # 96
psql postgresql://localhost/mems26 -c "SELECT ... FROM v9_trade_management_log WHERE trade_id=699"    # 4
# .env — מצב-דגלים
grep -E "^(SYSTEM7_SCORE_V1|ZONE_LIMIT_ENTRY_V1|OPENING_TYPE_GATE|...)=" .env
```

**לא הודלק ולא כובה שום דגל. לא בוצע restart. לא נכתב דבר מחוץ לקובץ הזה.**
