# Short-ready check — האם CONT/INITIATIVE נתפסים כ-responsive? · 2026-07-20

**סוכן:** cursor · קריאה-בלבד · חוק-5 · `CURSOR_SHORT_READY_CHECK_2026-07-20.md`  
**⛔ אין PLACE / .env / ריסטארט.**

---

## מסקנה אחת

**(א) הכל-נכון** — לא over-block של CONT/INITIATIVE.

1. בלוק 13:15 = **REACTIVE responsive** ברצפה → חסימה לגיטימית.  
2. בדיקת-המיקום (VAH/VAL) חלה **רק** על `_RESPONSIVE_REV={REACTIVE,HNS}` — INITIATIVE/ZLR/TT/GB100 **לא** דורשים VAH.  
3. S4 עכשיו = `NO_SETUP` (לא מזוהה ZLR/TT/GB100) — אין מה לחסום בשער.  
4. פריצה מתחת ל-VAL: playbook **יֽאשר** INITIATIVE/ZLR SHORT עם-יום; כרגע הזיהוי לא משלים FIRE (INITIATIVE: `b1_exp` לרוב 0).

**אין תיקון family-aware נדרש** — הקוד כבר family-aware.

---

## 1) הבלוק 13:15 — איזו תבנית?

| שדה | ערך |
|-----|-----|
| pattern | **REACTIVE_SHORT** (לא INITIATIVE) |
| entry | 7503.0 |
| day_type בשער | **Variation** (מהסיבה) |
| blocked_by | `daytype_playbook` |
| סיבה מדויקת | `REACTIVE responsive SHORT not at VAH (below_value) on Variation` |

```text
$ curl -s "http://127.0.0.1:8000/api/v9/gateway/decisions?limit=50"
{"decisions":[{"ts":"2026-07-20T17:15:00+00:00","system":2,"pattern":"REACTIVE_SHORT",
 "direction":"SHORT","entry":7503.0,"blocked_by":"daytype_playbook","outcome":"blocked"}],
 "today":{"fired":0,"blocked":1,"by_gate":{"daytype_playbook":1}}}

$ rg "2026-07-20 20:15:00" /tmp/backend.err.log | rg "FIRE|T1Setup|BLOCKED"
[FiveMin] FIRE: REACTIVE SHORT (conf=0.80, … loc=far)
[S2] T1Setup emitted: REACTIVE_SHORT SHORT entry=7503.00 …
[Gateway] BLOCKED by day-type playbook: REACTIVE responsive SHORT not at VAH (below_value) on Variation
```

**מסקנה:** REACTIVE-responsive על הרצפה → **נכון לחסום**. לא INITIATIVE.

---

## 2) האם location-check מבדיל REV מ-CONT/INITIATIVE?

קוד (`daytype_playbook.py`):

- `_RESPONSIVE_REV = {REACTIVE, HNS}` בלבד → ענף מיקום VAH/VAL.  
- `INITIATIVE` / `ZLR` / `TT` / `GB100`: **אין** `require_with_trend` ב-YAML → בכלל לא נכנסים לבלוק; תא Variation = FULL/REDUCED.  
- `CONFLUENCE_RI_ZLR`: יש `require_with_trend` אבל בענף **day_direction** (לא מיקום).  
- `DAYTYPE_LOCATION_GATE=0` (RULED) — לא חוסם CONT בחי.

### פרוב production (entry=7503, Variation, day_dir=DOWN)

```text
zone_of(7503) = near_val
_RESPONSIVE_REV = frozenset({'REACTIVE', 'HNS'})

require_with_trend: REACTIVE/HNS=True · INITIATIVE/ZLR/TT/GB100/FLAGS=None · CONFLUENCE=True

decide():
  REACTIVE          → SKIP  | responsive SHORT not at VAH (near_val)
  HNS               → SKIP  | same
  INITIATIVE        → FULL  | INITIATIVE FULL on Variation
  ZLR               → FULL  | ZLR FULL on Variation
  TT / GB100        → REDUCED (תא YAML, לא מיקום)
  TLB / FLAGS       → FULL
  CONFLUENCE_RI_ZLR → FULL  | with day_dir=DOWN (לא VAH)
```

חוזה הטסט `allow_responsive_fade` ("with-day continuation always allowed") — **מיושם**: CONT/INITIATIVE לא עוברים את ענף-המיקום של REACTIVE.

**מסקנה:** לא (ב) over-block. Family-aware כבר קיים.

---

## 3) S4 ZLR/TT/GB100 עכשיו (price≈VAL, RED)?

| שדה | ערך חי (~13:37 ET) |
|-----|---------------------|
| price | **7504.25** |
| VAL / VAH | **7505.5 / 7528.0** (מעט מתחת ל-VAL) |
| trend_state | **RED** |
| classification | **NO_SETUP** |
| active_patterns | `[]` |
| ready_to_route | false |
| A1/A3 | `no patterns` / `no patterns this bar` |
| gateway decisions מאז restart | **אין** system=4 |

אות אחרון ב-`/woodies/signals`: ZLR SHORT ב-**12:51 ET** (לפני ריסטארט 13:01) — לא אחרי ההדלקה.

```text
woodies/current: trend=RED cci_14=-55 classification=NO_SETUP ready_to_route=False
woodies/patterns: {"patterns":[],"classification":"NO_SETUP"}
```

**מסקנה:** S4 **לא מזהה** setup עכשיו → לא "נחסם בשער"; פשוט אין תבנית.

---

## 4) פריצה מתחת ל-VAL → שורט-המשך צריך לירות?

- **Playbook:** INITIATIVE/ZLR SHORT @7503 על Variation = **FULL** (סעיף 2) — מוכן מבחינת השער.  
- **Detection S2 INITIATIVE (לוג אחרי restart):** סריקות רבות עם `b1_exp=0` (חסר בר-הרחבה) → **אין** `FIRE: INITIATIVE` / אין `T1Setup INITIATIVE` מאז 13:01.  
- **S4:** NO_SETUP (סעיף 3).  
- rth_low היום **7499** — כבר היה מתחת ל-VAL; אין כרגע setup-המשך מוכן לירי.

**מסקנה:** השער לא חוסם המשך; **הזיהוי לא משלים** תבנית-המשך כרגע.

---

## טבלת-סיכום למייקל

| שאלה | תשובה |
|------|--------|
| 13:15 מה נחסם? | REACTIVE-responsive @below_value — **נכון** |
| CONT/INITIATIVE נתפסים כ-responsive? | **לא** |
| S4 שורט עכשיו? | לא מזוהה (NO_SETUP) |
| צריך תיקון family-aware? | **לא** |

אם מייקל רוצה שורט-המשך עכשיו: לחכות ל-INITIATIVE/ZLR שיעבור את גאומטריית-הזיהוי (לא לכבות את דגל-המיקום של REACTIVE).
