# Build Status — אודיט רכיבים לכל מערכת (מה האפיון דורש מול מה שמוצג)

> מטרה: לכל מערכת (S1–S6), מהם הרכיבים שהאפיון דורש, מה ה‑Build Status מציג היום, ומה **חסר** ויש להוסיף לעץ ההחלטות.
> מקור־אמת: `MEMS26_REGISTRY.yaml` (REQ‑S‑\*, עם `code_path`/`test_path`/`status` לכל רכיב) + ה‑compliance_manifest של כל מערכת.
> נבדק מול הקוד החי 2026‑06‑03 (read‑only). ציטוטים = נתיב:שורה.

## תקציר — שלוש המסקנות הגדולות

1. **שני שערי‑אש גלובליים חסרים לגמרי מה‑Build Status:** `pre_fire_validator` (7 בדיקות לפני כל ירי) ו‑`risk_checks` (תקרות LIVE: הפסד $250, 5 עסקאות, 2 חוזים, חיתוך 14:30 ET, עצירה אחרי 2 הפסדים רצופים). שניהם רצים רק *בתוך* כל מערכת בזמן ירי — לא מיוצגים כשערים. **זה הדבר הראשון להוסיף.**
2. **שלב TARGETS/STOP חסר כמעט בכל מערכת יורה.** S2, S4 ו‑S3 לא מציגים אף שורה של סטופ/1R/T1‑T2‑T3/חוזים/time‑stop — בדיוק החלק שתיקנו במוקאפ. צריך inspector שיחשוף אותו מהמנוע, לא מה‑frontend.
3. **S5 (TPO) ו‑S6 (Killzone) לא מחוברים בכלל ל‑Build Status.** אין `tpo_inspector` ולא `killzone_inspector`; ה‑aggregator מחבר רק `["bridge","five_min","footprint","woodies","day_type"]` (`aggregator.py:106`). הסכמה כבר תומכת בהם — חסרים שני מודולי inspector + 2 שורות ב‑aggregator.

---

## S1 · Day Type (observer) — מחובר

| שלב | רכיב נדרש (שדה) | מוצג היום? | פעולה |
|---|---|---|---|
| SOURCE | Sierra TPO (IB high/low), bars (session high/low), prev‑day loader | חלקי | להוסיף freshness לכל מקור |
| INPUT | `ib_high/low`, `ib_locked`, `bar_count`, `session_high/low`, `stage`, `confidence` | חלקי | — |
| **PRE‑OPEN** (A1/Q4) | `pd_poc`, `pd_vah`, `pd_val`, `on_high`, `on_low`, `gap_size`, `gap_direction`, `location_vs_pd`, `overnight_bias` | ❌ חסר | **להוסיף** — קיים ב‑`prev_day.load_previous_day_context` אך ה‑inspector לא קורא אותו |
| CLASSIFICATION | `day_type` (7 סוגים), `opening_type` (5), `ib_width_class`, `probability` | ✅ | — |
| **DECISION MATRIX** (B1) | `matrix_cell` (opening×ib_width→vote), `vote_history`, `top1/top2` | ❌ חסר | **להוסיף** — מוצג רק הסיווג הסופי, לא איך הוצבע |
| **PROFILE SHAPE** (C2) | `profile_shape` (8 צורות) | ❌ חסר | תלוי ב‑S5 שלא מחובר |
| RE‑EVAL (Q16) | `re_eval` state + טריגרים (news / שינוי profile) | ❌ חסר | להוסיף |
| **TARGETS** | `get_targets()` → T1/T2/T3, time_stop, sizing, no_trade | ❌ חסר | **להוסיף** — הפלט הפעולתי של המערכת |

## S2 · 5‑Min Patterns (firing) — מחובר, detection מכוסה טוב

| שלב | רכיב נדרש | מוצג היום? | פעולה |
|---|---|---|---|
| SOURCE | `v9_bars_5min` recency | ✅ | — |
| SOURCE | **Sierra JSON: `cumulative_delta.json` (COT/AMT), `tpo.json` (POC), `volume_profile.json` (S/R)** | ❌ חסר | **להוסיף freshness** — שלושתם משערים ירי; מקור חסר/ישן לא יוצג כלל |
| INPUT | bars b1..b4, `poc_vol`, COT/AMT, ATR‑14 | חלקי | לחשוף `_current_atr_5m` ו‑COT/AMT כ‑live_inputs |
| INPUT | זמינות הזרקת Footprint (belly/forces_history) | ❌ חסר | להוסיף — נופל ל‑HTTP fallback בשקט |
| GATE | mode, fhb_eligible, day_type_known, auth_cell, nt_skip, choppiness | ✅ | — |
| **GATE** | **S/R proximity** (`sr_proximity.check_proximity`) | ❌ placeholder | **להוסיף כשער אמיתי** — כרגע רק שורת footprint hard‑coded present=True |
| **GATE** | **COT/AMT directional** (COT>AMT ללונג) | ❌ placeholder | **להוסיף** — מוצג כ‑always‑pass; הערכים החיים לא נחשפים |
| GATE | Layer‑3 cluster `provisional` flag; `pre_fire_validator` ran? | ❌ חסר | להוסיף — entry/stop provisional לא מסומן |
| DETECTION | 10 תבניות, b1..b4, volume_drop, lookback_quiet, swings/triplet/pole | ✅ | — |
| **TARGETS/STOP** | adaptive stop (structural_anchor / ATR cap / floor / `binding_layer` / `reduce_size_signal`), `t1/t2/t3_price`, R, time_stop (`min(day,pattern)`), sizing (full/half/reject + `location_vs_poc_vol`), contract split, trail override, VSA variant | ❌ **חסר לגמרי** | **להוסיף את כל השלב** |

## S3 · Footprint (firing) — מחובר אך כמעט ריק · **מושבת**

> `FOOTPRINT_DISABLED` מאומת (`footprint_system.py:143-146` מדלג על כל העיבוד). הדגל **לא מיוצא** ב‑start_all/LaunchAgent/.env וה‑endpoint **לא** מגודר — שביר‑קונפיג. ה‑inspector קורא `get_state()` שלא קיים (רק `get_current()`) → נופל ל‑defaults.

| שלב | רכיב נדרש | מוצג היום? | פעולה |
|---|---|---|---|
| **DISABLED** | מודעות לדגל `FOOTPRINT_DISABLED`/`S3_MUTE` | ❌ חסר | **להוסיף באנר "מושבת"** — כרגע מציג armed/blocked על state ישן |
| SOURCE | `v9_bars_footprint` freshness, מנויי `tick_reversal_12/15` | ❌ חסר | להוסיף (כרגע hard‑coded `in_memory`) |
| INPUT | `bid_vol`/`ask_vol` לכל רמה, `imbalance_pct`, `stacked_count`, `delta` | ❌ חסר | להוסיף |
| INTERPRETATION | `dominance`, `cumulative_delta`(COT), `amt`, `confluence_total`, `classification` | ❌ חסר | להוסיף |
| DETECTION | 4 גלאים (absorption / stacked_imbalance / sweep_return / exhaustion) + ספים | חלקי (buffer/bars בלבד) | לחשוף ספים + evidence "למה אין איתות" |
| GATE | `pre_fire_validator`, dedup, `calculate_size`, gateway‑injected | ❌ חסר | להוסיף |
| TARGETS/STOP | `stop=min(low,entry−tick)`, t1=+risk, t2=+2R, time_stop=15 | ❌ חסר | להוסיף |
| **DRIFT** | הרגיסטרי מסווג S3 כ‑**observer‑only**, אך הקוד החי `system_type=FIRING` + נתיב ירי T3 | — | **לאשר עם מייקל** |

## S4 · Woodies CCI (firing) — מחובר, live_inputs טובים

| שלב | רכיב נדרש | מוצג היום? | פעולה |
|---|---|---|---|
| INPUT | `cci_14`, `cci_6_tcci`, `trend_state`, `swi/czi/ema_34/lsma`, `predictor` | ✅ (8 שדות) | לסמן אילו display‑only (ema_34, czi) |
| INTERPRETATION | trend_direction, cci_zone, active_patterns, ready_to_route | ✅ | — |
| GATE | A1 strategic (BLUE/RED), RTH, freshness | ✅ | — |
| **GATE** | **Day‑Type Matrix verdict** (✅/⚠️/❌ לכל תבנית × יום) + `entry_hint` + `t1_ref` | ❌ רק `day_type≠UNKNOWN` | **להוסיף** — תבנית ❌ ליום (ZLR ב‑NeuE) נראית ירוקה כמו ✅ |
| **GATE** | **A7 universal** (news ±5m, cool‑down 30m, daily loss −$200, **stop 3–8pt D‑001**, bridge, EOD>60m) | ❌ חסר | **להוסיף** |
| **GATE** | **Anti‑patterns** AP1/AP4/AP5/AP7/AP8/AP9 + `reject_reason` | ❌ חסר | **להוסיף** — תבנית חסומה ב‑AP נראית כמו "לא זוהתה" |
| DETECTION | 9 תבניות (ZLR/TLB/TT/GB100/VEGAS/GHOST/FAMIR/HTLB/HFE) | ✅ | — |
| **DISPATCH** | `r_t1` מול `min_r_t1_threshold` (שער LIVE), `winning_pattern`, GRAY/YELLOW | ❌ חסר | **להוסיף** — 9 תבניות נראות "armed" עצמאית; המנגנון בוחר אחת לפי R_t1 |
| **TARGETS/STOP** | stop שכבתי (`primary 3 ticks` / ATR‑cap ×1.0/1.2/1.5 לפי קבוצה / floor 4 ticks), `atr_14_ticks`, `r_t1`, T1/T2 (ticks קבוע לפי תבנית), `entry_price` | ❌ **חסר לגמרי** | **להוסיף** — מודל הסטופ של Woodies שונה מ‑five_min |
| SIZING | A6: REACTIVE{HFE,FAMIR,TT}=2 חוזים/TIGHT · INITIATIVE=3/WIDE | ❌ חסר | להוסיף |
| **FACT** | ה‑inspector מקודד `confidence≥0.5` כפרוקסי, אך השער האמיתי הוא `r_t1≥threshold` | — | לתקן את שורת ה‑gate |

## S5 · TPO Profile (observer) — **לא מחובר כלל**

צריך `tpo_inspector` חדש שיקרא את `v9_tpo_sessions` (שורת CASH של היום) + `TPOProfile` חי, ויחשוף:
- **רמות:** `poc`, `vah`, `val`, `range_high/low`, `session_high/low`
- **IB:** `ib_high/low`, `ib_width`, `ib_classification`, `ib_locked`
- **צורה:** `profile_shape` (8 צורות) + `shape_confidence` + `shape_locked`, `current_letter`/`letter_count`
- **מבנה:** `single_prints`, `buying/selling_tail_count`, `hvn_prices`, `lvn_prices`, `naked_pocs`/`naked_poc_status`
- **שערי כוונה:** `intent`, **`otf_clarity`** (היתר LONG/SHORT), `migration_pattern`, `poc_migration.velocity/stuck_count`
- **איכות:** `data_quality` (OK/DEGRADED · gap>60s)

## S6 · Killzone (gate) — **לא מחובר כלל**

צריך `killzone_inspector` שיקרא `get_killzone_status()` + `is_gate_open()`, ויחשוף:
- **פסיקת שער:** `is_gate_open` (OPEN/CLOSED) — היתר המסחר עצמו, חסר היום
- **אזור פעיל:** `current_killzone`, `quality` (HIGH/MED/LOW/OFF), `volatility`, `sizing_modifier`, `session_phase`
- **סיבת חסימה:** `is_blocked` + `block_reason` (חג / manager_disabled / news / first_15min / last_15min / half_day)
- **תזמון:** `time_in_zone_min`, `time_to_next_zone_min`, `next_zone`
- **לוח שנה:** `is_trading_day`, `is_holiday_half_day`
- **DRIFT:** `definitions.py` מגדיר 8 אזורים ישנים (מת/legacy); הקנוני הוא **11 אזורים ב‑`zones.py`**. `_compute_rtb_session` ב‑build_status משתמש ב‑RTH גנרי 09:30–16:00 ולא בשער ה‑killzone — **לאשר**.

---

## שערים גלובליים / pre‑fire (חלים על כל מערכת יורה)

| שער גלובלי | מוצג ב‑Build Status? | פעולה |
|---|---|---|
| Bridge freshness (8 זרמים) | ✅ `bridge_inspector` | — |
| RTH window + `in_rth` | ✅ | — |
| S1 day_type classified · S4 trend≠GRAY (readiness) | ✅ degrade | — |
| **`pre_fire_validator` (7 בדיקות: side/ordering/`R:R≥1.0`/confidence/time_stop)** | ❌ **חסר** | **להוסיף כשורת readiness/gate גלובלית** |
| **`risk_checks` LIVE (loss $250 · 5 trades · 2 contracts · 14:30 cutoff · 2‑consec‑loss STOP)** | ❌ **חסר** | **להוסיף** — קריטי ל‑LIVE |
| News block (±10m) | ❌ לא ממומש (placeholder `risk_checks.py:70-74`) | לסמן כ"לא ממומש" |
| Gateway injected / route_setup reachable | ❌ חסר | להוסיף (כל מערכת בודקת `_gateway is None` פנימית) |
| `FOOTPRINT_DISABLED`/`S3_MUTE` flag awareness | ❌ חסר | להוסיף |

## דגלי drift לאישור מייקל
1. **S3 firing מול observer** — קוד חי = FIRING; רגיסטרי = observer‑only.
2. **Killzone 8 מול 11 אזורים** — `definitions.py` (ישן) מול `zones.py` (קנוני).
3. **S2 confidence≥0.5** ב‑inspector הוא פרוקסי; השער האמיתי הוא R_t1 (S4) / pre_fire (R:R≥1.0).
4. **footprint מוחרג מ‑readiness קריטי** (`_NON_CRITICAL_STREAMS`) — footprint DEAD לא מוריד readiness; בכוונה, אך כדאי לוודא מול הסטטוס המושבת.

---

### עדיפות הוספה מומלצת (לעץ ההחלטות)
**P0:** שני השערים הגלובליים (`pre_fire_validator`, `risk_checks`) · שלב TARGETS/STOP ל‑S2+S4 · Day‑Type Matrix verdict ל‑S4.
**P1:** חיווט S6 Killzone (שער אמיתי) · S/R+COT/AMT כשערים אמיתיים ל‑S2 · anti‑patterns+A7 ל‑S4 · freshness ל‑3 קובצי Sierra של S2.
**P2:** חיווט S5 TPO · pre‑open context ל‑S1 · באנר disabled ל‑S3.
