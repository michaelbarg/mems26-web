# CC Handoff — שער-מגמה (trend_state) + הרחבת T1 (R-ladder) · 2026-06-18

**מאשר:** Michael (2026-06-18) — "לעבוד עם כיוון המגמה" + "להרחיב רווח ב-T1 לפי ההמלצה, עם דגל".
**מכין:** Cowork (אבחון + spec + אימות). **מבצע קוד:** CC. **חוזה/דיסציפלינה (מוטמע כאן, self-contained):** טסטים אנטי-טאוטולוגיים (RED-on-revert), סעיף **NOT-DONE** חובה, וצטט פקודה+פלט גולמי (Rule 5). הערה: `docs/handoff/CC_HANDOFF_CONTRACT.md` **לא קיים בריפו הנוכחי** — אם יש לו עותק אצל CC, לעבוד גם לפיו.

> שתי הליבות הן **trading-logic / risk-surface** → **flag-gated default-OFF**, אימות-SHADOW, ו-**אישור-Michael נפרד לפני הדלקה ב-SHADOW ולפני LIVE**. אסור להדליק את הדגלים ב-`.env` בלי אישור מפורש. שמירה על Standing Decisions: `LAYER0_CHOP_GATE`/`S2_CHOPPINESS_GATE`/`S2_REQUIRE_COT_AMT` נשארים OFF; לא לגעת ב-`sc_study`/bridge/market-data.

הבסיס האמפירי: `docs/reports/PATTERN_IMPROVEMENT_PROPOSAL_2026-06-18.html` + `docs/reports/PATTERN_BAR_AUDIT_2026-06-16.html` (122 עסקאות/8 ימים: HFE −$2,639, ZLR-SHORT −$1,491, REACTIVE_LONG −$1,020 כ-counter-trend; T1 נפגע 62% אך T2 רק 13%).

---

## שינוי 1 — Trend Direction Gate (דגל `TREND_DIRECTION_GATE`, default OFF)

**מטרה:** לחסום ירי **נגד-מגמה** של התבניות-המדממות בלבד, לפי `trend_state` **חי** (לא תלוי בסיווג-יום, שכרגע לא-אמין/מת ב-06-17). ממוקד — שומר את המנצחות (ZLR-**LONG**, TLB דו-כיווני).

**מקור-האות (כבר זמין ב-choke-point):** `trading_gateway.route_setup` כבר קורא `cross_context["woodies_system"]["trend_state"]` (ראה הגוש הקיים של `DAYTYPE_PLAYBOOK`, שורות ~150–167). counter-trend = `LONG∧RED` או `SHORT∧BLUE` (בדיוק כמו `daytype_playbook.decide()` שורה 109). `GRAY/YELLOW/None` → **fail-open (מתיר)**.

**יחס ל-`daytype_playbook`:** השער החדש **עצמאי** ומשלים. ל-`daytype_playbook.decide()` יש כבר `require_with_trend`, אך הוא פעיל **רק** כש-`day_type in {Trend_Normal,Trend_DD}` (שורה 106) — ולכן לא תפס את ה-counter-trend של 06-16 (היום תויג `Variation`). השער החדש פועל על `trend_state` ללא תלות ב-day_type. כפילות-חסימה (אם שניהם דולקים) בטוחה — שניהם רק חוסמים.

### 1.1 מודול חדש — `backend/v9/systems/trend_direction_gate.py`
מבנה במראה ל-`daytype_playbook.py` (fail-open, env-gated, config-tunable):

```python
# decide(pattern, direction, trend_state) -> (allow: bool, reason: str)
# _enabled(): os.environ["TREND_DIRECTION_GATE"] in {1,true,yes}
# OFF / no-cfg / trend_state not in {BLUE,RED} / pattern not targeted -> (True, reason)  # fail-open
# match: raw pattern_id first, then base (strip _LONG/_SHORT). cfg value = list of sides to gate.
# counter = (dir==LONG and ts==RED) or (dir==SHORT and ts==BLUE)
# if dir in targeted_sides and counter -> (False, "<pat> counter-trend (trend=<ts>)")
```

קריטי לטרגוט הנכון: **לשמור את הצד הרווחי.** `ZLR` ממופה ל-`[SHORT]` בלבד → ZLR-LONG **לא** נחסם גם כשהוא counter (LONG∧RED). `REACTIVE_LONG` מופרד מ-`REACTIVE_SHORT` (אל תנרמל החוצה את ה-side עבור ההתאמה — match על pattern_id המלא, ורק fallback ל-base).

### 1.2 קונפיג חדש — `config/trend_direction_gate.yaml` (עריכה=שורה-אחת)
```yaml
# with-trend discipline ממוקד, לפי trend_state חי (BLUE↔LONG, RED↔SHORT).
# value = הכיוונים שעליהם חל השער; חוסם כשאותו כיוון counter ל-trend_state.
# GRAY/YELLOW/None -> מתיר (fail-open).
patterns:
  HFE: [LONG, SHORT]      # שני הצדדים counter-trend → חסום (−$2,639)
  REACTIVE_LONG: [LONG]   # חסום LONG לתוך RED (−$1,020)
  ZLR: [SHORT]            # רק ZLR-SHORT (−$1,491); ZLR-LONG (+$1,372) נשמר
```

### 1.3 חיווט ב-`backend/v9/gateway/trading_gateway.py`
גוש חדש **אחרי** גוש ה-`DAYTYPE_PLAYBOOK` (שמסתיים ~שורה 167) ו**לפני** `cluster_guard` (~שורה 169), במראה מדויק לגוש הקיים (try/except fail-open, env-gated, `return` עם `blocked_by`):
```python
if os.getenv("TREND_DIRECTION_GATE", "0").lower() in ("1","true","yes"):
    try:
        from backend.v9.systems.trend_direction_gate import decide as _td_decide
        _td_g1 = extract_g1_entry_context(cross_context)
        _td_ts = (cross_context.get("woodies_system") if isinstance(cross_context, dict) else {} or {}).get("trend_state")
        _allow, _reason = _td_decide(resolve_pattern_id(setup, _td_g1), direction, _td_ts)
        if not _allow:
            result["blocked_by"] = "trend_direction_gate"
            logger.info("[Gateway] BLOCKED by trend-direction gate: %s", _reason)
            return result
    except Exception as _td_err:  # fail-open — never block on a bug
        logger.warning("[Gateway] trend-direction gate errored (fail-open): %s", _td_err)
```
התנהגות זהה ל-playbook: חסימה = **לא נרשם ב-SHADOW** (ה-`return` לפני `_execute_shadow`), נראה בלוג `[Gateway] BLOCKED by trend-direction gate: …`. כך נמדוד בשאדו דרך הלוג; את אפקט-ה-PnL מודדים בסים (§3).

### 1.4 טסטים (אנטי-טאוטולוגי, `tests/v9/.../test_trend_direction_gate.py`)
- flag ON + cfg למעלה: **חסום** {HFE-LONG@RED, HFE-SHORT@BLUE, REACTIVE_LONG@RED, ZLR-SHORT@BLUE}; **מתיר** {HFE-LONG@BLUE (with-trend), **ZLR-LONG@RED** (טרגוט-side — ה-assert הקריטי), REACTIVE_SHORT@BLUE (לא-ממוקד), HFE-*@GRAY (fail-open), כל-דבר@None}.
- flag OFF → הכל מתיר.
- **RED-on-revert (חובה):** היפוך תנאי-ה-counter (או הסרת HFE מה-yaml) → ה-asserts של ה"חסום" הופכים ל"מתיר" → הטסט נכשל. לצטט RED→GREEN.
- gateway-level: setup HFE-LONG עם `cross_context.woodies_system.trend_state=RED` ו-flag ON → `route_setup(...)["blocked_by"]=="trend_direction_gate"`; flag OFF → `None`.

---

## שינוי 2 — הרחבת T1 (דגל `T1_LADDER_V2`, default OFF)

**מטרה:** T1 רחוק יותר → הסקאלף תופס יותר. כיום הסולם הדוק מאוד: S4 CONT `1.0/0.75/0.65/0.5/0.4R`, REV ×`0.80`, HFE `t1_ladder_shift:-1` (מדרגה **נוספת** למטה), S2 לינארי `0.8→0.4R`. הכל ב-`config/stop_anchors.yaml`, נצרך דרך `SA.t1_price()` (`backend/v9/systems/stop_anchors/resolver.py:87`).

### 2.1 קונפיג (additive ב-`config/stop_anchors.yaml` — לא משנה את ברירת-המחדל)
```yaml
t1_ladder_continuation_v2:        # נצרך רק כש-T1_LADDER_V2=1 (ערכי-מועמד — לכיול בסים §3)
  - {max_risk_points: 5,  t1_r: 1.20}
  - {max_risk_points: 10, t1_r: 1.00}
  - {max_risk_points: 15, t1_r: 0.90}
  - {max_risk_points: 20, t1_r: 0.75}
  - {max_risk_points: 25, t1_r: 0.60}
t1_reversal_multiplier_v2: 0.90   # פחות-מצמצם לתבניות-היפוך
flag_relative_t1_v2:              # S2 (five-min)
  t1_r_max: 1.00
  t1_r_min: 0.60
  dist_tight_pts: 15
  dist_wide_pts: 25
```
כל הערכים ≤ `guardrails.t1_r_max: 1.5` → עוברים ולידציה. **הערכים זמניים — סופיים אחרי הסים (§3).**

### 2.2 חיווט — כל מסלולי-ה-T1 (full-pipeline; אסור להשאיר חלקי)
בכל אתר: בחר `_v2` כאשר `_flag("T1_LADDER_V2")`, אחרת הקיים (default).
1. `backend/v9/systems/woodies/woodies_system.py:693` (S4 CONT+FAMIR/HTLB/HFE) — `t1_ladder_cont` + `reversal_mult`.
2. `backend/v9/systems/stop_anchors/sizing.py:89` — אותה בחירה (`t1_ladder_continuation` + `t1_reversal_multiplier`).
3. `backend/v9/systems/five_min/five_min_system.py:1339-1340` — `t1_r_max/min` מ-`flag_relative_t1_v2`.
4. `scripts/sim_woodies_replay.py:29-30` — תמיכה ב-`_v2` כדי שהסים ימדוד את אותו מסלול (לפרמטר/דגל).
5. `backend/v9/config_loader.py:308` — להוסיף `"t1_ladder_continuation_v2"` ללולאת-הוולידציה (אחרת לא-מאומת).

> **wiring-check (memory `feedback_full_decision_pipeline_wiring`):** הדגל חייב להגיע לכל ארבעת מסלולי-החישוב + הסים. כל אתר שמדלגים עליו = דרישה לתעד למה ב-NOT-DONE.

### 2.3 טסטים (`tests/v9/regression/test_t1_ladder_v2.py`)
- flag ON: `SA.t1_price(entry,stop,...,t1_ladder_cont=v2)` מחזיר T1 **רחוק יותר** מ-default באותו risk (למשל risk=12pt: default 0.75R, v2 1.00R). flag OFF → זהה ל-default.
- **RED-on-revert:** השוואת default↔v2 — אם החיווט מצביע על אותו ladder (באג), הטסט (v2>default) נכשל.
- S2: `flag_relative_t1_v2` נותן t1_r גבוה יותר; OFF → קיים.
- `load_stop_anchors()` + `validate` עוברים עם הבלוק החדש (t1_r∈[0.2,1.5]).

---

## 3 · אימות לפני הדלקה (gate)
1. **Backtest (Cowork ירוץ, או CC):** `scripts/sim_woodies_replay.py` על 7 ימי-המסחר, default ladder מול `t1_ladder_continuation_v2` — להשוות net-PnL, T1-hit%, T2-hit%, ו-avg-win/avg-loss. **לכייל את ערכי-ה-v2 לפי התוצאה** (tradeoff: T1 רחב = פחות פגיעות-T1 אך רווח-לעסקה גדול). לתעד טבלה.
2. **טסטים:** שני קבצי-הרגרסיה ירוקים + הוכחת RED-on-revert (פקודה+פלט גולמי).
3. **import sanity:** `python -c "import backend.main"` OK.
4. **SHADOW (אחרי אישור-Michael):** להדליק דגל-אחד-בכל-פעם, restart, ולאמת בלוג: `[Gateway] BLOCKED by trend-direction gate` יורה על counter-trend של HFE/REACTIVE_LONG/ZLR-SHORT בלבד; T1 בעסקאות-SHADOW רחוק יותר. להריץ יום-יומיים מול הסים לפני DEMO/LIVE.

## 4 · NOT-DONE / מחוץ-לסקופ (למלא ע"י CC)
- אין הדלקת דגלים ב-`.env` (ממתין לאישור-Michael פר-דגל).
- לא נכלל: תיקון סיווג-היום (D10) ושורש 06-17 dead-day — **תלות-על** נפרדת; שער-המגמה לא תלוי בה (trend_state), אך ה-playbook כן.
- לא נכלל: progressive-trail ל-runner (Michael בחר "להעלות סולם-R", לא trail) — לתעד כ-OPEN אם רוצים בעתיד.
- I-34 (sizing=half לא-מיושם) — לא בסקופ הזה; פתוח בנפרד.
- כל אתר-T1 שלא חוּוט — לצטט ולמה.

## 5 · Rollout
commit flag-gated default-OFF (+טסטים) → backtest+כיול ערכי-v2 → **אישור-Michael** → SHADOW דגל-אחד-בכל-פעם → מעקב יום-יומיים מול הסים → DEMO/LIVE (gate נפרד). עדכון `STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html` בכל שלב.
