# MEMS26 · דוח EOD מאוחד — 2026-06-09

**שער-זמן (I-9):** ✅ הופק אחרי הסגירה — בעת הריצה השעה **15:12 CT** (≥15:00 CT). RTH 08:30–15:00 CT.
**מקורות:** 13 snapshots ב-`PATTERN_DIAG_2026-06-09.md` + API חי דרך Chrome (`/api/v9/trades/recent`, `/api/v9/chart/bars5min`, 99 ברי-5דק' של היום).
**מצב-יום:** day_type סווג post-IB (~09:30 CT) ל-Trend_Normal/Variation (פיצול I-1); trend RED רוב היום, התהפך RED→GRAY קצרות ~12:12 CT (S4 A1-veto זמני, verdict DEGRADED), חזר RED. **קריאה/תיעוד בלבד — לא נגעתי בקוד.**

---

## 1. עסקאות שנורו היום (2)

| sys | תבנית | id | כיוון | entry | stop_init | risk(pt) | תוצאה | R אמיתי (מ-raw) | pnl_r מדווח |
|-----|-------|----|-------|-------|-----------|----------|-------|-----------------|-------------|
| **S4** | HTLB | 20 | SHORT | 7489.25 | 7491.75 | **2.5** | **WIN** — T1+T2 hit מיד @08:50, C3 רץ ל-TIME_STOP @18:20 IL (+106pt) | C1 **+1.4R** · C2 **+2.8R** · C3 **+42.4R** | **233** ❌ מנופח |
| **S2** | BEAR_FLAG_SHORT | 22 | SHORT | 7313.5 | 7349.75 | **36.25** | **BE** — נסגר ידנית @11:26 ב-entry | **0R** (בפועל) | 0 ✅ |

**עסקת-S4 id=20 (HTLB) — ניצחון-יום אמיתי**, אך ה-`pnl_r=233` שגוי (I-22): R פר-חוזה מחושב `pnl_usd ÷ $1.25` (ערך-טיק) במקום `÷ $12.50` (risk_$ פר-חוזה) ⇒ **ניפוח ×10 פר-חוזה**. אומת raw: C1 `$17.5→14R` (אמיתי 1.4R), C3 `$530→424R` (אמיתי 42.4R). הניצחון אמיתי; רק כיול-ה-R שבור.

**עסקת-S2 id=22 (BEAR_FLAG) — יציאה-ידנית עלתה ~1R.** בפועל נסגרה BE. בתחזית-נגד (החזקה לפי ספק-התבנית, stop 7349.75 / T1 7259.375) — **T1 נפגע @11:35** (9 דק' אחרי היציאה-הידנית), ואז הרץ נעצר ב-BE @12:15 ⇒ **≈+1R** במקום 0. היציאה-הידנית קטעה את ה-T1.

---

## 2. טבלת תבניות מסודרת — נדרכה / נורתה / נחסמה

טווח: 13 snapshots (08:42–14:40 CT). "נדרכה" = armed/eligible באותו snapshot. pre-IB (#1–#2, 08:42+09:13) = day_type=UNKNOWN חוסם הכל (צפוי-שלב). post-IB (#3–#13) = הליבה.

| מערכת | תבנית | נדרכה # | נורתה # | לא-נדרכה # (סיבות) | לא-נורתה # (פירוק דחייה) | תחזית-נגד: W/L, ΣR |
|-------|-------|---------|---------|--------------------|--------------------------|---------------------|
| **S2** | REACTIVE_L/S · INITIATIVE_L/S · BULL_FLAG · BEAR_FLAG (6 מומנטום) | armed ב-11/13 (כל post-IB) | **1** (BEAR_FLAG id=22) | 2/13 pre-IB: `day_type_gate.day_type_known` (IB טרם הושלמה — צפוי-שלב) | detection-await אמיתי בבר (`b3_buyers/b1_buyers/b1_expansion/pole_found/b4_confirm`) — **לא** choppiness_ok (I-16 לא משחזר) | id=22: BE בפועל → **+1R** בהחזקה-לספק (1W) |
| **S2** | INV_HNS · HNS_TOP · DBL_BOTTOM_EE · DBL_TOP_AA (4 day-patterns) | armed-חלקי post-IB | 0 | 2/13 pre-IB day_type_gate | `auth_table_cell × Trend_Normal` (חוסם day-patterns **לגיטימית**) + detection (swing_lows/highs, neckline) | — (חסימה מוצדקת) |
| **S3** | ABSORPTION · STACKED_IMB · SWEEP_RETURN · EXHAUSTION | **0/13** | 0 | **13/13:** `data.bars_today=0`+`data.buffer_size=0` — שורש **I-11 ingest-break** (file→bridge→buffer); מושתק S3_MUTE | — (אין נתון כלל) | — (S3 deferred עד אחרי-LIVE) |
| **S4** | HTLB | armed (ירה) | **1** (id=20 @08:50) | 0 | — (נורתה) | **WIN** — T1+T2+runner +106pt; R אמיתי runner **+42.4R** |
| **S4** | ZLR | armed; הגיע ל-**A7 ≥3×** | 0 | 0 (post-IB); ~2 snapshots GRAY-veto (~12:12) | **A7 FAIL "missing fire_setup"** → `targets_stop.r_t1_gate/stop_price/targets`+`exit_rules.ready_to_route`. **target מנוון** (1pt T1 מול stop 17–37pt ⇒ R:R 0.03–0.06) | **CF (targets שפויים 1R/2R): 2W/1L, ΣR ≈ +1R** (ראה §3). עם ה-target המנוון — חסימה **מוצדקת** |
| **S4** | HFE | armed; הגיע ל-A7 | 0 | 0 | **A7 FAIL** — R:R מנוון (0.11–0.31, T1 1pt מול stop 3–9pt) | חסימה מוצדקת (R:R<1) — סימפטום של I-3 |
| **S4** | TLB · TT · GB100 · Vegas · Ghost · FaMir | armed post-IB | 0 | ~2 GRAY-veto (~12:12) | `detection.pattern_specific` (אין דפוס בבר) + `targets_stop.*` | — (אין setup טרי) |
| **S1** | Day Type (gate) | armed | — | — | detection-await (`probability_above_threshold/directional_certainty/zohar_rules`) | — (סיווג Trend_Normal/Variation, לא חוסם ירי) |

---

## 3. תחזית-נגד (counterfactual) — שחזור ברים בפועל

שוחזר מ-99 ברי-5דק' של היום (`bars5min`, ts IL = CT+8h). לכל signal שזוהה-אך-נחסם: entry/stop לפי הספק; **targets שפויים 1R/2R** (כי ה-targets בפועל היו מנוונים — 1pt). walk-forward עד T/stop.

| signal | שעה CT | entry | stop | risk(pt) | תוצאה (שחזור ברים) | R משוער |
|--------|--------|-------|------|----------|---------------------|---------|
| **ZLR SHORT** | 11:13 | 7302 | 7319.75 | 17.75 | T1@11:15, רץ נעצר BE@11:25 | **+1R** ✅ |
| **ZLR SHORT** | 11:40 | 7269.25 | 7306.25 | 37.0 | T1 miss, stop מלא @12:00 (מגמה התהפכה GRAY) | **−1R** ❌ |
| **ZLR SHORT** | 14:40 | 7359 | 7369.5 | 10.5 | T1@14:40, רץ נעצר BE@14:45 | **+1R** ✅ |
| **id=22 BEAR_FLAG** (החזקה-לספק) | 11:00 | 7313.5 | 7349.75 | 36.25 | T1@11:35, רץ נעצר BE@12:15 | **+1R** ✅ |

**ΣR-נגד (ZLR בלבד, targets שפויים): ≈ +1R · 2W/1L.** מינורי — שער ה-R:R/A7 **לא עלה לנו על עסקה גדולה ולא חסך הפסד גדול**.
**הסתייגות מהותית:** עם ה-**targets בפועל** (1pt T1, R:R 0.03–0.06) שלוש ה-ZLR היו "פוגעות T1" טריוויאלית אך מסכנות 17–37pt תמורת 1pt ⇒ תוחלת קטסטרופלית. **לכן חסימת A7/R:R היתה נכונה — הבאג הוא ה-target המנוון (היעדר טבלת stop/target, I-3), לא החסימה.**

---

## 4. לקחים

**תבניות שנדרכות-הרבה-ולא-יורות (ולמה):**
- **S4 ZLR** — נדרכה והגיעה ל-A7 ≥3× אך **לא יורה לעולם** כי `fire_setup` לא נבנה: ה-`targets_stop` מייצר target מנוון (1pt) ⇒ `r_t1_gate`/`R:R` נופל תמיד. **שורש מבני = היעדר טבלת stop/target פר-תבנית×day-type** (I-3, חופף ל-stop/target table של Michael). זו ה-bottleneck #1 ל-S4 fires מעבר ל-HTLB.
- **S4 HFE** — אותו דפוס: A1–A6 PASS, A7 FAIL על R:R מנוון. אותה טבלת stop/target תפתור.
- **S2 momentum (6)** — נדרכות 10/10 אך יורות רק על detection אמיתי; ביום הזה רק BEAR_FLAG התממשה (id=22). זו דריכה תקינה — לא חסימה-שגויה.

**תבניות שלא-נדרכות (ולמה):**
- **S3 footprint (4)** — 0 ברים כל היום (`bars_today=0`). שורש **I-11**: נתיב ingest file→bridge→buffer שבור (הקובץ נכתב, ה-buffer ריק). מושתק בכוונה (S3_MUTE) — S3 deferred עד אחרי-LIVE, **לא blocker**.
- **S2 pre-IB (08:30–09:30)** — נחסמו על `day_type_gate` עד תום ה-IB. **צפוי-שלב, לא באג.**

**דחיות מוצדקות מול שמרניות-מדי:**
- **מוצדקות:** S2 day-patterns על `auth_table_cell×Trend_Normal`; S4 ZLR/HFE על A7 R:R (בהינתן ה-target המנוון); pre-IB day_type_gate.
- **שמרניות-מדי? לא נמצאה אף דחייה שמרנית-מדי היום.** התחזית-נגד מראה שהחסימות **לא קטעו רווח משמעותי** (ΣR-נגד ≈ +1R בלבד). הבעיה ההפוכה: ה-**target המנוון** הוא שמונע מ-ZLR לירות בכלל — תיקון מבני, לא כיול-סף.
- **היציאה-הידנית של id=22** קטעה ~+1R (T1 נפגע 9 דק' אחרי). לא חסימת-מערכת — החלטה ידנית.

---

## 5. מקור-אמת — דורש הצלבת CC מול Sierra v9_export

לסמן ל-CC (לא כאן):
1. **`pnl_r` (I-22)** — id=20: `pnl_usd ÷ $1.25` (טיק) במקום `÷ $12.50` (risk_$ פר-חוזה) ⇒ ×10. הצלב entry/stop/exit-fills מול risk_$.
2. **ts עתידי בערוץ woodies_5min/bars5min (I-18)** — **אומת היום ברמת ה-DATA:** הבר האחרון ב-`/api/v9/chart/bars5min` נושא ts=`2026-06-10 22:40:00+03:00` (יום קדימה). הצלב mtime+last-bar מול `~/SierraChart_Data/v9_export/`.
3. **CCI-14/TCCI (I-15)** — engine cci_14 מול פאנל-UI (skew משתנה 1–128pt לאורך היום, לעיתים פער-סימן). מי ה-SoT.
4. **ZLR targets/stop (I-3)** — ה-target המנוון (1pt) מקורו בבקנד או Sierra? נדרשת טבלת stop/target.
5. **footprint ingest (I-11)** — קובץ נכתב אך 0 ברים ל-buffer.
6. **`Y IB dll_missing`** — atr_daily/yesterday-IB חסר מה-DLL ⇒ חשוד-שורש ל-day_type split + vote_history=[] (I-1).

**NOT-DONE:** (1) ZLR counterfactual מבוסס targets-שפויים שלי (1R/2R), לא טבלת-stop/target אמיתית — כשתוגדר, לחשב מחדש. (2) פיצול day_type Variation↔Trend_Normal — feed-instance, CC. (3) future-ts לא אופיין שורשית. (4) FHB-state לא נחשף ב-endpoint (I-4). (5) `/trades/recent?limit=200` מחזיר שגיאת-ולידציה (תקרה 100) — מפרט-המשימה צריך limit≤100 (ראה I-25).
