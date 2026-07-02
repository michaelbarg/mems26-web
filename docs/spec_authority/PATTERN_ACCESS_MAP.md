# MEMS26 — Pattern Access Map (נתיב-גישה מסודר לכל תבנית)

_נבנה 2026-06-28 (Cowork) מתוך האינדקס הקנוני: `_INDEX.md` (gen_index) · `docs/FLAG_INDEX.md` (live .env 2026-06-25) · `config/stop_anchors.yaml` · `config/targets.yaml` · `S4_WOODIES_TABLE_A`._
_מטרה: לכל תבנית — איפה הקוד (detection), מה הטריגר, איפה הסטופ, מאיפה היעדים, ואילו גייטים חיים חלים. **לא לגרוף עיוור — להסתכל כאן קודם.**_

---

## 0 · שרשרת-הגייטים החיה ב-Gateway (חלה על כל תבנית, לפי סדר)

מקור: `backend/v9/gateway/trading_gateway.py` · מצב מ-`FLAG_INDEX.md` (live .env).

| # | גייט | דגל | מצב חי | מה חוסם |
|---|------|-----|--------|---------|
| 1 | Feed watchdog | `FEED_WATCHDOG` | 🔴 OFF (ON ב-LIVE) | פיד 5min/woodies מעופש >90s |
| 2 | Cooldown (2-stop) | — | תמיד | אחרי 2 סטופים |
| 3 | Suffering-side veto | — (D-049) | תמיד | הכיוון ה"סובל" |
| 4 | Dedup fire guard | `DEDUP_FIRE_GUARD` | ✅ ON | ירי זהה תוך 30s |
| 5 | Layer-0 chop | `LAYER0_CHOP_GATE` | 🔴 OFF (standing) | — (מדולג) |
| 6 | Opening-type | `OPENING_TYPE_GATE` | ✅ ON | counter-drive בחלון-הפתיחה (עד IB-lock) |
| 7 | Day-type playbook | `DAYTYPE_PLAYBOOK` | 🟡 ON·**inert** | **NO-OP** — מחזיר FULL כש-POSITION_GATE=1 (חור R1) |
| 8 | Trend-direction (legacy) | `TREND_DIRECTION_GATE` | 🟡 ON·**inert** | מדולג (superseded) |
| 9 | Reactive-location (legacy) | `REACTIVE_LOCATION_GATE` | 🟡 ON·**inert** | מדולג (superseded) |
| 10 | **Day-type position** | `DAYTYPE_POSITION_GATE` | ✅ **ON** | כיוון × מחיר-מול-POC/IB · **כולל Nontrend-disable** · **PATTERN-BLIND** (R2) |
| 11 | Direction context | `DIRECTION_CONTEXT` + `DIRECTION_LSMA_VETO` | ✅ ON | ירי נגד כיוון-LSMA/CVD חי |
| 12 | **Cont-trend filter** | `CONT_TREND_FILTER` | ✅ ON | **CONT** דורש מגמת-LSMA מתמשכת K=3 ברים · **REV פטור** |
| 13 | Structural targets | `DAYTYPE_TARGETS_STRUCTURAL` | ✅ ON | מחליף T1/T2/T3 ב-IB/POC/VA (fail-safe ל-R) |
| 14 | Risk breakers | `PATTERN_LOSS_BREAKER` (N=2) · `PATTERN_RISK_CAPS` | ✅ ON | אחרי N הפסדים / חריגת-ריסק פר-תבנית |
| 15 | DEMO execution | `DEMO_EXECUTION_ENABLED` | 🔴 OFF | — (אין הזמנות DEMO) |

**משמעות מעשית:** היום הסלקטיביות מגיעה מ-#10 (DAYTYPE_POSITION_GATE) + #11 (LSMA/CVD) + #12 (CONT-trend) + Nontrend-disable. המטריצה פר-תבנית×יום (#7 playbook) **לא פעילה** — חור ידוע (CASCADE_AUDIT §5 R1).
**S3 מושתק:** `FOOTPRINT_DISABLED`/`S3_MUTE` ✅ → כל קלט footprint (COT/AMT/belly) רך/עקוף.

---

## 1 · S2 · Five-Min — 5 משפחות

סטופ פר-תבנית מ-`config/stop_anchors.yaml` (`STOP_ANCHORS_V2` ✅ ON · כולם −3T anchor_offset).
דגלי-S2 חיים: `S2_VSA_VOLUME` ✅ · `S2_VOL_ADAPTIVE` ✅ · `S2_REQUIRE_COT_AMT` 🔴 · `S2_ATR_RELATIVE` ✅ · `S2_CHART_ALL_DAYTYPES` ✅.

| תבנית | Detection (file) | טריגר-כניסה (מקור) | סטופ (anchor · max-risk) | יעדים | קבוצה |
|------|------------------|--------------------|--------------------------|--------|-------|
| `REACTIVE_LONG/SHORT` | `five_min_system.py::_detect_reactive` | B4 סוגר מעבר ל-high/low של B3 (4-בר) | `support_zone` w4 · 15נק' | R לפי-יום / structural | CONT |
| `INITIATIVE_LONG/SHORT` | `five_min_system.py::_detect_initiative` | פריצת הרמה (breakout bar) | `breakout_bar` w1 · 12נק' (הדוק) | R לפי-יום / structural | CONT |
| `DOUBLE_BOTTOM_EE / TOP_AA` | `patterns/double_bt.py` | שבירת neckline אחרי תחתית/פסגה 2 | `second_bottom_top` · 20נק' | R לפי-יום | REV |
| `INVERSE_HNS / HNS_TOP` | `patterns/head_shoulders.py` | שבירת neckline | `shoulder` (כתף-ימין) · 20נק' | R לפי-יום | REV |
| `BULL_FLAG / BEAR_FLAG` | `patterns/flags.py` | פריצת ה-flag | `breakout_bar` w1 · 15נק' (`flag_relative_t1`) | R לפי-יום | CONT |

יציאה (כל S2): thesis-based `S2_EXIT_DEFINITION_V6` — Type-A (close+vol / belly הפוך / TCCI×CCI / direction-change) · Type-B (wick/throwback/low-vol = להישאר) · Type-C (time-stop לפי-יום על DD).
סיזינג פר-תבנית×יום: `S2_AUTH_TABLE_V1` → `quality_tier.py` (אבל ראה חור R1 — playbook inert).

---

## 2 · S4 · Woodies — 9 תבניות

Detection ב-`backend/v9/systems/woodies/patterns/{name}.py`. סטופ מ-`stop_anchors.yaml`. סטופ-מנוע: `atr_stop.py`.
דגלי-S4 חיים: `HTLB_DIRECTION_GATE` ✅ (מַתְוֶוה כיוון לכל הוודיס) · `ZLR_SPEC_V2` ✅ · `TLB_SPEC_V2` ✅ · `VEGAS_SPEC_V2` ✅ · `HFE_DISABLED` ✅ · `RUNNER_TRAIL_V1` ✅ · `GIANT_BAR_STOP_V1` ✅.

| תבנית | Detection (file) | טריגר-כניסה (מקור Table A) | סטופ (anchor · max-risk) | יעדים | קבוצה / מצב |
|------|------------------|----------------------------|--------------------------|--------|-------------|
| ZLR | `patterns/zlr.py` | buy-stop 1T מעל high של בר-Stage-3 | `cluster_low` w4 · 15נק' | R לפי-יום | CONT · `ZLR_SPEC_V2` |
| TLB | `patterns/tlb.py` | 1T מעל בר-שבירת-קו | `since_trendline_peak` w8 · 15נק' | R לפי-יום | CONT · `TLB_SPEC_V2` (Stage-2 לא נבנה) |
| TT | `patterns/tt.py` | 1T מעל בר-האות | `zl_excursion` w9 · 15נק' | R לפי-יום | CONT · 0 ירי אי-פעם |
| GB100 | `patterns/gb100.py` | 1T מעל בר חציית +100 בחזרה | `cluster_low` w6 · 15נק' | R לפי-יום | CONT |
| VEGAS | `patterns/vegas.py` | שבירת rim של cup-and-handle | `swing_extreme` (t1×0.75 t2×1.0) · 20נק' | מידת-cup | REV · `VEGAS_SPEC_V2` |
| GHOST | `patterns/ghost.py` | שבירת neckline (CCI H&S) | `shoulder` (t1×0.5) · 18נק' | מידת-H&S | REV |
| FAMIR | `patterns/famir.py` | flip אחרי ZLR שנכשל | `failed_bar` · 12נק' | R לפי-יום | REV |
| HTLB | `patterns/htlb.py` | שבירת קו אופקי | `consolidation_extreme` · 20נק' | R לפי-יום | REV · גם מַתְוֶוה-כיוון |
| HFE | `patterns/hfe.py` | hook מקצה ±200 | `extreme_bar` (t1-shift −1) · 20נק' | R לפי-יום | REV · **`HFE_DISABLED` ✅ → לא יורה** |

---

## 3 · מקורות-אמת פר-תבנית (להעמיק)

- **זיהוי/כניסה (מקור):** `S4_WOODIES_TABLE_A_Pattern_Setup.csv` (S4) · `S2_AUTH_TABLE_V1.md` + `S2_EXIT_DEFINITION_V6.md` (S2).
- **סטופ (מקור):** `S4_WOODIES_TABLE_C` §6.1 · **סטופ (קוד):** `config/stop_anchors.yaml`.
- **יעדים (קוד):** `config/targets.yaml` (R לפי-יום) + `structural_targets.py` (כש-`DAYTYPE_TARGETS_STRUCTURAL`).
- **יום-מטריצה (מקור):** `S4_WOODIES_TABLE_B` (S4) · `S2_AUTH_TABLE_V1` §4 (S2).
- **מצב-דגלים קנוני:** `docs/FLAG_INDEX.md` (תמיד — לא מהזיכרון/קוד-default).
- **חורים ידועים:** CASCADE_AUDIT §5 (R1 playbook inert · R2 position-gate pattern-blind).
