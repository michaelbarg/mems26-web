# PATTERN EOD · 2026-06-08 (יום שני) — דוח סוף-יום מאוחד

**נוצר:** 2026-06-08 15:12 CT (אחרי סגירת RTH 15:00 CT — שער-זמן I-9 ✓ חלף).
**מקור:** 13 סנאפ-שוטים ב-RTH (08:42–14:53 CT) מ-`PATTERN_DIAG_2026-06-08.md` + אימות-סגירה חי
מ-`/api/v9/trades/recent` ו-`/api/v9/chart/bars5min` (Chrome→localhost:8000, post-close).
**אופי:** read-only/דיאגנוסטיקה. לא נגעתי בקוד/לוגיקת-ירי.

---

## TL;DR

- **0 עסקאות נורו היום** בכל המערכות (אומת: `trades/recent` מחזיר רק 3 עסקאות, כולן
  מ-שישי 2026-06-05; `gateway` `trades_today=0/daily_pnl=0/shadow_active_count=0`).
- **הסיבה אינה דחיות-לוגיקה אלא feed:** הבוקר ערוץ ה-5דק'/study **לא עלה בכלל** עד
  ~09:00 CT (I-21 כ-session-non-start), ו-`footprint` (S3) נשאר **0 ברים כל היום** (I-11).
  ⇒ S2/S4 נדרכו רק אחרי 09:00, S3 לא נדרך כלל.
- **counterfactual: אין מועמד מובהק.** אף signal לא זוהה-ונחסם-בטעות. ה-near-miss היחיד:
  **HFE (S4) ב-12:27** — נחסם **לגיטימית** ב-A7 (R:R 0.29 < 1.0), לא ב-A5/sizing.
- **ΣR/win-rate חסום ע"י I-22** — נוסחת `pnl_r` מנופחת ~22–30× (כעת **מאובחנת לשורש**:
  R מחולק בערך-טיק $1.25 במקום במרחק-הסטופ-$). ראה §תיקון-נגד למטה.

---

## 1. טבלת EOD מאוחדת — פר מערכת × תבנית

טווחי "נדרכה #" משקפים תנודתיות לאורך 13 הסנאפ-שוטים (I-17 buffer-flip). "נורתה #" = עסקאות
ב-`v9_trades` היום (כולן 0).

| מערכת | תבנית | נדרכה # (טווח-יום) | נורתה # | לא-נדרכה (סיבות) | לא-נורתה (פירוק דחייה) | תחזית-נגד W/L, ΣR |
|-------|-------|---------------------|---------|-------------------|--------------------------|--------------------|
| **S2** | REACTIVE_LONG | 0→armed (רוב היום) | 0 | 08:42 feed-dead (`day_type_known`+`fhb_eligible` missing); חלון 10:11/11:05/12:27/12:45 `Missing: choppiness_ok` | detection `b2_volume_drop` (ratio ✗) | אין setup |
| **S2** | REACTIVE_SHORT | 0→armed | 0 | כנ"ל | detection `b1_buyers` (bar bull) | אין setup |
| **S2** | INITIATIVE_LONG | 0→armed | 0 | early auth SKIP×Normal (נוקה ~11:38) → אח"כ feed/chop | detection `b1_bull` (b1 close<open ✗) | אין setup |
| **S2** | INITIATIVE_SHORT | 0→armed | 0 | כנ"ל | detection `lookback_quiet` (lookback_max≫threshold ✗) | אין setup |
| **S2** | INV_HNS_LONG | 0→armed | 0 | feed/chop | `swing_lows_found` 0/20 | אין setup |
| **S2** | HNS_TOP_SHORT | 0→armed | 0 | feed/chop | `swing_highs_found` 1/20 | אין setup |
| **S2** | DOUBLE_BOTTOM_EE | 0→armed | 0 | feed/chop | `swing_lows_found` 0 | אין setup |
| **S2** | DOUBLE_TOP_AA | 0→armed | 0 | feed/chop | swing_highs/neckline per-bar | אין setup |
| **S2** | BULL_FLAG | 0→armed | 0 | feed/chop | `pole_found` per-bar | אין setup |
| **S2** | BEAR_FLAG | 0→armed | 0 | feed/chop | `flag_retrace`/`pole_found` per-bar | אין setup |
| **S4** | ZLR | armed (כש-RED/BLUE) | 0 | A1-veto כש-trend=GRAY (09:40/10:47/12:45/13:09/13:38) | A3 "no pattern this bar" כשלא-GRAY | אין setup-ZLR (I-3) |
| **S4** | TLB | armed (RED/BLUE) | 0 | A1-veto GRAY | `detection.pattern_specific` no-pattern | אין setup |
| **S4** | TT | armed | 0 | A1-veto GRAY | no-pattern this bar | אין setup |
| **S4** | GB100 | armed | 0 | A1-veto GRAY | no-pattern this bar | אין setup |
| **S4** | HFE | armed | 0 | A1-veto GRAY | **12:27 setup חי → A7 R:R 0.29<1.0** (לא A5; sizing=half PASS) | ⭐ near-miss יחיד — ראה §2 |
| **S4** | HTLB | armed | 0 | A1-veto GRAY | no-pattern this bar | אין setup |
| **S4** | FAMIR | armed | 0 | A1-veto GRAY | no-pattern this bar | אין setup |
| **S3** | ABSORPTION | **0 כל היום** | 0 | `data.buffer_size`/`bars_today=0` (I-11) | — (אין נתון) | אין נתון |
| **S3** | STACKED_IMBALANCE | **0 כל היום** | 0 | I-11 | — | אין נתון |
| **S3** | SWEEP_RETURN | **0 כל היום** | 0 | I-11 | — | אין נתון |
| **S3** | EXHAUSTION | **0 כל היום** | 0 | I-11 | — | אין נתון |

**S5 (TPO)/S6 (killzone):** gates/observers, לא תבניות-ירי. S5 `disabled (S3_MUTE/S5)` (I-24);
S6 `KZ ✗ לא-מחזור` רוב היום.

---

## 2. תחזית-נגד (counterfactual)

**אין מועמד מובהק היום.** הקריטריון הוא "signal שזוהה-אך-נחסם/לא-נורה" — והיום אף תבנית
לא הגיעה לכדי setup פרט ל:

**⭐ HFE (S4) @ 12:27 CT — ה-near-miss היחיד.** ה-setup זוהה (active_patterns=[HFE]),
עבר A5 (sizing=half, PASS), ונחסם ב-**A7 R:R**: stop≈10.5pt / T1≈3pt ⇒ R:R≈0.29 < סף 1.0.
- **תחזית-נגד מבנית (ללא שחזור-ברים):** אם היה נורה, T1 ב-+0.29R מול stop ב-−1.0R ⇒
  ה-expectancy שלילי כל עוד win-rate < ~78%. **הדחייה מוצדקת מבנית**, לא שמרנית-מדי.
- **חסר לשחזור-ברים מלא:** מחיר-הכניסה המדויק ב-12:27 לא תועד בסנאפ-שוט (רק stop/T1
  במונחי-pt). לשחזור hit_T1/stop פר-בר צריך את ה-entry הגולמי → **ל-CC** (הצלבת
  `v9_bars_5min`/Sierra). זה אותו פגם-מבני שמתועד ב-I-13: **HFE כמעט-אף-פעם לא יעבור A7
  בלי כיול טבלת stop/target** (anchor חסר).

**ΣR/win-rate היפותטי פר-תבנית:** N/A היום — אין signals שנחסמו-בטעות, ולכן אין R לצבור.

### תיקון-נגד: R הנכון של עסקאות-שישי (הוכחת I-22 מ-raw `contracts_pnl`)

אין עסקה-טרייה, אך 3 עסקאות-שישי עדיין בטבלה — והן **חוסמות כל ΣR אמין** עד תיקון I-22.
מ-`contracts_pnl` הגולמי הוכחתי את הנוסחה השגויה: **R = pnl_usd ÷ $1.25 (ערך-טיק)**
במקום **R = pnl_usd ÷ risk_$ (מרחק-הסטופ × $5 × חוזים)**:

| id | תבנית | entry | stop_init | risk_pt | C1 pnl_usd / R-מדווח | בדיקה: 18.75/15=**$1.25**=טיק | R **נכון** (מצרפי) | R מדווח | אינפלציה |
|----|-------|-------|-----------|---------|----------------------|------------------------------|---------------------|---------|----------|
| 13 | REACTIVE_SHORT | 7414.25 | 7418 | 3.75 | $18.75 / 15R | ✓ R=usd/טיק | **≈+1.19R** (C1 1.0·C2 2.5·C3 0.07, ÷3) | 26.75R | ~22× |
| 12 | HTLB | 7443.75 | 7447.25 | 3.50 | $17.50 / 14R | ✓ 17.5/14=$1.25 | **≈+0.38R** (C1 1.0·C2/C3 BE, ÷3) | 16R | ~42× |
| 10 | REACTIVE_SHORT | 7444 | 7443.75* | ~13 (לפי register) | $230 / 92R | ✓ זהה | **≈+1.17R** | 92R | ~79× |

\* id=10 `stop` בטבלה=7443.75 אך זהו ה-trailing/BE; ה-`stop_initial` האמיתי ≈13pt לפי
register — לכן R-הנכון תלוי ב-stop_init, **ל-CC לאשר מול `v9_trades.stop_initial`**.

**מסקנה:** השורש של I-22 כעת חד-משמעי — המכנה הוא ערך-טיק ($1.25) ולא דולר-הסיכון.
תיקון = §DESIGNS I-22.

---

## 3. לקחים (Lessons)

**אילו תבניות נדרכות-הרבה-ולא-יורות (ולמה):** כל S2 (10) ו-S4 (7) נדרכו ברוב היום אך
לא ירו — **לא** בגלל ספים שמרניים אלא כי **לא היה setup-בבר** (detection per-bar נכשל
לגיטימית: ratios/swings/poles לא התמלאו). זו התנהגות תקינה ביום ללא תבניות-מובהקות.

**אילו לא-נדרכות (ולמה):**
- **S3 (כל 4) — לא נדרכו כלל היום.** השורש: I-11 — קובץ `footprint` נכתב (FRESH 0s)
  אבל 0 ברים מגיעים ל-buffer. **חוסם 100% מ-S3.** זו הבעיה החמורה-מבנית #1.
- **S2/S4 בשעה הראשונה (08:30–09:00)** — לא נדרכו כי ערוץ ה-5דק'/study **לא עלה בפתיחה**
  (I-21 session-non-start). אבדה שעת-המסחר הראשונה (כולל הרצת-פתיחה, I-14).

**דחיות מוצדקות מול שמרניות-מדי:**
- **מוצדקות:** A1-veto על trend=GRAY (CCI חוצה אפס — אמיתי, לא תקלת-תצוגה; I-15 לא משחזר
  קונפליקט מנוע↔לוח); A7 R:R על HFE (0.29<1.0 — מבני).
- **חשד שמרני-מדי (לכיול, לא הוכח היום):** סף A7/טבלת stop-target של HFE — חוסם תבנית
  70%-conf באופן כמעט-קבוע (I-13). דורש כיול anchor פר-תבנית×יום (project: stop/target table).
- **תקלות-תצוגה (לא חוסמות-ירי):** I-16 `Missing: choppiness_ok` (פער score≠gate-flag,
  תנודתי גבול-בר I-17); I-18/I-20 TZ-mix + lag-predicate; I-1 פיצול day_type — **אף אחת
  מהן לא חסמה ירי בפועל**, אך מרעישות את הדיאגנוסטיקה.

---

## 4. סטטוס-סגירה פר-חשוד (תמצית; פירוט ב-ISSUES_REGISTER)

| # | חומרה | סטטוס-סגירה 2026-06-08 |
|---|-------|------------------------|
| I-11 | 🔴 | footprint 0 ברים כל היום (25 אישורים). ingest file→bridge→buffer שבור. מושתק `S3_MUTE` — לא נפתר. |
| I-21 | 🟡 | session-non-start בבוקר → התאושש ~09:00. residual-סגירה: woodies_5min מפגר ~16דק' אחרי five_min ב-14:53. |
| I-22 | 🔴 | **מאובחן לשורש** (R÷טיק). חוסם ΣR. |
| I-1 | 🟡 | פיצול state↔readiness נמשך, אך **לא חוסם S2** (10/10 armed בסגירה). residual: opening_type=UNKNOWN/session_min=0/vote_history=[]. |
| I-14 | 🔴 | הרצת-פתיחה לא רצה — השנה בעיקר עקב feed-dead בפתיחה (I-21), לא auth (auth נוקה). שרשרת opening→entry ל-CC. |
| I-13 | 🔴 | HFE@12:27 שוב נחסם A7 (R:R) — anchor/טבלת-stop חסרה. |
| I-3 | 🔬 | ZLR לא נדרך setup כל היום (RED→armed/no-pattern, GRAY→A1-veto). אין counterfactual. |
| I-16/I-17 | 🔬 | choppiness_ok flip-flop — תנודתיות גבול-בר, לא קלט-חסר-קבוע. לא חוסם בסגירה. |
| I-18/I-20 | 🟡 | TZ-mix + lag-predicate נמשכים. תצוגה/freshness, לא fire-path. |
| I-24 | 🟡 | tpo/tick_reversal_15/footprint `disabled (S3_MUTE/S5)` ⇒ verdict READY. **CC לאשר כוונה ולא דריפט + commit.** |
| I-15/I-19/I-23 | 🔬/🟡 | לא משחזרים בסגירה (trend מנוע↔לוח מסכימים; pattern-status <100ms; gateway counters נכונים ביום-ללא-עסקה). |

---

## 5. מקור-אמת ל-CC (הצלבת `~/SierraChart_Data/v9_export/` — חובה, לא בוצע כאן)

read-only API בלבד. כל הבאים דורשים הצלבה מול ה-export הגולמי:
1. **I-21 שורש:** למה `woodies_5min`/`5min_bars`/`tick_reversal` לא התחילו לכתוב ב-08:30 CT
   בעוד `footprint`/`cumulative_delta`/`volume_profile`/`imbalance` כן.
2. **I-21 residual:** למה `woodies_5min`-export מפגר ~15דק' אחרי `five_min` לקראת הסגירה.
3. **I-11:** נתיב file→bridge→buffer של footprint (קובץ נכתב, 0 ברים ל-buffer).
4. **I-15:** הצלבת `cci_14`/`swi`/`ema_34`/`lsma` גולמי מול ה-export (פער UI↔endpoint ~15–56pt לאורך היום).
5. **I-22:** אימות `stop_initial` של id=10 ב-`v9_trades` כדי לאשר את ה-R-הנכון.

---

*עודכן: 2026-06-08 15:12 CT · סוכן-EOD (Cowork) · read-only*
