# CC Handoff — REACTIVE Location Gate (`REACTIVE_LOCATION_GATE`, flag-gated default-OFF) + Variation tightening · 2026-06-18

**מאשר:** Michael (2026-06-18) — "REACTIVE_LONG לא צריך להיכנס בקצה-העליון (VAH); שם רק SHORT" (ובסימטריה: SHORT לא בקצה-התחתון/VAL).
**מכין:** Cowork (אבחון + counterfactual + spec). **מבצע קוד:** CC.
**חוזה/דיסציפלינה (self-contained):** anti-tautological tests (RED-on-revert), סעיף **NOT-DONE** חובה, פקודה+פלט גולמי (Rule 5). trading-logic / risk-surface → **flag-gated default-OFF + אישור-Michael נפרד לפני SHADOW**. Standing Decisions נשארות OFF; לא לגעת ב-sc_study/bridge/market-data.

## הרקע + הראיה (counterfactual על ירי אמיתי)
REACTIVE = דהיית-קצוות value-area. במיקום שגוי זה "קונה לתוך התקרה / מוכר לתוך הרצפה". **אומת מול `cross_context` (VA בזמן-כניסה, כל עסקאות REACTIVE):**
- REACTIVE_LONG **מעל VAH = −$480 (0/2)**; כל הזון-העליון (POC→מעל-VAH) = **−$697 (2/9)**.
- REACTIVE_SHORT בזון-העליון (הנכון, ליד VAH) = +$32 (1/1); shorts במיקום-שגוי (מתחת-POC/VAL) = **−$694** (6W אך 2 הפסדים גדולים → נטו שלילי).
- חסימת ה-fade בצד-הלא-נכון ≈ **+$1,390** (אינדיקטיבי, hindsight על ירי אמיתי; REACTIVE היא S2 — לא ניתן לסים-ה-S4, ולכן זו הראיה).

נקודה: מיקום לבד לא מספיק — REACTIVE_LONG ליד VAL ביום-ירידה עדיין הפסיד (−$315) ⇒ מתחבר לשער-המגמה (REACTIVE = מיקום-נכון **וגם** עם-מגמה). זה כבר חי דרך `trend_direction_gate`.

## המימוש (flag `REACTIVE_LOCATION_GATE`, default OFF)
מודול חדש `backend/v9/systems/reactive_location_gate.py`, sibling ל-`trend_direction_gate.py` (fail-open, env-gated):
```python
# decide(pattern, direction, entry_price, poc) -> (allow: bool, reason: str)
# OFF / pattern not REACTIVE* / entry|poc None -> (True, ...)  # fail-open
# REACTIVE_LONG : block if entry_price > poc  (upper half — wrong side; long belongs near VAL)
# REACTIVE_SHORT: block if entry_price < poc  (lower half — wrong side; short belongs near VAH)
# else allow
```
החלוקה לפי **POC** (קו-האמצע של ה-value-area) — נתמך בנתונים (כל הזון-העליון ל-LONG מפסיד). עידון לבנדים VAH/VAL — דחוי (POC-divider קודם).

### חיווט ב-`trading_gateway.route_setup`
גוש חדש sibling לשער-המגמה (אחרי `TREND_DIRECTION_GATE`, לפני `cluster_guard`), במראה לו (try/except fail-open, env-gated, return עם `blocked_by`):
```python
if os.getenv("REACTIVE_LOCATION_GATE","0").lower() in ("1","true","yes"):
    try:
        from backend.v9.systems.reactive_location_gate import decide as _rl_decide
        _rl_g1 = extract_g1_entry_context(cross_context)
        _rl_tpo = (cross_context.get("tpo_system") if isinstance(cross_context, dict) else {}) or {}
        _allow, _reason = _rl_decide(resolve_pattern_id(setup, _rl_g1), direction, setup.get("entry_price"), _rl_tpo.get("poc"))
        if not _allow:
            result["blocked_by"] = "reactive_location"
            logger.info("[Gateway] BLOCKED by reactive-location gate: %s", _reason)
            return result
    except Exception as _rl_err:
        logger.warning("[Gateway] reactive-location gate errored (fail-open): %s", _rl_err)
```
**CC לאמת בזמן-החיווט:** ש-`cross_context["tpo_system"]` מ-`_capture_cross_context()` (system get_current()) אכן מכיל מפתח `poc` (וגם `vah`/`val` לעידון עתידי). אם המפתח שונה — להתאים. fail-open אם `poc` חסר.

### טסטים (`tests/v9/.../test_reactive_location_gate.py`, anti-tautological)
- REACTIVE_LONG entry>POC → **block**; entry≤POC → **allow**.
- REACTIVE_SHORT entry<POC → **block**; entry≥POC → **allow**.
- non-REACTIVE (TLB/ZLR/HFE) → allow (לא ממוקד). · poc=None → allow (fail-open). · flag OFF → allow.
- **RED-on-revert:** היפוך אופרטור-ההשוואה (`>`↔`<`) → טענות ה-block/allow מתהפכות → הטסט נכשל. raw RED→GREEN.
- gateway-level: setup REACTIVE_LONG עם `cross_context.tpo_system.poc < entry` + flag ON → `blocked_by=="reactive_location"`.

## חידוד Variation (נפרד — config, דורש אישור נפרד)
ימי-Variation הם רוב-הדימום (−$2,835); הקונפיג רופף שם. **הצעה (`config/daytype_playbook.yaml`):**
- `HFE.cells.Variation: REDUCED → SKIP` (HFE ב-Variation = −$2,260; היפוך בימי-Variation מפסיד).
- (אופ') לשקול `REACTIVE` — להישען על ה-location gate גם ב-Variation.
⚠️ זה **שינוי לקונפיג של שער-DAYTYPE_PLAYBOOK שכבר חי** (לא default-OFF) → משנה התנהגות-חיה ב-restart → **אישור-Michael מפורש + restart**, הפיך ע"י עריכה-חזרה. **לא לבצע יחד עם ה-flag השקט — פריט-אישור נפרד.**

## אימות + Rollout
1. טסטים ירוקים + RED-on-revert (raw). · `python -c "import backend.main"` OK.
2. (ה-counterfactual כבר מהווה את ה-backtest; REACTIVE לא בסים-S4.)
3. **SHADOW (אחרי אישור):** `REACTIVE_LOCATION_GATE=1` + restart → לאמת בלוג `[Gateway] BLOCKED by reactive-location` על REACTIVE_LONG בזון-עליון / REACTIVE_SHORT בזון-תחתון בלבד.
commit flag-gated default-OFF + טסטים → אישור-Michael → SHADOW → מעקב → DEMO. עדכון STATUS_BOARD + ROADMAP.

## NOT-DONE / מחוץ-לסקופ (CC ימלא)
- אין הדלקת `.env` (אישור פר-דגל).
- עידון בנדי-VAH/VAL (כרגע POC-divider) — דחוי.
- חידוד-Variation ב-YAML — **פריט-אישור נפרד** (לא לבצע בשקט).
- ניהול מותנה-יום (trail) = ה-spec הנפרד `CC_TRAILING_RUNNER_2026-06-18.md`.
- כל מפתח-cross_context שלא אומת — לצטט.
