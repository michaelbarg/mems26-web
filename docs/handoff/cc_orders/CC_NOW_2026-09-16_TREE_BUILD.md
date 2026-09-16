# CC_NOW 2026-09-16 16:25 — בניית העץ החכם מתחילה עכשיו, במקביל ליום-המסחר (cowork-dev → cc-macbook)

**מייקל 16.09 16:20:** *"למה בעצם לא ביצעת בדיקה עם קלוד קוד … ובעצם מיישמים בנייה של העץ ממה שלמדנו? תיכנס לראש סוחר מקצועי."* — צודק. הדסק סוחר על הבסיס המוקפא; צוות-הבנייה בונה במקביל, לא מחכה לערב.
**התוכנית:** `docs/plans/PLAN_2026-09-16_DOCTRINE_TREE_AND_LEARNING_LOOP.md` (קרא אותה ראשונה — 5 דקות). פריטים: T-396 · T-390 · T-391 · T-389 · T-392 ב-`TASK_LOG.md`.

## גבולות קשיחים (השוק פתוח 16:30-23:00 IL, המערכת סוחרת על כסף אמיתי, 2 חוזים)

- **אפס ריסטארט. אפס `.env`. אפס דגל דלוק. אפס נגיעה בתהליך הרץ** (‏uvicorn רץ בלי `--reload` — עריכת קבצים בריפו לא משפיעה עליו עד הריסטארט הבא, שהוא של cowork).
- **אפס הרנס/ריפליי/שאילתות-DB כבדות לפני 23:05 IL.** המכונה ב-166 MB פנויים ו-swap 1.4 GB — ריצה כבדה בזמן RTH מסכנת את המסחר. טסטי-יחידה (‏pytest על קבצים בודדים) — כן. `replay_admits.py`/`fwd_harness.py`/`gap_analysis.py --run` — **רק אחרי 23:05**.
- כל פריט = קומיט אחד + טסטים + שורה ב-`TASK_LOG` + שורה ב-`STATUS_BOARD` + LOG חתום ב-`LIVE_CHANNEL` עם פלט גולמי (Rule 5). `git -C …` תמיד, לעולם לא `cd && git`.
- **בלי שאלות** (CLAUDE.md 14.09). דו-משמעות ⇒ בוחרים את הפרשנות שההזמנה מסמנת כ-golden, כותבים "החלטתי X כי…" ב-LOG, וממשיכים. אי-אפשר לסיים ⇒ NOT-DONE מפורש + הפריט הבא.
- **בלי דגלי-דוקטרינה חדשים.** מותר: מתג-כיבוי אחד ללוגר (‏`SITUATION_VECTOR_LOG_V1`, ברירת-מחדל **דלוק בקוד**, `=0` מכבה). כל השאר — ברירת-מחדל בקוד, בלי env.
- לוודא אחרי כל עריכה של `config/RULED_FLAGS.yaml`: `python3 -c "import yaml; yaml.safe_load(open('config/RULED_FLAGS.yaml'))"` (הבוקר: NO-GO כוזב מגרש-נמלט).
- ראשון `git pull`. הסדר: **T-396 → T-390 → T-391 → T-389 → T-392.** דווח "סיים פריט N" אחרי כל אחד ותמשיך לבא — לא לעצור.

---

## T-396 · סוגר-סשן לעסקאות-צל (30 דק') — היגיינה, לא דוקטרינה

**הממצא (11:25):** 26 שורות-צל מ-14-15.09 נשארו FILLED/PARTIAL; ה-TradeManager ניהל אותן בכל בר ⇒ backend 55-80% CPU, 1,000 שורות-לוג/דק', `SLOW handler 620ms`, 70 התראות-`stuck_trade`/יום. נוקה ידנית (`scripts/close_stale_shadow.py --apply`). השורש: אין סוגר לצל.

**לבנות:**
1. `backend/v9/services/trade_manager/bar_level_detector.py` — בבר-הסגירה של ה-RTH (הבר שה-`ts` שלו ≥ 22:55 IL, אותו טריגר שמשמש את `_eod_flatten`, **בלי** התלות בדגלי `EOD_*`) — כל עסקה `mode='shadow'` ב-`FILLED`/`PARTIAL` ⇒ `state='CLOSED', exit_reason='STALE_UNRESOLVED', exit_price=NULL` (‏`pnl_usd` נשאר כמו שהוא אם יש חלקי-ממומש, אחרת NULL). **אותו כלל-כנות של הסקריפט: לא ממציאים תוצאה.** לייב/דמו — לא נוגעים.
2. הידרציית ה-TradeManager בבוט (‏`manager.py` — `_ACTIVE_TRADE_STATES` query): עסקת-`shadow` שה-`entry_ts` שלה **לפני סשן-ה-RTH הנוכחי** אינה נטענת לניהול — נסגרת באותו כלל, עם לוג אחד `[TradeManager] shadow from previous session closed STALE_UNRESOLVED: n=…`.
3. **בדיקה למה `T2 HIT: trade 1608` נרשם 123 פעמים** — אותו HIT על אותה עסקה יותר מפעם אחת = מעבר-מצב שלא קורה. תמצא ותתקן אם זה ≤ 20 שורות; אחרת NOT-DONE עם הממצא המדויק (file:line).
4. `tests/v9/regression/test_shadow_session_close.py`: (א) צל מאתמול ב-PARTIAL ⇒ אחרי on_bar של בר-הסגירה CLOSED/STALE_UNRESOLVED/exit_price None; (ב) לייב באותו מצב ⇒ לא נוגעים; (ג) הידרציה מדלגת/סוגרת צל-ישן.

---

## T-390 · וקטור-מצב + רישום בכל החלטה ובכל בר (2-3 שע')

**למה:** `GAP_INVENTORY`: כל הוראה הפכה לשער כי לעץ אין עיניים. הווקטור הוא העיניים. `v9_trades.cross_context` כבר נושא את רובו על 1,506 עסקאות מיוני — הפריט הזה הופך אותו למבנה אחד, סיבתי, שנרשם **גם כשאף מפיק לא ירה**.

**לבנות — `backend/v9/services/situation_vector.py` (חדש):**
```python
@dataclass(frozen=True)
class SituationVector:
    ts: str                      # ISO UTC של הבר
    price: float
    day_type: str | None         # התווית החיה ברגע-ההחלטה (לא סופית!)
    day_type_conf: float | None
    phase: str | None            # A/B/C/D — אותו _resolve_phase של השער
    opening_type: str | None
    zone: str | None             # location_gate.zone_of(price, vah, val, ib_width) על ה-VA המתפתח
    prior_zone: str | None       # אותו zone_of מול ה-VA של הסשן הקודם (pd_ctx / previous_session)
    ib_locked: bool
    ib_width: float | None
    extension: str               # 'up' | 'down' | 'both' | 'none' — רק כש-ib_locked; session_high>ib_high / session_low<ib_low
    extension_pts: float         # max(session_high-ib_high, ib_low-session_low, 0)
    vol_ratio: float | None      # ווליום-הבר / חציון ווליום אותה-דקת-יום ב-10 סשני-RTH הקודמים (סיבתי; None אם <5 סשנים)
    bars_since_high: int | None  # ברים-RTH סגורים מאז שיא-הסשן
    bars_since_low: int | None
    dir_hint: str | None         # dp_dir_hint של השער / S1DayDir
    atr_causal: float | None     # ATR14 על ברים סגורים בלבד
```
- `compute_situation_vector(*, cross_context, price, ts, bars_rth_today, prior_sessions_bars, phase, dir_hint) -> SituationVector` — **פונקציה טהורה, fail-open** (שדה שאי-אפשר לחשב ⇒ None; לעולם לא זורקת). **אפס look-ahead:** רק ברים סגורים, רק סשנים קודמים לחציון.
- **חיבור בשער (‏`trading_gateway.py`, `route_setup`):** מחשבים פעם אחת לכל setup, שומרים `setup["metadata"]["situation"] = asdict(sv)` (כך כל שורת-`v9_trades` נושאת אותו), ומעבירים ל-`dalton_playbook` (ראה T-391). **הקוד הקיים של השערים לא משתנה** בפריט הזה.
- **רישום — טבלה חדשה `v9_decision_vectors`:** `id · ts timestamptz · kind ('DECISION'|'BAR') · system int · classification · direction · entry numeric · phase · blocked_by · reason · mode_result jsonb · vector jsonb · created_at`. שורת-DECISION לכל קריאת-שער (ירה או נחסם); שורת-BAR אחת לכל בר-RTH-5-דק' סגור **גם בלי setup** (‏hook ב-`bar_router` אחרי ה-handlers; `system=0`, `classification='BAR'`). כתיבה **לא-חוסמת** (‏thread/queue כמו `ntfy_notify`), `try/except` סביב הכל, לעולם לא על נתיב-המסחר. מתג-כיבוי `SITUATION_VECTOR_LOG_V1` (ברירת-מחדל **דלוק**). מיגרציה: `backend/v9/db/migrations/…_decision_vectors.sql` + `CREATE TABLE IF NOT EXISTS` בבוט (‏Postgres מקומי בלבד; `read.py`/ORM, לא `sqlite3`).
- **טסטים** `tests/v9/regression/test_situation_vector.py`: zone/prior_zone · extension רק אחרי ib_locked · vol_ratio סיבתי (חציון מ-N סשנים קודמים בלבד; מבחן שמזריק ווליום-ענק **בסשן הנוכחי** ומוודא שהחציון לא זז) · bars_since_* על ברים סגורים · fail-open על cross_context ריק · הלוגר לא זורק כשה-DB למטה.
- **אימות (אחרי 23:05 בלבד):** `fwd_harness --session 2026-09-15` ⇒ `routes`/`would_write` **זהים בית-בית** לריצת הבסיס (`harness_out/t367/head_2026-09-15.json`) — הווקטור מוסיף מידע, לא משנה החלטה. `Traceback=0`, `T-335=0`.

---

## T-391 · שפת-תנאים על הווקטור ב-`_match_condition` (1-2 שע')

**הממצא:** `backend/v9/services/dalton_playbook.py:102` — `_match_condition(cond, opening_type, day_type)` מכיר `default` · `opening_type ==/in` · `day_type ==/in` בלבד. לכן כל כלל עם מיקום/הרחבה/ווליום חייב קוד ⇒ הופך לדגל.

**לבנות:**
- חתימה חדשה, תואמת-אחורה: `_match_condition(cond, opening_type, day_type, vector: dict | None = None)`. כל השורות הקיימות ב-`config/dalton_playbook.yaml` מתנהגות **בדיוק** כמו היום (מבחן: כל ה-golden-ים הקיימים של הפלייבוק עוברים ללא שינוי).
- צורה חדשה: `expr: "<ביטוי>"` — מוערך על `vector` (+ `opening_type`, `day_type` כשמות). **מעריך בטוח, לא `eval`:** `ast.parse(expr, mode='eval')` + רשימה-לבנה של צמתים: `Expression, BoolOp(And/Or), UnaryOp(Not), Compare(Eq/NotEq/Lt/LtE/Gt/GtE/In/NotIn), Name, Constant, List, Tuple`. **כל צומת אחר (Call, Attribute, Subscript, Lambda, dunder…) ⇒ `ValueError` בטעינת ה-YAML** (נכשל בבוט, לא בשקט). שם לא-מוכר או ערך None בהשוואה ⇒ השורה **לא** מתאימה (fail-closed לשורה). דוגמה: `expr: "day_type in ['Variation','Normal_Variation'] and extension == 'down' and zone != 'mid_value' and bars_since_low >= 2"`.
- חיבור: `dalton_playbook.intent(...)` מקבל את `setup["metadata"]["situation"]` מהשער (T-390) ומעביר ל-`_match_condition`. **אפס שורות-`expr` בפרודקשן בפריט הזה** ⇒ אפס שינוי-התנהגות.
- **טסטים** `tests/v9/regression/test_condition_expr.py` (≥15): כל אופרטור · `in` על רשימה · קינון עם סוגריים · None ⇒ False · שם לא-מוכר ⇒ False · **הזרקות נדחות:** `__import__('os')`, `x.__class__`, `f()`, `a[0]`, `lambda: 1` ⇒ ValueError בטעינה · תאימות-אחורה על כל שורות ה-YAML הקיימות.

---

## T-389 · `scripts/gap_analysis.py` — לכתוב עכשיו, **להריץ אחרי 23:05** (2 שע' כתיבה)

**השאלה של מייקל:** *"אם ביום עשינו 10 נקודות והטווח היה 200 — היו המון עסקאות שפספסנו."* הסקריפט עונה עליה על **85 סשני-RTH** (יוני-ספטמבר), עם המודל הקבוע.

**קלט:** `v9_bars_5min_woodies` (RTH 16:30-23:00 IL) · `v9_trades` (‏`mode in ('live','shadow')`, עם `cross_context`) · המודל הקבוע — **לייבא** מ-`scripts/replay_admits.py` (‏`LADDER`, `size_for`, `walk`; אל תכתוב מודל שני).
**לכל סשן:**
- `day_type_final` — מ-`classify_replay` (המנוע המאומת לפי `docs/SOURCE_OF_TRUTH.md`), `opening_type` (מה-`cross_context` של העסקה הראשונה ביום, אחרת None), `range_pts`, `rth_close`.
- `captured_live_usd` / `captured_live_pts` — כניסות-הלייב של היום דרך המודל הקבוע (לא ה-`pnl_usd` שנרשם).
- **3 התנועות הגדולות** — פירוק זיגזג על ברים סגורים עם סף `max(8 נק', 1.0×ATR14-סיבתי)`; לכל תנועה: `t_start, t_end, pts, dir`.
- **לכל תנועה — המעמד:** setup לייב/צל שנכנס ב-30% הראשונים של התנועה ובכיוונה ⇒ `FIRED_LIVE` / `FIRED_SHADOW_ONLY` (עם התוצאה במודל הקבוע) / `BLOCKED:<blocked_by>` (מ-`cross_context.woodies_system.last_route.blocked_by` או מ-`reason`); אין setup בכלל ⇒ `NO_SETUP` (**פער-מפיק**).
- **לכל הפסד-לייב:** הווקטור בכניסה (מ-`cross_context`: day_type+conf, opening_type, zone מול vah/val, extension מול ib, bars_since_extreme מ-session_high/low, dir).
**פלט:** `harness_out/gap/gap_sessions.json` + `docs/reports/GAP_ANALYSIS_2026-09-17.md`: (1) טבלה לפי `day_type_final`: N ימים · טווח-ממוצע · נלקח-ממוצע · **יחס נלקח/טווח** · חלוקת-מעמד של התנועות (NO_SETUP / BLOCKED:x / FIRED); (2) 20 התנועות הגדולות שהוחמצו עם הסיבה; (3) **ענפים-מועמדים**: קיבוץ של תנועות-שהוחמצו והפסדים לפי `(day_type, phase, zone, extension, dir-vs-move)` — **רק קבוצות עם N ≥ 15**, לכל אחת: N · Σ$ במודל הקבוע אילו נכנסנו/לא נכנסנו · הענף המוצע כשורת-`expr`; (4) תשובה במספר: `TREND_STEP` ו-`RE_ACCEPTANCE` — כמה מהתנועות-שהוחמצו בימי-Trend/Normal היו להן setup-צל, ומה Σ$ שלו במודל הקבוע.
**כלל-כנות:** כל מספר בדוח ניתן-לשחזור מ-`python3 scripts/gap_analysis.py --session 2026-09-15 --verbose`. אין תוצאה למהלך תוך-ברי (AMBIG לא-מוקצה, כמו במודל). `--dry` מדפיס סשן אחד בלי לכתוב.

---

## T-392 · טיוטת-העץ v2 + מנוע-הערכה במצב-צל (2-3 שע') — לא נטען בפרודקשן

- `config/dalton_tree_v2_draft.yaml` — הכללים הקיימים כשורות-`expr`, אחד-לאחד, עם `source: T-319b|T-329|T-355|T-365|T-367|edge_fade` ו-`measured: UNMEASURED`. **T-367 נכתב מפוצל** (זה הלקח מהבוקר): שורה א' — `Variation ∧ zone == mid_value ∧ setup נגד ה-extension ⇒ block`; שורה ב' — `Variation ∧ extension != none ∧ setup עם ה-extension ∧ zone != mid_value ⇒ allow (BREAK|PULLBACK)`; **כניסה עם-הכיוון מ-mid_value לא נחסמת** (ה-GHOST SHORT של 15.09 19:10). `FRESH_EXTREME` (T-366, נמדד שלילי) — **אין שורה**.
- `backend/v9/services/dalton_tree.py` — `evaluate(tree, vector, setup) -> {"decision": allow|block|stand_down, "row": id, "reason": …}` — **לא מחובר לנתיב-הירי.** מחובר רק ל-**לוג-צל**: בשער, אחרי ההחלטה האמיתית, מעריכים את הטיוטה ורושמים `[TREE-DIFF] real=<blocked_by|FIRED> tree=<decision row>` + שדה `tree_shadow` בשורת-`v9_decision_vectors`. כך ההגירה נמדדת לייב מחר בלי לסכן כלום.
- `scripts/tree_diff.py --sessions 2026-09-15 2026-09-11 …` (אחרי 23:05): מריץ את `replay_admits` עם השערים הקיימים מול העץ ומדפיס לכל סשן את ההחלטות השונות. **קריטריון-ההגירה (יום א'): אפס הבדל על 85 סשנים חוץ מהפיצול המכוון של T-367.**
- טסטים: כל שורה בטיוטה נטענת ומוערכת; שורה עם `Call` נדחית; golden: 15.09 19:10 GHOST SHORT ⇒ `allow` בעץ (היום: `variation_mid_value`).

---

## דיווח

אחרי כל פריט: LOG חתום ב-`LIVE_CHANNEL.md` (פקודה + פלט גולמי + "החלטתי X כי…"), `TASK_LOG` (‏🟠 ⇒ ✅ רק עם שורת-לוח ב-`STATUS_BOARD`), commit+push, ו-**"סיים פריט N"** — ותמשיך. cowork מאמת הלילה בשער-הבטיחות ומריץ את `gap_analysis.py` על 85 הסשנים; הריסטארט שטוען T-390/T-391/T-396 הוא של cowork, מחר לפני הפתיחה, אחרי `Traceback=0` על 15.09+11.09.
