# CC — חיווט Stop-Anchor V2 ל-14 התבניות (אחת-אחת, flag-gated)

Cowork בנה את היסוד הבדוק (committed): `config/stop_anchors.yaml` (SPEC מאושר
Michael) · `backend/v9/config_loader.py::load_stop_anchors()` · resolver
`backend/v9/systems/stop_anchors/resolver.py` · מנוע-S4
`woodies/atr_stop.py::compute_stop_v2`. 31 טסטים ירוקים, **דגל כבוי = אפס שינוי**.
המשימה שלך: לחבר את 14 נקודות-הקריאה — **אחת-אחת**, עם טסט לכל אחת, הדגל נשאר
**OFF** עד שכל ה-14 מחוברות ואומתו.

## חוקי-ברזל (CLAUDE.md)
- **חיווט מלא, לא חלקי.** כל החלטה ב-SPEC מגיעה לכל ענף מושפע. אסור להמציא מספרים —
  כולם ב-`stop_anchors.yaml`. אם חסר משהו — עצור ושאל את Michael, אל תמלא חור.
- **`STOP_ANCHORS_V2` OFF = התנהגות-היום בדיוק.** כל commit חייב לכלול טסט-רגרסיה
  שמוכיח זאת (כמו `test_legacy_compute_stop_unchanged`).
- **קרא את הקוד הקיים של כל פטרן לפני שינוי** — איך הוא מחשב עוגן היום. אל תשנה מהזיכרון.
- **Rule 5:** לכל תבנית — הדבק `pytest` גולמי ירוק לקובץ
  `docs/reports/STOP_ANCHORS_WIRING_2026-06-08.txt`.

## דפוס-החיווט (זהה לכל פטרן)
בכל נקודת-קריאה שהיום קוראת ל-stop (legacy):
```python
from backend.v9.shared.atr import flag
if flag("STOP_ANCHORS_V2"):
    from backend.v9.config_loader import load_stop_anchors
    from backend.v9.systems.stop_anchors import resolver as SA
    cfg = load_stop_anchors()
    if cfg:  # fallback: cfg None -> legacy path (אל תשבור)
        a = cfg["anchors"][PATTERN_KEY]          # type + window
        window_bars = _select_window(bars, a["type"], a["window"])  # פר-type
        struct = SA.resolve_anchor_from_window(window_bars, direction,
                                               cfg["principles"]["anchor_offset_ticks"])
        # S4: compute_stop_v2(...)  ·  S2: <ה-V2 שתבנה ל-adaptive_stop>
        ...  # T1 = SA.t1_price(...) · contracts = SA.final_contracts(...)
# else: הקוד הקיים בדיוק כמו היום
```
מיפוי `type → בחירת-חלון` (מ-`ANCHOR_RESEARCH_ALL_PATTERNS_2026-06-07.md`):
`cluster_low`=N הברים האחרונים · `since_trendline_peak`=מאז הפסגה (3-8) ·
`zl_excursion`=ברי האקסקורסיה (4-9) · `swing_extreme`/`shoulder`/`failed_bar`/
`extreme_bar`/`breakout_bar`/`second_bottom_top`/`flag_low`/`consolidation_extreme`=
המחיר-המבני שהפטרן כבר מזהה (אל תמציא — קרא מהקוד מאיפה הפטרן יודע אותו).

## סדר העבודה (אחת-אחת; commit+טסט פר-תבנית)
**שלב 0 — מנוע S2:** בנה `adaptive_stop.compute_stop_v2` אנלוגי ל-S4 (סטופ-מבני
קובע, ATR=שער-גודל, רצפה 4T) + טסט + הוכחת legacy-unchanged.
**שלב 1 — S4 CONT:** ZLR(cluster 4) · TLB(since-peak 3-8) · TT(zl-exc 4-9) · GB100(cluster 6).
**שלב 2 — S4 REV:** VEGAS · GHOST · FAMIR · HTLB(consolidation) · HFE(ladder_shift -1).
**שלב 3 — S2:** Reactive · OFA_Initiative(⚠️ breakout_bar הדוק, **לא** cluster) · Double_BT · HnS · Flag(⚠️ flag_low, **לא** מוט).
**שלב 4 — גדלים+T1+monitor:** נתיב-הגדלים = `SA.final_contracts(risk, ladder, auth, mode_cap)`
(מסווג-מצב מ-`trend_state`+auth+VA, ראה `resolver.classify_mode`). T1 מ-`SA.t1_price`.
monitor כבר מטפל ב-t1/t2/t3 — ודא שהוא מקבל את הערכים החדשים (כמו תיקון-T3).
**שלב 5 — end-to-end:** טסט פר-תבנית שמזרים בר→setup→trade ומוכיח שהמחיר מגיע
מה-YAML עד ל-trade.t1/stop/contracts. **רק אז** — הדלק `STOP_ANCHORS_V2=1` ב-SHADOW.

## בדיקת-שפיות חובה אחרי כל תבנית (הדבק פלט גולמי)
```bash
# 1. כל הטסטים ירוקים — שום דבר קיים לא נשבר
pytest tests/ -q 2>&1 | tail -5
# 2. הדגל עדיין כבוי (חיווט-חלקי אסור לרוץ חי)
ps eww $(pgrep -f "uvicorn backend.main"|head -1) | tr ' ' '\n' | grep STOP_ANCHORS || echo "STOP_ANCHORS_V2 OFF (תקין)"
# 3. מה בדיוק השתנה
git log --oneline -3 && git show --stat HEAD | head -20
```
אם (1) לא ירוק או (2) הדגל דלוק לפני שכל ה-14 מחוברות — **עצור מיד ודווח**.
כתוב הכל ל-`docs/reports/STOP_ANCHORS_WIRING_2026-06-08.txt` (Cowork קורא ומצליב).

## NOT-DONE / עצור-ושאל
- אם פטרן לא חושף מאיפה העוגן-המבני שלו (REV/structure) — עצור, דווח ל-Michael,
  אל תמציא חלון.
- אל תדליק את הדגל לפני ששלב 5 ירוק לכל 14. דגל-ON עם חיווט-חלקי = תקרית-5-הדגלים.
- כל תבנית: commit נפרד, paths מפורשים (לא `git add -A` — ~270 untracked docs).
- Cowork מצליב כל תבנית מול `MEMS26_MASTER_TRADE_SPEC_ONE_TABLE.xlsx` + ה-SPEC.
