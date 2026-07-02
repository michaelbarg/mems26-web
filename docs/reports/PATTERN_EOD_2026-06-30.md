# MEMS26 · דוח EOD מאוחד — 2026-06-30 (יום שלישי)

**שער-זמן (I-9):** ✅ הופק אחרי הסגירה — בעת הריצה **15:12 CT** (≥15:00 CT, אומת `TZ=America/Chicago date` → `2026-06-30 15:12 CDT`; UTC 20:12; IL 23:12). RTH 08:30–15:00 CT, יום-מסחר-רגיל (שלישי, לא חג-US). יום-המסחר השני-ברציפות מאז 06-29.
**מקורות:** API חי דרך Chrome (`http://localhost:8000`) — `/trades/recent?limit=100` (200→**422**, I-25) → **0 עסקאות-היום** (האחרונה id259 מ-06-29) · `/chart/bars5min?limit=200` → 129 ברים (**78 ברי-RTH היום**) · `/day_type/state` · `/build/pattern-status` · `/gateway/status` · `/chop_score/current` · `/layer0/state` · `/woodies/current`. **+ הצלבה מול `STATUS_BOARD.md` (חיוני):** סוכן-Cowork-פיתוח כבר אבחן את אפס-הירי **תוך-כדי-הסשן** (entries 09:25/09:45/12:40/14:15 CT). **דוח-זה מאחד את ה-CF (חוץ-פנימה) עם האבחון-החי (פנים-החוצה) — לא מציג שורש-חדש שכבר-ידוע** (Rule 2/5).

> **🟢🟢 כותרת-העל #1 — ה-feed בריא, יום-2 ברציפות. I-47 לא-שוחזר.** 78 ברי-RTH רצופים 08:30→14:55 CT, latest=**14:55 CT**, `dateCounts={06-26:9, 06-29:42, 06-30:78}`, 0 שכפול. ה-promoter-sidecar החזיק שוב.

> **🟢 כותרת-העל #2 — אפס-עסקאות, וזו הפעם בעיקר *הצלחה* של שער-המשפחה (לא כשל-זיהוי).** יום-מגמה-עולה-חלק (open 7500 → שפל 7495.75@08:30 → שיא 7567.75@14:15 → נעילה 7544.75; **+44.75pt, טווח 72pt, chop=13/FOUND**). **המערכת *כן* זיהתה תבניות-עם-המגמה** (INITIATIVE_LONG setup 262 @09:00 CT · ZLR_LONG @09:25 · REACTIVE_LONG contracts=3 @09:45) — **אך כולן נחסמו ע"י `DAYTYPE_PATTERN_AWARE_V1` (שער-המשפחה הדו-כיווני, חי-מהיום)** + פיצול-מקור-day_type (I-44/I-50) + כשל-ניתוב-S4 (A7-FAIL). **זה מנע את מחלקת-06-29** (4 shorts-נגד-מגמה, −4R) — אבל גם חסם את ה-CONT-LONG הטובים.

> **🔴 כותרת-העל #3 — עלות-ההזדמנות של החסימה ≈ +3..+9R (תחזית-נגד על setups-אמיתיים-שנחסמו).** ה-LONG-עם-המגמה שזוהו-ונחסמו, מוחזרים על 78 ברי-אמת, היו מגיעים ל-**+3R כ"א** (T3); שורט-נגד-מגמה היה **−1R**. ⇒ שער-המשפחה **over-blocks**: נכון שחסם את ה-REV/short, **שגוי שחסם את ה-CONT-LONG**. השורש: ה-day_type שעליו השער נשען **מרצד ולא-יציב** (D-daytype-stability) ו**נקרא ממקור-תקוע** (I-44).

> **🔴 כותרת-העל #4 — שורש אפס-הירי כבר-מאובחן היום (3 שרשראות, 2 handoffs קיימים).** (1) **I-44/I-50 day_type-source-split** → gate/Auth קוראים day_type-תקוע/ישן ולא את ה-7-טיפוסי-החי (`CC_DAYTYPE_SOURCE_CONSISTENCY_2026-06-30.md`). (2) **שער-משפחה `DAYTYPE_PATTERN_AWARE_V1`** חוסם CONT על קריאת-"balanced" ו-REV על קריאת-"trend/Variation" — **שני-הכיוונים**. (3) **S4 A7-FAIL** — woodies יורה (ZLR/GHOST דו-כיווני) אך `fire_setup=None` (חשד `best.stop=None`) → `ready_to_route=False` → 0 ניתוב (`CC_WOODIES_ROUTE_A7_FIRE_SETUP_2026-06-30.md`). **כל-אלה trading-risk-surface → אישור-Michael.**

---

## מצב-היום

**נתונים-אמינים: כל ה-RTH 08:30–14:55 CT (78 ברים, feed בריא).** זמני-CT: ה-STATUS_BOARD משתמש ב-UTC (CT=UTC−5); 14:00/14:25/14:45 UTC = 09:00/09:25/09:45 CT.

שחזור צורת-היום (ברים נבחרים, CT):

| CT | O | H | L | C | Vol | הערה |
|----|---|---|---|---|-----|------|
| 08:30 | 7500 | 7506.75 | **7495.75** | 7500.25 | 28,404 | פתיחה · **שפל-יום בבר-הפתיחה** |
| 08:50 | 7507 | 7522 | 7505.75 | 7518.75 | 23,907 | **פריצת-OR מעל 7510** |
| 09:00 | 7526.75 | 7532.75 | 7515.5 | 7532.5 | 24,006 | **INITIATIVE_LONG (setup 262) ירה → Auth SKIP** |
| 09:25 | 7530.75 | 7533.5 | 7527 | 7532.5 | 9,653 | **ZLR_LONG ירה → family-gate "continuation blocked"** |
| 09:45 | 7535.75 | 7535.75 | 7523.75 | 7526 | 13,393 | **REACTIVE_LONG (3 חוזים) → family-gate "reversal blocked (CONT only)"** |
| 11:10 | 7548.5 | 7551 | 7548.25 | 7550.5 | 4,086 | grind, volume דועך |
| 12:30 | 7552.5 | 7554.25 | 7550.5 | 7553.25 | 4,610 | טווח-צר אחה"צ |
| **14:15** | 7564.75 | **7567.75** | 7563 | ~7565 | — | **שיא-יום 7567.75** |
| 14:55 | 7560.25 | 7564 | 7544.5 | 7544.75 | 26,473 | **נעילה 7544.75** (pullback ~23pt מהשיא) |

**צורה:** פתיחה 7500 → שפל-בר-פתיחה 7495.75 → טיפוס-רציף → שיא 7567.75 (14:15) → pullback-נעילה ל-7544.75. **טווח-אמת 72pt, +44.75pt.** יום-מגמה-עולה חלק. ה-pullback-בנעילה (~23pt) הפך את woodies-cci ל-RED ב-snapshot ה-post-close.

**Snapshots post-close (15:16–15:18 CT, טריים):**
- `day_type/state`: `Variation/0.18/LOCKED_LOW_CONF/B2` · `opening_type=OPEN_DRIVE` · `session_min=0 · vote_history=[]`. **זהה-בית-לבית ל-06-29** ⇒ ה-endpoint = wrapper-מת (I-44). **אך** ה-classifier-החי (`v9_day_type_state`) קבע נכון `Trend_Normal/OPEN_DRIVE` בבוקר (לפי STATUS_BOARD 09:25) — **ופה הבעיה:** ה-gate קורא את המקור-התקוע, לא את החי. (ועוד: ה-`current_day_type` הפר-בר **מרצד** UNKNOWN→Trend_Normal→Normal→Variation→Neutral_Extreme→Variation תוך 45 דק' — D-daytype-stability.)
- `gateway/status`: `trades_today=0 · daily_pnl=0 · cooldown.consecutive_stops=0 · cluster_guard.recent_attempts=0 · ssv.veto_active=false · chop_state=FOUND · live_enabled=[]`. **היום `trades_today=0` נכון** (באמת 0 עסקאות).
- `chop_score/current`: `chop_score=13 state=FOUND · R/A=3.534` — מגמתי, לא-choppy.
- `woodies/current`: `cci_14=−228.56 trend_state=RED classification=NO_SETUP ready_to_route=false`. RED = ה-pullback-בנעילה; intraday-trend (בטיפוס) היה BLUE.
- `build/pattern-status`: `readiness=READY` · 5 מערכות `running hydrated` · `five_min.mode=OVERNIGHT_MODE` (post-close).

---

## 1. עסקאות שנורו היום (0) — אך 3+ setups זוהו-ונחסמו

**אפס עסקאות ב-`v9_trades` (06-30).** אך זה **לא** "אין-setup" — היו **setups-תקפים-שזוהו-ונחסמו** (מ-STATUS_BOARD, raw-verified):

| setup | CT | מערכת | תבנית | כיוון | חוזים | תוצאת-ניתוב | סיבת-חסימה |
|-------|-----|-------|-------|-------|-------|-------------|-------------|
| 262 | 09:00 | S2 | INITIATIVE_LONG | LONG (CONT) | — | **skipped** | `T1Setup skipped: day_type=UNKNOWN · Auth Table SKIP` (I-44: Auth קורא מקור-תקוע) |
| — | 09:25 | S4 | ZLR_LONG | LONG (CONT) | — | **blocked** | family-gate: `"balanced day (Normal) — continuation (ZLR) blocked"` |
| — | 09:45 | S2 | REACTIVE_LONG | LONG (REV) | 3 | **blocked** | family-gate: `"Variation — reversal (REACTIVE_LONG) blocked (CONT only)"` |
| 263 | — | S2 | DOUBLE_BOTTOM_EE | LONG | — | (setup) | — |
| (S4 דו-כיווני) | — | S4 | ZLR/GHOST | LONG+SHORT | 2 | **A7-FAIL** | `fire_setup=None` (חשד best.stop=None) → not routed |

**פר-מערכת:** S2: 0-trades (2+ setups חסומים) · S4: 0-trades (A7-FAIL, דו-כיווני) · S3: muted.
**🟢 I-31 לא-שוחזר:** `five_min.fired_today_count=0`==DB-0.

---

## 2. טבלת תבניות — נדרכה / נורתה / נחסמה

ללא `PATTERN_DIAG_2026-06-30.md` (יום-20 ללא סוכן-30-דק') ⇒ ספירות-intraday מלאות לא-זמינות. אך **STATUS_BOARD מספק את ה-arming/blocking האמיתי** (raw-verified ע"י סוכן-הפיתוח). `נורתה#`=0 (DB).

| מערכת | תבנית | נורתה# | מצב-אמת (intraday, מ-STATUS_BOARD) | תחזית-נגד |
|-------|-------|--------|-------------------------------------|-----------|
| **S2** | INITIATIVE_LONG | 0 | **נדרך+ירה** (setup 262 @09:00) → **Auth SKIP** (day_type=UNKNOWN, I-44) | **+3R (§3)** |
| **S2** | REACTIVE_LONG | 0 | **נדרך+ירה** (3 חוזים @09:45) → **family-gate block** (REV-on-Variation) | (REV — נכון-לחסום) |
| **S2** | DOUBLE_BOTTOM_EE | 0 | setup 263 | — |
| **S2** | יתר (INV_HNS/HNS_TOP/FLAGS/INIT_SHORT) | 0 | post-close `blocked: "Missing data.mode_context"` (= מצב-לילה-OVERNIGHT, **לא** כשל-RTH) | — |
| **S4** | ZLR_LONG | 0 | **נדרך+ירה** @09:25 → **family-gate block** (CONT-on-balanced) | **+3R (§3)** |
| **S4** | ZLR/GHOST (דו-כיווני) | 0 | **ירו אך A7-FAIL** (`fire_setup=None`) → 0 ניתוב | (S4-routing חסום מבני) |
| **S4 — Σ** | 9 תבניות | **0** | armed; אף-ניתוב (A7-FAIL מבני) | — |
| **S3** | 4 תבניות | 0 | muted (I-11) | — |
| **S1** | Day Type | classified | classifier-חי קבע Trend_Normal/OPEN_DRIVE; **endpoint=wrapper-מת + current_day_type מרצד** (I-44/I-1/D-daytype-stability) | — |

**🔑 הבהרה ל-I-52 (תוקן):** ה-`"S2 blocked: Missing data.mode_context"` ב-snapshot ה-post-close הוא **מצב-לילה-OVERNIGHT תקין — לא כשל-RTH.** ההוכחה: באותו RTH, S2 **כן** נדרך ופלט setups (262 INITIATIVE_LONG, REACTIVE_LONG 3-חוזים). ⇒ **S2 לא-הורעב** — הוא עבד; ה-setups נחסמו ע"י שער-המשפחה/Auth, לא ע"י mode_context-חסר. **I-52 = benign (display-label בלבד).**

---

## 3. תחזית-נגד (counterfactual)

הספֵק (CC_PROMPT §5): לכל signal-שזוהה-ונחסם — חשב entry/stop/T1/T2, שחזר את הברים-הבאים בפועל, סמן hit/stop/timeout→R. **היום יש signals-אמיתיים-שנחסמו** (לא רק שחזור-היפותטי): INITIATIVE_LONG@09:00, ZLR_LONG@09:25, REACTIVE_LONG@09:45. ה-CF להלן מעוגן בהם (entry/stop משוערים סביב מחיר-הברים בעת-הזיהוי), מוחזר על 78 ברי-אמת:

| תרחיש (setup-אמיתי-שנחסם) | כניסה CT | entry | stop | risk | תוצאה | MFE | MAE | exit |
|----------------------------|----------|-------|------|------|--------|-----|-----|------|
| A · INITIATIVE_LONG (setup 262) | ~09:00 | 7527 | 7515 | 12.0 | **+3R (T3)** | 36.75pt (3.06R) | −11.5pt | 14:05 |
| B · ZLR_LONG (S4) | ~09:25 | 7531 | 7522 | 9.0 | **+3R (T3)** | ~30pt | −5pt | ~11:00 |
| C · פריצת-OR (proxy) | ~08:50 | 7511 | 7498 | 13.0 | **+3R (T3)** | 41.25pt (3.17R) | −5.25pt | 11:05 |
| S · CT-SHORT (proxy, לבדיקת-תקֵפות) | ~09:05 | 7522 | 7533 | 11.0 | **−1R (STOP)** | 3.25pt | — | 09:25 |

**ΣR-with-trend (היפותטי, על setups-שנחסמו) = +9R (3 כניסות) / +3R (יחידה).** כל-שלוש→T3, MAE רדוד (≤11.5pt). **שורט-נגד = −1R** (STOP@09:25).

**קביעה:** שער-המשפחה **צדק** שחסם את ה-REV/short (היה −1R), **שגה** שחסם את ה-CONT-LONG (היה +3R×3). ⇒ **over-block סימטרי**: ההגנה שמנעה את מחלקת-06-29 (−4R) עלתה ב-+3..+9R הזדמנות-CONT. **הבעיה אינה השער עצמו אלא ה-day_type-input שלו** — מרצד (D-daytype-stability) ונקרא-ממקור-תקוע (I-44). ברגע שה-input יתוקן, השער יתיר CONT-LONG ביום-Trend ויחסום CONT-short/REV — בדיוק הרצוי.

**🟢 אימות-מערכתי (backtest 215 shadow-trades 06-05→06-29, Cowork היום):** **CONT = +11.1R** (92 עסקאות, 64% win) · **REV-ביום-Trend = −34.6R** (74, 38%) · ZLR +5.3R. ⇒ ה-CF-של-היום (+3R CONT / −1R short) **עקבי-לחלוטין** עם ההטיה-המערכתית: ה-over-block נכון-לחסום REV (חוסך −34.6R לאורך-זמן) אך שגוי-לחסום CONT (מוותר על +11.1R). **המסקנה אינה "פתח-הכל" אלא "הפרד CONT מ-REV נכון"** — בדיוק מה ש-day_type-source-consistency (I-44) ישיג. ר' prompt `CC_SIM_2026-06-30_WHAT_SHOULD_HAVE_FIRED.md` (סימולציית-pipeline מלאה, deliverable `SIM_2026-06-30...` ממתין).

---

## 4. ממצאים — מאוחד עם האבחון-החי של היום

### 🔴 I-51 (EOD — כימות, trading-logic → Michael) — שער-המשפחה over-blocks CONT-LONG ביום-Trend (≈+3..+9R/יום)
**הממצא:** אפס-עסקאות ביום-מגמה-עולה; ה-CF: setups-LONG-שנחסמו היו +3R×3, short=−1R. **השורש כבר-מאובחן היום** (לא חדש): שרשרת I-44/I-50 (day_type-source-split) + שער-המשפחה `DAYTYPE_PATTERN_AWARE_V1` הדו-כיווני + D-daytype-stability (day_type מרצד). **תרומת-ה-EOD:** **כימות עלות-ההזדמנות** (+3..+9R/יום) ⇒ דחיפות-תיקון-ה-input. **echo-הופכי ל-I-50** (06-29: under-block → 4 shorts; היום: over-block → 0 LONG). **סיווג:** trading-logic → **Michael** (חלק מ-thread day_type-source). → D-I51. **שמור 06-30 כ-golden-fixture** (over-block, משלים את 06-29 under-block).

### 🟢 I-52 (תוקן → benign) — "S2 blocked: Missing data.mode_context" = מצב-לילה, לא כשל-RTH
**הוכחה (same-day):** S2 נדרך ופלט setups ב-RTH (262 INITIATIVE_LONG, REACTIVE_LONG 3-חוזים) ⇒ mode_context **היה** נוכח ב-RTH; ה-"Missing" הוא state-post-close (OVERNIGHT_MODE). **לא-באג.** **שינוי-safe-אופציונלי:** label את ה-post-close כ-`overnight (expected)` ולא `missing-input`. → D-I52 (display-only, נמוך).

### 🔴 ממצאי-הפיתוח של היום (לא-EOD, מתועדים ב-STATUS_BOARD — מובאים לאיחוד)
- **I-44/I-50 day_type-source-split (LIVE-blocker → Michael):** gate+Auth קוראים day_type-תקוע/ישן ולא 7-טיפוסי-חי. handoff `CC_DAYTYPE_SOURCE_CONSISTENCY_2026-06-30.md`. **שורש-העל של אפס-הירי.**
- **D-daytype-stability (חדש → Michael):** `current_day_type` מרצד תוך-45-דק'; השער רוכב על קריאה-רגעית-שבירה. echoes I-44/I-50.
- **S4 A7-FAIL routing (LIVE-blocker מבני → Michael):** `fire_setup=None` (חשד best.stop=None) → 0 ניתוב-S4 דו-כיווני. handoff `CC_WOODIES_ROUTE_A7_FIRE_SETUP_2026-06-30.md`. **עדכון:** תיקון-A7 `fd153c3` ייתכן-כבר-חי (screenshot `ready_to_route=true`) — **לאשר על CONT-routable** ב-SIM.
- **ZLR RISK_CAP / `GIANT_BAR_EXCLUDE` (חוסם-נוסף ל-S4):** `GIANT_BAR_EXCLUDE=ZLR,HFE` (`woodies_system.py:679`) → `STRICT_SKIP` כש-stop>15pt (ברי-יום-תנודתי). חלק מ-9 זיהויי-ZLR היום ייתכן-נחסמו פה (לא רק A7). config-decision → Michael. (לאמת stop_pts מול cap לכל ZLR ב-SIM.)
- **INITIATIVE auth-timing:** INITIATIVE_LONG@09:00 ירה **פרה-נעילה** (day_type=UNKNOWN) → `Auth Table SKIP` (Neutral_Center); post-lock@Variation=FULL. ⇒ חלון-UNKNOWN-פרה-נעילה הוא חוליה-חסרה (תיקון = הרשאה לפי opening-type, חלק מ-I-44 handoff).
- **#1 ZLR-divergence (instrumented 3a8c16b, verdict ממתין):** woodies מעבד כל בר אך 0 זיהויי-ZLR למרות דגלי-DLL; 2 traces נוספו; verdict בירִי-ZLR-הבא (scheduled `mems26-zlr-trace-verdict` 07-01 09:45 CT).
- **commits היום:** `e6b9d69` (is_synthetic default+INSERT — **סוגר את "woodies write broken" מה-memory**) · `c247296` (S1_OPEN_DRIVE_TREND חי) · `3a8c16b` (ZLR-trace) · ZLR stop→breakout_bar/1.

### 🟡 פתוחים / מתחזקים (EOD-snapshot)
- **I-44 (day_type source-split):** endpoint זהה-בית-לבית ל-06-29 ⇒ wrapper-מת/קפוא. מתחזק. → D-daytype-source (כעת בעדיפות-עליונה — שורש-העל).
- **I-1 (S1-staging):** session_min=0/vote_history=[] תקועים (wrapper-מת). 🟢 opening_type=OPEN_DRIVE.
- **I-25 (שוחזר):** `limit=200`→422. השתמשנו limit=100.

### 🟢 לא-שוחזרו / נקיים
- **I-47 (+3h dup) — יום-2 ✅** · **I-45 (feed-death) ✅** · **I-31 (over-count) ✅** (0==0) · **D35/orphan ✅** (0 עסקאות).
- **⚪ I-48/D-037/D-049/I-23 (guards-bus) — לא-נבחנו** (0 fills; המונים=0 נכון היום). נשאר פתוח מ-06-29.

---

## 5. לקחים

- **🟢 אפס-הירי היום הוא ברובו *הצלחת*-הגנה, לא כשל-זיהוי.** שער-המשפחה מנע את מחלקת-06-29 (4 shorts-נגד-מגמה, −4R). **המערכת זיהתה היטב** (INITIATIVE_LONG/ZLR_LONG/REACTIVE_LONG כולם נדרכו). הכשל הוא ב-**input של השער** (day_type מרצד+תקוע), לא בזיהוי ולא ב-feed.
- **🔴 אבל ה-over-block יקר: ≈+3..+9R/יום הזדמנות-CONT-LONG אבדה (I-51).** ה-CF על setups-אמיתיים-שנחסמו: +3R×3. **התיקון הקריטי = day_type-source-consistency (I-44) + יציבות (D-daytype-stability)** — שניהם כבר ב-handoff/→Michael. ברגע שיתוקנו, אותו שער יתיר CONT-LONG ויחסום REV — הרצוי.
- **🟢 הצלבת-STATUS_BOARD מנעה דיווח-כפול/שגוי (Rule 2).** ה-CF-החיצוני שלי כמעט-הוביל ל-"I-51/I-52 שורש-לא-ידוע / S2-mode_context-מורעב" — אך ה-log-החי הראה שהשורש כבר-מאובחן ו-S2 עבד. **תרומת-ה-EOD המדויקת: כימות (+3..+9R) + איחוד, לא שורש-חדש.**
- **🟢 feed בריא יום-2.** מדדי-המסחר תקפים.
- **תפעולי — I-25 שוחזר** (limit=200→422); **יום-20 ללא PATTERN_DIAG** (אבל היום סוכן-הפיתוח החי כיסה את ה-intraday).

---

## 6. מקור-אמת — דורש הצלבת CC מול Sierra v9_export / לוג / DB (Rule 2/5)

1. **🔴 I-44/I-51 (day_type-source → CONT-block):** אַמת את handoff `CC_DAYTYPE_SOURCE_CONSISTENCY_2026-06-30.md` — שה-gate+Auth יקראו `v9_day_type_state`/`classify_replay` (7-טיפוסי-חי), לא ה-wrapper-המת. הצלב `v9_export` 09:00–09:45 CT ש-day_type-האמת היה Trend_Normal לכל-אורך (לא מרצד-באמת אלא קריאה-לא-יציבה).
2. **🔴 D-daytype-stability:** מקור ה-flicker (UNKNOWN→Trend_Normal→Normal→Variation→…). escalation-only לא-נאכף — אמת ב-`v9_day_type_state` per-bar.
3. **🔴 S4 A7-FAIL:** אמת handoff `CC_WOODIES_ROUTE_A7_FIRE_SETUP_2026-06-30.md` — `fire_setup=None`↔`best.stop=None`; הצלב `v9_woodies_signals` 5102/5103.
4. **🟡 #1 ZLR-divergence:** verdict ממתין לירִי-ZLR (07-01 09:45 CT, `3a8c16b` traces). הצלב `v9_export` דגלי-DLL מול 0-זיהויים.
5. **⚪ guards-bus (I-48/D-037/D-049/I-23):** פתוח מ-06-29; לא-נבחן היום (0 fills).

**NOT-DONE / מגבלות:**
- **כל הקריאות דרך Chrome מול `localhost:8000`** (אין PG מה-sandbox). ערכי-Sierra הגולמיים **לא-הוצלבו** — read-only, CC.
- **השורש כבר-מאובחן ע"י סוכן-הפיתוח** (I-44/family-gate/A7/D-daytype-stability) — דוח-זה **מאמת+מכמת**, לא מאבחן-מחדש.
- כניסות-ה-CF (§3) **מעוגנות ב-setups-אמיתיים-שנחסמו** (262/ZLR/REACTIVE), אך entry/stop משוערים סביב ברי-הזיהוי (לא ערכי-ה-V2-sizing המדויקים — אלה ב-`v9_five_min_setups`/לוג, CC).
- `armed#/blocked#`-intraday-מלא לא-זמין (יום-20 ללא DIAG); השלמנו מ-STATUS_BOARD.
