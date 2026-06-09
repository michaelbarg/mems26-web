# CC PROMPT — D-094 R:R Fire Selection + Same-Bar Buffering (impl)

**תאריך:** 2026-05-31 · **מקור:** Cowork · **החלטה:** D-094 LOCKED (Michael 31/5)
**מצב:** SHADOW בלבד · שינוי routing (DEMO/LIVE slot fill) → **מאחורי flag default OFF** (flag-OFF = first-wins הקיים)
**סוג:** מימוש מבוקר. diagnose-first · smallest correct change · Rule 5 (פלט גולמי).

---

## הקשר + מה ננעל

GAP-3: ה-gateway ממלא slot DEMO/LIVE ב-**first-wins** (`trading_gateway.py:124-139`). Michael נעל מעבר ל-**בחירה לפי R:R**:
- **מדד = Option A · R:R טהור** (ה-R:R הגבוה זוכה; confidence **לא** בניקוד).
- **חלון = same-bar flush** (אוסף את כל המתמודדים בתוך בר 5-דק', בוחר ב-bar-close).
- **tie-break:** confidence גבוה → firing_system נמוך → arrival order.
- **SHADOW לא מושפע** — רושם כל setup מיד, ללא buffer/בחירה.

נוסחה (החוזים מתבטלים — הדירוג תלוי-מרחק בלבד, **אין** תלות ב-MES_POINT_VALUE):
```
R:R = Σ_i ( |target_i − entry| × split_pct_i ) / |entry − stop|
```
`split_pct_i` מ-`contract_split.get_contract_split(pattern) -> (t1_pct,t2_pct,t3_pct)`.

---

## משימה — מימוש מאחורי flag `RR_FIRE_SELECTION` (default OFF)

### D1. Diagnose-first — hook סגירת-בר
מצא איך ה-gateway יכול להיוודע על סגירת בר 5-דק' כדי לבצע flush. בדוק `backend/v9/services/bar_router.py` (קיים) + איך `five_min_system`/`woodies_system` מנויים. **אל תמציא hook** — אם אין אירוע bar-close נגיש ל-gateway, **עצור ודווח** עם הממצא והאפשרויות (למשל: ה-gateway נרשם כ-subscriber, או ה-bar_router קורא ל-callback). הדבק את הקוד הרלוונטי.

### D2. `compute_rr_score(setup) -> float`
פונקציה טהורה (utility נפרד, ~20 שורות). מחזירה R:R לפי הנוסחה. בדיקות יחידה: LONG/SHORT, split שונה (OFA 25/50/25 מול Flag 50/50/0), entry==stop → הגנה (אל תחלק ב-0).

### D3. Gateway buffering (flag ON)
- הוסף `self._slot_candidates: List[dict]` (DEMO/LIVE).
- ב-`route_setup`, **אחרי** 5 שערי הסיכון: SHADOW עדיין נרשם מיד (ללא שינוי). אם הדגל ON ו-DEMO/LIVE enabled → במקום למלא slot מיד, **הוסף ל-candidates** (לוג "buffered"), אל תמלא.
- ב-bar-close (D1): אם יש candidates ו-slot פנוי → `winner = max(candidates, key=R:R)` עם tie-break; מלא slot מה-winner; שאר ה-candidates → לוג **"outranked"** (לא "blocked"); נקה את ה-buffer.
- **flag OFF:** התנהגות זהה לחלוטין לקוד הקיים (first-wins, ללא buffer). זה ה-golden baseline.

### D4. שמירה על אינווריאנטות
- 5 שערי הסיכון (cooldown/SSV/chop/cluster/strict) רצים **לפני** ה-buffering — לא משתנים.
- cluster_guard עדיין חוסם DEMO/LIVE בלבד; SHADOW רושם.
- slot יחיד נשמר; winner ממלא, השאר לא.

### D5. Tests + golden
- **golden flag-OFF = identical:** הרץ את סוויטת ה-gateway הקיימת עם הדגל OFF → חייב לעבור ללא שינוי (הדבק פלט). `test_demo_first_wins`/`test_live_first_wins` עדיין ירוקים ב-OFF.
- flag-ON: טסט שמאמת (a) ה-R:R הגבוה זוכה ב-slot, (b) tie-break בסדר הנכון, (c) SHADOW נרשם לכל ה-candidates (לא מושפע), (d) losers="outranked".
- הדבק פלט pytest גולמי (0 failed).

---

## פלט מצופה
1. `docs/reports/D094_RR_SELECTION_IMPL_2026-05-31.md`: ממצא ה-bar-close hook (D1) · diff gateway · פלט golden flag-OFF identical · פלט טסטי flag-ON.
2. commit אחד (מאחורי flag OFF).
3. עדכון `STATUS_BOARD.md` שורת log (Rule 5).

**שערים:** אם אין bar-close hook נגיש → strategic-stop + דווח (D1) לפני שתבנה buffering. flag default OFF — אפס שינוי התנהגות בלי הדלקה מפורשת. SHADOW בלבד · אפס DEMO/LIVE/order. אל תיגע ב-Auth Table / MAX_CONTRACTS (thread נפרד).
