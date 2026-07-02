# MEMS26 · דוח EOD מאוחד — 2026-06-25 (יום חמישי)

**שער-זמן (I-9):** ✅ הופק אחרי הסגירה — בעת הריצה **15:12 CT** (≥15:00 CT, אומת `TZ=America/Chicago date` → `2026-06-25 15:12 CDT`; UTC 20:12; IL 23:12). RTH 08:30–15:00 CT, יום-מסחר-רגיל (חמישי, **לא** חג-US; Juneteenth כבר חלף ב-06-19).
**מקורות:** API חי דרך Chrome (`http://localhost:8000`) — `/trades/recent?limit=100` → 100 עסקאות, מהן **1 בלבד של היום** (id **245**) · `/chart/bars5min?limit=100` → **93 ברים** אך האחרון **06-25 09:40 CT** (≠ recent) · `/day_type/state` · `/build/pattern-status` (`ts=15:18 CT`, חי) · `/gateway/status` · `/chop_score/current` (`computed_at=15:16 CT`) · `/layer0/state` · `/woodies/current`. `limit=200`→נחסם (I-25), השתמשתי ב-cap=100.

> **🔴🔴 כותרת-העל — יום של נפילת-הזנת-נתונים, לא יום-מסחר. ערוץ ה-market-data מת ב-~09:40 CT והמערכת היתה עיוורת ~88% מ-RTH.** הברים (`/chart/bars5min`) **קופאים על 06-25 09:40 CT**; `pattern-status` סיסטם-0 **Bridge·Live Data Feed = `fresh:false, lag=9558s, last_bar_ts=null`**; S2+S4 `last_bar_ts=09:40 CT`, `lag=20358s` (~5.6h). **רק עסקה אחת נורתה** (id245 REACTIVE_LONG @09:35, **דקות לפני המוות**), והיא **תקועה-פתוחה** (`state=FILLED`, `outcome=null`, `pnl=0`, `bars_count=1`). זה השורש לכל-היתר: 0 עסקאות-נוספות, `day_type session_min=0`, 0 ברים אחרי 09:40.

> **🔴 הממצא-המהותי: זו נפילת-feed אמיתית, לא קריאת-טבלה-בייתה.** S4·Woodies — שקורא מ-`v9_bars_5min_woodies` (טבלת-ה-SoT-החיה לפי CLAUDE.md) — מראה **גם-הוא `last_bar_ts=09:40 CT`**. ⇒ זה **לא** ה-SoT-split של 06-22 (בו `/chart/bars5min` קרא טבלה-בייתה בעוד woodies חי); **שתי הטבלאות קפאו יחד** ⇒ **הגשר/Sierra-export עצמם הפסיקו להזרים ב-09:40 CT**. מיפוי: **I-45 חדש** (מוות-feed אמצע-RTH), קשור-ל-I-21 (ערוץ-5דק'-מת, אך שם=session-non-start; כאן=death-mid-session).

> **🟡 ממצא-נלווה (I-46 חדש): דגל-הטריוּת משקר post-close.** S2+S4 מדווחים `fresh:true` למרות `lag=20358s` מול `threshold=660s` — בעוד הגשר (סיסטם-0, `threshold=90`) מדווח נכון `fresh:false`. ההסבר-הסביר: freshness-של-S2/S4 מותנה ב-`in_session` (מחוץ-ל-RTH "טרי-by-exception"), ולכן ב-15:18 (post-close) הסטייל-מוסווה. **חיובי:** במהלך 09:40–15:00 (in_session) ה-freshness-gate **כן** היה `false` → ככל-הנראה זה מה ש**מנע ירי-על-נתונים-קפואים** (אין ירי-רע אחרי 09:35). **שלילי:** ה-stall **לא צף** עד-EOD (silent-failure, נוגד CLAUDE.md §No-silent-failures).

---

## מצב-היום (כיסוי-חלקי — נתונים רק 08:30→09:40 CT; השאר חסר)

`/chart/bars5min` — **15 ברי-RTH בלבד היום** (08:30→**09:40 CT**, אחרי-כן קיפאון). שחזור-הבוקר (כל הנתונים שיש):

| CT | O | H | L | C | Vol | הערה |
|----|---|---|---|---|-----|------|
| 08:30 | 7485.75 | **7490.5** | 7464.5 | 7469.75 | 40,956 | פתיחה; **שיא-היום 7490.5** |
| 08:40 | 7466.5 | 7468 | 7436.25 | 7439 | 40,810 | תחילת מכירה |
| 08:45 | 7439 | 7444 | 7410.5 | 7424.25 | 64,562 | |
| 08:50 | 7424.75 | 7432 | 7399.5 | 7401.75 | 56,099 | |
| 08:55 | 7401.75 | 7407 | **7390** | 7393 | 57,571 | **שפל-היום 7390** (−95.75pt מהפתיחה ב-25 דק') |
| 09:00 | 7393.25 | 7430.25 | 7392.25 | 7427.75 | 55,376 | תחתית-V → ריבאונד |
| 09:15 | 7437 | 7453.25 | 7427.75 | 7452.25 | 41,638 | התאוששות |
| 09:30 | 7450.75 | 7467.75 | 7449.25 | 7460.5 | 33,704 | |
| 09:35 | 7460.5 | 7465.5 | 7452.25 | 7463 | 24,015 | **← id245 REACTIVE_LONG entry @7460.5** |
| 09:40 | 7463.25 | 7464 | 7458 | 7458.25 | **6,254** | **בר אחרון — vol חלקי ⇒ מוות-feed** |

**צורת-הבוקר:** פתיחה-גבוהה 7485.75 → **מכירה-חדה −95.75pt** ל-7390 @08:55 (25 דק') → **ריבאונד-V +73pt** ל-7463 @09:35 → **קיפאון @09:40 @7458.25.** טווח-70-הדקות = **100.5pt** (7390↔7490.5) ⇒ עקבי עם `ib_width=EXTREME`. **כל-מה-שאחרי 09:40 — לא ידוע** (אין ברים).

`day_type/state` = **Normal `confidence=0.56` `LOCKED_LOW_CONF` `stage=B2`** · `opening_type=OPEN_AUCTION_IN` · `ib_width=EXTREME` · `behavior=DEVELOPING` · `vote_history=[]` (I-1) · **`session_min=0`** (I-1 — instance לא-עוקב-סשן; כאן מוחמר ע"י מוות-ה-feed: אין ברים-חדשים לקדם את ה-stage) · `playbook=null`. conf=0.56 (06-24: 0.68 · 06-23: 0.48) — נתקע low-conf כי ה-IB מעולם-לא-התפתח (feed מת ב-09:40, IB-window 08:30–09:30 בקושי-הסתיים). `chop_score=29.3 state=EXPANDING range_atr_ratio=0.283` (06-24: 1.323 · R/A-נמוך = מדידה על-טווח-קפוא, חסר-משמעות) · `poc_vwap_distance=11.38`. `gateway`: `shadow_active_count=1` (**id245-הפתוחה**) · `trades_today=0` (I-23, מנותק) · `daily_pnl=0` · `cluster_guard recent_attempts=1` (=הירי-הבודד) · `cooldown` off · `demo_enabled=[2,4]`.

---

## 1. עסקאות שנורו היום (1 — REACTIVE_LONG · עדיין-פתוחה · SHADOW · ΣPnL realized=$0)

זמנים = CT (אומת `America/Chicago`; entry_ts ב-`+03:00` IL, CT=IL−8). 3 חוזים MES ($5/pt) נומינלי (I-34). `risk_pt = |entry − stop0|`.

| id | CT | sys | תבנית | כיוון | entry | stop0 | risk | T1 | T2 | state | תוצאה | PnL$ | day_type | wt | mfe | mae | sizing | bars |
|----|-----|-----|-------|-------|-------|-------|------|-----|-----|-------|--------|------|----------|----|----|-----|--------|------|
| 245 | 09:35 | S2 | REACTIVE_LONG | **L** | 7460.5 | 7443.5 | 17.0 | 7469 | 7494.5 | **FILLED (פתוחה)** | **— (לא-נסגרה)** | **0** | Normal | GRAY | 3.5 | 2.5 | 2 | **1** |

**🔴 העסקה תקועה-פתוחה (orphaned-open):** `state=FILLED`, `exit_ts=null`, `outcome=null`, `pnl=0`, `bars_count=1`, `t1_hit=false`. נכנסה @09:35 על ה-ריבאונד-מהשפל (REACTIVE_LONG, conf=0.75), קיבלה **בר-אחד** (09:35) + בר-חלקי (09:40), ואז **ה-feed מת** ⇒ אין ברים לקדם/לסגור. ב-נקודת-הקיפאון: high הגיע 7465.5 (T1=7469 **לא-נגע**, חסר 3.5pt), low 7452.25 (stop=7443.5 **לא-נגע**). ⇒ ב-snapshot היא **ירוקה-קלות-ופתוחה** (mfe +3.5 / mae −2.5). **תוצאתה-האמיתית בלתי-ניתנת-לקביעה** — ר' §3.
**🟡 חוסר-רצף (I-32, ממשיך):** id **244 חסר** (gap; yesterday tail=243@06-24-14:45). insert-fail-שקט/rollback — חשד-קבוע. → D9.
**🟢 woodies_trend=GRAY @entry:** ה-S2-REACTIVE נורתה למרות trend-GRAY (S2 ⟂ S4 per החלטה-עומדת; S4-A1-veto לא חל על S2). תקין-בכוונה.

**פר-מערכת:** **S2: 1 (פתוחה) $0** · **S4: 0** (כל-התבניות A1-vetoed ב-trend=GRAY בבר-הקפוא) · **S3: 0** (I-11 muted).
**פר-כיוון:** **LONG 1 (פתוחה) · SHORT 0.**

---

## 2. טבלת תבניות — נדרכה / נורתה / נחסמה (מצב-קפוא post-09:40)

ללא `PATTERN_DIAG_2026-06-25.md` (סוכן-30-דק' לא רץ מאז 06-10, **יום-15**) **+ feed מת ב-09:40** ⇒ "נדרכה#"/"לא-נורתה#(פירוק)" לא-ניתנים-לספירה לאורך-הסשן. הטבלה משקפת את ה**מצב-הקפוא** ב-`pattern-status` (frozen @09:40, נקרא 15:18). **`fired_today_count`: S2=1 · S4=0** — **תואם-בדיוק** את ה-DB (1 S2 / 0 S4) ⇒ **I-31 (over-count) לא-שוחזר היום** (אך n=1, מבחן-חלש).

| מערכת | תבנית | armed (קפוא) | נורתה # | לא-נדרכה (סיבה) | לא-נורתה (פירוק) | תחזית-נגד |
|-------|-------|--------------|---------|-------------------|-------------------|-----------|
| **S2** | REACTIVE_LONG | false (קפוא) | **1** | feed-frozen post-09:40 | — | **פתוחה/בלתי-נקבעת (§3)** |
| **S2** | REACTIVE_SHORT | false | 0 | feed-frozen | אין בר-טרי לדריכה | — |
| **S2** | INITIATIVE_L/S | false | 0 | **auth-table** (קפוא) | auth×day_type | — |
| **S2** | INV_HNS/HNS_TOP/DOUBLE_BOT/DOUBLE_TOP/BULL_FLAG/BEAR_FLAG | false | 0 | feed-frozen | geometry + אין-בר-טרי | — |
| **S4** | ZeroLineReject (ZLR) | false | 0 | **A1-veto trend=GRAY** | stage-A1 strategic-gate | — (אין setup על בר-קפוא) |
| **S4** | TrendLineBreak (TLB) | false | 0 | **A1-veto trend=GRAY** | stage-A1 | — |
| **S4** | TT/GB100/HTLB/FAMIR/GHOST | false | 0 | A1-veto GRAY / detection | — | — |
| **S4** | **HFE** | false | **0** | **🟢 `HFE_DISABLED=1`** (+ feed-frozen) | — | נוטרל (יום-2) |
| **S3** | 4 התבניות | **0** (I-11) | 0 | footprint muted | — | מחוץ-לתחום pre-LIVE |
| **S1** | Day Type (gate) | classified | — | **Normal conf=0.56** · `opening_type=OPEN_AUCTION_IN` · `ib_width=EXTREME` · `session_min=0`+`vote_history=[]` (I-1) · נתקע (feed מת לפני התפתחות-IB) | — | לא-רלוונטי (יום-קטוע) |

**הערה:** ה-`armed=false` הגורף הוא **artifact של הקיפאון** — ב-09:35 הפטרנים-כן-נדרכו (כך id245 נורתה). אחרי 09:40 אין-בר-טרי ⇒ שום-דבר לא-יכול-לדרוך. **זה לא מצב-סלקטיביות אמיתי** אלא היעדר-נתונים.

---

## 3. תחזית-נגד (counterfactual) — בלתי-ניתנת-לחישוב היום

הספֵק (CC_PROMPT §5) דורש: לכל signal — חשב entry/stop/T1/T2, **שחזר את הברים-הבאים בפועל**, וסמן hit/stop/timeout→R. **היום זה בלתי-אפשרי**: ה-feed מת ב-09:40, ולכן **אין ברים-באים לשחזר** עבור id245 (נכנסה @09:35, קיבלה 2 ברים בלבד). ה-`v9_bars_5min`/`_woodies` **שניהם** מסתיימים @09:40 ⇒ אין-DB-לשחזור.

**CF חלקי (רק 2-הברים-הקיימים):** id245 LONG @7460.5, T1=7469, stop=7443.5. בברים 09:35+09:40: max-high=7465.5 (T1 **לא-נגע**, חסר 3.5pt), min-low=7452.25 (stop **לא-נגע**, מרווח 8.75pt). ⇒ בתוך-הנתונים-הקיימים: **פתוחה, +3.5 mfe, T1/stop לא-נגעו.** מעבר-לזה — **timeout/indeterminate** (חסר-נתונים, לא-stop ולא-target).

**ΣR-נגד מצטבר היום = N/A (0 signals-ברי-שחזור).** אין "סף-ששמרני-מדי" או "סף-שעלה-על-עסקה" להעריך — **השאלה כולה מוחלפת ע"י "ה-feed מת".** הלקח-היחיד: עסקה-פתוחה-יתומה לא-נסגרת בהיעדר-feed (אין EOD-flatten / feed-loss-flatten) ⇒ ב-LIVE זו **חשיפת-פוזיציה-פתוחה-עיוורת** — סיכון חמור.

---

## 4. ממצאים — חדשים / מתחזקים

### 🔴🔴 I-45 (חדש — top, infra/trading-safety) — מוות-feed אמצע-RTH @09:40 CT
**הממצא (אומת-API, Rule 2):** ערוץ ה-market-data הפסיק ב-~09:40 CT. ראיות-מצטלבות: (1) `/chart/bars5min` בר-אחרון **06-25 09:40 CT** (vol 6,254, חלקי) על-אף `ps_ts=15:18 CT`. (2) `pattern-status` סיסטם-0 **Bridge·Live Data Feed = `fresh:false · lag_seconds=9558 · last_bar_ts=null`**. (3) S2+S4 `last_bar_ts=2026-06-25 09:40 CT · lag=20358s`. (4) **S4·Woodies (`v9_bars_5min_woodies`, ה-SoT-החי) קפא גם-הוא @09:40** ⇒ **לא** SoT-split של 06-22, אלא **מוות-מקור אמיתי** (גשר/Sierra-export). **השפעה:** ~88% מ-RTH (09:40→15:00, 320 דק') ללא-נתונים; 1 ירי בלבד (לפני-המוות), תקוע-פתוח; day_type קפוא; 0 CF. **חשד-שורש:** הגשר יצא/מת (LaunchAgent `KeepAlive=SuccessfulExit:false` ⇒ יציאה-נקייה **לא** מקימה-מחדש — CLAUDE.md §LaunchAgent) **או** Sierra-export עצר. **סיווג:** infra → אך **trading-safety** (פוזיציה-עיוורת-פתוחה). **CC לאמת (Rule 5):** (א) `~/SierraChart_Data/v9_export/` — האם Sierra המשיך-לייצא אחרי 09:40 (⇒ מוות-גשר) או עצר (⇒ מוות-Sierra/DLL); (ב) `/tmp/bridge.err.log` — `API push FAILED` / exit-code; (ג) `launchctl list com.mems26.bridge` — מצב/last-exit. → DESIGNS D34.
**🔴 הישנות-ישירה, לא-חדש-לגמרי:** זהו **בדיוק** ה-feed-death של **06-19** (I-38) — אז ה-bridge `bars_5min` מת ~12:00 CT, חצי-RTH-עיוור, **פוזיציות-יתומות 186/187** (FILLED-תקועות) — שעבורו נקבע **blocker-LIVE #0 (D22): feed-watchdog + halt-on-death**. **D22 מעולם-לא-נבנה ⇒ הבעיה חזרה היום** (id245 = ה-186/187 של היום). ⇒ I-45 = **הישנות I-38**; D34/D35 = **החייאת D22**. גם-קשור-ל-I-21 (ערוץ-5דק'-מת; שם session-non-start). **לקח-מתודי:** blocker-LIVE-#0 שזוהה-ולא-נבנה חזר-לנשוך — זו הראיה-החיה שצריך לבנות-את-ה-watchdog לפני-LIVE.

### 🔴 orphaned-open trade (תת-ממצא של I-45, trading-safety) — id245 FILLED ללא-סגירה
**הממצא:** id245 `state=FILLED`/`exit_ts=null`/`outcome=null`/`pnl=0`/`bars_count=1` ב-15:18 (6 שעות אחרי entry). אין EOD-flatten ואין feed-loss-flatten. ב-SHADOW זה רק מלכלך-נתונים; **ב-LIVE זו פוזיציה-אמיתית-פתוחה שהמערכת עיוורת-אליה** (אין ברים ⇒ אין trail/stop-management). **סיווג:** trading-safety → **Michael**. → D35. **CC:** מנגנון feed-loss-detect → force-flatten/alert + EOD-reconcile.

### 🟡 I-46 (חדש — display/observability) — דגל-freshness משקר post-close
**הממצא:** S2+S4 `data_freshness.fresh=true` למרות `lag=20358s ≫ threshold=660s`; הגשר (`threshold=90`) נכון `fresh:false`. סביר: freshness-S2/S4 מותנה-`in_session` (post-close ⇒ "טרי-by-exception"). **תוצאה:** ה-stall מוסווה בכל-תצוגה-post/pre-session ולא-צף עד-EOD (silent-failure). **חיובי:** in-session (09:40–15:00) ה-gate כנראה-חסם-ירי-על-קיפאון (אין ירי-רע). **סיווג:** display/observability → safe. → D36. **CC:** אמת ש-freshness in-session **כן** היה false 09:40–15:00 (⇒ חסם ירי), והפרד "stale-but-out-of-session" מ-`fresh:true`.

### 🟡 I-32 (ממשיך) — gap id 244
id **244 חסר** (yesterday tail 243; today 245). זהה-לדפוס 06-23/06-24 (229/234). → D9. **CC:** `SELECT id FROM v9_trades WHERE id IN (243,244,245)` — מה-קרה ל-244.

### 🟢 I-31 (לא-שוחזר היום) · 🟡 I-23 (מנותק) · 🟡 I-1 (מוחמר ע"י I-45)
**I-31:** `fired_today_count` S2=1/S4=0 = **תואם-DB בדיוק** (≠ over-count 17/7 של 06-24). אך n=1 ⇒ מבחן-חלש; לא-נסגר. **I-23:** `gateway.trades_today=0`/`daily_pnl=0` מול 1-ירי + `shadow_active_count=1` (כן-סופר-פתוחות). counter-ירי-מנותק. → D-gateway-counters. **I-1:** `session_min=0`+`vote_history=[]` — היום **מוחמר** ע"י I-45 (אין-ברים-לקדם-stage), לא-ניתן-להפריד instance-bug מ-feed-death. **I-34:** sizing=2 על id245, אך PnL=0 (לא-נסגרה) ⇒ **לא-נבדק היום.**

---

## 5. לקחים

- **🔴🔴 הסיפור-היחיד של היום = נפילת-feed @09:40 CT, לא מסחר.** המערכת היתה עיוורת ~88% מ-RTH. כל-"מדד-מסחר" היום (1 ירי, $0, 0 CF) הוא **artifact של היעדר-נתונים**, לא של לוגיקת-מסחר. אסור להסיק שום-דבר על תבניות/גייטים מ-06-25.
- **🔴 זו נפילת-מקור אמיתית (גשר/Sierra), לא קריאת-טבלה-בייתה.** ה-SoT-table-החי (`v9_bars_5min_woodies`/S4) קפא גם-הוא @09:40 ⇒ שולל את הסבר-ה-SoT-split של 06-22. **המנוף = לאתר למה הגשר/Sierra עצר** (CC §6).
- **🔴 הסיכון-החמור-ל-LIVE שנחשף: פוזיציה-פתוחה-יתומה.** id245 נשארה FILLED 6 שעות ללא-feed. ב-LIVE = פוזיציה-עיוורת ללא-stop-management. **חובה לפני-LIVE: feed-loss-watchdog → force-flatten/alert + EOD-reconcile** (D35).
- **🟡 ה-stall לא-צף עד-EOD** (silent-failure, נוגד CLAUDE.md §No-silent-failures). דגל-freshness-post-close `fresh:true` מסווה (I-46). צריך alert-חי כש-`lag>threshold` in-session.
- **🟢 חיובי-יחיד: ה-freshness-gate-in-session כנראה מנע ירי-על-נתונים-קפואים** (0 ירי 09:40–15:00) — להוכיח (CC §6.4). + **I-31 לא-שוחזר** (fired-count מדויק היום, n=1).
- **תפעולי — יום-15 ללא DIAG** ⇒ אין armed#/blocked#-intraday. + **המוות @09:40 הופך כל-EOD-מבוסס-ברים לבלתי-שמיש היום** — הדוח הוא **דוח-תקלה**, לא דוח-ביצועים.

---

## 6. מקור-אמת — דורש הצלבת CC מול Sierra v9_export / לוג / DB

1. **🔴🔴 I-45 — שורש מוות-ה-feed @09:40:** (א) `ls -la ~/SierraChart_Data/v9_export/*.json` + mtime — האם Sierra **המשיך** לכתוב אחרי 09:40 CT (⇒ מוות-גשר) או **עצר** (⇒ מוות-Sierra/DLL/study). (ב) `tail -100 /tmp/bridge.err.log` — `API push FAILED` / exit / exception @~09:40. (ג) `launchctl list | grep mems26` + `tail /tmp/bridge.out.log` — האם הגשר חי/יצא; last-exit-code. (ד) `psql postgresql://localhost/mems26 -c "SELECT MAX(ts) FROM v9_bars_5min_woodies; SELECT MAX(ts) FROM v9_bars_5min;"` — לאשר ששתיהן עוצרות @09:40.
2. **🔴 orphaned-trade id245:** `SELECT id,state,entry_ts,exit_ts,outcome,pnl_usd,bars_count FROM v9_trades WHERE id=245` — האם נסגרה-מאז; האם יש מנגנון-flatten בהיעדר-feed.
3. **🟡 I-46 — freshness in-session:** אמת ש-`data_freshness.fresh` היה **false** עבור S2/S4 בחלון 09:40–15:00 (in_session) ⇒ חסם-ירי; והפרד "out-of-session" מ-`fresh:true` post-close.
4. **🟡 I-32 — gap 244:** `SELECT id FROM v9_trades WHERE id BETWEEN 243 AND 246` — מה-קרה ל-244.
5. **🟡 I-23 — counters:** מדוע `gateway.trades_today=0` מול ירי-1 (+`shadow_active_count=1` כן-תקין).
6. **רקע day_type:** `classify_replay` 06-25 (אם-בכלל-רץ) — האם נתקע ב-Normal/0.56/B2 כי ה-IB-window נקטע ב-09:40.

**NOT-DONE / מגבלות:**
- **אין נתוני-מסחר תקפים ל-06-25** — feed מת @09:40. הדוח הוא **דוח-תקלת-תשתית**; אין armed#/blocked#-intraday (יום-15 ללא DIAG) ואין CF (אין ברים-לשחזר).
- מוות-ה-feed אומת **API-only** (bars-frozen + `pattern-status.data_freshness` + woodies-frozen). **שורש-המוות (גשר מול Sierra) טרם-אומת** — דורש גישת-Mac ל-`v9_export`/`bridge.err.log`/`launchctl` (CC, §6.1). אל-תניח גשר-מול-Sierra בלי הלוג.
- ערכי-קלט-Sierra (CCI/study/OHLC) לא-הוצלבו — read-only, CC.
- כל-הקריאות בוצעו דרך Chrome מול `localhost:8000` (לא DB-ישיר — אין גישת-PG מה-sandbox).
