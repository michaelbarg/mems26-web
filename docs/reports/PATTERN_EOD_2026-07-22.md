# PATTERN EOD — 2026-07-22 (Cowork, אוטונומי · יום-SIM אחרי-cutover)

**שער-זמן I-9:** ✅ `TZ=America/Chicago date` → `2026-07-22 15:12 CDT` (IL 23:12). RTH סגור → מפיק EOD.

**⚠️ מקור-נתונים (Rule 1 — כשל-כן > ערך-סינתטי):** בריצה-אוטונומית זו **Chrome לא-מחובר** (`list_connected_browsers=[]`) וה-sandbox **לא-מגיע ל-`localhost:8000`/Postgres של המאק**. לכן `/trades/recent` ו-`/chart/bars5min` **לא-נמשכו**. מסלול-המחיר והתוצאות **שוחזרו מ-`docs/reports/OPS_LOG_2026-07-22.md`** (עקבת-ביצוע Sierra-מבוססת: fills/stops/T1 + מחירי-טריגר של gateway BLOCKED/FIRED). כל שורה מסומנת **`↻CC`** = דורשת הצלבה מול `~/SierraChart_Data/v9_export/` + `v9_bars_5min_woodies`. **שום קוד/flag/.env/DB לא-שונה (read-only).**

**מקורות שנקראו:** `OPS_LOG_2026-07-22.md` · `FAULTS_AND_FIXES_2026-07-22.md` · `EOD_REVIEW_2026-07-22.md` · `briefings/BRIEF_2026-07-22.md` · `MEMS26_ISSUES_REGISTER.md` (קטלוג I-1…I-75) · `git log` (HEAD `f5a087d5`). **אין `PATTERN_DIAG_2026-07-22.md`** — cron-snapshots-30דק' מושבת מ-06-10 (I-9-קשור); הניתוח מבוסס OPS_LOG.

---

## 1. תמונת-יום

- **מצב:** יום-מסחר פעיל בבוקר (live) → **cutover ל-SIM ב-12:09 ET** (`MEMS26_MODE=sim`, Michael: "לא נעשה כמו שצריך") + מגה-אימות. ~6+ ריסטארטים (I-74).
- **מבנה-מחיר (ET):** פתיחה ~7515 → זחילת-בוקר 7530→**שיא 7562.25 (12:33)** → דעיכת-אחה"צ 7562→7544 → צ'ופ 7544–7557 עד הסגירה. IB-high 7556.25 (נפרץ; breakout-watch הסיר override ל-Normal ב-18:34 IL). טווח ~47pt.
- **סוג-יום:** מכונה נתקעה `Trend_Normal` (escalation-only) → **override ידני מייקל → Normal** (18:20 IL, Dalton walkthrough) → breakout-watch → `Normal` דרך `get_live_day_type`.
- **P&L:** `v9_trades` live = **$0.00** · **Sierra = +$37.50** (סגירה 13:00, = רגל-T1 של GB100 SHORT #466). **פער-רקונסיליאציה 🔴** (records≠reality — ראה §5).
- **flag_guard:** PASS 111/111 (על המערכת-הרצה; 3 דגלי-cc-החדשים עדיין לא-ב-.env — ראה §5).

---

## 2. טבלת-תבניות מסודרת (S2/S3/S4)

מספרים = **setups מובחנים** ב-RTH (re-triggers של אותו setup מכווצים לשורה). "נדרכה"=eligible+detector-רץ · "נורתה"=נוצרה עסקה (live/shadow).

| מערכת | תבנית | נדרכה # | נורתה # (live/shadow) | לא-נדרכה (סיבה) | לא-נורתה # — פירוק-שער | תחזית-נגד W/L, ΣR |
|-------|-------|:---:|:---:|---|---|---|
| **S2** | REACTIVE_LONG | 2 | 1 (0/1 #467) | — | 2: `rr_entry`×1 (11:22) · `location_gate`×1 (14:30) | 1W/1flat → **+2R** (rr false-block); loc=0R justified |
| **S2** | REACTIVE_SHORT | 3 | 0 | — | 3: `daytype_playbook`×3 (10:45/13:35/14:12) | 0W/3L → **−3R avoided (כולם justified)** |
| **S2** | BEAR_FLAG_SHORT | 1 | 0 | — | 1: `entry_not_confirmed` (13:35) | 0W/1L → **−1R avoided (justified)** |
| **S2** | INITIATIVE_L/S · INV_HNS · HNS_TOP · DOUBLE_B/T · BULL_FLAG | 0 | 0 | לא-נדרכה (אין תבנית-גיאומטריה / buffer-reset I-74) | — | — |
| **S3** | ABSORPTION · STACKED_IMB · SWEEP_RETURN · EXHAUSTION | 0 | 0 | **S3 muted (I-11 / S3_MUTE)** — footprint לא-מעובד | — | — (מובנה) |
| **S4** | ZLR | ~8 | 5 (2/3: #460L,#468,#469 short; #462/#464 order_failed) | — | ~11 blk: `cont_trend`×~7 (12:45–15:10) · `rr_entry`×3 (11:40/13:50) · `lsma_flat`×2 (14:50) · `entry_not_confirmed`×1 (12:33) | mix → **גזרת-הליבה, ΣR פירוט §3** |
| **S4** | GB100 | 2 | 1 (1/1 #466 **T1=+$37.50** ✅) | — | 1: `lsma_flat` (11:10) | +2R (lsma false-block); #466=**הזוכה-האמת** |
| **S4** | FAMIR | 2 | 1 (0/1 #470) | — | 1: `rr_entry` (13:40) | −1R avoided (justified) |
| **S4** | TLB · TT · HFE · HTLB | 0 | 0 | לא-נדרכה (אין setup בגיאומטריית-היום) | — | — |

**נורו-בפועל (11 fires, מ-OPS_LOG):** #459/#460 ZLR SHORT @7535 (shorted-the-rally) → STOP −82.5/−67.5 · #461/#463 ZLR LONG @7557–58 (bought-top) → STOP −71/−60 · **#462/#464 ZLR LONG order_failed r=−1 → BE(0)** · **#465/#466 GB100 SHORT @7557.75 → T1 (#466=+$37.50 ✅)** · #467 REACT_LONG @7556 → STOP −48.75 · #468/#469 ZLR SHORT @7553 → T1 (fade) · #470 FAMIR LONG @7547.75 → ~STOP · #471/#472/#473 ZLR SHORT @7544–45 → צ'ופ/לא-נסגר.

---

## 3. תחזית-נגד (counterfactual) — signals שזוהו-אך-נחסמו

שיטה: לכל setup-חסום, entry=מחיר-הטריגר, stop=3.25pt (חציון-fills היום), T1=1R, T2=2R; **replay** על מסלול-המחיר בפועל (OPS_LOG). מאומת ב-`cf_2026-07-22.py` (Rule 5, output למטה).

| setup חסום | שער | side | entry | תוצאה-CF | R | פסק |
|---|---|:--:|--:|:--:|--:|---|
| REACT_SHORT | daytype_playbook | S | 7530.0 | STOP | −1.0 | ✅ justified (שורט לתוך ראלי) |
| **GB100_LONG** | **lsma_flat** | L | 7548.75 | **T2** | **+2.0** | 🔴 **false-block** (זחילת-עלייה) |
| **REACT_LONG** | **rr_entry** | L | 7552.25 | **T2** | **+2.0** | 🔴 **false-block** |
| **ZLR_LONG** | **rr_entry** (cluster) | L | 7554.0 | **T2** | **+2.0** | 🔴 **false-block** |
| ZLR_LONG | entry_not_confirmed (שיא) | L | 7562.25 | STOP | −1.0 | ✅ justified (קניית-שיא-מדויק) |
| ZLR_LONG | cont_trend (post-peak) | L | 7560.75 | STOP | −1.0 | ✅ justified |
| BEAR_FLAG_SHORT | entry_not_confirmed | S | 7551.5 | STOP | −1.0 | ✅ justified |
| REACT_SHORT | daytype_playbook (pm) | S | 7551.0 | STOP | −1.0 | ✅ justified |
| FAMIR_LONG | rr_entry | L | 7555.75 | STOP | −1.0 | ✅ justified |
| **ZLR_SHORT** | **rr_entry** (pm) | S | 7552.75 | **T2** | **+2.0** | 🟠 **false-block** (fade תפס) |
| REACT_LONG | location_gate | L | 7547.0 | timeout | 0.0 | ✅ justified (צ'ופ) |
| ZLR_SHORT | cont_trend+lsma_flat (pm) | S | 7544.25 | timeout | 0.0 | ✅ justified (צ'ופ) |

**ΣR-נגד (חסומים) = +2.0R** · n=12 · **W4/L6/flat2**.

**פירוש:** הסך-הכל **מתון-חיובי** — הגייטים **הותירו ~+2R על-השולחן**, מרוכזים כמעט-כולם ב-**`rr_entry_gate` (×3) + `lsma_flat` (×1)** שחסמו לונגים-של-זחילת-הבוקר (7548→7562) + שורט-fade-אחה"צ אחד. שאר 6 החסימות (`daytype_playbook`/`entry_not_confirmed`/`cont_trend`) **מוצדקות** — חסכו 6R של הפסדים (שורטים-לתוך-ראלי, קניות-שיא, קניות-post-peak). **המסקנה: הגייטינג היה דוקטרינרית-שפוי; הדליפה = rr_entry_gate + lsma_flat over-block על מבנה-כניסה-תקף בזחילה — המשך-ישיר של הפספוס-הבודד ב-07-20 (rr_entry false-block ~+2R) וממשפחת I-70.**

**הערת-ביצוע (לא-שער):** #462/#464 (ZLR_LONG order_failed r=−1) — במודל-הפשוט STOP, אך בפועל היו נוגעים T1 7561.5 (@12:33) ואז דועכים → **~ניטרלי בעסקה-הזו**; הכאב הוא **אמינות-הביצוע** (I-76), לא ה-P&L של המופע הבודד.

```
BLOCKED-signal counterfactual: n=12  W=4 L=6 flat=2  SigmaR=+2.0R
GB100_LONG/lsma_flat 11:10 LONG 7548.75 T2 +2.0 | REACT_LONG/rr_entry 11:22 LONG 7552.25 T2 +2.0
ZLR_LONG/rr_entry(cluster) 11:40 LONG 7554.0 T2 +2.0 | ZLR_SHORT/rr_entry(pm) 13:50 SHORT 7552.75 T2 +2.0
(6× justified STOP −1.0 · 2× timeout 0.0)
```

---

## 4. לקחים (סיכום)

**א. תבניות שנדרכות-הרבה-ולא-יורות (ולמה):**
- **ZLR (S4)** — הכי-פעילה (~8 setups). בבוקר נחסמה LONG ב-`rr_entry` (×3, כולן היו-מנצחות +2R) ואז ירתה LONG בשיא (order_failed/STOP). אחה"צ נחסמה SHORT שוב-ושוב ב-`cont_trend` (×7, מוצדק — צ'ופ). **דפוס: ה-detector צודק בכיוון אך ה-rr_entry_gate מאחר/חוסם את הכניסה-הטובה ומאשר את המאוחרת-הגרועה.**
- **REACTIVE_SHORT (S2)** — נדרכה 3× ונחסמה 3× ב-`daytype_playbook` — **כולן מוצדקות** (שורט-נגד-מבנה ביום-Normal-עולה). הגייט עבד.

**ב. תבניות שלא-נדרכות (ולמה):** INITIATIVE / HNS / DOUBLE / BULL_FLAG / TLB / TT / HFE / HTLB — **0 דריכה**: אין גיאומטריה-מתאימה ביום-צ'ופ-צר + **buffer-S2 מתאפס בכל-ריסטארט (I-74, ~6 ריסטארטים)** → עיוורון 15–20דק' פר-ריסטארט. **S3 (footprint) 0 — מובנה (I-11/S3_MUTE).**

**ג. דחיות מוצדקות מול שמרניות-מדי:**
- **מוצדקות (8/12, חסכו 6R):** `daytype_playbook` ×3 · `entry_not_confirmed` ×2 (כולל קניית-שיא 7562) · `cont_trend` post-peak · `location_gate` · pm-chop.
- **שמרניות-מדי / false-block (4/12, עלו +8R-פוטנציאל):** **`rr_entry_gate` ×3** + **`lsma_flat` ×1** — כולן על **לונגי-זחילה-תקפים-מבנית** (7548→7562). `lsma_flat` ב-11:10 חסם לונג בזמן-שהמחיר-עלה-ברציפות → LSMA לא-באמת-שטוח שם (חשד false). **זה החוט-החם לתיקון** (§DESIGNS D-A).

**ד. הכאב-האמת של היום = לא-פספוס-שער אלא בטיחות+ביצוע:** אורפן-עירום −10 (I-68, §5), order_failed r=−1 (I-76), ופער-רקונסיליאציה. הגייטינג הציל יותר ממה-שעלה.

---

## 5. חשודים-חמורים שהתממשו/עלו היום (פירוט ל-§register + §DESIGNS)

- **🔴🔴 I-68 (אורפן-עירום) — חזר בפעם-ה-4-בשבוע על-כסף-אמת.** 18:07 IL: **naked SHORT −10 @7538.12**, `working=0`, מחיר 7548.75 → **−$531 פתוח**. קדם לו #460 ZLR SHORT live 17:55 @7535 → STOP 7539.5 −67.50 (נרשם CLOSED). TM=0, Sierra=−10 → **records≠reality**. reconciler התריע q30s + המליץ stop-מגן @7548 אך **חסום מ-heal** (`ORPHAN_AUTO_STOP_V1=0`, אין PLACE_STOP sim-מאומת). Journal-אירועים **ריק ל-17:50–18:10** (capture-gap שוב, I-81). מייקל התריע ×2, שיטח ידנית. **בטיחות > P&L · חוסם-LIVE.**
- **🔴 I-76 (חדש) — order_failed r=−1 על כניסת-live.** #462/#464 ZLR LONG נורו live בשיא → Sierra דחתה (`ORDER_FAILED:-1`) → נרשם BE ואז CANCELLED. P8a/P10a תיקנו **כנות-תצוגה** (outcome=CANCELLED/order_failed, "Sierra דחתה" אדום) אך **השורש** (למה Sierra דוחה כניסת-live, OCO-per-contract) פתוח. משפחת op=EXIT-broken.
- **🔴 I-73/I-40 (זיהום-ברים) — 12 זוגות +1h היום** (TS-HOUR-FIX ממשיך @22:10). cc בנה `WOODIES_TS_HOUR_FIX=0` (P2) **אך לא-הודלק** (regressions). **תיקון-שורש-אמת:** ה-offset ה-raw = −5h מ-wall-clock → `=0` **מסיר-כפילות אך משאיר ברים ב-−1h** → צריך תיקון-offset-בכניסה, לא רק =0 (cowork measured, LIVE_CHANNEL 16:02).
- **🔴 I-80 (חדש) — TPO/VA שגוי ב-DB, נפרד-מזיהום-הברים.** `v9_tpo_sessions` id1523=**3.5pt** מול Sierra `tpo.json` **בריא 19.5pt** (VAH7555/VAL7535.5). **השורש (commit `f5a087d5` diagnose):** ה-backend **מחשב-מחדש TPO מברים-מזוהמים** ומתעלם מ-VA הקנוני של Sierra. תיקון = לקרוא VA קנוני כמו ש-IB עושה (Rule 1). ↻CC.
- **🟠 I-79 (חדש) — S2/S4 עיוורים ל-S1 בזיהוי.** `day_type_at_fire` **ריק 8/8** על כל ה-setups; `_detect_reactive` לוקח רק-ברים. opening-type סווג (OPEN_DRIVE) אך **OPENING_ENTRY_V1=shadow** → לא-מניע live. ארכיטקטורלי (S1=מוח, S2/S4=ידיים) — cursor+cowork+cc triple-confirmed.
- **🔴 I-77 (חדש, dev-process) — דליפת-state ברמת-החבילה מ-mega-fix.** `_hydrate_decisions` (trading_gateway.py:240) טען `gateway_decisions.jsonl` האמיתי לכל gateway כולל-בטסטים (len16 vs 2) → 12–15 regressions + **סיכון-פרודקשן** (gateway-חדש בולע-החלטות-קודמות בריסטארט). **HEAD `b00346e9` "decisions hydrate opt-in"** נחת אחרי ה-NO-GO → **דורש אימות-חבילה חוזר** (145/145) לפני GO. ↻CC.
- **🟠 I-78 (חדש) — migration 023 (`pnl_sierra`) לא-אומת-רץ.** הקובץ קיים (`backend/v9/db/migrations/versions/023_pnl_sierra_column.py`) + מודל `trades.py` עודכן, אך `\d v9_trades`→count=0 בבדיקת-cowork (~22:40) → P9c (cross-check pnl_sierra) **inert בפועל**. ↻CC (הרץ migration + אמת).
- **🟡 I-74 (buffer-S2 מתאפס) — נמשך.** ~6 ריסטארטים → S2 עיוור → סיבה-מרכזית ל-0-דריכה של INITIATIVE/HNS/FLAGS.
- **🟡 I-1/I-71 (פיצול-סוג-יום) — תפקד-הגנתית אך נתקע.** escalation-only → מייקל override ידני. `DAYTYPE_ACCEPTANCE_DEMOTION_V1`+`DAYTYPE_BOOT_SEED_CANONICAL_V1` (P6a/b) **בנויים ב-RULED=1 אך לא-ב-.env** → לא-חיים.

---

## 6. מקור-אמת — משימות-הצלבה ל-CC (`~/SierraChart_Data/v9_export/`)

1. **↻CC I-68** — אימות-חזותי Sierra 37138283 בזמן-האורפן; שורש `ORPHAN_AUTO_STOP_V1`-חסום + phantom-heal; feed-אירועים ריק 17:50–18:10 (regex live-format, I-81).
2. **↻CC I-76** — למה כניסת-live #462/#464 החזירה r=−1 (OCO-per-contract) מול Sierra-log.
3. **↻CC I-73** — offset raw −5h: אמת ש-`WOODIES_TS_HOUR_FIX=0` מנחית בר-טרי ל-ts-נכון (לא −1h) בסים לפני-הדלקה.
4. **↻CC I-80** — `v9_tpo_sessions` id1523 (3.5) מול `tpo.json` (19.5) — אמת שהתיקון (VA קנוני) סוגר את הפער.
5. **↻CC I-77/I-78** — הרץ חבילת-טסטים מלאה (parent-parity 145/145 אחרי `b00346e9`) + migration 023; הדבק raw (Rule 5).
6. **↻CC counterfactual** — הצלב את מסלול-המחיר-המשוחזר (§3) מול `v9_bars_5min_woodies` 09:45–14:10 CT; אשר/הפרך את ה-+2R (rr_entry/lsma_flat false-blocks).

**מדגיש שוב: read-only. שום קוד/flag/.env/DB לא-שונה.**
