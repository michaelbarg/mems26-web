# CC — 2 תיקונים: day_type endpoint/wrapper + choppiness gate · 2026-06-05

חוזה `CC_HANDOFF_CONTRACT.md` + `CC_VERIFICATION_PROTOCOL.md`. בסיום:
`docs/reports/VERIFY_ENDPOINT_CHOP_2026-06-05.md` עם raw output. smallest correct change.

**רקע מאומת (Cowork, חי+קוד):** day_type **מסווג נכון** (Normal, IB 7552.75/7505.75 מ-Sierra TPO,
`backend/main.py:405`). שני באגים נפרדים מסתירים/חוסמים את זה:

═══════════════════════════════════════
## FIX A · day_type — endpoint מטעה + dead-wrapper + propagation ל-Woodies
═══════════════════════════════════════
**הבעיה:**
1. `/api/v9/day_type/state` (`day_type/api.py:42` `get_state`) קורא `_get_engine()` עם BarInput-אפסים
   → instance טרי/מת → מחזיר `A1/UNKNOWN/bar_count=0`, בעוד ה-machine האמיתי
   (`app.state.day_type_machine`) מסווג Normal. **endpoint משקר.**
2. `wrappers.py` `DayTypeSystem` (subscribed `cumulative_delta`/`volume_profile`) = **dead path** —
   מקבל payloads בלי OHLC/IB → bars אפסים → תקוע A1. dead-wiring שמטעה.
3. **Woodies A4 עדיין `day_type:missing`** — ה-Normal מגיע ל-S2 (hydrate) אבל לא ל-Woodies A4.

**מה לעשות:**
- `get_state()` יקרא מ-**`app.state.day_type_machine`** (האמיתי) או מ-DB `v9_day_type_state`
  (כמו `_get_state_machine_classification`/`/history`) — לא מ-instance טרי.
- **הסר/נתב** את ה-dead-wrapper `DayTypeSystem` (או נתק את ה-subscription שלו) — אל תשאיר dead-wiring.
- **חבר את day_type ל-Woodies A4** — אותו מקור (DB/event) שמזין את S2.

**VERIFY A (raw):** `curl /api/v9/day_type/state` = **Normal** (זהה ל-`/v9/current`) · `curl woodies/current`
→ A4 `day_type=Normal` (לא missing) · grep שמראה שה-wrapper נותק.

═══════════════════════════════════════
## FIX B · choppiness_ok — חוסם 8/10 תבניות-S2 (I-16)
═══════════════════════════════════════
**הבעיה (אומת):** `five_min_system.py:832-836` מחשב `choppiness_score` **רק כש-mode=FIRST_HOUR_TACTICAL**.
אחרי המעבר ל-`DAY_TYPE_MODE` (אחרי שעה ראשונה) הוא **לא מתעדכן** → stale/missing. ה-gate
`s2_inspector.py:142-143` (`chop_ok = choppiness_score < 70`) חוסם 8/10 תבניות-S2
(REACTIVE/HNS/DOUBLE/FLAG) על `Missing: data.choppiness_ok` / ערך תקוע (Michael ראה `79 stale 1m`).

**מה לעשות (diagnose-first):**
- אבחן: מהו מקור-האמת ל-choppiness — `compute_choppiness(rth_bars)` (S2) או `layer0/chop_score`?
  (gateway מראה `chop_state=EXPANDING` — ייתכן פער-חיווט בין שני המקורות.)
- **תקן** כך ש-`choppiness_score` **מתעדכן רציף** (גם ב-DAY_TYPE_MODE), או שה-gate צורך מקור-חי
  (layer0) במקום השדה התקוע. **מקור-אחד, טרי.**
- ⚠️ זה gate שמשפיע על **ירי-S2** → ודא שהתיקון לא פותח/חוסם ירי בטעות; דווח מה הערך החדש ולמה.

**VERIFY B (raw):** `curl /api/v9/build_status/pattern-status` → `choppiness_ok` **fresh** (לא stale/missing)
ו-8 התבניות כבר לא חסומות עליו · הצג את הערך החי + מקורו · regression שמוכיח שעדכון רציף עובד
(stale→fresh). **אל תשנה את הסף 70 בלי Michael.**

═══════════════════════════════════════
## NOT-DONE
ציין כל מה שנשאר; כל פער Sierra↔backend; אם ה-choppiness מקור-כפול — דווח לפני איחוד.
