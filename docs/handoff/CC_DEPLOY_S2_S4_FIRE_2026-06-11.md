# CC — פריסת תיקוני‑ירי S2+S4 (commit + דגלים + restart) · SHADOW · 2026‑06‑11

> פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`. **SHADOW בלבד — אל תדליק LIVE.**
> כל התיקונים כבר **כתובים בעץ‑העבודה ואומתו ע"י Cowork** (18 טסטים ירוקים, סימולציה על 06‑09). תפקידך: **לסגור (commit), להדליק דגלים, לאתחל, ולאמת חי** — לא לכתוב מחדש. כל הדגלים default‑OFF בקוד, אז ה‑commit לבדו לא משנה התנהגות; ההדלקה מפורשת ל‑SHADOW.

## מקור‑האמת לתיקונים (Cowork הכין + אימת)
| # | קובץ | מה | אימות‑Cowork |
|---|---|---|---|
| 1 | `backend/v9/systems/day_type/state_machine.py` | `_maybe_provisional_classify` — provisional day_type@30 מ‑IB המתפתח של סיירה (דגל `S1_PROVISIONAL_DAYTYPE`, default OFF). `ib_locked` נשאר False. | 4 טסטים: day_type≠UNKNOWN@30 כשדלוק · UNKNOWN כשכבוי (RED‑on‑revert) · בלי IB→UNKNOWN (no‑synth) · lock@60 גובר. |
| 2 | `backend/v9/shared/pre_fire_validator.py` | (א) R:R על ה‑runner (D‑094, לא על T1‑scalp). (ב) שערי `MEMS_MIN_RISK_POINTS`/`MEMS_MAX_RISK_POINTS` (default OFF). | 4+3 טסטים: 9/9 setups עוברים · min דוחה 1‑נק' · max דוחה 110‑נק' · off‑by‑default. |
| 3 | `backend/v9/api/v9/bars.py` | בדיקת price‑band רק ל‑5min (ברי woodies/tpo כבר לא נחסמים — שורש שתיקת‑S4). | סימולציה: S4 עבר מ‑0 ל‑8 תבניות נסרקות. |
| — | טסטים חדשים | `tests/v9/regression/test_s1_provisional_daytype.py` · `test_pre_fire_risk_gates.py` (+ `test_a7_rr_on_runner.py`, `test_pre_fire_t2_none.py` קיימים) | — |
| — | תיעוד | `scripts/sim_woodies_replay.py` · `docs/reports/SIM_0609_POSTFIX_2026-06-11.html` | — |

## שלב 0 — אימות לפני commit (Rule 5 — הדבק raw)
```bash
git status --short
git diff --stat
python3 -m pytest tests/v9/regression/test_s1_provisional_daytype.py \
  tests/v9/regression/test_pre_fire_risk_gates.py \
  tests/v9/regression/test_a7_rr_on_runner.py \
  tests/v9/regression/test_pre_fire_t2_none.py -q   # צפוי: 18 passed
python3 -m pytest tests/v9/regression -q             # הסוויטה המלאה — הדבק pass/fail; ציין נכשלים‑קיימים אם יש
```
**אם אדום (מעבר לנכשלים‑קיימים מתועדים) → strategic‑stop, דווח, אל תמשיך.**

## שלב 1 — commit
- commit אחד לתיקוני‑הירי + הטסטים + ה‑sim/report. הודעה כמו:
  `fix(S1+S2+S4): provisional day_type@30 + pre_fire runner-R:R + min/max-risk gates + bars staleness (flag-gated, SHADOW)`
- **אל תכלול** את ניקוי‑ה‑dead‑code (סבב נפרד).

## שלב 2 — הדלקת דגלים ב‑.env (SHADOW · החלטה מפורשת)
```
S1_PROVISIONAL_DAYTYPE=1
STOP_ANCHORS_V2=1            # ודא שכבר מוגדר
MEMS_MIN_RISK_POINTS=2       # דוחה סטופים מנוונים (1‑נק')
MEMS_MAX_RISK_POINTS=60      # רשת‑ביטחון לסטופ ענק (110‑נק')
```
(אל תיגע ב‑`S2_CHOPPINESS_GATE`/`LAYER0_CHOP_GATE`/`S2_REQUIRE_COT_AMT` — Standing Decisions, default‑OFF.)

## שלב 3 — restart (CLAUDE.md §Service Bring‑Up)
- בדוק listeners קיימים על `127.0.0.1:8000` ו‑`127.0.0.1:3000` — **אל תריץ כפול**.
- אתחל את ה‑backend לפי הנוהל הקיים (`scripts/start_all.sh` / LaunchAgent). ודא **uvicorn יחיד**.
- `curl -s localhost:8000/health` → `alive:true, mode:shadow`.

## שלב 4 — אימות‑חי אחרי restart (Rule 5 — 4 הוכחות, הדבק raw)
1. **day_type@30:** תוך 30 דק' מפתיחת RTH —
   `SELECT to_char(ts,'HH24:MI'), stage, opening_type, ib_width_class, day_type, lock_state FROM v9_day_type_state WHERE ts::date=CURRENT_DATE ORDER BY ts;`
   → `day_type ≠ UNKNOWN` ב‑~30 דק' עם `lock_state=PENDING` (provisional). הדבק את ה‑ts של הסיווג‑הראשון מול (RTH‑open+30). זו **התקלה‑החוזרת** — תעד שנסגרה.
2. **S4 יורה:** `v9_woodies_patterns`/`v9_trades` של היום **לא ריקים** (לא שותק). הדבק setup עם entry/stop/T1‑מהסולם + day_type מאוכלס.
3. **שערי‑הסטופ חיים:** הדבק לוג‑דחייה ("degenerate stop" ל‑<2נק') והיעדר ניתוב של setup עם risk>60.
4. **אין רגרסיה:** `/health` <100ms · גשר local‑only 0 push errors (`/tmp/bridge.err.log`).

## ⛔ אסור
- **אל תדליק LIVE** (זה SHADOW; מעבר‑LIVE = gate נפרד + אישור Michael).
- Standing Decisions · §Polling Floors · bridge→localhost · sc_study ללא §7a · אל תסנתז.

## NOT‑DONE (חובה — נדחה במכוון)
- מוניטור‑חציית‑CCI ל‑T2/T3 (§1.6) — S4 T2/T3=None עדיין.
- trail מתקדם אחרי T1 — חי יש BE+1T בלבד (אין lock‑1R/trail; `gateway/trade_management.py` orphan).
- ניקוי‑dead‑code (stages/, gateway כפול, wrappers) — סבב נפרד.
- אי‑התאמת‑חותמות `v9_bars_5min` ↔ `v9_bars_5min_woodies` (~3ש') — המשך I‑18.
- max‑risk reject דוחה (לא מרחיב) — אם רוצים ש‑S2 Initiative/Bull‑Flag *יסחרו* עם סטופ‑מורחב במקום להידחות, זה תיקון נפרד ל‑`setup_wrapper`.

## עדכון בורדים (חובה)
עדכן `docs/plans/ROADMAP_TO_LIVE.html` + `docs/plans/STATUS_BOARD.md`: התיקונים נפרסו ל‑SHADOW + ה‑4 הוכחות, עם ממצא+פתרון+אימות פר‑שורה.
