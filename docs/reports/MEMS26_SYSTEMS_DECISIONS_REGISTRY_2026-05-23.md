# MEMS26 — Systems & Decisions Registry

**Status:** 🟢 LIVE registry · single source of truth for 6-system map + per-pattern decision tracker
**Created:** 2026-05-23 (Michael strategic review · pre-LIVE)
**Owner:** Michael Barg
**Author:** Cursor agent (Claude) · sourced from spec authority + actual code state
**Locks captured in this session (2026-05-23):**

| # | החלטה | קישור |
|---|---|---|
| L1 | **S1 = Observer** (locked) | §2 + Master Index V2 |
| L2 | **S3 = Firing system** (locked — supersedes D-082 + D-086) | §2 + §6 D-089 (pending doc) |
| L3 | **S3 `if mode == "LIVE"` safety net = KEEP** until Michael says otherwise | §6.3 |
| L4 | Per-pattern table format: 4 cols = known / Claude rec / Michael lock / pre-LIVE post-SHADOW | §4 |

---

## 0. הוראות שימוש למסמך הזה

- **קרא לפני כל פעולה שנוגעת ל-firing/observer/gate** של מערכת.
- **עמודה "🔒 החלטה נעולה — Michael" ריקה ב-V1** — מיועדת למלא בעצמך בימים הקרובים. כל מילוי = D-decision חדש (D-089+).
- **עמודה "המלצה pre-LIVE לפי SHADOW"** תמולא אחרי SHADOW soak (5-10 ימים). לפני זה — אל תשנה stops/targets/patterns (per `P32_NEXT_CHAT_PROMPT_2026-05-22.md` §5).
- אם משהו כאן סותר את `docs/spec_authority/MEMS26_MASTER_INDEX_V2.markdown` — D-decisions מאוחרים מנצחים את Master Index, ו-Master Index מנצח את Constitution V3 (per heirarchy ב-`docs/spec_authority/README.md`).

---

## 1. מצב — איפה אנחנו במרחב (2026-05-23 בוקר)

| ציר | ערך | מקור |
|---|---|---|
| **Phase** | P31 לפני **P-S0** (SHADOW activate gate) | `docs/handoff/P31_TASK_BOARD.md` §0 |
| **% ל-LIVE** | ~82% | `P31_TASK_BOARD.md` §0 |
| **Backend `:8000`** | 🟢 PID 52505 (last restart 22/5 16:11 IL) | `P31_TASK_BOARD.md` §0 |
| **Frontend `:3000`** | 🟢 PID 26120 | `P31_TASK_BOARD.md` §0 |
| **Bridge (12 streams)** | 🟢 `json_bridge.py` PID 55100 · §9 TZ workaround active | `P31_TASK_BOARD.md` §0 |
| **`v9_trades` (DB)** | S2=3 · S4=2,467 · all SHADOW · 0 LIVE | `sqlite3 data/mems26_local.db` (23/5) |
| **RCA-1 (S6 direction-aware)** | ✅ **DONE** — code + 5 regression tests | `backend/v9/services/trade_context.py:285-292` · `tests/v9/services/test_trade_context.py:143-166` |
| **UAT S2 fire ב-RTH** | ✅ **DONE** — 3 trades fired | `v9_trades` firing_system=2 |
| **Stepped POC chart** | ✅ **DONE** — approved by Michael 22/5 ערב | `TpoContinuityOverlay.tsx` · `tpo_history_snapshotter.py` · migration 017 |
| **חוסם open לפני SHADOW** | D-089 doc + sync `wrappers.py` + `types.ts` (S3 → firing) | §6 |

---

## 2. Spec Authority — היררכיית מקורות

כפי שמוגדר ב-`docs/spec_authority/README.md`:

```
1. Master Index V2 (LOCKED 16/5)         ← אינדקס סמכותי לכל המערכות
2. Constitution V3 FINAL (9/5)            ← 4-Layer architecture
3. D-decisions LOCKED (D-001 → D-089)     ← מאוחר מנצח מוקדם
4. Per-system spec docs (Drive IDs)       ← Day Type Tree V2, Footprint V3, Woodies V1, ...
5. compliance_manifest.yaml per system    ← code-truth
```

**3 המסמכים הסמכותיים השמורים מקומית:**

| מסמך | path | הערות |
|---|---|---|
| Master Index V2 | `docs/spec_authority/MEMS26_MASTER_INDEX_V2.markdown` | LOCKED 16/5/2026 |
| Constitution V3 Final | `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt` | 9/5/2026 |
| MEMS26 FIRST | `docs/spec_authority/MEMS26_FIRST.md` | mandatory first-read |

**Drive IDs לא שמורים מקומית** (per `README.md` §"Related Primary IDs"):
- 3-Mode V3 LOCKED: `1F9KWXpSplBsPHhLu2erlMbHDQp4EmqmV4T00U9NYHyM`
- Day Type Tree V2: `1Tx1sfVdebnTNS2Cv8MQpnBOXwCbVutmFyIZ-tJtYGuU`
- Spec Registry: `1_gQCaMTq-3D3Fe34_ddV54-9eQvOAW9Mfx4zAyPMSwk`
- 5-min Tree V3.3: `1dP8x4vaat49BAw0L1DgOBTBqQ4Ci1YllUoWTwoy1DSQ`
- Footprint Spec V3: `1iPndwDKwYn70pXCwkHNJVyAwLeU8WislDGAQX3HXvT4`
- Woodies CCI Spec V1: `1NtKDNZNVwWi8Dio_C-42Yj0c6DPFGEfnFSo3Vx4rp0k`
- TPO Tree V2: `1DrjQOphmG3Edn0QaniSRf7Ijr50i-7TWrNqRWK2xn_0`
- Killzone Spec V1: `1s6GpXv2zXy8KzQASkzIgdxRYDDG8KYWkyokdq-3iSzY`

---

## 3. טבלת 6 המערכות — תפקיד · כניסה · מקור · חישוב · יציאה · חוסמים

| # | מערכת | תפקיד נעול | Trigger (כניסה) | מקור נתון | חישוב פנימי | יציאה — `route_setup` | חוסמים | מקורות סמכותיים |
|---|---|---|---|---|---|---|---|---|
| **S1** | Day Type | 🔒 **OBSERVER** | bar 5min + IB lock + 10:00 ET | `v9_bars_5min` + `v9_tpo_history` (PD H/L/C) | A1→A7 state machine · 6 day types · `probability`+`certainty`+`lock_state` | **NEVER** | — | Day Type Tree V2 · `docs/architecture/for_designer/02_SYSTEMS_SPEC.md` §S1 · `backend/v9/systems/day_type/compliance_manifest.yaml` · `state_machine.py` |
| **S2** | 5-Min T1 | 🔒 **FIRING** | bar 5min close | `v9_bars_5min` + `v9_footprint_signals` (COT/AMT) + S5 POC_VOL | 4-bar Reactive/Initiative · belly + POC trend · COT/AMT comparison | `route_setup(2)` ← entry=close · stop=±2pt **קבוע** · T1=1R · T2=2R · T3=0 | AMT (fixed 22/5) · pre_fire · gateway · S6 killzone | Constitution V3 §T1 · 5-min Tree V3.3 · `backend/v9/systems/five_min/five_min_system.py:317-421,551-647` · `setup_emitter.py` · `compliance_manifest.yaml` |
| **S3** | Footprint T3 | 🔒 **FIRING** (locked 23/5, **supersedes D-082+D-086**) | bar 15-tick reversal + footprint levels | `v9_bars_footprint` + bid/ask volume per level | 4 detectors במקביל: Absorption · StackedImb · Sweep+Return · Exhaustion · `strength` 0..1 | `route_setup(3)` ← entry/stop/T1/T2 **לא מהsignal** — מ-`pre_fire_validator` (🔴 לא מתועד) | `if mode == "LIVE"` safety net (🔒 KEEP per Michael 23/5) · pre_fire · gateway | Footprint Spec V3 · Constitution V3 §T3 · `backend/v9/systems/footprint/footprint_system.py` · `signals/{absorption,stacked_imbalance,sweep_return,exhaustion}.py` · `compliance_manifest.yaml` · D-082 + D-086 (overridden) |
| **S4** | Woodies T2 | 🔒 **FIRING** · 2,467 SHADOW trades | bar woodies_5min close (D-074: 5min, **לא** 30min) | `~/SierraChart_Data/v9_export/woodies_5min.json` → `v9_bars_5min_woodies` + 11 studies | 9 detectors → best by confidence → `decision_tree.evaluate_bar` A1–A7 → `ready_to_route` | `route_setup(4)` ← entry/stop/T1/T2 מה-detector (§5) | A1–A7 fail · cluster_guard · cooldown · SSV · chop | Woodies CCI Spec V1 · `docs/v9/MEMS26_WOODIES_SPEC_V1_DERIVED.md` · Decision Tree V1 · D-074 · `backend/v9/systems/woodies/{woodies_system.py,decision_tree.py,pattern_engine.py,patterns/*.py}` |
| **S5** | TPO | 🔒 **OBSERVER** | bar 5min + TPO letters | `tpo.json` + native Sierra IB study | profile_builder · POC/VAH/VAL · POC migration · HVN/LVN · IB lock | **NEVER** | — | TPO Tree V2 · `02_SYSTEMS_SPEC.md` §S5 · `backend/v9/systems/tpo/tpo_system.py` · `compliance_manifest.yaml` |
| **S6** | Killzone | 🔒 **OBSERVER + GATE** | wall clock ET + session flags | `datetime.now(zoneinfo("America/New_York"))` + D-073 holidays | 11 zones · edge_class A/B/C/D · `gate_open` · `quality_modifier` | **NEVER** (אבל **חוסם** firing systems כש-`gate_open=False`) | RCA-1 ✅ DONE 22-23/5 | Killzone Spec V1 · D-061 (trade-all-the-time) · D-068 (Market Clock) · D-073 (2026 NYSE holidays) · `backend/v9/systems/killzone/{killzone_system.py,definitions.py,zone_playbook.py}` |

---

## 4. טבלת פטרנים — S2 (4 patterns)

מקור קוד: `backend/v9/systems/five_min/five_min_system.py:317-421,551-647` + `setup_emitter.py`. מקור spec: Constitution V3 §T1 + 5-min Tree V3.3 (Drive `1dP8...DSQ`).

| Pattern | מה ידוע מהקוד | המלצת Claude + מחקר | 🔒 החלטה נעולה — Michael | המלצה pre-LIVE (post-SHADOW) |
|---|---|---|---|---|
| **Reactive LONG** | 4-bar: b1=c<o+vol>0 · b2=vol≤10%×b1 · b3=c>o+belly_dominant+poc_rising · b4=c>o. **AND** `cot > amt`. Stop=bar.low − **2.00pt קבוע**. T1=1R. T2=2R. T3=0. confidence base=0.75 | Constitution V3 §T1 דורש "drop 90% volume" — תואם. דאגה: stop 2pt agnostic לתנודתיות (ATR=0.5 vs ATR=3.0). | _____ | אם ATR בשעת ירייה > 2× ממוצע יומי → לשקול ATR-adaptive stop |
| **Reactive SHORT** | Mirror של LONG. **AND** `cot < amt`. Stop=bar.high + 2pt. | תואם §T1 Reactive Short. דאגה: COT=−144K (לפני 22/5) הפך תנאי SHORT לטריוויאלי תמיד-True. | _____ | למדוד hit-rate Reactive SHORT לפני/אחרי AMT fix |
| **Initiative LONG** | 4-bar: b1=expansion ≥6-7 ticks · b2=Higher Low / חזרה ל-POC · b3=continuation גדולה מ-b1 · b4=second test = entry. **AND** `cot < amt`. | תואם §T1 Initiative. הפרמטר "6-7 ticks" hardcoded — לא נחשף ל-config. | _____ | post-SHADOW: לבדוק אם "expansion ≥6 ticks" עובד גם ב-Trend_DD (low vol) |
| **Initiative SHORT** | Mirror. **AND** `cot > amt`. | אותו דבר. | _____ | אותו דבר |

**חוסרים גלובליים ל-S2:**
- `t3 = 0.0` קבוע — Constitution V3 §Layer 4 דורש T3 ל-Trend_Normal/Variation/Trend_DD/Neutral. **חסר logic**.
- Stop fixed 2pt — Constitution V3 PART 5 #15 קובע "ATR-adaptive" כ-MISSING.
- אין `time_stop` enforcement (קיים בschema, לא נאכף).
- אין "active pattern overlay" (REQ-UI-004 ב-`02_SYSTEMS_SPEC.md` §S2 §6).

---

## 5. טבלת פטרנים — S4 (9 patterns) — **כולם מאומתים בקוד**

מקור קוד: `backend/v9/systems/woodies/patterns/*.py` (9 קבצים). מקור spec: Woodies CCI Spec V1 · `docs/v9/MEMS26_WOODIES_SPEC_V1_DERIVED.md` · Decision Tree V1 (DTV1). MES TICK_SIZE = 0.25.

| # | Pattern | קבוצה | Lookback | Stop ticks | T1 ticks | T2 ticks | T3 | R:R (T1/T2) | confidence formula | spec ref | מה ידוע — בסיס ספציפי | המלצת Claude + מחקר | 🔒 Michael | pre-LIVE post-SHADOW |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **ZLR** | CONT | 12 bars | **8** (2.00pt) | **12** (3.00pt) | **24** (6.00pt) | — | 1.5 / 3.0 | `min(0.9, 0.5 + cci/400)` | DTV1 §A3 | Pullback CCI מ-±100 חזרה לאזור 0, ועלייה | baseline בריא; הכי הרבה fires היסטוריים | _____ | אם hit-rate T1 ≥ 55% → keep |
| 2 | **TLB** | CONT | 10 bars | **10** (2.50pt) | **15** (3.75pt) | **30** (7.50pt) | — | 1.5 / 3.0 | `min(0.85, 0.4 + abs(curr-pred)/200)` | DTV1 §A2 | Linear regression slope ±2 + break ≥10 CCI | **+25% stop vs ZLR** (10 vs 8) — logical: TLB דורש confirmation breakout | _____ | אם DD גבוה → tighten ל-9 ticks |
| 3 | **TT** | CONT | 3 bars | **8** | **12** | **20** | — | 1.5 / **2.5** | קבוע `0.7` | DTV1 §A3 | TCCI hooks back to CCI14 then bounces; trend BLUE/RED | **T2 נמוך** (20 vs 24) — TT הוא "turbo trend continuation" קצר | _____ | אם T1 hit ו-T2 לא → 22 ticks |
| 4 | **GB100** | CONT | 3 bars | **8** | **12** | **24** | — | 1.5 / 3.0 | `min(0.85, 0.5 + (curr-100)/200)` | DTV1 §A4 | CCI crosses ±100 with momentum, trend BLUE/RED | זהה ל-ZLR — logical, שניהם continuation | _____ | post-SHADOW |
| 5 | **VEGAS** | REV | 20 bars | **12** (3.00pt) | **16** (4.00pt) | **32** (8.00pt) | — | 1.33 / 2.67 | קבוע `0.75` | DTV1 §B1 | Price HH + CCI LH (divergence) | **Stop רחב** (12 vs 8) — reversal trades צריכים סטופ רחב | _____ | למדוד hit-rate reversal vs continuation |
| 6 | **GHOST** | REV | 20 bars | **12** | **16** | **32** | — | 1.33 / 2.67 | קבוע `0.7` | DTV1 §B2 | CCI head-and-shoulders pattern | זהה ל-VEGAS — logical | _____ | post-SHADOW |
| 7 | **FAMIR** | REV | 5 bars | **10** | **14** | **28** | — | 1.4 / 2.8 | `min(0.8, 0.5 + (200-max)/100)` | DTV1 §B3 | CCI מתקרב ל-±200 ולא מצליח (NEAR=170, max<210) | T1/T2 mid-range בין CONT לREV | _____ | post-SHADOW |
| 8 | **HTLB** | REV | 15 bars | **10** | **14** | **28** | — | 1.4 / 2.8 | קבוע `0.65` | DTV1 §B4 | CCI breaks horizontal level (2+ touches, tolerance=15 CCI) | זהה ל-FAMIR | _____ | post-SHADOW |
| 9 | **HFE** | REV | 12 bars | **8 (DLL) / bar.low+8 (Python)** | **12** | **24** | — | 1.5 / 3.0 | `min(0.8, 0.5 + hook/400)` | DTV1 §A3 / pattern #9 | CCI hit ±200 and hooks back. Primary: DLL JSON `hfe_detected`. Fallback: Python compute | **🟡 חריג**: HFE משתמש ב-`bar.low/high` (לא close) ל-stop בPython fallback | _____ | להחליט: DLL only או keep Python fallback |

**חוסרים גלובליים ל-S4:**
- **T3 לא מוגדר ב-9 patterns** — `targets[]` רק 2 (T1, T2). Constitution V3 §Layer 4 דורש T3 ל-Trend_Normal/Variation/Trend_DD/Neutral. **חסר logic**.
- **Confidence formulas שונות** — 5 dynamic, 4 קבועים. לא תיעוד שיטתי. למדוד SHADOW.
- **HFE כפול-מסלול** (DLL/Python) — עלול ליצור פערים. לקבע ל-LIVE: DLL only.
- **`decision_tree` מתעלם ממחירים** — רק מאשר/חוסם. כל ההיגיון הכלכלי בידי הdetectors.

---

## 6. טבלת פטרנים — S3 (4 detectors)

מקור קוד: `backend/v9/systems/footprint/signals/{absorption,stacked_imbalance,sweep_return,exhaustion}.py`. מקור spec: Footprint Spec V3 (Drive `1iPn...XvT4`) · Constitution V3 §T3.

**⚠ קריטי**: ה-detectors מחזירים רק `{signal, direction, level, strength, evidence}` — **אין entry/stop/T1/T2**. הם מחושבים ב-`backend/v9/shared/pre_fire_validator.py` או ב-`footprint_system.py::calculate_size` (🔴 לא תיעדנו לעומק עדיין — gap לפני LIVE).

| Detector | מה ידוע מהקוד | המלצת Claude + מחקר | 🔒 Michael | pre-LIVE post-SHADOW |
|---|---|---|---|---|
| **Absorption** | Lookback=5 bars. ABSORPTION_RATIO=**2.0** · MIN_VOLUME=**50** · MIN_LEVEL=10. **Direction = COUNTER** (absorption at high → SHORT). | thresholds מסומנים `🟡 V1 defaults — calibrate post-SHADOW` בקוד עצמו. הtargets לא בdetector. | _____ | calibrate ABSORPTION_RATIO + MIN_VOL לפי SHADOW |
| **Stacked Imbalance** | STACK_N=**3** levels רצופים. IMB_THRESHOLD=**2.5** (ask/bid או הפוך). MIN_LEVEL_VOL=10. **Direction = WITH** (BUY_DOMINATED → LONG). | אותה בעיה: thresholds V1 default + entry/stop/T1/T2 לא בkוד | _____ | calibrate STACK_N + IMB_THRESHOLD |
| **Sweep + Return** | Lookback=5. MIN_SWEEP_TICKS=**2.0pt**. RETURN_BARS=3. `cur_high > range_high+2pt` AND `cur_close ≤ range_high` → SHORT. **Direction = COUNTER**. | MIN_SWEEP_TICKS=2.0 V1 default. | _____ | לבדוק האם sweep_pts threshold עובד ב-low-volume sessions |
| **Exhaustion** | TREND_BARS=**4** · EXHAUSTION_FACTOR=**0.6** (vol < 60% של ממוצע) · DIRECTIONAL_BODY_PCT=**0.5**. **Direction = COUNTER** (bull exhaustion → SHORT). | V1 defaults. | _____ | לבדוק false-positive ב-news minutes |

### 6.1 — D-089 — S3 = FIRING (locked Michael 23/5) — 🔒 LOCKED + sync'd

**Status:** 🔒 **LOCKED** · doc at `docs/decisions/D-089_S3_FIRING_LOCKED.md` · sync'd ב-`types.ts` + `wrappers.py`

**מה ההחלטה אומרת:**
S3 (Footprint T3) מסווג מחדש כ-**Firing system**, מבטל את D-082 (S3 = Observer only per V3 spec) ואת D-086 (S3 SHADOW firing path tolerated until post-SHADOW).

**מה כן ומה לא נכלל ב-D-089:**

| Capability | במצב הנעילה החדשה? | הערה |
|---|---|---|
| Observer journal every bar (`v9_footprint_journal`) | YES | ממשיך כרגיל |
| Signal detection + internal sizing (full/half/reject) | YES | ממשיך כרגיל |
| `pre_fire_validator` | YES | ממשיך כרגיל |
| SHADOW row in `v9_trades` | YES | ממשיך כרגיל |
| **`if mode == "LIVE":` safety net ב-`_fire()`** | 🔒 **KEEP** (Michael 23/5) | "להשאיר עד שאני אגיד" — לא להסיר עד SHADOW data + הוראה מפורשת |
| DEMO slot | NO (עדיין) | post-SHADOW decision |
| LIVE slot | NO (עדיין) | post-LIVE-pilot decision |

**3 הסינקים שנדרשים מהנעילה (פעולות מיידיות לפני SHADOW activate):**

1. **`docs/decisions/D-089_S3_FIRING_LOCKED.md`** — לתעד את ההחלטה והקשר ל-D-082+D-086 (15 דק').
2. **`backend/v9/systems/wrappers.py:8-14`** — לעדכן S3 role לfiring (אם כיום observer).
3. **`frontend/v9/src/v9/types/index.ts:222-233`** — להחזיר `S3 = firing` (היה firing → תוקן ל-observer ב-22/5 commit `2bc6796` per D-082; D-089 מבטל את התיקון הזה).

**Cross-system implication:**
- כל הconfluence/agreement filters ב-`trade_context.py::_system_agrees(sid=3)` כבר direction-aware (לא צריך RCA נוסף).
- `02_SYSTEMS_SPEC.md` §S3 כבר כתוב "FIRING" — מתעד את הspec הקיים.

---

## 7. רכיבים חסרים לפיתוח עד LIVE

מבוסס על Constitution V3 PART 5 (🔴 MISSING) · `MEMS26_FIRST.md` §"Components remaining" · `P31_TASK_BOARD.md` · קריאת קוד 2026-05-23.

### 7.1 — חוסמי SHADOW activate (לפני P-S0)

| # | רכיב | סטטוס | קובץ | מאמץ |
|---|---|---|---|---|
| 1 | **D-089 S3 firing locked doc** | 🟡 verbal locked, doc חסר | `docs/decisions/D-089_S3_FIRING_LOCKED.md` | 15 דק' |
| 2 | **`wrappers.py` S3 → firing** | 🟡 sync needed (post D-089) | `backend/v9/systems/wrappers.py:8-14` | 5 דק' |
| 3 | **`types.ts` S3 → firing** | 🟡 sync needed (revert commit `2bc6796` partial) | `frontend/v9/src/v9/types/index.ts:222-233` | 5 דק' |
| 4 | **S3 entry/stop/T1/T2 spec audit** | 🔴 לא תיעדנו | `pre_fire_validator.py` + `footprint_system.py::calculate_size` | 1-2h חקירה |
| 5 | **S3 `if mode == "LIVE"` safety net** | 🔒 **KEEP** (Michael 23/5) | `footprint_system.py::_fire()` | אפס פעולה |

### 7.2 — RCA-1 ו-UAT S2 ו-Stepped POC — ✅ DONE (23/5 review)

| # | רכיב | סטטוס | ראיה |
|---|---|---|---|
| 6 | **RCA-1: S6 `_system_agrees` direction-aware** | ✅ **DONE** | `trade_context.py:285-292` + 5 tests `test_trade_context.py:143-166` |
| 7 | **UAT S2 fires in RTH** | ✅ **DONE** | 3 trades fired (`firing_system=2` in `v9_trades`) |
| 8 | **Stepped POC chart visualization (Issue B)** | ✅ **DONE** approved 22/5 ערב | `TpoContinuityOverlay.tsx` · `tpo_history_snapshotter.py` · migration `017_v9_tpo_history_unique_ts.sql` |

### 7.3 — Trade Management gaps (Constitution V3 PART 5)

| # | רכיב | סטטוס | המלצה pre-LIVE |
|---|---|---|---|
| 9 | **Trailing stop after T1** | 🔴 חסר — היום Smart BE רק מעביר ל-entry | DEMO אחרי SHADOW |
| 10 | **Partial exit at T1** (1/3 או 1/2 חוזים) | 🔴 חסר — כל 3 חוזים יחד היום | DEMO |
| 11 | **Time stop enforcement** | 🔴 בschema, לא נאכף | חובה לפני LIVE — `time_stop_minutes` חייב לפעול |
| 12 | **T3 dynamic** | 🔴 קבוע 0.0 בכל ה-firing systems | DEMO+ |
| 13 | **ATR-adaptive stops** | 🔴 stops קבועים (8/10/12 ticks) | DEMO+ — לא לשנות לפני SHADOW data |

### 7.4 — Architecture gaps (Constitution V3 PART 5 #1-#16)

| # | רכיב | סטטוס | הערה |
|---|---|---|---|
| 14 | **L0 Market State Gate** (chop_score 0-100, 4 states) | 🟡 חלקי — `chop_state` ב-gateway | Constitution V3 §Layer 0 |
| 15 | **15-tick reversal bar primary entry** | 🟡 stream פעיל, אבל לא mandatory entry | Constitution V3 PART 5 #1 |
| 16 | **Per-bar Volume Profile מ-reversal bars** | 🟡 partial | Constitution V3 PART 5 #2 |
| 17 | **Cluster detection** | 🟡 קוד ב-`reversal_routes.py` — לא בדקנו לעומק | Constitution V3 PART 5 #3 |
| 18 | **Empty zone detection** | 🟡 partial | Constitution V3 PART 5 #4 |
| 19 | **Setup → Entry handoff** (15-tick reversal as L3) | 🟡 partial | Constitution V3 PART 5 #5 |
| 20 | **UFL / UFH primitive** (Unfair Low/High) | 🔴 חסר | Constitution V3 PART 5 #11 |
| 21 | **Tail Detection** (3+ TPO letters) | 🔴 חסר | Constitution V3 PART 5 #12 |
| 22 | **Direction Change Detector** | 🔴 חסר — נדרש ל-trade management exits | Constitution V3 PART 5 #16 |
| 23 | **Behavior Phase** | 🔴 חסר | Constitution V3 PART 5 #15 |

### 7.5 — SHADOW/DEMO/LIVE infra (`MEMS26_FIRST` §Components remaining)

| # | רכיב | Phase | סטטוס |
|---|---|---|---|
| 24 | **Per-system promotion logic** | post-SHADOW | 🔴 חסר |
| 25 | **SHADOW Analyst Agent** (`backend/v9/agents/shadow_analyst.py`) | post-SHADOW | 🔴 חסר |
| 26 | **Risk Management Widget** (Cockpit V6 §4, LIVE only) | pre-LIVE | 🔴 חסר |
| 27 | **Emergency Kill UI** | pre-LIVE | 🔴 חסר |
| 28 | **LIVE Pre-Flight Checklist Modal** (Cockpit V6 §8) | pre-LIVE | 🔴 חסר |
| 29 | **Mode Progression Card UI** | post-SHADOW | 🔴 חסר |

---

## 8. עץ המערכת המלא

```
MEMS26 V9 — autonomous MES futures trading
│
├── 📚 Spec Authority (locked, single source of truth)
│   ├── Master Index V2 (16/5/2026)      ─── docs/spec_authority/MEMS26_MASTER_INDEX_V2.markdown
│   ├── Constitution V3 FINAL (9/5/2026) ─── docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt
│   ├── MEMS26 FIRST.md                  ─── docs/spec_authority/MEMS26_FIRST.md
│   └── D-decisions (D-001 → D-088 + D-089 pending doc)
│
├── 🏛 V9 Architecture — 4 Layers (Constitution V3 PART 1)
│   │
│   ├── L0 — Market State Gate           [🟡 partial · chop_state in gateway]
│   │
│   ├── L1 — Setup Identification (3 firing systems)
│   │   ├── S2 — 5-Min T1 [🔒 FIRING · 3 SHADOW trades]
│   │   │   ├── Reactive  LONG/SHORT  (4-bar + COT>AMT / COT<AMT)
│   │   │   └── Initiative LONG/SHORT (4-bar expansion + COT<AMT / COT>AMT)
│   │   │   Code: backend/v9/systems/five_min/ · 14 files
│   │   │   Status: 🟢 fires confirmed RTH 22/5
│   │   │
│   │   ├── S3 — Footprint T3 [🔒 FIRING — locked 23/5, supersedes D-082+D-086]
│   │   │   ├── Absorption       (ratio 2.0, lookback 5)   COUNTER
│   │   │   ├── Stacked Imbalance (3 levels, ratio 2.5)    WITH
│   │   │   ├── Sweep + Return    (5 bars, 2pt sweep)      COUNTER
│   │   │   └── Exhaustion        (4-bar trend, vol<60%)   COUNTER
│   │   │   Code: backend/v9/systems/footprint/ · 8 files
│   │   │   Status: 🟡 entry/stop/T1/T2 spec gap · safety net KEEP
│   │   │
│   │   └── S4 — Woodies T2 [🔒 FIRING · 2,467 SHADOW trades · 5-min per D-074]
│   │       ├── Continuation: ZLR · TLB · TT · GB100
│   │       └── Reversal:     VEGAS · GHOST · FAMIR · HTLB · HFE
│   │       Code: backend/v9/systems/woodies/ · 9 pattern files + decision_tree A1-A7
│   │       Status: 🟢 working · all 9 patterns coded · T3 gap
│   │
│   ├── L2 — Quality (3 observer systems)
│   │   ├── S1 — Day Type [🔒 OBSERVER]
│   │   │   A1→A7 state machine · 6 day types · endpoint /api/v9/day_type/v9/current
│   │   │
│   │   ├── S5 — TPO [🔒 OBSERVER]
│   │   │   POC/VAH/VAL · POC migration · HVN/LVN · IB lock
│   │   │   endpoint /api/v9/tpo/current · Stepped POC chart ✅
│   │   │
│   │   └── S6 — Killzone [🔒 OBSERVER + GATE]
│   │       11 zones · gate_open · edge_class A/B/C/D
│   │       endpoint /api/v9/killzone/current
│   │       RCA-1 ✅ DONE
│   │
│   ├── L3 — Entry Execution (15-tick reversal)
│   │   ├── Cluster detection      [🟡 partial]
│   │   ├── Empty zone detection   [🟡 partial]
│   │   └── Setup→Entry handoff    [🟡 partial]
│   │
│   └── L4 — Trade Management (TradeManager)
│       ├── ✅ accept_setup / on_fill / on_target_hit / on_stop_hit
│       ├── ✅ Smart BE on T1 hit
│       ├── 🔴 trailing stop
│       ├── 🔴 partial exit T1
│       ├── 🔴 time stop enforcement
│       ├── 🔴 T3 dynamic
│       └── 🔴 ATR-adaptive stops
│
├── 🔌 Data Pipeline (LOCAL ONLY · CLOUD_URL=localhost:8000)
│   Sierra DLL (sc_study/MES_AI_DataExport.cpp)
│       ↓ writes JSON
│   ~/SierraChart_Data/v9_export/{woodies_5min,footprint,tpo,live_price,...}.json
│       ↓ Bridge (12 streams · §9 TZ workaround active)
│   FastAPI :8000 (POST /api/v9/bars/*)
│       ↓ INSERT + BarRouter.dispatch
│   SQLite (data/mems26_local.db)
│       ↓ system.process_bar(event)
│   TradingGateway.route_setup(setup, system_id)
│       ↓ gates: cooldown · cluster_guard · SSV · chop
│   ShadowExecutor → INSERT v9_trades (state=PENDING)
│
├── 🛣 Path to LIVE (P30 Road · P31 daily)
│   ✅ Phase 0-2: P27.5 → P28 → P29
│   ✅ P30 Waves 0-2 (D-088, D-087)
│   ✅ P31 STOP_HIT code · T2 Woodies CCI · COT session reset · AMT 90-min rolling
│   ✅ P31-02 S2 UAT RTH (22/5)
│   ✅ Issue B (Stepped POC chart) approved (22/5 ערב)
│   ✅ RCA-1 (S6 direction-aware) coded + 5 tests
│   🟡 D-089 doc + sync (15 דק' + 10 דק' code)
│   ⬜ P-S0 SHADOW activate
│   ⬜ SHADOW soak 5-10 days (≥20 trades, 4h green)
│   ⬜ DEMO soak (Sierra Sim · 7 days)
│   ⬜ P-L0 Preflight (kill-switch, Registry §18)
│   ⬜ P-L1 LIVE micro (1 חוזה · יום)
│   ⬜ LIVE full (D-067 lift · push to main → blasttt.com)
│
└── 🛡 Guardrails (Pre-LIVE protocol)
    ├── M13 IRON: Sierra > Spec > Computed · NEVER INVENT
    ├── M14: STOP + report if already done
    ├── M18: pre_fire_validator per fire (D-063)
    ├── Bridge LOCAL-ONLY (CLOUD_URL=localhost:8000)
    ├── 4-axis UAT: Quality + Recency + Cardinality + Latency
    └── Strategic stop at phase gates + plan contradictions
```

---

## 9. References — מפת מסמכים מלאה

### 9.1 — Spec authority (local)
| מסמך | path | LOCKED |
|---|---|---|
| Master Index V2 | `docs/spec_authority/MEMS26_MASTER_INDEX_V2.markdown` | 16/5/2026 |
| Constitution V3 Final | `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt` | 9/5/2026 |
| MEMS26 FIRST | `docs/spec_authority/MEMS26_FIRST.md` | living |
| Spec authority README | `docs/spec_authority/README.md` | 18/5/2026 |

### 9.2 — Architecture (for designer)
| מסמך | path |
|---|---|
| 00 README | `docs/architecture/for_designer/00_README.md` |
| 01 Architecture | `docs/architecture/for_designer/01_ARCHITECTURE.md` |
| 02 Systems Spec | `docs/architecture/for_designer/02_SYSTEMS_SPEC.md` |
| 03 Frontend + Tokens | `docs/architecture/for_designer/03_FRONTEND_AND_TOKENS.md` |
| 04 Design Brief | `docs/architecture/for_designer/04_DESIGN_BRIEF.md` |

### 9.3 — Per-system Agent specs (read-only audits)
| מערכת | spec |
|---|---|
| S1 Day Type observer | `docs/handoff/agents/AGENT_S1_DAYTYPE_OBSERVER_SPEC.md` |
| S2 5-Min T1 firing | `docs/handoff/agents/AGENT_S2_FIVEMIN_T1_FIRE_SPEC.md` |
| S3 Footprint T3 firing | `docs/handoff/agents/AGENT_S3_FOOTPRINT_T3_FIRE_SPEC.md` |
| S4 Woodies T2 firing | `docs/handoff/agents/AGENT_S4_WOODIES_T2_FIRE_SPEC.md` |
| S5 TPO observer | `docs/handoff/agents/AGENT_S5_TPO_OBSERVER_SPEC.md` |
| S6 Killzone observer+gate | `docs/handoff/agents/AGENT_S6_KILLZONE_OBSERVER_SPEC.md` |

### 9.4 — Code-truth (per system)
| מערכת | קוד | compliance manifest |
|---|---|---|
| S1 | `backend/v9/systems/day_type/state_machine.py` + `api.py` + `day_type_seed.py` | `backend/v9/systems/day_type/compliance_manifest.yaml` |
| S2 | `backend/v9/systems/five_min/{five_min_system.py,setup_emitter.py,quality_tier.py,time_stop_mapper.py,cot_amt.py,confluence.py,...}` | `backend/v9/systems/five_min/compliance_manifest.yaml` |
| S3 | `backend/v9/systems/footprint/{footprint_system.py,detectors.py,signals/{absorption,stacked_imbalance,sweep_return,exhaustion}.py}` | `backend/v9/systems/footprint/compliance_manifest.yaml` |
| S4 | `backend/v9/systems/woodies/{woodies_system.py,decision_tree.py,pattern_engine.py,patterns/{zlr,tlb,tt,gb100,vegas,ghost,famir,htlb,hfe}.py}` | `backend/v9/systems/woodies/compliance_manifest.yaml` |
| S5 | `backend/v9/systems/tpo/tpo_system.py` | `backend/v9/systems/tpo/compliance_manifest.yaml` |
| S6 | `backend/v9/systems/killzone/{killzone_system.py,definitions.py,zone_playbook.py,api.py}` | `backend/v9/systems/killzone/compliance_manifest.yaml` |

### 9.5 — D-decisions cited
| ID | קובץ | מצב |
|---|---|---|
| D-061 | "Trade all the time" — see Master Index V2 §⚙ D-decisions | 🔒 LOCKED |
| D-067 | "Local-First — NO push to main until LIVE-ready" | 🔒 LOCKED |
| D-068 | "Market Clock authoritative (zoneinfo · 2026 holidays)" | 🔒 LOCKED |
| D-073 | "2026 NYSE holidays — CME-verified" | 🔒 LOCKED |
| D-074 | "S4 Woodies = 5-min (supersedes Constitution V3 §T2 30-min)" | 🔒 LOCKED |
| D-082 | "S3 = Observer only per V3 spec" (referenced from `docs/decisions/D-087_REGISTRY_WAIVER.md`) | 🟡 **SUPERSEDED by D-089** |
| D-086 | `docs/reports/P30_DECISION_D086_S3_FIRING.md` — S3 SHADOW firing path tolerated, defer to post-SHADOW | 🟡 **SUPERSEDED by D-089** |
| D-087 | `docs/decisions/D-087_REGISTRY_WAIVER.md` | 🔒 LOCKED |
| D-088 | `docs/decisions/D-088_CLUSTER_GUARD_SHADOW.md` | 🔒 LOCKED |
| **D-089** (NEW) | `docs/decisions/D-089_S3_FIRING_LOCKED.md` (🟡 **pending**) | 🟡 **verbal-locked Michael 23/5** |

### 9.6 — Recent handoff (P30 → P31 → P32)
| מסמך | path | תוכן |
|---|---|---|
| P31 Task Board | `docs/handoff/P31_TASK_BOARD.md` | מצב יומי, גאנט, חוסמים |
| P31 Systems Firing Strategy | `docs/reports/PROMPT_P31_SYSTEMS_FIRING_STRATEGY.md` | מצב 6 מערכות + עצי החלטה |
| P31 Confluence Filter RCA-1 | `docs/reports/PROMPT_P31_CONFLUENCE_FILTER_RCA.md` | RCA-1 fix (S6 direction-aware) — ✅ DONE |
| P31 Strat S3 UAT | `docs/reports/PROMPT_P31_STRAT_S3_UAT.md` | S3 firing path UAT |
| P31 IB Source Fix | `docs/reports/PROMPT_P31_IB_SOURCE_FIX.md` | IB live tracking |
| P31 T2 Woodies CCI close | `docs/reports/PROMPT_P31_T2_WOODIES_CCI_CLOSE.md` | T2 CCI pipeline ✅ |
| P32 Next Chat Prompt | `docs/handoff/P32_NEXT_CHAT_PROMPT_2026-05-22.md` | next-chat handoff |
| Stepped POC viz | `docs/reports/PROMPT30_10b_TPO_LEVELS_FIX.md` + `docs/handoff/P31_NEXT_CHAT_2026-05-22_EVE_CHART.md` | Issue B ✅ |

### 9.7 — Tests cited
| מערכת | test path |
|---|---|
| S6 direction-aware (RCA-1) | `tests/v9/services/test_trade_context.py:143-166` (5 regression tests) |
| Day Type compliance | `tests/v9/compliance/test_day_type_compliance.py` |
| Day Type mid-session restart seed | `tests/v9/systems/test_day_type/test_mid_session_restart_seed.py` |
| Five Min plan fire diagnosis | `tests/v9/frontend/test_plan_fire_diagnosis_contract.py` |
| Footprint AMT rolling | `tests/v9/systems/test_footprint_amt_rolling.py` (8 tests) |
| Footprint COT session | `tests/v9/systems/test_footprint_cot_session.py` (4 tests) |
| Woodies compliance | `tests/v9/compliance/test_woodies_compliance.py` |
| TPO Sierra contract | `tests/v9/api/test_tpo_routes_sierra_contract.py` |
| TPO overlay six lines | `tests/v9/frontend/test_tpo_overlay_six_lines.py` |
| TPO history snapshotter | `tests/v9/services/test_tpo_history_snapshotter.py` |

---

## 10. Open items — מה ממתין להחלטה / לפעולה

| # | פעולה | מי | זמן | חוסם? |
|---|---|---|---|---|
| O-1 | פתיחת `docs/decisions/D-089_S3_FIRING_LOCKED.md` | ✅ **DONE 23/5 11:15** | — | — |
| O-2 | sync `wrappers.py:8-14` ל-D-089 (header note) | ✅ **DONE 23/5 11:15** | — | — |
| O-3 | sync `types.ts:222-236` ל-S3='firing' + D-089 citation | ✅ **DONE 23/5 11:15** | — | — |
| O-4 | spec audit `pre_fire_validator.py` + `footprint_system::calculate_size` ל-S3 entry/stop/T1/T2 | Cursor + report ל-Michael | 1-2h | YES — לפני LIVE |
| O-5 | מילוי עמודה 🔒 Michael ב-§4/5/6 | Michael | days-weeks | NO (לא חוסם SHADOW) |
| O-6 | מילוי עמודה pre-LIVE post-SHADOW ב-§4/5/6 | Cursor + Michael | post-SHADOW (5-10 days) | NO (לא חוסם SHADOW) |
| O-7 | P-S0 SHADOW activate gate | Michael | next | NO blockers from D-089 — ready |

---

## 11. שינויים — Changelog

### V1 → V2 (23/5 11:15 IL · D-089 trio executed)

| שינוי | מקור |
|---|---|
| D-089 doc opened | `docs/decisions/D-089_S3_FIRING_LOCKED.md` |
| `types.ts:222-236` flipped S3 → 'firing' + D-089 citation | per D-089 §"Sync actions" |
| `wrappers.py:8-14` header updated with D-089 reference | per D-089 §"Sync actions" |
| Registry §6.1 status → LOCKED + sync'd | this doc |
| Registry §10 O-1/O-2/O-3 → DONE | this doc |

### V0 (23/5 בוקר טיוטה) → V1 (23/5 ~11:00 IL · 3 verified items)

| שדה | V0 (טיוטה) | V1 | מקור עדכון |
|---|---|---|---|
| RCA-1 (S6 direction-aware) | "🔴 pre-LIVE blocker, ממתין fix" | ✅ DONE — code + 5 tests | `trade_context.py:285-292` + `test_trade_context.py:143-166` |
| UAT S2 fires in RTH | "🟡 ממתין RTH 09:30 ET" | ✅ DONE — 3 SHADOW trades fired | `sqlite3 data/mems26_local.db` |
| Stepped POC chart (Issue B) | לא צוין | ✅ DONE approved 22/5 ערב | `TpoContinuityOverlay.tsx` + P31_TASK_BOARD §0 |
| S3 safety net | "שאלה פתוחה" | 🔒 **KEEP** until Michael says otherwise | Michael 23/5 |
| Pattern table columns | 4 cols | 4 cols (no change) | per Michael 23/5 |

---

*End of registry. עדכן את §10 ו-§11 בכל שינוי. מסמך זה חי — לא תיעוד היסטורי.*
