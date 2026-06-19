# CC Handoff — Trailing Runner אחרי T1 (`RUNNER_TRAIL_V1`, flag-gated default-OFF) · 2026-06-18

**מאשר:** Michael (2026-06-18) — "להרוויח יותר בעסקה" = לתת ל-runner לרוץ (לא להרחיב T1).
**מכין:** Cowork (אבחון + spec + backtest + אימות). **מבצע קוד:** CC.
**חוזה/דיסציפלינה (self-contained):** טסטים אנטי-טאוטולוגיים (RED-on-revert), סעיף **NOT-DONE** חובה, פקודה+פלט גולמי (Rule 5). זהו **trading-logic / risk-surface** → **flag-gated default-OFF + אישור-Michael נפרד לפני הדלקה ב-SHADOW**. אסור להדליק ב-.env בלי אישור. Standing Decisions נשארות OFF; לא לגעת ב-sc_study/bridge/market-data.

## הרקע (למה זה השינוי הנכון)
האבחון מצא: T1 נפגע 62% אך **T2 רק 13%** — הזוכות נחתכות בסקאלף וה-runner ננעל ב-BE (id159: stop-התחלתי 5.5pt → T1 → BE → +$23 בלבד). **שתי גרסאות הרחבת-T1 הפסידו** (flat −$144, struct −$624 — אל תיישם). **ה-trailing-runner הוא היחיד שיצא חיובי.**

**Backtest (Cowork, sim 6 ימים 06-09..16, מנוע-אמיתי, S4): live-BE מול trail = +$273 (BE +$279 → trail +$552, כמעט פי-2).** מודל ה-trail: אחרי T1, stop נגרר ל-`hwm − 1×risk`. ⚠️ caveat: 06-15 (יום-range) הזיק (−$112→−$313) — ה-trail נמרח ב-chop. נטו חיובי, אך ראה §refinement.

## הקוד הקיים (audit — KEEP/ADAPT/REPLACE)
- `manager.py::_apply_smart_be_after_t1` (L282) — **הליבה החיה**: ב-T1 מזיז stop ל-BE+1T, idempotent, never-widen, שומר `quality["initial_stop"]`. זה כל מה שקורה ל-runner היום (אין trail).
- `manager.py::_apply_stop_after_t2` (L339) — BE+0.5R ב-T2 (גודר RUNNER_TARGETS_V1). T2 נדיר.
- `bar_level_detector.py::on_bar` (L100) — **ה-driver הפר-בר**: stop-check ראשון (L102) ואז target-check. כאן ה-trail מתחבר (לפני ה-stop-check).
- `services/trail_engine.py` (830 שורות, 4-layer) — **orphan, לא להפעיל** (כבד/לא-נבדק; out of scope).
- `gateway/trade_management.py::apply_trailing_stop` — פונקציית-trail orphan, T2-gated, offset קבוע 2pt. **לא בשימוש** — לא לחווט (נשאיר; ה-trail שלנו פשוט וממוקד).

⇒ **NEW פשוט + ADAPT-נקודת-חיווט.** לא להפעיל את trail_engine.

## המימוש (flag `RUNNER_TRAIL_V1`, default OFF)

### 1. מתודה חדשה — `manager.py::apply_trail_after_t1(trade, bar_high, bar_low)`
מראה ל-`_apply_smart_be_after_t1`:
```python
# gated by caller; here pure logic
if trade.entry_price is None: return
initial = self._initial_stop(trade)              # pre-BE initial stop (L271)
if initial is None: return
entry = float(trade.entry_price); risk = abs(entry - initial)
if risk <= 0: return
k = <runner_trail.k_risk from config, default 1.0>
tick = MES_TICK_SIZE; d = (trade.direction or "").upper()
q = dict(trade.quality) if isinstance(trade.quality, dict) else {}
# high-water-mark since entry (persist in quality)
if d == "LONG":
    hwm = max(float(q.get("trail_hwm", entry)), float(bar_high)); q["trail_hwm"] = hwm
    trail = hwm - k * risk
    floor = entry + tick                         # never below BE+1T
    new_stop = max(trail, floor)
    if trade.stop is not None and new_stop <= float(trade.stop): trade.quality=q; return  # never widen
elif d == "SHORT":
    hwm = min(float(q.get("trail_hwm", entry)), float(bar_low)); q["trail_hwm"] = hwm
    trail = hwm + k * risk
    floor = entry - tick
    new_stop = min(trail, floor)
    if trade.stop is not None and new_stop >= float(trade.stop): trade.quality=q; return
else: return
trade.quality = q
# reuse the audit + log pattern of _apply_smart_be_after_t1
<set trade.stop = round(new_stop,2); append cross_context stop_move audit; self._log_management(trade.id,"TRAIL",{"from":...,"to":...,"hwm":hwm})>
```
**אסור-להרחיב + רצפת-BE+1T ⇒ ה-trail תמיד ≥ ההתנהגות הנוכחית** (שיפור או שווה, לעולם לא גרוע).

### 2. חיווט ב-`bar_level_detector.py::on_bar` — לפני ה-stop-check (L100, אחרי `stop = trade.stop` ב-L98)
```python
import os
if os.getenv("RUNNER_TRAIL_V1","0").lower() in ("1","true","yes") \
   and trade.t1_hit_ts is not None and trade.state != TradeState.CLOSED.value:
    try:
        self._tm.apply_trail_after_t1(trade, bar_high, bar_low)
        stop = trade.stop          # refresh so the stop-check below uses the trailed stop
    except Exception as _e:
        logger.warning("[BarLevelDetector] trail error (fail-safe skip): %s", _e)
```
fail-safe: שגיאה ב-trail לא תפיל את ה-on_bar (try/except, ה-stop נשאר כפי-שהוא). חל על **כל** עסקה פוסט-T1 (S2+S4 — ה-detector מנוי ל-5min+woodies).

### 3. קונפיג (Michael-tunable) — `config/stop_anchors.yaml`
```yaml
runner_trail:
  k_risk: 1.0            # trail = hwm − k×initial_risk (1.0 = הנבדק; כיול עתידי)
```

## טסטים (anti-tautological, `tests/v9/.../test_runner_trail.py`)
- **post-T1 LONG, מחיר עולה ל-hwm ואז נסוג:** flag ON → ה-stop נגרר ל-`hwm−risk` והיציאה ברווח **גבוה מ-BE**; flag OFF → יציאה ב-BE+1T. (הליבה.)
- **RED-on-revert (חובה):** לבטל את עדכון-ה-hwm (או להפוך את כיוון-ה-trail) → טענת ה"יציאה-ברווח" נכשלת. לצטט RED→GREEN.
- **never-widen:** סדרת ברים יורדת אחרי T1 → ה-stop לא זז אדוורסרית (נשאר ≥ BE+1T).
- **floor:** ה-trail לעולם לא מתחת ל-BE+1T.
- **flag OFF:** אין trail — אחרי T1 ה-stop נשאר BE+1T (כמו היום).
- **SHORT סימטרי.**

## אימות לפני הדלקה (gate)
1. טסטים ירוקים + RED-on-revert (raw).
2. `python -c "import backend.main"` OK.
3. **(אופ') Cowork ירחיב את ה-backtest** (כיול k_risk: 0.75/1.0/1.5; ובדיקת trend-conditional).
4. **SHADOW (אחרי אישור-Michael):** `RUNNER_TRAIL_V1=1` + restart → לאמת בלוג `TRADE_MANAGEMENT_LOG` שמופיעות שורות `TRAIL` על עסקאות פוסט-T1, ושה-T2-hit% עולה / היציאות-בפועל רחוקות מ-BE. מעקב מיוחד אחרי **ימי-range** (06-15 היה הסיכון).

## NOT-DONE / מחוץ-לסקופ (CC ימלא)
- אין הדלקת `.env` (אישור-Michael פר-דגל).
- **לא** מפעילים את `trail_engine.py` (orphan 4-layer) ולא את `gateway/trade_management.apply_trailing_stop` — מחוץ-לסקופ.
- **trend-conditional trail** (לגרור יותר בימי-trend, פחות/לא ב-range — לרכך את הפגיעה של 06-15) — refinement נפרד, לא בגרסה הזו.
- כיול `k_risk` סופי — אחרי backtest-sweep.
- I-34 (sizing=half), שער-המגמה — נפרדים.

## Rollout
commit flag-gated default-OFF + טסטים → backtest-confirm/כיול → **אישור-Michael** → SHADOW + restart → מעקב (דגש range-days) → DEMO/LIVE (gate נפרד). עדכון STATUS_BOARD + ROADMAP בכל שלב.
