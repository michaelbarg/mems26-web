# cursor verify report — זיהום + S1-arch (2026-07-22 ~22:50 IL) · read-only · חוק-5

**מקור-משימה:** `CURSOR_VERIFY_CONTAM_AND_S1_ARCH_2026-07-22.md`  
**היקף:** אימות עצמאי; לא נסמך על cowork/cc; אפס-בנייה; לא נגעתי ברגרסיות של cc (cc רץ ALTER על `v9_trades` — נמנעתי מנעילות).

---

## טבלת-ממצאים

| # | טענה | פסק | ראיה |
|---|---|---|---|
| A1 | 12 זוגות +1h חיים היום ב-woodies | 🟢 CONFIRMED | SQL join זהה-OHLC `ts+1h`: **12** זוגות 17:05–18:00 → 18:05–19:00 IL |
| A2 | 12 זוגות +1h גם ב-`v9_bars_5min` | 🟢 CONFIRMED | **12** זוגות (חלון אחר: 20:10–21:05 → 21:10–22:05 IL) |
| A3 | VA היום = 3.5pt (לא-סביר) | 🟢 CONFIRMED | `v9_tpo_sessions` 2026-07-22: VAH **7561.75** / VAL **7558.25** → width **3.5**; ATR≈3.43 (רוחב-VA ≈ בר אחד) |
| A4 | שורש = קליטה (`_hour_shift_fix`) לא DLL | 🟢 CONFIRMED | ייצוא Sierra `woodies_5min.json`: **0** זוגות +1h פנימיים; לכל זוג-DB ה-OHLC מופיע ב-export לכל היותר 1×. לוג: `TS-HOUR-FIX applied: +3600s` עד **22:10:29** (5279 applied / 8304 skipped היום) |
| A5 | `WOODIES_TS_HOUR_FIX=0` כבר פותר בלייב | 🔵 SUSPECT / חלקי | בקוד+RULED default/expected **0** (P2). אבל applied עד 22:10 → תהליך-backend רץ עם ברירת-מחדל ישנה (ON) או בלי ריסטארט אחרי P2. **הזוגות עדיין ב-DB** — כיבוי הדגל לא מוחק רפאים |
| B1 | `day_type_at_fire` ריק בכל setups היום | 🟢 CONFIRMED | 8/8 setups (#526–#533): `day_type_at_fire=None` |
| B2 | S2 detection לא מקבל day-type בזיהוי | 🟢 CONFIRMED | `_detect_reactive(bars_5m)` — גאומטריה+נפח בלבד. `S2_DETECTION_LIVE_DAYTYPE_V1=0` ב-.env (G2 בנוי OFF) |
| B3 | כניסות היום לא בקצה-value נכון | 🔵 SUSPECT (VA מורעל) | עם VA=3.5pt כל מיקום "מתחת ל-VAL". מול IB הסביר (7556.25/7525): רוב הכניסות **mid_IB** / קרוב ל-IBH — לא fade בקצה-value דלטוני |
| C1 | סוג-פתיחה מזוהה היום | 🟢 CONFIRMED | `v9_day_type_state` + history: **OPEN_DRIVE**, day_type=Variation, dir=`with_extension(UP)` |
| C2 | סוג-פתיחה לא הניע ירי S2/S4 לייב | 🟢 CONFIRMED | `OPENING_ENTRY_V1=shadow`; gateway `shadow_only` → recorded not routed. `OPENING_TYPE_GATE`/`OPENING_WINDOW_FIRE` = מתיר/חוסם בלבד, לא טריגר-כניסה |
| D | ארכיטקטורת-יעד S1=מוח / S2+S4=זרועות | 📝 מתועד למטה | פער מול המצב החי — בנייה רק אחרי פסיקת-מייקל + ניקוי-זיהום |

---

## חלק א — הזיהום (פירוט)

**זוגות woodies (12):**
```
17:05→18:05 … 18:00→19:00  (OHLC זהים בייט-בייט)
```
**זוגות bars_5min (12):** חלון מאוחר יותר (20:10→22:05) — אותו מנגנון, stream נפרד.

**מנגנון:** `backend/v9/api/v9/bars.py::_hour_shift_fix` — כשהבר החדש ב-payload בן ~3600±120s, מוסיף +3600 לכל הברים → כתיבת-רפאים ב-ts+1h על גבי ברים אמיתיים ישנים יותר.  
לוג גולמי (דוגמה):  
`[woodies_5min] TS-HOUR-FIX applied: +3600s to 50 bars (newest was 3627s old, tol=120s)` @ 22:10:26

**הכרעת-שורש:** **קליטה (backend hour-fix)** — לא DLL. הייצוא נקי מכפילויות +1h.

**השלכות:** TPO VA=3.5pt = פרופיל על ברים מזוהמים/חלון שגוי. כל שער-מיקום שקורא VA הזה מקבל רמות-זבל.

**סדר-תיקון מומלץ (לא בוצע):**  
1) ודא backend רץ עם `WOODIES_TS_HOUR_FIX=0` (ריסטארט + בדיקת-לוג: 0 applied)  
2) מחק זוגות-רפאים (כמו ניקוי אתמול) אחרי גיבוי  
3) בנה מחדש TPO/VA מהברים הנקיים  
4) רק אז לחבר S1→S2/S4

---

## חלק ב — S2/S4 לא כפופות ל-S1 בזיהוי

| setup | pattern | dir | entry | day_type_at_fire |
|---|---|---|---|---|
| 526 | REACTIVE_SHORT | SHORT | 7530.00 | **None** |
| 527 | REACTIVE_LONG | LONG | 7552.25 | **None** |
| 528 | DOUBLE_BOTTOM_EE_LONG | LONG | 7555.50 | **None** |
| 529 | BEAR_FLAG_SHORT | SHORT | 7551.50 | **None** |
| 530 | REACTIVE_SHORT | SHORT | 7551.00 | **None** |
| 531 | REACTIVE_LONG | LONG | 7556.00 | **None** |
| 532 | REACTIVE_SHORT | SHORT | 7544.75 | **None** |
| 533 | REACTIVE_LONG | LONG | 7547.00 | **None** |

קוד: `_detect_reactive` מקבל רק `bars_5m`. day-type נכנס מאוחר (sizing / playbook / location_gate) — "לזהות בכל מקום ואז לפסול", לא "לזהות רק איפה שמותר".  
`S2_DETECTION_LIVE_DAYTYPE_V1=0` — G2/G3 בנויים ולא דלוקים.

---

## חלק ג — סוג-פתיחה מזוהה, לא מניע ירי

- מזוהה: **OPEN_DRIVE** (state + history 2026-07-22).
- Stance/פאנל: קיימים (DIRECTIONAL map).
- ירי לפי סוג-פתיחה: מודול `opening_entry.py` קיים, דגל **`OPENING_ENTRY_V1=shadow`** — הגייטוויי רושם ולא מנתב לייב/דמו.
- `OPENING_TYPE_GATE` / `OPENING_WINDOW_FIRE` = שערי-היתר/חסימה בחלון-פתיחה, **לא** מחוללי-כניסה.

**מסקנה:** הנקודה של מייקל מדויקת — S1 יודע *מה* הפתיחה, אבל לא מפעיל את הזרועות (S2/S4) לפיה בלייב.

---

## חלק ד — ארכיטקטורת-יעד (תיעוד בלבד)

```
                    ┌─────────────────────────────┐
                    │  S1 = מוח (הקשר יחיד)        │
                    │  day_type · opening_type     │
                    │  IB/VAH/VAL/POC · expansion  │
                    │  direction / stance          │
                    └─────────────┬───────────────┘
                                  │ context object (אחד)
                 ┌────────────────┼────────────────┐
                 ▼                                 ▼
        ┌─────────────────┐              ┌─────────────────┐
        │ S2 = זרוע       │              │ S4 = זרוע       │
        │ זיהוי רק אם     │              │ זיהוי רק אם     │
        │ מיקום+כיוון     │              │ מיקום+כיוון     │
        │ תואמים להקשר    │              │ תואמים להקשר    │
        └────────┬────────┘              └────────┬────────┘
                 └────────────┬───────────────────┘
                              ▼
                     Gateway (סיכון / OCO / S6)
```

**כללי-יעד (מייקל):**
1. S1 מספק אובייקט-הקשר יחיד — גם לפרונט וגם לזיהוי.
2. S2/S4 מקבלים אותו **בשלב-הזיהוי** (לא רק reject בסוף):  
   - fade רק בקצה המתאים לסוג-יום (אחרי probe)  
   - continuation עם-הכיוון באזור-פולבק  
   - בפתיחה: לפי `opening_type` (DRIVE→עם-הכיוון, REJECTION→היפוך, AUCTION→המתן/אין-edge)
3. **סדר-תלות קריטי:** ניקוי-זיהום → VA/IB כנים → cc סוגר רגרסיות → ואז בניית-חיווט S1→זרועות.  
   חיבור לפני ניקוי = S1 מוסר רמות-זבל לזרועות.

**פער נוכחי:** זיהוי עיוור למיקום/סוג-יום/פתיחה; שערים מאוחרים; opening-entry רק צל; מקורות-תצוגה/שער חלקים תוקנו (P0) אבל ההקשר לא זורם לזיהוי.

---

## המלצת-סדר למייקל (הכרעות-בנייה — לא בוצע)

1. **P0 עכשיו:** ריסטארט-backend עם `WOODIES_TS_HOUR_FIX=0` מאומת (לוג: 0× applied) + ניקוי 12+12 רפאים + rebuild TPO.  
2. **אחרי VA כנה:** הדלקת/אימות location_gate על רמות אמיתיות.  
3. **אחרי cc-green:** תכנון חיווט S1-context→S2/S4 detection (G2 + opening-driven arm) — פסיקה נפרדת; `OPENING_ENTRY` נשאר shadow עד הוכחה קדימה.  
4. **לא** להדליק `WOODIES_TS_HOUR_FIX=1` בלי אימות chartbook-TZ חי מחדש.

---

## פלט-גולמי מרכזי (חוק-5)

```
# pairs woodies = 12 (17:05→18:05 … 18:00→19:00)
# pairs bars_5min = 12 (20:10→21:10 … 21:05→22:05)
# TPO VA: VAH=7561.75 VAL=7558.25 width=3.5
# export woodies: 0 internal +1h twins
# day_type_at_fire empty: 8/8
# S2_DETECTION_LIVE_DAYTYPE_V1=0
# opening_type=OPEN_DRIVE / day_type=Variation
# OPENING_ENTRY_V1=shadow
# TS-HOUR-FIX applied last: 2026-07-22 22:10:29
```
