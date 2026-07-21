# עץ-ההחלטות של MEMS26 בפועל — מהפתיחה עד הסגירה (נגזר מהקוד, לא מהזיכרון)

**עודכן: 2026-07-21 14:20 IL (cursor) · מצב-דגלים = `.env` החי, flag_guard PASS 107/107.**
כל צומת: מה קורה · הדגל ששולט · מצבו עכשיו · איפה בקוד. שעות בפורמט `ET (IL)`.
עדכן מסמך זה בכל שינוי-שער/דגל — אחרת הוא שקר (כמו FLAG_INDEX, stale=באג).
**שינויי 07-21 (פסיקות-מייקל, כולם חיים ואומתו):** שער-TS ✅ · IB-expansion ✅ · סולם-4-חוזים
T0=+4 ✅ · BE-אחרי-T1-אמיתי ✅ · ביטול time-stop ✅ · C4 לפי סוג-יום + DLL-hardening ✅ ·
T2/T3-מבניים-לא-נדרסים ✅ · C4-flatten-בטרנד 15:45 ✅ · היום=סים על MacBook (`MEMS26_MODE=sim`).

---

## שלב 0 — לפני הפתיחה (בוט + פיד)

```
Sierra DLL כותב JSON  →  bridge (LaunchAgent, localhost בלבד)  →  POST /api/v9/bars/*  →  PG
```

| צומת | מה קורה | דגל / מצב | קוד |
|---|---|---|---|
| bridge | דוחף כל ~5s; מסרב לרוץ מול host לא-מקומי | `CLOUD_URL=localhost` קשיח | `bridge/v9_streams/base_stream.py` |
| תיקון-שעה | ts חדש בדיוק 3600±120s מאחורי now → הזחה +1h; 3300–3900 אבל לא-בדיוק → אזהרה **בלי** הזחה | `WOODIES_TS_HOUR_FIX` unset→**ON** | `bars.py:429` |
| 🕳→🚪 שער-TS | פיד מתקדם אבל >900s מאחורי now → דחיית-batch כנה. **החור של 07-20** (−1h עבר בלי תיקון ובלי דחייה) — נסגר | `TS_OFFSET_INGEST_GATE_V1` **1 ✅** (פסיקה 07-21 07:59) | `bars.py:485` |
| שערי-כתיבה | עתידי>2דק' → דחייה · מחוץ-RTH → דילוג · vol>100K → דחייה · מחיר-מעופש (B-13) → חסימה · סתירה מול woodies → חסימה | תמיד-ON | `bars.py:528-562` |

**ביקורת-בוקר:** `curl :8000/api/v9/health/streams` — הכל healthy, errors=0 · בר-אחרון age<6דק'.

---

## שלב 1 — פתיחה 09:30 ET (16:30 IL) → נעילת-IB 10:30

```
בר ראשון נכנס
└─ מסווג-S1 קנוני (7-סוגים): מצב FORMING (עד 12 ברים)
   ├─ תווית לשער-המסחר: FORMING → day_type=None        [OPENING_FIRE_CVD_V1=1 ✅ — תיקון באג 06-29 פעיל]
   │   (אין תווית-מוקדמת-כוזבת מהמנוע הישן)              trade_context.py:656
   └─ זיהוי סוג-פתיחה (דלתון, 6 ברים ראשונים):
       OPEN_DRIVE / OPEN_TEST_DRIVE / OPEN_REJECTION_REVERSE / OPEN_AUCTION
       + אישור-CVD ל-DRIVE (דיברג'נס = ספיגה → לא DRIVE)   opening_detector_v2.py:104-116
```

**האם יורים בפתיחה? כן, בשני תנאים:**
```
setup בחלון-הפתיחה (לפני נעילת-IB)
├─ OPENING_TYPE_GATE=1 ✅  (opening_type_gate.py:28, gateway:604)
│   ├─ DRIVE מזוהה + ירי עם-הכיוון        → עובר
│   ├─ DRIVE מזוהה + ירי נגד-הכיוון       → blocked_by=opening_type_gate
│   ├─ OPEN_AUCTION (רוטציה, אין קצה)      → hold הכל
│   └─ drive נכשל (חזר דרך מחיר-הפתיחה)   → משוחרר
└─ 30 דק' ראשונות: opening_window_override — אישור-חיובי עם-drive
    שדורס סירובי-סוג-יום (רק ALLOW, לא עוקף שערי-סיכון)   opening_type_gate.py:245
```

---

## שלב 2 — נעילת-IB 10:30 ET (17:30 IL) → סיווג

```
IB ננעל: מקור = Sierra TPO (v9_tpo_sessions CASH)          ib_source="sierra_tpo"
├─ S1_IB_SANITY_V1=1 ✅ — הצלבה מול 12-הברים-הראשונים ב-DB
│   └─ ⚠ אם ה-DB מזוהם (07-20!) ההגנה הזו מחליפה IB נכון בשגוי.
│      ההגנה-שלפניה היא שער-ה-TS (שלב 0). classifier_core.py:82-92
├─ סיווג רץ על כל בר: 7 סוגים (Normal / Normal_Variation→Variation /
│  Nontrend / Neutral_Center / Neutral_Extreme / Trend_Normal / Trend_DD)
│  לפי דלתון: הרחבות מול IB, acceptance, value, POC drift, נפח, EOD.
│  הרחבה נספרת מכל פריצת-IB (IB_BREAK_ANY_EXPANSION_V1=1 ✅, פסיקה 07-21)
│  אסקלציה-בלבד בתוך סשן (Normal→Variation→Trend, לא חוזרים).  shadow_reclass.py:85
└─ צרכן: get_live_day_type() = override(אם יש) → 7-type חי → fallback
   [S1_NEW_CLASSIFIER=1 ✅ + S1_ENGINE_NEW_CLASSIFIER=1 ✅]     trade_context.py:640-659
```

**ביקורת:** `curl :8000/api/v9/day_type/classify_replay?date=<today>` — `ib_source=sierra_tpo` (לא bars_fallback!), התקדמות-סוג הגיונית מול המסך.

---

## שלב 3 — זיהוי setups (במקביל, כל בר)

| מערכת | מה מזהה | תלות-סוג-יום | קוד |
|---|---|---|---|
| **S2** five-min | FHB · Reactive · Initiative · Double · HnS (גאומטריית-מחיר+נפח; COT/AMT **לא** נדרש — S2⟂S3, פסיקה 06-08) | emit+sizing = live ✅ · **detection עדיין תווית-ישנה** (`S2_DETECTION_LIVE_DAYTYPE_V1=0`, G2/G3 סים-gated) | `five_min_system.py` |
| **S4** woodies | ZLR (spec_v2) · TT · GB100 · VEGAS · GHOST · FAMIR · HTLB · TLB (CCI 14/6) | sizing = live ✅ (`S4_OVERRIDE_AWARE_V1=1`) · fallback-מת עדיין קיים (`S4_HONEST_DAYTYPE_FALLBACK_V1=0`, G6) | `woodies_system.py` |

---

## שלב 4 — הלב: מסע-setup דרך שערי-הגייטוויי (הסדר האמיתי מהקוד, route_setup)

כל setup עובר את השערים **בסדר הזה**; הראשון שחוסם עוצר (לכן טסט חייב לבודד — לקח §0).
`blocked_by`+`reason` נרשמים ב-decisions feed → UI.

| # | שער (`blocked_by`) | דגל | מצב | חוסם מתי | שורה |
|---|---|---|---|---|---|
| 1 | `kill_switch` | KILL_SWITCH | OFF | עצירת-חירום ידנית | 493 |
| 2 | `session_gate_closed` | חלון-ירי | ON | מחוץ 09:30–16:00 ET | 502 |
| 3 | `eod_entry_cutoff` | `EOD_RISK_WINDOW_V1` | **1** ✅ | כניסה חדשה ב-45 הדק' האחרונות (אחרי 14:15 CT = 22:15 IL) | 517 |
| 4 | `feed_watchdog` | — | ON | פיד מעופש | 532 |
| 5 | `cooldown` | — | ON | צינון אחרי עסקה | 542 |
| 6 | `suffering_side_veto` | — | ON | צד שסופג הפסדים רצופים | 553 |
| 7 | `duplicate_fire` | `DEDUP_FIRE_GUARD` | **1** ✅ | אותו sys+dir+pattern+entry±0.5pt תוך 30s | 572 |
| 8 | `chop_searching` | `LAYER0_CHOP_GATE` | **OFF** (פסיקה 06-08) | — מנוטרל | 595 |
| 9 | `opening_type_gate` | `OPENING_TYPE_GATE` | **1** ✅ | נגד-drive בחלון-הפתיחה (שלב 1) | 623 |
| 10 | `daytype_playbook` | `DAYTYPE_PLAYBOOK` | **1** ✅ | מטריצת תבנית×סוג-יום = SKIP (מקור-יחיד לכיוון-פר-תבנית) | 714 |
| 11 | `trend_direction_gate` | `REQUIRE_WITH_TREND_DAY_DIRECTION_V1` | **1** ✅ | ביום-Trend: ירי נגד כיוון-היום | 734 |
| 12 | `reactive_location` | — | ON | Reactive-fade לא בקצה הנכון (VAH/VAL) | 752 |
| 13 | `location_gate` | `DAYTYPE_LOCATION_GATE` | **0** (כובה 07-20) | — מנוטרל | 787 |
| 14 | `daytype_position_gate` | `DAYTYPE_POSITION_GATE` | **0** (כובה 07-20) | — מנוטרל | 812 |
| 15 | `cont_trend_filter` | `CONT_TREND_FILTER` | **1** ✅ | תבנית-המשך בלי מגמת-LSMA מתמשכת (K=`LSMA_SUSTAIN_BARS`=2; REV פטורות; `CONT_TREND_STATE_CERT_V1=1` מתקן pullback-בטרנד-כחול) | 846 |
| 16 | `direction_context` | `DIRECTION_CONTEXT` | **1** ✅ | ירי נגד כיוון-CVD+פריצה חי; פטור-fade ל-Neutral/Variation/Normal (`NEUTRAL_RESPONSIVE_V1=1`, `NORMAL_ROTATION_FIX_V1=1`) | 896 |
| 17 | `lsma_flat` | `LSMA_FLAT_GATE_V1` | **0** | — מנוטרל (LSMA אופקי) | 933 |
| 18 | `news_blackout` | `NEWS_BLACKOUT_V1` | **1** ✅ | חלון-חדשות (config/news_calendar.yaml) | 955 |
| 19 | `day_direction_doctrine` | דוקטרינה | ON | סתירת-דוקטרינה יום×כיוון (G8: פסיקת-A 07-20) | 1017 |
| 20 | `entry_not_confirmed` | — | ON | מחיר-חי רחוק מהכניסה (אישור-כניסה) | 1475 |
| 21 | `t1_wrong_side` | — | ON | T1 בצד הלא-נכון של הכניסה | 1504 |
| 22 | `rr_entry_gate` | `RR_ENTRY_GATE_V1` | **1** ✅ | R:R‏<1.0 (ימי-רוטציה: `RR_MIN_ROTATION=0.65`) | 1536/1579 |
| 23 | `zone_limit_late_entry` | `ZONE_LIMIT_ENTRY_V1` | **1** ✅ | כניסה מאוחרת: drift-שלילי >2pt או אות ישן >180s | 1641/1664 |
| 24 | `daily_loss_halt` | `RISK_HALT_V1=1` ✅ + `RISK_DAILY_LOSS_CAP` | **800** | הפסד-יומי ≥ $800 → עצירת-יום (הגב האמיתי, כל המצבים) | 1692 |
| 25 | `consecutive_loss_halt` | `RISK_CONSECUTIVE_LOSS_LIMIT` | **0=OFF** | — מנוטרל (זה שעצר את 07-20 בבוקר; כובה) | 1716 |
| 26 | `pattern_loss_breaker`/`s4_risk_cap` | metadata מה-S4 | breaker **OFF** | N הפסדים-רצופים לתבנית / חריגת-cap-נקודות | 1738 |
| 27 | `cluster_guard` | — | ON | צביר-ניסיונות (חוסם DEMO/LIVE; shadow נרשם) | 1824 |

---

## שלב 5 — ניתוב: צל / לייב

```
עבר את כל השערים
├─ תמיד: _execute_shadow (רישום-צל, gateway:1762)
└─ לייב?  (gateway:1867-1922)
    ├─ _is_live_enabled(system)?         [07-21: `MEMS26_MODE=sim` (פסיקת 11:19 — היום סים על MacBook) · LIVE_EXECUTION_V1=1 · LIVE_TRADING_ARMED=1]
    ├─ live_slot פנוי? (עסקת-לייב אחת בו-זמנית; מתפנה ב-close, gateway:2003)
    └─ passes_strict_checks("live")      [risk_checks.py — לייב-בלבד]
        ├─ cutoff-לייב: אחרי 15:30 ET (22:30 IL, פסיקת 07-19) → לא   [RISK_CUTOFF_HOUR_ET=15 + MINUTE=30]
        ├─ הפסדים-רצופים: RISK_CONSECUTIVE_LOSS_LIMIT=0 → מנוטרל (כובה 07-20 אחרי ה-STOP-DAY)
        └─ הכל כן → _execute_live → op=PLACE ל-Sierra (bracket/OCO פר-חוזה)
```

**ביקורת:** `curl :8000/api/v9/gateway/decisions` — כל ניסיון עם `blocked_by`+`reason`; אם ציפית ללייב וקיבלת צל — `live_slot` תפוס או strict-check.

---

## שלב 6 — ניהול-עסקה (אחרי מילוי)

| רכיב | התנהגות | דגל/מצב | קוד |
|---|---|---|---|
| סטופ ראשוני | על קצה-המבנה (+6T), לא מרחק-ATR | `STRUCTURAL_STOP_ORIGIN_V1=1` ✅ (תיקון #420) | five_min_system |
| חלון-הסטופ | קורא ברים **סגורים** בלבד | `STOP_WINDOW_COMPLETED_V1=1` ✅ (מחווט, אומת 07-20) | five_min_system.py:1308 |
| סטופ רחב-מ-ATR | מתקבל במקום להידחות | `STOP_WIDEN_TO_STRUCTURE_V1=1` ✅ | sizing/stops |
| דחיית-סטופ ע"י Sierra | הרחבה-לרצפה (widen-only) | `STOP_WIDEN_TO_FLOOR_ON_REJECT_V1` **OFF** — סים-gated | Task#10 |
| **סולם 4 חוזים (07-21)** | C1→**T0=כניסה±4** · C2→T1 · C3→T2 · C4→T3; כל חוזה OCO משלו עם סטופ. **C4 בלי T3:** Normal/Neutral→הקצה-השני (VAL/VAH, IB-fallback) · Variation→stop-only (trail עם T3) · Trend→ראנר. **DLL-hardened: C4 לעולם לא עירום** — אומת בירי-אמת (8 working = 4×OCO) | `FIXED_CONTRACTS_4=1` ✅ · `T0_TARGET_PTS=4.0` ✅ · `C4_RULING6_V1=1` ✅ | `sierra_command.py:342-402` + DLL |
| BE (סטופ→כניסה) | **רק אחרי T1 אמיתי** (מילוי-C2), לא אחרי T0 | `BE_AFTER_REAL_T1_V1=1` ✅ (פסיקה-3, אומת `has_t0=True` על עסקה-אמיתית) | `manager.py:489` |
| time-stop | **אין** — מערכת 6 מנהלת משך, לא שעון | `time_stop_minutes: null` בכל 7 הסוגים + dispatcher (פסיקה-5) ✅ | targets.yaml · dispatcher_config.yaml |
| יעדים T2/T3 מבניים | pattern_t1 קובע רק T1 — לא דורס T2/T3 מבניים (POC/VAL/IB) | `T2T3_NO_STOMP_V1=1` ✅ (Task#4, 07-21) | gateway:1253-1279 |
| C4 ביום-Trend | flatten ראנרים 15:45 ET (15 דק' לפני סגירה), CANCEL-pattern | `C4_TREND_FLATTEN_V1=1` ✅ (פסיקה-6) | trade_manager |
| System6 | מצב-הגנתי בלבד: MODIFY_STOP→BE + התרעות; **אף פעם op=EXIT** | `SYSTEM6_AUTOCORRECT=protective` ✅ (פסיקה 07-15) · אומת חי על 437 | system6_supervisor |
| יציאה ידנית | FLATTEN_ACCOUNT בלבד (op=EXIT שבור עד EXIT-v2) | קבוע · אומת 07-21 (437→flat) | CLAUDE.md |
| אורפנים | זיהוי + FLATTEN_ORPHAN ב-DLL (סטופ-וירטואלי backend); סטופ-אוטו עדיין OFF | `ORPHAN_AUTO_STOP_V1=0` — ממתין אימות-סים (פסיקות-ממתינות #4) | Task 1א/1ב |

---

## שלב 7 — סגירה 16:00 ET (23:00 IL)

```
15:00 ET  אין כניסות חדשות (eod_entry_cutoff)
15:45 ET  ביום-Trend: flatten ראנרים (C4_TREND_FLATTEN_V1=1 ✅, פסיקה-6)
16:00 ET  סשן נסגר → המסווג נועל תווית טרמינלית (is_eod) → v9_day_type_history
          rollover למחרת ~06:55 IL · אימות: position_qty=0 ב-sierra_state.json
✅ Task#6  נסגר 07-21: trade_fills.json ריק = by-design (ה-poller צורך ומרוקן; האמת ב-trade_fills_journal.jsonl,
          עובד) · trade_activity_feed עוקב אחרי החשבון הנכון (sim→Sim1) + מפרסר לוגי-Sim1 (SIM_FILL/SIM_FLATTEN)
🔴 נותר   מילויים ידניים/orphan שלא עוברים ב-Pipeline 5 — פער-רקונסיליאציה בלוח S124
```

---

## "איך אדע שהמערכת עובדת" — 6 בדיקות-דקה

| מתי | פקודה | תקין = |
|---|---|---|
| לפני הפתיחה | `bash scripts/mems26_verify.sh` + `python3 scripts/flag_guard.py` | הכל ירוק · PASS |
| פתיחה | `classify_replay?date=today` | FORMING→PROVISIONAL, `ib_source=sierra_tpo` |
| 10:35 | אותו endpoint | IB = מה שאתה רואה בצ'ארט-Sierra (±טיק) |
| במהלך היום | `/api/v9/gateway/decisions` | כל חסימה עם reason שאתה מבין ומסכים לו |
| עסקה חיה | `/api/v9/status` + Sierra | סטופ ב-Sierra = קצה-מבנה+6T; live_slot תואם |
| סגירה | `v9_day_type_history` + `sierra_state.json` | תווית = מה שראית · position_qty=0 |

## הפערים הפתוחים שמופו (בכוונה, לא באג) — עודכן 07-21 14:20
G2/G3/G6 סים-gated (S124, ממתין ליום-סים ירוק) · `ORPHAN_AUTO_STOP_V1` OFF (ממתין אימות-סים) ·
G4/D1 OFF (פסיקת 07-20) · מילויים-ידניים/orphan מחוץ ל-Pipeline 5 (S124) · S2-detection על תווית-ישנה
(G2/G3) · `hydrate_live_pnl` לפני 09:30 ET טוען סשן-אתמול (מינורי, live-cap בלבד).
**נסגרו 07-21:** שער-TS ✅ · IB-expansion ✅ · Task#6 fills ✅ · תווית-07-20 (כבר Normal_Variation ✅) ·
C4-עירום ✅ · time-stop ✅ · BE-אחרי-T1 ✅ · T2/T3-stomp ✅.
