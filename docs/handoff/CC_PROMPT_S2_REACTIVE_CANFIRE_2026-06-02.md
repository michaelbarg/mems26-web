# CC PROMPT — S2 Reactive CAN-FIRE: Diagnosis Correction + Threshold Fix + 3-Variant Observer · 2026-06-02

פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.

**תווית החלטה:** `D-RVX` (ראה `docs/plans/DECISION_LEDGER.md`)
**מאת:** Cowork diagnostic agent (read-only) → **אל:** Claude Code
**מחליף/מתקן:** `CC_MEGA_PROMPT_REACTIVE_CHECK_FIX_DISPLAY_2026-06-01.md` + `CC_PROMPT_REACTIVE_VARIANT_SHADOW_HARNESS_2026-06-01.md`

> ⚠️ **תיקון אבחון מהותי לפני הכל:** שני הפרומפטים הקודמים בנו את Phase 0 סביב
> **השערת "event-channel mismatch"** (מנוי על `mems26:events:bar.5min` מול פרסום
> `"5min"`). **ההשערה הזו הופרכה בקוד** — ראה Phase 0 §B למטה. ה-wiring של ה-BarRouter
> **תקין**, `process_bar` **כן** נקרא. אל תבזבז זמן על תיקון ערוצים — שורש התקלה אחר.
> ה-Phases 2–5 של MEGA_PROMPT (refactor הגייט + 3 וריאציות + תצוגות) **נשארים תקפים
> ככתבם** — הם ה-superset; פרומפט זה מחליף רק את האבחון (Phase 0) ומחדד את שורש התקלה.

> **משמעת Pre-LIVE (CLAUDE.md) — חובה בכל phase:** diagnose-first · read-current-code ·
> audit-existing (KEEP/ADAPT/REPLACE/DEFER) · smallest-correct-change · **Rule 5
> (command + raw output, לא assertion)** · strategic-stop לפני נגיעה ב-live fire path ·
> No silent failures · NOT-DONE section חובה.
>
> **עיקרון-על:** הוריאציות הן **צופים (observational)**. ה-live Reactive
> (`DROP_THRESHOLD_PCT=0.10`) **לא משתנה**. אפס מעבר ב-gateway/route_setup, אפס זיהום
> fires/trades ראשיות, אפס נגיעה ב-risk/sizing/order. תווית `# D-RVX` בכל שורה שנוגעים.

---

## Phase 0 · אבחון מאומת — למה S2 מת (כבר בוצע על-ידי Cowork; CC מאמת מחדש)

להלן האבחון עם ראיה גולמית. **CC חייב לשחזר כל אחד מהבדיקות ולהדביק raw output
(Rule 5) לפני שממשיך** — לא לקבל את הטענות שלי על אמון.

### §A · עובדה: 0 fires all-time (DB)
```
$ python3 -c "import sqlite3; c=sqlite3.connect('file:data/mems26_local.db?mode=ro',uri=True);
print('five_min_setups', c.execute('SELECT count(*) FROM v9_five_min_setups').fetchone()[0]);
print('five_min_state', c.execute('SELECT count(*) FROM v9_five_min_state').fetchone()[0]);
print('trades_sys2', c.execute('SELECT count(*) FROM v9_trades WHERE firing_system=2').fetchone()[0]);
[print(r) for r in c.execute('SELECT system_id,count(*) FROM v9_system_signals GROUP BY system_id')]"
five_min_setups 0
five_min_state 0
trades_sys2 0
(3, 136)            # רק System 3 (Footprint) רשם signals; S2 אף-פעם.
```

### §B · ההשערה "channel mismatch" — **מופרכת** (file:line)
- `bar_aggregator_5min.py:206` → `_bar_router.publish_threadsafe("5min", bar_dict)`.
- `bar_router.py:~99` → ה-dispatch מנתב לפי `self._subscribers.get(bar_type, [])` כאשר
  `bar_type == "5min"`.
- `five_min_system.py:695-696` → `subscribed_bar_types()` מחזיר `["5min"]`.
- `backend/main.py:88-89` → בעלייה: `for bt in five_min_system.subscribed_bar_types():
  bar_router.subscribe(bt, five_min_system.process_bar)` → **רישום ל-"5min" תואם בדיוק**.
- ה-`subscribed_channels = ["mems26:events:bar.5min", ...]` (שורה 88 ב-class) הוא מנגנון
  **Event-Bus נפרד** שלא משמש למסירת ברים ל-S2. ה-mismatch הנטען בין שורה 88 לשורה 696
  **אינו רלוונטי** — מסירת הברים עוברת דרך ה-BarRouter (`subscribed_bar_types`), והוא תקין.
- **מסקנה:** `process_bar` כן רץ בכל בר 5-דק'. ה-wiring **לא** השורש. **אל תיגע ב-wiring.**

### §C · שורש התקלה האמיתי — גייט הווליום בלתי-מושג (raw bar-math)
ה-detector (`_detect_reactive`, `five_min_system.py:469-543`) דורש **בו-זמנית**:
- `b2_drop` (ש'499): `b2_vol <= b1_vol * 0.10` — נפילת ווליום 90% בר-על-בר.
- `lookback_quiet` (ש'509-512): כל 3 הברים שלפני b1 חיוביים **וגם** `max(prev3) < b1_vol*0.6`
  (כלומר b1 חייב להיות בר-ספייק).

בדיקה על **1086 ברי 5-דק' אמיתיים** (`is_synthetic=0`, 2026-05-04 → 06-02, ~29 ימים):
```
$ python3 -c "...ראה למטה..."
non-synthetic bars: 1086 | vol min/median/max: 3 / 2541 / 242703 | zero-vol: 0
b2<=0.10*b1 (90% drop): 2     # מתוך 1085 זוגות — נדיר קיצונית
b2<=0.20*b1: 4 | b2<=0.30*b1: 18 | b2<=0.50*b1: 85 | min ratio: 0.0009
eval windows (7-bar): 1080 | lookback_quiet pass: 69 | b2_drop pass: 2
BOTH lookback_quiet AND b2_drop (גייטי הווליום לבד): 0   ← ⛔ אפס, על 29 ימים
```
**מסקנה חד-משמעית:** שני גייטי-הווליום **לא נפגשים אפילו פעם אחת** ב-29 ימי נתונים —
וזה **לפני** COT/AMT, belly, b3/b4. הסיכוי לירי = אפס מתמטי, לא תקלת-wiring.

### §D · חוסם משני — מקור COT/AMT חסר
`_detect_reactive:488` מחזיר מיד אם `cur_cot is None or cur_amt is None`.
המקור: `_cot_amt_from_sierra` → `read_cumulative_delta()` (קורא
`~/SierraChart_Data/v9_export/cumulative_delta.json`).
```
$ python3 -c "import os;print(os.path.exists(os.path.expanduser('~/SierraChart_Data/v9_export/cumulative_delta.json')))"
False    # בסנאפשוט הזה הקובץ חסר → COT/AMT=None → גם אם הווליום היה עובר, יציאה מוקדמת
```
**CC חייב לאמת מחדש על המכונה החיה ב-RTH** — ייתכן שהקובץ קיים live. אם חסר ב-RTH → זה
חוסם שני אמיתי שדורש תיקון bridge/export נפרד (לדווח, לא לתקן בשקט).

### §D2 · חוסם-נתונים נוסף — נפחי close מנופחים (מאומת Cowork 2026-06-02 PM, raw)
ב-`v9_bars_5min` של 2026-06-02 קיים אשכול נפחים **חריג** בחלון הסגירה 15:15–16:15,
כולם `is_synthetic=0`, פי ~50–100 מנפח RTH נורמלי (~4K–13K):
```
$ python3 -c "import sqlite3;c=sqlite3.connect('file:data/mems26_local.db?mode=ro',uri=True);
[print(r) for r in c.execute(\"SELECT ts,volume FROM v9_bars_5min WHERE substr(ts,1,10)='2026-06-02' ORDER BY volume DESC LIMIT 8\")]"
2026-06-02 15:20  980001
2026-06-02 15:25  960000
2026-06-02 16:00  950000
2026-06-02 15:55  880000
2026-06-02 16:15  750024
2026-06-02 15:45  710000
2026-06-02 16:10  580000
2026-06-02 15:15  540000
# all-time MAX(volume)=980001 ; count(volume>=500000 today)=8 ; round-thousand → חשד settlement/ingestion artifact
```
**למה זה רלוונטי ל-S2:** אם בר מנופח כזה נכנס כ-b1 או b2, הוא מעוות **גם** את יחס `b2_drop`
(b2/b1) **וגם** את `lookback_quiet` (max(prev3)/b1). זה חוסם-נתונים נפרד מהגייט.
**diagnose-first:** CC חייב להצליב מול Sierra export (`~/SierraChart_Data/v9_export/`) —
האם הערכים האלה אמיתיים מה-DLL או תוצר אגרגציה/תקרה? אם נמצאת סינתזה → **strategic-stop**
(CLAUDE.md §Source-of-Truth), לדווח לא לתקן. **אסור לכייל את b2_drop לפני שמקור הנפחים מאומת.**

### §E · VERDICT (Phase 0)
1. ✅ S2 **מקבל ומעבד** ברים (BarRouter wiring תקין). השערת ה-channel-mismatch מופרכת.
2. ⛔ S2 **לא יכול לירות** — גייט `b2_drop=0.10` ∧ `lookback_quiet` בלתי-מושג (0/1080).
3. ⚠️ חוסם משני: COT/AMT (`cumulative_delta.json`) ייתכן חסר → יציאה מוקדמת.
4. ⚠️ חוסם-נתונים (§D2): נפחי close מנופחים (980001…540000, 15:15–16:15) מעוותים b2_drop+lookback.
   לאמת מקור מול Sierra export לפני כיול הגייט.

**זה ה-can-fire verdict: עם הקוד הנוכחי S2 לא יכול לירות לעולם.** התיקון המינימלי הוא
**לא** wiring — אלא הגייט. ראה Phase 1.

**strategic-stop — הדבק את 3 הבלוקים הגולמיים (§A/§C/§D) ל-Michael לפני Phase 1.**

---

## Phase 1 · התיקון המינימלי — refactor גייט בר 2 (זהה-בייט) + הזרקה

זהו ה-Phase 2 של MEGA_PROMPT — מקודם להיות התיקון העיקרי (לא wiring):
- **Refactor בטוח:** הוצא את גייט בר 2 (`b2_drop`, `five_min_system.py:499`) ל-callable
  מוזרק, default **זהה-בייט** ל-`b2_vol <= b1_vol*0.10`. הרץ טסטים קיימים
  (`backend/v9/systems/five_min/tests/`) → חייבים לעבור ללא שינוי (הוכחת live-unchanged).
- טסט regression anti-tautological: מייבא `FiveMinSystem._detect_reactive`, מזין fixture
  של 7 ברים, מוודא שהגייט ה-default מתנהג כמו `0.10` (*if reverted → RED because הגייט
  המוזרק לא יחזיר את ערך ה-0.10 והטסט ייכשל*).
- תווית `# D-RVX (Phase1 gate-extract)`.
- **strategic-stop: הצג diff + פלט טסטים זהים-בייט לפני בניית ה-observers.**

---

## Phase 2 · 3 וריאציות כצופים (D-RVX core — מ-MEGA_PROMPT Phase 2, ללא שינוי)

Evaluator נפרד (observer) שמריץ את ה-setup ה-4-ברי המלא (b1/b3/b4 + COT/AMT + belly +
lookback) ל-3 גייטים, נבדל **רק** בבר 2 — **עם ספים יחסיים שכן מושגים** (לפי §C: גייט
מוחלט 0.10 = 0 פגישות; יחסי = ריאלי):
- **A · VSA:** `b2<b1 AND b2<b0 AND b2 ≤ 0.7×rolling_avg_20(vol)`
- **B · RVOL-TOD:** `b2 ≤ 0.6×baseline_TOD(clock_time)` (ממוצע אותה שעת-שעון, 10–20
  sessions מ-`v9_bars_5min`, read-only, mode=ro)
- **C · Strict:** `b2 ≤ 0.5×rolling_avg_20(vol)`

טבלה `v9_reactive_variant_signals`: `id, ts, variant_id(A/B/C), direction, entry_price,
b0_vol,b1_vol,b2_vol, rolling_avg_20, rvol_tod, gate_value, other_conditions_json
(cot,amt,belly,lookback pass/fail), atr_5m, session_date, created_at`. כתיבה נפרדת מ-fires.

Outcome labeler (job סוף-session, read-only על bars, חלון time-stop ~18 ברים):
T1=entry±12t לפני stop=entry∓8t? → `outcome, mfe_ticks, mae_ticks, bars_to_resolution`
→ `v9_reactive_variant_outcomes`.

**edge-cases:** החרג/טפל 2 ברים אחרי 09:30, בר 15:55–16:00, roll/half-days.

---

## Phase 3 · תצוגת Build-Status ל-S2 (audit-first — surface כבר קיים)

**Audit — KEEP/ADAPT:** ה-S2 inspector כבר עשיר ומפיק armed/blocked/fired + reason לכל
pattern (`backend/v9/systems/build_status/s2_inspector.py:46-386`), כולל:
- `status` ∈ {fired, vetoed, blocked, armed} עם label+reason (ש'328-365).
- gate `b2_volume_drop` כבר מוצג כ-detection component
  (`s2_pattern_probe.py:566-573`, `spec="b2.volume ≤ b1.volume × 0.1 (90% drop)"`).
- `fired_today`, `last_fire_ts`, `fired_today_count` (מ-`v9_trades` firing_system=2).

**ADD (smallest-correct):** בלוק `reactive_variants` ל-S2 ב-build_status — לכל A/B/C:
`armed` (gate-alone עבר היום), `fired_today` (bool), `fires_count`, `last_fire_ts`,
ו-`last_eval_ts` (מתי הוערך לאחרונה) + `blocked_reason` (למשל "cot_amt=None"
או "0/N windows passed"). **המלצת שדות Build-Status מפורשת (Michael ביקש):**
- `armed: bool` — גייט ה-volume לבד עבר היום (יש לפחות חלון אחד).
- `blocked_reason: str | null` — סיבת חסימה אנושית: `"volume_gate_unreachable"`,
  `"cot_amt_missing"`, `"nt_no_trade"`, `"day_type_skip"`, או `null` אם armed.
- `last_eval_ts: ISO8601` — חותם הזמן של ההערכה האחרונה (proof-of-life שה-detector רץ).
- `fired_today: bool` + `fires_count: int` + `last_fire_ts`.
- **בפרונט:** שלושה אינדיקטורים A/B/C — אור ירוק=`fired_today`, צהוב=armed-לא-ירה,
  אפור=blocked (+tooltip עם `blocked_reason`+`last_eval_ts`). read-only display.
- **Rule 5:** הדבק JSON של ה-endpoint + תיאור הרכיב אחרי session.

---

## Phase 4 · תצוגת טריידר (מ-MEGA_PROMPT Phase 4, ללא שינוי)
Audit עמוד Trades + route; הצג אותות וריאציות (`v9_reactive_variant_signals`) עם
badge A/B/C + outcome, מסומנים **SHADOW-VARIANT** (לא נספרים ב-WR/PnL).

## Phase 5 · דוח השוואתי + UAT (מ-MEGA_PROMPT Phase 5, ללא שינוי)
`scripts/reactive_variant_report.py` פר-וריאציה: `fires_per_day, gate_alone_pass_rate,
full_setup_fires, win_rate, avg_mfe/mae, expectancy_proxy` — זה-לצד-זה, בלי להכריז מנצח.
4 צירי UAT (Quality/Recency/Cardinality/Latency) לכל endpoint חדש.

---

## Strategic stops
1. סוף Phase 0 — 3 בלוקי raw (§A/§C/§D) + VERDICT לפני תיקון.
2. סוף refactor (Phase 1) — diff + טסטים זהים-בייט לפני observers.
3. אחרי session ראשונה — 3 שורות variant גולמיות לאימות תיוג.
4. אם COT/AMT (§D) חסר ב-RTH live — strategic-stop, זה חוסם נפרד (bridge/export).

## NOT DONE / DEVIATIONS (CC חובה למלא — גם אם "none")
- מה לא בוצע · למה · מה צריך כדי לבצע.

## בסיום
עדכן `ROADMAP_TO_LIVE.html` (סקשן 1c · D-RVX) + `STATUS_BOARD.md`
(root→fix→verification, Rule 5) + `DECISION_LEDGER.md` (D-RVX → 🟢 IMPLEMENTED-SHADOW).
שורת STATUS_BOARD חייבת לתעד: root=גייט-volume 0.10∧lookback בלתי-מושג (0/1080 windows,
לא channel-mismatch) → fix=גייט מוזרק + 3 וריאציות יחסיות צופות → verified=<פלט>.

---

### עיגון קוד (מאומת 2026-06-02)
- `backend/v9/systems/five_min/five_min_system.py`: `DROP_THRESHOLD_PCT=0.10` (ש'30),
  `subscribed_channels` (ש'88, event-bus — לא bars), `_detect_reactive` (469-543, גייט
  בר2 `b2_drop` ש'499, lookback ש'509-512, יציאת COT/AMT-None ש'488),
  `subscribed_bar_types`→`["5min"]` (695-696), `_cot_amt_from_sierra` (433-451).
- `backend/main.py:88-89` — רישום BarRouter תקין (`subscribe("5min", process_bar)`).
- `backend/v9/services/bar_aggregator_5min.py:206` — `publish_threadsafe("5min", ...)`.
- `backend/v9/services/bar_router.py:~99` — dispatch לפי `bar_type`.
- `backend/v9/systems/build_status/s2_inspector.py` (46-386) + `s2_pattern_probe.py`
  (566-573 `b2_volume_drop`) — תצוגת build_status (KEEP/ADAPT).
- `v9_bars_5min` — baseline TOD + labeler (read-only, mode=ro).
