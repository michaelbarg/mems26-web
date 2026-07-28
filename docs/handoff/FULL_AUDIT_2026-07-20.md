# ביקורת-דלתון מקיפה — שערים + R:R/סטופ + T0–T4 · 2026-07-20

**מקור:** `CURSOR_FULL_GATE_TARGET_AUDIT_2026-07-20.md` · סוכן: cursor · קריאה-בלבד לאבחון · **אין הדלקת דגלים**.  
**חוק-5:** חוזי-דטרמיניסטיים רצו — ראו §E.

---

## הממצא הגדול

1. **סטופ-מבני כבר בקוד אך OFF** — `STRUCTURAL_STOP_ORIGIN_V1` + `STOP_WINDOW_COMPLETED_V1` ב-`five_min_system.py:1268-1311`. OFF → קצה-בר-כניסה / חלון-חלקי → ATR-floor → #420 סטופ **בתוך** המבנה.
2. **`rr_entry_gate` לגיטימי** — לא לכבות. סטופ-שגוי מנפח risk → R:R נמוך → חסימה. תיקון-סטופ מתקן גם את ה-R:R.
3. **יעדים מבניים דלוקים ואז נדרסים** — `DAYTYPE_TARGETS_STRUCTURAL=1` כותב C1/C2/C3 ב-`trading_gateway.py:1115`, ואז `pattern_t1_points` ב-`:1172` דורס T1/T2/T3 ל-`entry±pts/2×/3×`.
4. **שערי-upstream על סיגנל-שבור** — G6/G2/G3/location כבויים היום (null לפני נעילה / expansion חסר). `require_with_trend` עדיין מדלג על SHORT@VAH כש-`trend_state=BLUE`.

---

## A — שערי-gateway (`blocked_by`)

| שער | סיגנל | אמין היום? | דלתון? | Over-block? | מצב / תיקון |
|-----|--------|------------|--------|-------------|-------------|
| `kill_switch` / `session_gate` / `eod_entry_cutoff` / `feed_watchdog` / `cooldown` / `news_blackout` / `daily_loss_halt` / `consecutive_loss_halt` | ops | כן | N/A | לא | KEEP |
| `duplicate_fire` / `cluster_guard` | trade ledger | כן | N/A | לא | KEEP |
| `chop_searching` | Layer-0 chop | standing OFF | — | — | לא לגעת (standing) |
| `suffering_side_veto` (SSV) | outcomes | SSV_GATE OFF | — | — | OFF — KEEP OFF |
| `opening_type_gate` | opening drive | ON | חלקית | test-drive נדחה → אזור-מת (Task#3) | ADAPT אחרי Task#3 |
| `daytype_playbook` | day_type × pattern + **require_with_trend←trend_state** | day_type=override OK; **trend_state רגעי לא** | **לא** על fade@VAH | כן — #5א | **P0** — כיוון-יום / מיקום |
| `trend_direction_gate` / `reactive_location` | CCI/POC | OFF (superseded) | — | — | OFF |
| `location_gate` | expansion | **לא** (None כשגלאי פספס) | לא כשסיגנל שבור | כן היום | **OFF** עד Task#5 |
| `daytype_position_gate` | POC/IB | OFF | pattern-blind | — | OFF |
| `cont_trend_filter` | LSMA sustained | ON | CONT vs רגעי | סיכון על CONT עם bounce | ADAPT עם doctrine |
| `direction_context` | CVD+breakout | ON | לא = כיוון-יום | אפשרי | ADAPT |
| `lsma_flat` | LSMA slope | OFF | — | — | OFF |
| `day_direction_doctrine` | IB expansion side | **OFF** | **כן — השער הנכון** | — | הדלקה אחרי Task#5 |
| `entry_not_confirmed` | confirm bar | ON (S4) | OK | לא | KEEP |
| `t1_wrong_side` | T1 side | ON | OK | לא | KEEP |
| **`rr_entry_gate`** | T1 vs stop | ON; **מספרים שגויים מסטופ שגוי** | כן כשסטופ נכון | סימפטום #420 | **KEEP ON** — תקן סטופ |
| `zone_limit_late_entry` | zone | ON | OK | — | KEEP |
| S4 RCB / pattern blocks | woodies | ON | — | — | KEEP |
| G2/G3 (`S2_DETECTION_LIVE…`) | get_live | היו ON→null-block; חזרו | תלוי מקור | כן לפני נעילה | OFF עד מקור אמין |
| G6 (S4 honest fallback) | get_live | אותו | — | כן | OFF |

**מפל היום (כרונולוגי):** G6 → G2/G3 → location → **rr** (+ playbook require_with_trend). עכשיו G6/G2/G3/location OFF; **rr ON**.

---

## B — R:R / מיקום-סטופ (חשד-מייקל — מאומת)

| שלב | מה קורה | #420 |
|-----|---------|------|
| מוצא סטופ S2 | `STRUCTURAL_STOP_ORIGIN_V1` OFF → `bar.high` לא swing 7521–7527 | סטופ ~7514 **בתוך** מבנה |
| חלון | `STOP_WINDOW_COMPLETED_V1` OFF → בר חלקי בחלון | מרחק מבני קורס → ATR floor |
| Gateway resolver | `STOP_RESOLVER` / band דוחה מבנה רחב מ-ATR | הסטופ-הנכון נדחה (טסט: low-ATR band rejects ≥7522.75) |
| R:R | `setup["stop"]` → risk גדול או T1 קטן יחסית | `rr_entry_gate` חוסם setups חדשים |

**מסקנה:** אל תכבה `RR_ENTRY_GATE_V1`. הדלק מוצא-מבני + widen-to-structure; אז R:R מתיישר.  
**חוזה מאומת:** `tests/v9/regression/test_stop_at_structural_edge_420.py` — stop≥7522.75; ATR-floor=7514 inside; band rejects correct stop.

---

## C — סולם T0–T4

| יעד | מקור היום | מבני? | בעיה |
|-----|-----------|-------|------|
| T0 | `FIXED_CONTRACTS_4` + `T0_TARGET_PTS` | סקאלפ | OK אם BE אחרי T1-אמיתי |
| T1 | structural C1 **או** `pattern_t1_points` | חצי — אמפירי OK | stomp אחרי structural |
| T2 | אמור POC/מבנה; בפועל **2×pts** אחרי stomp | **לא** אחרי stomp | Variation SHORT צריך POC |
| T3 | אמור VAL/VA edge; בפועל **3×pts** | **לא** אחרי stomp | Variation SHORT צריך VAL |
| T4 | slot 4c / runner | תלוי | — |
| BE | `BE_AFTER_REAL_T1_V1` | — | **OFF** — לא להדליק בלי פסיקה |

**קוד:** `structural_targets.py` Variation REV SHORT → C2=POC, C3=VAL (`:240-242`). Gateway stomp `:1172-1196`.  
**חוזה מאומת:** `tests/v9/regression/test_dalton_t2_t3_structural_variation.py` — 5 passed (REV C2=POC/C3=VAL; CONT C3=VAL≠VAH; 2×/3×≠VAL).

**תיקון מוצע (cc, אחרי פסיקה):** T1 אמפירי מותר; **T2/T3 לא לדרוס** אחרי structural — או להריץ pattern_t1 לפני structural רק ל-T1.

---

## D — הצלב מול `EOD_FIX_LIST_2026-07-20.md`

| Task | נושא | מצב | חוזה-טסט | בעלים |
|------|------|-----|----------|-------|
| #6 | Sierra reconcile / P&L | פתוח | `test_sierra_reconcile_420_pnl` ✅ | cc |
| #7 | סטופ בקצה-מבנה | פתוח (דגלים OFF) | `test_stop_at_structural_edge_420` ✅ | cc |
| #5 | מקור-יחיד + הרחבה | פתוח | `test_dalton_ib_break_variation_7501` ✅ | cc |
| #5א | require_with_trend = כיוון-יום | פתוח (playbook pin SKIP) | `test_dalton_require_day_direction_vah` ✅ | cc |
| #8 | boot buffer | פתוח | — | cc |
| #3 | first-hour fire / test-drive | פתוח | — | cc |
| T2/T3 stomp | structural נדרס | פתוח | `test_dalton_t2_t3_structural_variation` ✅ | cc |
| G2/G3/G6/location | OFF עד #5 | — | — | מייקל |
| ORPHAN / STOP_WIDEN | OFF, sim-gated | — | harness קיים | מייקל→cc |

---

## E — חוק-5 (פקודה + פלט)

```text
$ git pull
Already up to date.

$ BRIDGE_TOKEN=test python3 -m pytest \
  tests/v9/regression/test_stop_at_structural_edge_420.py \
  tests/v9/regression/test_dalton_ib_break_variation_7501.py \
  tests/v9/regression/test_dalton_require_day_direction_vah.py \
  tests/v9/regression/test_sierra_reconcile_420_pnl.py \
  tests/v9/regression/test_dalton_t2_t3_structural_variation.py -q
26 passed
```

| מקרה-אמת | קובץ | חוזה |
|----------|------|------|
| #420 stop | `test_stop_at_structural_edge_420` | ≥7522.75; 7514 inside; band reject |
| IB-break→Variation | `test_dalton_ib_break_variation_7501` | mechanical + noise_IB_FRAC=0 |
| SHORT@VAH + BLUE | `test_dalton_require_day_direction_vah` | Dalton allow; playbook SKIP pin |
| reconcile #420 | `test_sierra_reconcile_420_pnl` | fills≠−82.50; empty≠MATCH |
| T2/T3 מבני | `test_dalton_t2_t3_structural_variation` | REV POC/VAL; CONT VAL |

**מיון רגרסיה:** `BRIDGE_TOKEN=test pytest tests/v9/regression/ -q --tb=no` → **110 failed, 1174 passed, 2 xfailed**. ראו `REGRESSION_TRIAGE_2026-07-20.md` — (ג) באג-אמת=0; רוב stale/rot. אין שינוי-קוד-מסחר בסשן זה.

---

## רשימת-תיקונים ממוינת (לפני כל הדלקה)

1. **P0** סטופ-מבני — `STRUCTURAL_STOP_ORIGIN_V1` + `STOP_WINDOW_COMPLETED_V1` + resolver widen (מבנה גובר) · טסט #420 ירוק תחת ON.
2. **P0** `require_with_trend` / CONT על **כיוון-יום** · REV fade לפי VAH/VAL · טסט VAH+BLUE.
3. **P0-אמון** Sierra fills reconcile · טסט #420 pnl.
4. **P1** מקור-יחיד day_type + גלאי-הרחבה (כל מעבר-IB) · טסט 7501 · אז G2/G3/G6/location/doctrine.
5. **P1** T2/T3 לא לדרוס אחרי structural · טסט Variation POC/VAL.
6. **P1** אזור-מת 10:00 + boot buffer (#3/#8).

**אין הדלקה בלי:** טסט ירוק תחת הדגל + פסיקת-מייקל + RULED + ריסטארט + אימות-cowork (חוק-5).
