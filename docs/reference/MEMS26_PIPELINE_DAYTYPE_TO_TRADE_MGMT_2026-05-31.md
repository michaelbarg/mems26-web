# MEMS26 — צינור מלא: מזיהוי סוג-היום ועד ניהול עסקה (As-Built)

**תאריך:** 2026-05-31 · **מקור:** Cowork · **בסיס:** `docs/reports/FULL_PATH_MEGA_TABLE_2026-05-31.md` (30 שלבים, קוד↔אפיון) + קריאת קוד ישירה ב-`backend/v9/gateway/`
**אופי המסמך:** **As-built + פערים** — מתאר מה המערכת עושה *בפועל היום*, מסומן ב-✅ כשקוד=אפיון, וב-⚠️ **GAP** כשיש פער פתוח/החלטה ממתינה.
**מצב מערכת:** SHADOW בלבד · 5 דגלי relative/CVD default OFF (אלא אם הודלקו) · אין נתיב order ל-Sierra (Pipeline 5 פתוח).

> **איך לקרוא:** המסמך בנוי לפי **6 שלבים** (Phase 0–5) שמתארים את מסע הבר מרגע שהוא נכנס מ-Sierra ועד שהעסקה נסגרת ונרשמת. כל שלב מציין: מה נכנס, מה הלוגיקה, מה יוצא, לאן זה ממשיך, ומיקום הקוד. עמודת **Source-of-Truth** מצביעה על מסמך האפיון הנעול.

---

## 0. מפת המערכת — 6 המערכות והשכבות

| מערכת | תפקיד | שכבה | יורה? | קוד |
|-------|-------|------|-------|-----|
| **S1 · Day Type** | מסווג את סוג-היום (Trend/Variation/Neutral/Normal/Nontrend) | Layer 2 — observer | ❌ צופה (מספק הקשר) | `backend/v9/systems/day_type/` |
| **S2 · Five-Min** | תבניות 5-דק' (OFA + Chart: H&S/Double/Flags) | Layer 1 — firing | ✅ | `backend/v9/systems/five_min/` |
| **S3 · Footprint** | אותות footprint (absorption/imbalance/sweep/exhaustion) | Layer 1 (T3) — firing | ✅ | `backend/v9/systems/footprint/` |
| **S4 · Woodies** | עץ החלטה Woodies (9 תבניות CONT/REV) | Layer 1 (T2) — firing | ✅ | `backend/v9/systems/woodies/` |
| **S5 · TPO** | פרופיל מחיר (POC/VAH/VAL, צורות) | Layer 2 — observer | ❌ | `backend/v9/systems/tpo/` |
| **S6 · Killzone** | אזורי זמן (NY open / midday / וכו') | Layer 2 — observer | ❌ | `backend/v9/systems/killzone/` |

**עיקרון מנחה (CLAUDE.md):** ערכים חיים מגיעים מ-**Sierra Chart exports** דרך ה-bridge ל-API/DB — לא מסונתזים בבקאנד/פרונטאנד. כשה-DLL שותק → מפיצים `None`/"missing", לא ממציאים.

---

## Phase 0 — קליטת נתונים (Data Ingestion)

הבר נכנס מ-Sierra ומתפצל למערכות המנויות.

| # | שלב | קלט | לוגיקה | פלט → ל | קוד | SoT | מצב |
|---|-----|-----|--------|---------|-----|-----|-----|
| 1 | ברים 5-דק' | Sierra DLL JSON (OHLCV+studies) | Bridge קורא `v9_export/*.json` → push ל-`localhost:8000/api/v9/bars` → BarRouter מפזר | BarEvent → S1,S2,S3,S4,S5 | `bridge/v9_streams/base_stream.py`; `services/bar_router/` | Constitution V3 §Layer 0-1 | ✅ |
| 1b | footprint | tick_reversal_15/12 + תאי ask/bid לכל level | אותו צינור, מנוי bar_type שונה | tick_reversal → S3 | `bridge/v9_streams/` | Constitution V3 §Layer 3 | ✅ |
| 1c | Woodies studies | DLL מחשב 11 מדדים (CCI-14, TCCI, EMA-34, LSMA, SWI, CZI, trend_state, predictor, HFE, ZLR) | DLL = מקור אמת; fallback פייתון `compute_all_studies()` אם DLL נעדר | woodies_5min → S4 | `sc_study/MES_AI_DataExport.cpp`; `woodies_system.py:251-270` | D-092 §SoT | ✅ |

**כלל local-only (CLAUDE.md):** ה-bridge דוחף **רק** ל-`localhost:8000`; מסרב לעלות אם `CLOUD_URL` אינו localhost.

---

## Phase 1 — זיהוי סוג-היום (S1, observer)

S1 הוא ה-observer שקובע את ההקשר שכל מערכות הירי משתמשות בו ל-sizing ולאישור. הזיהוי מתקדם בשלבים A→B→C לאורך היום.

### A — פתיחה ו-IB

| # | שלב | לוגיקה (flag-OFF) | flag-ON | פלט | קוד |
|---|-----|-------------------|---------|-----|-----|
| 2 | **A1 הקשר טרום-פתיחה** | gap = open − PD close; `>±2.0pt`→UP/DOWN, אחרת FLAT; magnitude=gap/ATR (≥1.0 LARGE / ≥0.3 MEDIUM / else SMALL) | `S1_IB_WIDTH_ATR`: gap לפי tiers ATR (<0.25 TINY / <0.5 SMALL / <1.0 MEDIUM / ≥1.0 LARGE) | PreOpenContext | `state_machine.py:357-442`; `detector.py:211-234` |
| 3 | **A2 סיווג הרצת פתיחה** | מחיר בלבד: directional_ratio ≥0.7→OPEN_DRIVE (0.95); pullback 20-60%→OPEN_TEST_DRIVE (0.70); retrace >50%→OPEN_REJECTION_REVERSE (0.65); outside PD→OPEN_AUCTION_OUT (0.50); inside→OPEN_AUCTION_IN (0.40) | `S1_CVD_OPENING`: נתיב CVD צללי — `PE_30>0.65 & range_exp>1.0`→DRIVE; `net_CVD/total<0.15 & PE<0.25`→AUCTION; CVD מחליף price-based כשבטוח | (OpeningType, drive_direction, confidence, cvd_meta) | `detector.py:119-191` (price); `:255-363` (CVD) |
| 4 | **A3-A4 IB + נעילה + רוחב** | צבירת IB high/low; נעילה ב-60 דק' (10:30 ET). רוחב: `classify_ib_width` → NARROW <15pt / MEDIUM 15-25 / WIDE >25 | `S1_IB_WIDTH_ATR`: לפי ATR יומי — NARROW <0.5 / MEDIUM 0.5-1.0 / WIDE 1.0-1.5 / **EXTREME >1.5** | IBClassification | `state_machine.py:460-518`; `detector.py:14-75`; `extensions.py:72-83` |

### B — החלטה והתפתחות

| # | שלב | לוגיקה | פלט | קוד |
|---|-----|--------|-----|-----|
| 5 | **B1 מטריצת החלטה** | lookup 25-תאים (OpeningType × IBWidth) → DayType + התפלגות. דוגמה: (OPEN_DRIVE, NARROW)→Trend_Normal 60%/Trend_DD 25%/Variation 15%. (INDETERMINATE,*)→Normal. conf התחלתי 0.5 | (flag-ON: עמודת EXTREME 4th) | DayType vote + dist | `decision_matrix.py:30-151` |
| 6 | **B2-B6 התפתחות + staging** | B2 extensions; B3 behavior (TRENDING/FAILED_EXT/COMPRESSED/DEVELOPING); B4 failed-ext; B5 range/ATR (COMPRESSED<0.7/NORMAL/EXPANDED/EXTREME≥2.0); B6 re-score (behavior +0.30, range +0.20, vote ×0.40, base 0.10); switch אם ΔConf>0.15 | `S1_DAYTYPE_STAGING`: conf מוגבל ל-60% לפני session_min 60; C-period (10:30-11:00) re-eval: retrace<25%→HOLD, ≥50%→RE_DIAGNOSE | DayType vote מעודכן | `state_machine.py:542-627`; `detector.py:368-492,78-114` |
| 6b | **B+ כללי זוהר** | 6 כללים: Alpha (TDD invalidation), Beta (Drive fail), Gamma (Test-Drive fail), Delta (דו-צדדי→Neutral), Width (>5 letters→Normal), Timing (reversal<12:30→Variation; trend>12:30→TDD) | RuleVerdict | `zohar_rules.py:35-171` |
| 6c | **תת-סוג Neutral** | פתיחה ב/מעבר לקצה VA (±0.25pt)→Neutral_Extreme; בתוך VA→Neutral_Center | Neutral_Extreme/Center | `neutral_classifier.py:13-49` |

### C — נעילה ו-Playbook

| # | שלב | לוגיקה | פלט → ל | קוד |
|---|-----|--------|---------|-----|
| 7 | **C1-C3 נעילה + Playbook** | **C1 נעילה:** conf ≥**0.85** אפקטיבי (ראה GAP-5 — הסף הנקוב 0.70 הוא תאימות-טסטים בלבד) **או** consecutive_same_vote ≥2 **או** session_min ≥210 (13:00 ET forced). re-eval פוסט-נעילה: extreme move >3ATR/30min, failed-ext, range חרג. **C3 Playbook:** DayType→(strategy, sizing, time_stop_min, key_rules) | DayTypeClassification (13 שדות) + Playbook → **S2,S3,S4** | `state_machine.py:680-746` |

⚠️ **הערה (GAP-5, LOW):** `ConfidenceThreshold` משתמש ב-`__eq__` hack ששווה גם ל-0.85 וגם ל-0.70 (תאימות טסטים); הנעילה בפועל היא `>=` כך שסף=0.85 אפקטיבית.
⚠️ **הערה (GAP-1, LOW):** תוויות ה-sizing של ה-Playbook (AGGRESSIVE/STANDARD/HALF/MIN) ב-`state_machine.py:38-116` הן **dead code** — הוחלפו ע"י Auth Table V1 (ראה Phase 3). `setup_emitter` קורא ל-Auth Table ישירות ועוקף אותן. רק `time_stop_min` מה-Playbook עדיין בשימוש.

---

## Phase 2 — זיהוי תבניות וירי (S2/S3/S4) + observers (S5/S6)

המערכות היורות מקבלות את ה-DayType מ-S1 ומזהות setups. כל אחת מייצרת signal עצמאי שמועבר ל-gateway.

| # | מערכת | תבניות / לוגיקה | פלט | קוד |
|---|-------|-----------------|-----|-----|
| 8 | **S2 OFA** | **Reactive (חולשת מוכר/קונה):** Bar1 bearish+vol גבוה → Bar2 ירידת vol ≤10% → Bar3 bullish+belly≥1.5+POC↑ → Bar4 bullish>bar3.high+COT>AMT. **Initiative (Expansion):** Bar1 bullish+range 1.3-2.5×avg_range(14bars) → Bar2 test → Bar3 joining → Bar4 close>bar1.high+COT<AMT. (Michael 2026-06-08: ratio adapts to avg candle size, not fixed ATR×k) | pattern, direction, conf 0.75-0.80, anchor | `five_min_system.py:461-603` |
| 9 | **S2 H&S** | Inverse H&S: 3 שפלים, ראש נמוך, סימטריה ≤5%, הארכה ≥2T, neckline=max highs, breakout>neckline+1T. conf base 0.60 +sym 0.20 +ext 0.20 | INVERSE_HNS | `patterns/head_shoulders.py:141-207` |
| 9b | **S2 Double BT** | Double Bottom Eve&Eve: 2 שפלים ±3% סימטריה, neckline rise ≥10%, breakout>neckline+1T | DOUBLE_BOTTOM_EE | `patterns/double_bt.py:165-227` |
| 9c | **S2 Flags** | Bull Flag: pole 5-15 bars ≥4.0pt ≥60% bullish; flag 3-8 bars retrace ≤50%; breakout>flag_high+1T. flag-ON: pole=5.5×ATR, flag=2.5×ATR | BULL_FLAG | `patterns/flags.py:141-200` |
| 10 | **S3 Footprint** | 4 גלאים: Absorption / Stacked Imbalance (3+ levels ratio≥2.5) / Sweep-Return / Exhaustion. Dominance ask/bid≥1.5. Confluence: STRATEGIC ≥6 / TACTICAL ≥4. flag-ON `S3_RELATIVE`: accumulation=1.0×ATR5m, min_level_vol=0.3×median | T3 signal: direction, strength, confluence | `footprint/footprint_system.py:302-387` |
| 11 | **S4 Woodies** | 9 תבניות: CONT (ZLR,TLB,TT,GB100), REV (VEGAS,GHOST,FAMIR,HTLB,HFE). **A1** Trend-Gate (YELLOW=5th opp bar→BLOCK ALL); **A2** validity; **A3** detection; **A4** touch-points (advisory); **A5** aux alignment→sizing; **A6** entry class; **A7** pre_fire_validator | T2 signal: pattern, direction, conf, tier, stop/targets | `woodies/woodies_system.py:202-494`; `decision_tree.py` |
| 12 | **S5 TPO** (observer) | פרופיל אות-אחר-אות; POC, VAH/VAL (70%), 8 צורות, IB lock 60min, POC migration, HVN/LVN | POC/VAH/VAL/shape → S1,S2,S4 | `tpo/tpo_system.py:133-200` |
| 13 | **S6 Killzone** (observer) | 8 אזורים (ASIA/LONDON/NY_PREMARKET/NY_OPEN/MIDDAY/NY_PM/POST/CLOSED) לפי ET (polling 30s) | zone + edge_class → S4 (A4) | `killzone/killzone_system.py:83-119` |

✅ **הערה (GAP-6 — RESOLVED 31/5):** ה-"39 כשלי ZLR" היה מספר מנופח (כלל את כל תבניות woodies). בפועל 17 טסטי ZLR, **כולם עוברים, אפס skip/xfail** (תוקנו ב-`aafb699`+`acacf8b`). מקור: `docs/reports/GAP6_ZLR_RECONCILE_2026-05-31.md`. *(ממתין לאימות Rule 5 ע"י Cowork.)*

---

## Phase 3 — בניית ה-Setup (sizing, stop, split, time-stop, validation)

לפני שה-signal מגיע ל-gateway, S2 בונה T1Setup מלא. (S3/S4 נושאים sizing משלהם — ראה למטה.)

| # | שלב | לוגיקה | פלט | קוד |
|---|-----|--------|-----|-----|
| 14 | **Auth Table + Quality Tier** | **Quality:** מחיר ≤2.0pt מ-POC/VAH/VAL→HIGH; בתוך VA→MEDIUM; מחוץ→LOW (flag-ON proximity=1.25×ATR5m). **Auth Table:** lookup 70-תאים (pattern×day_type)→(verdict, contracts לפי tier). SKIP→אין ירי. **max=3**. Nontrend→תמיד SKIP | verdict (FULL/REDUCED/SKIP) + contracts 0-3 | `auth_table_v1.py:33-104`; `quality_tier.py:41-78` |
| 15 | **Adaptive Stop** | 3 שכבות: A (מבני) anchor±1T; B (ATR cap) entry±multiplier×today_typical; C (floor) entry±FLOOR×0.25. multipliers: Reactive 1.0×, OFA/Flag 1.5×, Double/H&S 2.0×. LONG: max(A,B) clamp≤C | stop_price, binding_layer, reduce_size_signal | `adaptive_stop.py:130-194` |
| 16 | **Contract Split** | OFA 25/50/25; H&S+Double 33/33/34; Flags 50/50/0 (אין T3) | t1/t2/t3_pct | `contract_split.py:15-30` |
| 17 | **Time Stop** | TN: None; TDD 90min; NV 60; NeuE 45; NeuC/Norm 30; NT: NO_TRADE | time_stop_minutes | `time_stop_mapper.py:12-30` |
| 18 | **Setup Emitter** | (1) סירוב NT (2) Quality lookup (3) SKIP→None (4) time-stop (5) split (6) build T1Setup conf=75 (7) pre_fire_validator (8) return | T1Setup או None | `setup_emitter.py:24-120` |
| 19 | **Pre-Fire Validator (7 בדיקות)** | (1-2) system_id/direction (Pydantic) (3) צד stop (4) סדר targets (5) **R:R ≥ 1.0** (6) conf∈[0,100] (7) time_stop∈[1,180] | FireResponse: valid + fail_reason | `pre_fire_validator.py:42-59` |

**Sizing לפי מערכת:** S2 → Auth Table (max 3). S3 → עצמאי (`footprint_system.py:389-426`, strength+aux→3/2/reject). S4 → עצמאי (`woodies_system.py:637-684`, tier+aux+trend→3/2/reject).

---

## Phase 4 — Gateway: שערי סיכון וניתוב

ה-`route_setup` מריץ 5 שערי סיכון לפני מילוי slot, ואז מנתב ל-3 מצבים.

### 5 שערי הסיכון (לפי הסדר)

| שער | תנאי חסימה | היקף | קוד |
|-----|-----------|------|-----|
| 1 · Cooldown (ζ.A4) | 2 STOP רצופים → חסימה 30 דק' | הכל | `cooldown.py:18-92` |
| 2 · SSV (ζ.B2, D-049) | מ-10 עסקאות אחרונות ≥60% stop בצד אחד → veto לכיוון (מינ' 2) | הכל | `suffering_side_veto.py:19-63` |
| 3 · Chop (ζ.F2) | Layer-0 chop_state="SEARCHING" → חסימה | הכל | `trading_gateway.py:97-101` |
| 4 · Cluster Guard (ζ.A5, D-037) | 5+ עסקאות ב-60s → חסימה 5 דק' | **DEMO/LIVE בלבד** (SHADOW כן רושם) | `trading_gateway.py:104-121` |
| 5 · Strict checks | **LIVE בלבד:** cutoff 14:30 ET · daily loss cap $250 · max 5 trades/day · 2 הפסדים רצופים→STOP DAY · news (placeholder) | LIVE | `risk_checks.py:26-75` |

### ניתוב 3-מצבי (שלב 21)

| מצב | כלל | קוד |
|-----|-----|-----|
| **SHADOW** | תמיד רץ, slots בלתי-מוגבל, נרשם ל-`shadow_trades` (cap 500) | `trading_gateway.py:109-114` |
| **DEMO** | slot יחיד: `if demo_slot is None`→מילוי, אחרת skip | `:124-130` |
| **LIVE** | slot יחיד: `if live_slot is None AND passes_strict_checks`→מילוי | `:132-139` |

⚠️ **GAP-3 (HIGH — החלטה ממתינה):** הניתוב הוא **first-wins** טהור (מי שמגיע ראשון ל-slot זוכה). כל המפרטים הנעולים + הקוד תואמים first-wins. כוונת Michael היא **בחירה לפי R:R בדולרים** בין setups מתחרים — פיצ'ר חדש שמשנה first-wins ודורש: נוסחת R:R, חלון buffering, ו-tie-breaking. **טיוטה ב-`docs/decisions/D-094_RR_FIRE_SELECTION.md` (PROPOSED) → אישור Michael → מימוש.**

⚠️ **GAP-2 (LOW):** שער ה-news ב-strict checks הוא placeholder מוער (`risk_checks.py:70-73`). אין השפעה ב-SHADOW.

⚠️ **GAP-4 (MEDIUM — בטיחות LIVE):** `MAX_CONTRACTS = 2` (`risk_checks.py:20`) **מוגדר ולא נאכף** באף `if`. אי-התאמה תלת-כיוונית: קוד=2 · Auth Table max=3 · החלטת Michael 31/5=5. **דורש יישוב** (ראה פרומפט GAP4 משימה B). תקרת סיכון מצטברת = **שער חובה לפני LIVE (P-L0a)**.

⚠️ **GAP-7 (צפוי — Pipeline 5):** ה-DLL עדיין לא קורא לפונקציות order של ACSIL (TODO ב-`MES_AI_DataExport.cpp:813-815`). אין השפעה ב-SHADOW. ראה D-093.
⚠️ **GAP-8 (MEDIUM):** שתי מימושי gateway קיימים — Legacy (`backend/v9/gateway/`, מחווט) ו-New (`services/trading_gateway/`, לא מחווט, מכיל W14 RiskValidator). D-093.Q1 נעול = MERGE (Legacy + חילוץ RiskValidator).

---

## Phase 5 — ניהול עסקה ומחזור-חיים (TradeManager)

לאחר שה-slot מתמלא, ה-setup עובר ל-TradeManager שמנהל את העסקה מ-PENDING ועד CLOSED.

| # | שלב | לוגיקה | פלט | קוד |
|---|-----|--------|-----|-----|
| 22 | **accept_setup** | יוצר V9Trade (state=PENDING) + TradeStateMachine. resolve trail config מ-day_type×pattern. persist+flush→trade_id. emit "trade_created" | trade_id; שורת V9Trade | `manager.py:84-187` |
| 23 | **on_fill → FILLED** | PENDING→FILLED. entry_price=fill, entry_ts=UTC. emit "trade_filled" | state=FILLED | `manager.py:189-204` |
| 24 | **BarLevelDetector — זיהוי פגיעה** | לכל בר 5-דק', לכל עסקה FILLED/PARTIAL: **stop קודם** (adverse priority): LONG low≤stop / SHORT high≥stop → on_stop_hit. **אחר כך targets T1→T2→T3** רציף. dedup לפי bar_ts | on_stop_hit / on_target_hit | `bar_level_detector.py:43-128` |
| 25 | **T1 → Smart BE+1T** | →PARTIAL. מזיז stop ל-entry+1T (LONG) / entry−1T (SHORT). 1T=0.25pt. idempotent. audit cross-context | state=PARTIAL, stop=BE+1T | `manager.py:206-248,261-315` |
| 26 | **כללי ניהול (Layer 4)** | trail / lock-in / tightening / EXIT מיושמים ב-**TrailEngine** דרך `_apply_layer4()` — 5 שירותי Layer-4 בסדר mfe→cci→tcci→swi→day_type_targets, נקראים לכל בר. נעול ב-D-094 §3.B Option C+ (`1e01c4a`); Pkg 4a/4b נדחו כי הscope נספג (D-095). | שינוי stop / CLOSE | `services/trail_engine.py:100,548` (`_apply_layer4`) |
| 26c | **דמה: gateway/trade_management.py** ⚠️ | קובץ ישן עם C.2/C.4/C.6/C.7 כפונקציות — **superseded dead code** (אפס callers). הוחלף ע"י TrailEngine (D-095). | — | `gateway/trade_management.py` |
| 26b | **S4 Time Stop (W-10)** | bars_open ≥ limit (default 18 ברים ≈90 דק')→סגירה ב-close האחרון | exit_reason=TIME_STOP | `woodies_system.py:560-623` |
| 27 | **סגירה** | →CLOSED. exit_ts/price/reason. PnL: יציאת חוזים לפי target-levels; $5/point MES; pnl_r=total/(3×risk). outcome WIN/LOSS/BE | exit_reason, pnl_usd, pnl_r, outcome | `manager.py:317-584` |
| 28 | **on_trade_close** | משחרר slot DEMO/LIVE; מעדכן daily stats; רושם outcome ל-SSV | slot חופשי | `trading_gateway.py:161-189` |

✅ **הערה (ניהול עסקה — מחוּוט ופועל):** מלוא היקף ניהול-העסקה (trail / lock-in / tightening / EXIT) מיושם ב-**`trail_engine.py::_apply_layer4()`** (5 שירותי Layer-4, נקרא לכל בר) ונעול ב-**D-094 §3.B Option C+** (`1e01c4a`); Pkg 4a/4b נדחו כי הscope נספג (**D-095**). C.1 Smart BE+1T (`manager.py`) ו-C.3 time-stops (S2/S4) מחוּוטים בנפרד. ⚠️ הקובץ `gateway/trade_management.py` הוא **superseded dead code** (0 callers) — אל תתבלבל איתו (כמו GAP-1). הטבלה המקורית `FULL_PATH_MEGA_TABLE` הצביעה על הקובץ המת בטעות.

⚠️ **הערה (Bug C, פתוח):** stop/target נרשמים לעיתים ב-bar-open ולא במחיר fill בפועל → השפעת PnL. `bar_level_detector.py`.

---

## Phase 6 — שמירה ותצוגה

| # | שלב | לוגיקה | קוד |
|---|-----|--------|-----|
| 29 | **Persistence → DB** | טבלת `v9_trades`: id, mode, firing_system, direction, state, entry/exit_ts, prices, stop, t1-t3 (+hit_ts), exit_reason, pnl_usd, pnl_r, outcome, cross_context (JSON), is_synthetic, timestamps. + `V9TradeManagementLog` | `db/models/trades.py` |
| 30 | **API → Frontend** | `GET /api/v9/trades` (enriched: pnl_mode, excursion, agreement); `/recent` (30 newest, poll 30s); `/active` (contract-level, poll 5s); detail→insight מ-cross_context | `api/v9/trades.py`; `frontend/.../components/trades/` |

**רצפות polling (CLAUDE.md — לא לשנות בלי אישור):** systemState 5s · Sound 10s · livePrice 5s · WoodiesCci 5s · StreamHealth 15s · Layer0 15s · TopBar 15s · TradeHistory 30s.

---

## טבלת פערים פתוחים (ריכוז)

| GAP | חומרה | שלב | מהות | מצב |
|-----|-------|-----|------|-----|
| **GAP-3** | HIGH | 21 | ניתוב first-wins מול כוונת R:R selection | טיוטת D-094 → אישור Michael |
| **GAP-4** | MEDIUM | 20 | MAX_CONTRACTS לא נאכף; אי-התאמה 2/3/5 | audit (פרומפט B) → החלטה |
| **GAP-1** | LOW | 7b | תוויות sizing Playbook = dead code (Auth Table גובר) | לתעד/למחוק |
| **GAP-2** | LOW | 20 | news gate = placeholder | לפני LIVE |
| **GAP-5** | LOW | 7 | `ConfidenceThreshold.__eq__` hack | קוסמטי |
| ~~GAP-6~~ | RESOLVED | 11 | "39 ZLR" היה מנופח; בפועל 17 טסטים, כולם עוברים | ✅ תוקן 31/5 |
| **GAP-7** | — | 1c | DLL ללא order ACSIL | Pipeline 5 (צפוי) |
| **GAP-8** | MEDIUM | — | dual gateway (Legacy מחווט / New לא) | D-093.Q1=MERGE |
| **GAP-11** | MEDIUM | — | S2 `current_day_type=None` ב-restart אמצע-session | hydration מ-DB |
| ~~GAP-12~~ | RESOLVED | 26 | ניהול-עסקה מחוּוט ב-`trail_engine.py::_apply_layer4()` (D-094 §3.B / D-095); `gateway/trade_management.py` = dead code | ✅ נעול בהחלטה |
| Bug C | — | 24 | stop/target ב-bar-open לא fill בפועל | פתוח |

**Source-of-Truth ראשי:** `MEMS26_CONSTITUTION_V3_FINAL.txt`, D-089/091/092/093, `S2_AUTH_TABLE_V1.md`, `S2_EXIT_DEFINITION_V6`, `docs/reports/FULL_PATH_MEGA_TABLE_2026-05-31.md`.

*נוצר ע"י Cowork 2026-05-31. As-built — משקף קוד+אפיון נכון לתאריך. כל ✅/⚠️ ניתן לאימות ע"י CC (ראה פרומפט אימות נלווה).*
