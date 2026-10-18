# OPEN_PARITY 2026-10-18 — T-588 פריט 1, **חצי-הלייב בלבד** (חלקי במוצהר)

**נמדד:** cowork-dev, ריצה 327, 18.10 23:05→23:20 IL (יום ראשון, שוק סגור, אפס עסקאות).
**הזמנה:** `docs/handoff/cc_orders/CC_ORDER_2026-10-18_OPEN_PARITY.md` · **בעלים:** Cursor / fix-agent.
**מצב:** פריט 1 **חצי** — צד-הלייב של הטבלה נמדד במלואו ונסגר; **צד-הריפליי NOT-DONE**, הסיבה
מדודה ולא משוערת (§4). פריטים 3/4/5 לא נפתחו. פריט 2 נסגר כבר ב-10:59 בקומיט `39f7f1c8`.

⚠️ **הקובץ הזה אינו "ההזמנה בוצעה".** מי שמרים את ההזמנה: §4 אומר מה חסר ומה לבדוק לפני.

---

## 1 · צד-הלייב — הפלט הגולמי (Rule 5)

```bash
awk '$1=="2026-10-06" && $2>="16:25:00" && $2<="17:15:00"' /tmp/backend.err.log \
 | grep -E "TREE_V3|\[DayType\]|locked opening|opening_type=|OpeningDetector"
```
```raw
16:30:05 [gateway.trading_gateway] TREE_V3 FAMIR LONG 7863.5 → SKIP [hour=*(16)/opening_type=OPEN_AUCTION_IN/phase=A/day_type=*(Trend_Normal)]
16:30:06 [day_type.state_machine] FIX-9 RTH-boundary reset: dropping carried pre-RTH state (day_type=UNKNOWN, bars=66) — fresh session, stages decide
16:40:07 [gateway.trading_gateway] TREE_V3 CEILING_FLIP_TOUCH2 LONG 7865.25 → SKIP [hour=*(16)/opening_type=OPEN_AUCTION_IN/phase=A/day_type=*(Variation)]
16:45:07 [gateway.trading_gateway] TREE_V3 OPENING_EXTREME_REJECT LONG 7867.5 → TAKE [hour=*(16)/opening_type=OPEN_AUCTION_IN/phase=B/day_type=*(Variation)/kind=REVERSAL]
16:50:03 [gateway.trading_gateway] TREE_V3 OPENING_DRIVE LONG 7871.5 → SKIP [hour=*(16)/opening_type=OPEN_AUCTION_IN/phase=B/day_type=*(Variation)/kind=*(WITH_DRIVE)/edge=*(none)]
17:00:06 [mems26] [DayType] Classification changed: UNKNOWN -> Trend_Normal (conf=0.35)
17:05:03 [gateway.trading_gateway] TREE_V3 INITIATIVE_LONG LONG 7881.0 → SKIP [hour=*(17)/opening_type=OPEN_AUCTION_IN/phase=B/day_type=*(Variation)/kind=*(BREAK)/edge=*(none)]
```

**זמינות-הראיה (נבדקה, לא הונחה):** `/tmp/backend.err.log` = 90,530,909 בתים, מחזיק
`2026-10-02` והלאה, מהם **67,563 שורות של 06.10** ⇒ חלון-הפתיחה של 06.10 מדיד **מהלוג החי**,
לא מציטוט ההזמנה. 528 שורות `TREE_V3` בלוג כולו.

## 2 · הטבלה — מה שמדיד היום

| פוש | מועמד-העץ | ot-לייב | day_type-לייב | החלטת-לייב | ot-ריפליי | day_type-ריפליי |
|---|---|---|---|---|---|---|
| 16:30:05 | FAMIR LONG | `OPEN_AUCTION_IN` | `Trend_Normal` | SKIP | — NOT-DONE | — NOT-DONE |
| 16:40:07 | CEILING_FLIP_TOUCH2 | `OPEN_AUCTION_IN` | `Variation` | SKIP | `UNKNOWN`\* | `FORMING`\* |
| 16:45:07 | OPENING_EXTREME_REJECT | `OPEN_AUCTION_IN` | `Variation` | **TAKE** | — NOT-DONE | — NOT-DONE |
| 16:50:03 | OPENING_DRIVE LONG | `OPEN_AUCTION_IN` | `Variation` | SKIP | `OPEN_REJECTION_REVERSE`\* | `FORMING`\* |
| 17:05:03 | INITIATIVE_LONG | `OPEN_AUCTION_IN` | `Variation` | SKIP | — NOT-DONE | — NOT-DONE |

\* שתי שורות-הריפליי היחידות שיש — **מצוטטות מההזמנה**, לא נמדדו בריצה הזו. אסור לקרוא
לטבלה "מאומתת דו-צדדית" לפני §4.

## 3 · שני ממצאים שההזמנה לא רשמה

**(א) הלייב לא סירב לכל חלון-הפתיחה — ב-16:45:07 הוא לקח.** `OPENING_EXTREME_REJECT LONG
7867.5 → TAKE [kind=REVERSAL]`. ההזמנה מנסחת "הריפליי לוקח, הלייב מסרב"; זה נכון
ל-`OPENING_DRIVE` ב-16:50, **לא** לחלון כולו. ⇒ `OPEN_AUCTION_IN` + `Variation` אינם
חוסמים-כשלעצמם: אותו צמד-תוויות בדיוק ייצר TAKE אחד ו-SKIP ארבעה, וההבדל הוא ב-`kind`
(`REVERSAL` עבר · `WITH_DRIVE`/`BREAK` + `edge=none` נפלו). מי שמייחס את ההחמצה לתווית-היום
לבדה — מייחס לשדה הלא-נכון.

**(ב) הפער בין שני מקורות-התווית אינו נסגר אחרי שהמכונה מסווגת.** ההזמנה כתבה
"16:40–17:05 Variation בגייטוויי בעוד המכונה UNKNOWN עד 17:00". המדידה מחדדת: ב-`17:00:06`
המכונה עברה ל-`Trend_Normal`, ובכל זאת ב-`17:05:03` — **חמש דקות אחרי** — הגייטוויי עוד
מדווח `day_type=*(Variation)`. כלומר זה **לא** "המכונה עוד לא מוכנה" אלא מקור שונה שאינו
מתכנס גם כשיש למכונה תווית. זה מחזק את פריט 3 ומצמצם אותו (§4).

## 4 · מה חסר, ולמה — NOT-DONE מפורש

**חצי-הריפליי של פריט 1 לא בוצע. הסיבה מדודה:** הפריט דורש (א) הוספת לוג-INFO של
`_cls_result` ל-`s1_on_bar`, שקיים **רק** ב-`scripts/fwd_harness.py:790`, ו-(ב) הרצת
`fwd_harness.py --session 2026-10-06`. שני המשטחים **תפוסים בסשן אחר, בזמן-אמת**:

```raw
23:13:27  49229?  —  ps: 46909 00:19 74.9% fwd_harness.py --session 2023-05-08 --variant hist_k --out harness_out/t466
                      47021 00:13 69.9% fwd_harness.py --session 2023-05-11 --variant hist_k --out harness_out/t466
23:14:56  ps:      49229 00:21 24.0% fwd_harness.py --session 2023-05-08 --variant hist_k --out harness_out/t466
                   49468 00:11 72.6% fwd_harness.py --session 2023-05-11 --variant hist_k --out harness_out/t466
⇒ שני עובדים במקביל, ה-PID מתחלפים כל ~20-30 שנ' ⇒ סריקה רצה, לא ריצה בודדת
git log -1 -- scripts/fwd_harness.py ⇒ 3e1a9b40 10-18 19:52 "T-597: harness crashed on 2026-08-07…"
```

1. **עריכת `fwd_harness.py` הייתה נבלעת בסריקה החיה.** כל עובד חדש נטען מהקובץ שעל הדיסק;
   הוספת לוג באמצע סריקה משנה בשתיקה את הפלט של סוכן אחר על מאות סשנים. הקובץ גם נמצא
   בבעלות-עריכה טרייה של אותו סשן (`19:52` היום).
2. **`harness_out/t466/` הוא גם יעד-הכתיבה של הסריקה** — ובדיוק הספרייה שההזמנה קוראת ממנה
   (`t567ref_2026-10-06.json`). הרצה שלישית לתוכה = התנגשות-פלט.
3. **המכונה בלחץ-זיכרון:** `unused RAM 121M < 400M` · `swap used 2,962M/4,096M` · load
   `6.08 6.57 6.36` על 8 ליבות, בעוד שני העובדים ב-~75% CPU כל אחד.

**זה הכלל-של-תור-הלילה לפי רוחו, לא לפי אותיותיו:** המבחן הפורמלי ("קומיט לא-launchd מ-23:00+
או שורת-claim") החזיר **פנוי** — הקומיט היחיד מ-23:00 הוא `4b40a9ef 23:05:22 eod-handoff`,
שהוא launchd+data-only, ואין שורת-claim. אבל ההתנגשות שהכלל נועד למנוע **נמדדה ישירות
ב-`ps`**. ⇒ לא נלקחה בעלות ולא נפתח סוכן-משנה. ⚠️ **מלכודת 38** נרשמה ב-`COWORK_DAILY_READ`.

**הצעד-הבא לבעלים (Cursor/fix-agent), בסדר הזה:**
1. `ps -eo pid,command | grep fwd_harness` ⇒ **אפס** לפני כל נגיעה בקובץ או ב-`harness_out/t466/`.
2. לוג-INFO ב-`s1_on_bar` (`fwd_harness.py:790`): `opening_type` · `day_type` · `session_date`
   לכל פוש, ואז `--session 2026-10-06` (+ `--restart-at 15:40` לשחזור הציטוט) ⇒ למלא את
   חמש שורות-ה-NOT-DONE בטבלה §2.
3. פריט 3 מצומצם לשאלה אחת: `_dp_dt_raw = _dp_gldt()` ⇒ `get_live_day_type()`
   (`backend/v9/services/trade_context.py:565`) — **מה הוא החזיר ב-16:40 וב-17:05 ב-06.10**,
   כשהמכונה הייתה `UNKNOWN` ואז `Trend_Normal`? ההיסטרזיס `_dp_hyst`
   (`trading_gateway.py` ~1130-1156, "hold Trend") הוא מועמד-מכניזם ל-17:05 אך **לא נמדד**,
   והערך-הגולמי אינו בלוג ⇒ לא מיוחס (כלל 1).

## 5 · ציר-הקוד — אומת ב-HEAD, קריאה-בלבד

```raw
backend/v9/gateway/trading_gateway.py
  210  def _resolve_live_cls()                       ← מקור 1: app.state.last_cls_result
  226      return _cls_session_guard(_r)              ← T-588 פריט 2, קיים ב-HEAD
  231  def _cls_session_guard(result, today_iso)      ← טהור; session_date ≠ היום-ET ⇒ None
  234      os.getenv("CLS_RESULT_SESSION_GUARD_V1","0") not in ("1","true","yes") ⇒ מחזיר כמו-שהוא
 ~1160  _dp_ot = "UNKNOWN"                            ← ברירת-מחדל
 ~1167  if _opening_type_locked: _dp_ot = _opening_locked_val    ← T-314, מקור מועדף
  1177  _dp_cls_ot = _resolve_live_cls()              ← הנפילה-אחורה שאכלה את 06.10
```

**שרשרת-השורש, שלושה משטחים בלתי-תלויים:**

| משטח | מדידה |
|---|---|
| ספירת-נעילה | `grep -c "locked opening"` ⇒ 06.10 = **0** · 08.10 = **1** · 09.10 = **1** |
| לוג-הגייטוויי | `opening_type=OPEN_AUCTION_IN` בכל חמשת הפושים של 06.10 |
| סדר-הקוד | ‏`1160` ברירת-מחדל → `1167` נעילה (לא קרתה) → `1177` `last_cls_result` הישן |

⇒ בלי נעילת-T-314, `_dp_ot` נופל למקור 1, ושם — לפני `39f7f1c8` — שכנה התוצאה של **05.10**
בלי בדיקת `session_date`. הדגל `CLS_RESULT_SESSION_GUARD_V1` **כבוי כברירת-מחדל** (`"0"`)
⇒ ההתנהנות זהה-בייט. **אפס הדלקה בריצה הזו** (פסיקה היא של מייקל).

## 6 · אפס-נגיעה

ריסטארט · דגלים · דגלי-גודל · `.env` · פוזיציות · פקודות · `op=EXIT` · קוד-פרודקשן · DLL ·
סיירה · עץ-ההחלטות · כתיבות-DB · `fwd_harness.py` · `harness_out/` · הטלפון.
`ruled_contracts() = 1` נקרא לדיווח בלבד. 14 הקבצים-המלוכלכים של הסשן האחר לא נוגעו —
הועלו לאינדקס המסמכים שלי בלבד, תוספות בלבד.

---

## 7 · ציר-הקוד של **פריט 3** — מה מייצר את התווית, ומה באמת אומר `*( )` (ריצה 328, 18.10 23:3x, קריאה-בלבד)

הצעד-הבא של ריצה 327 היה "שאלה אחת ב-`trade_context.py:565`". הוא נענה, ובדרך **נמצאה
טעות-קריאה בהזמנה עצמה**. אפס הרנס, אפס DB, אפס עריכת-קוד — רק קריאת-קוד ב-HEAD.

### 7.1 · `*(value)` אינו הדגשה ואינו חלק מהתווית — זו כוכבית-**תת-כיסוי של העץ**

`backend/v9/services/decision_tree.py:160-168`, גולמי:
```python
        for key, child in branches.items():
            if key == "*":
                continue
            if _match(str(key), value):
                chosen, key_taken = child, str(key); break
        if chosen is None and "*" in branches:
            chosen, key_taken = branches["*"], "*"
        if chosen is None:
            return {"leaf": "SKIP", ... f"no branch for {feat}={value}"}, path
        path.append((feat, value if key_taken != "*" else f"*({value})"))
```

⇒ `day_type=*(Variation)` פירושו: **לעץ אין ענף ספציפי ל-`Variation` בצומת הזה, והוא לקח
את ה-wildcard `*`**. הערך בסוגריים הוא הערך **הנצפה האמיתי** — ולכן ממצא-ההתיישנות של
פריטים 1-2 **שורד במלואו** (`Trend_Normal` ב-16:30:05 אכן היה התווית של 05.10). אבל
הכוכבית היא עובדה על **כיסוי-העץ**, לא על דיוק-התווית, ובהזמנה היא נקראה כאילו היא חלק
מהתווית (`hour=*(16)`, `kind=*(WITH_DRIVE)`, `edge=*(none)` — כולם מכוכבים באותה שורה).

**נגזרת מעשית לפריט 3:** ההצעה "שהעץ יראה `FORMING` עד נעילת-IB" **לא תשנה דבר בצמתים
האלה** — הם ממילא לקחו `*`. המקום היחיד שבו דיוק-התווית מזיז התנהגות הוא ענף יום-ספציפי
(**לא** מכוכב). לכן פריט 3 צריך קודם לספור אילו צמתים בעץ 3.4.0 מכוכבים על `day_type` —
וזו מדידה על ה-YAML, בלי הרנס.

### 7.2 · נשא **שני** לתווית-אתמול, שההזמנה אינה רושמת: `self._dp_hyst`

`backend/v9/gateway/trading_gateway.py:1129-1155`, גולמי:
```python
                from backend.v9.services.trade_context import get_live_day_type as _dp_gldt
                _dp_dt_raw = _dp_gldt() or ""
                if not hasattr(self, "_dp_hyst"):
                    self._dp_hyst = {"label": None, "bars": 0}
                _dp_is_trend = _dp_dt_raw.startswith("Trend") if _dp_dt_raw else False
                _dp_was_trend = (self._dp_hyst["label"] or "").startswith("Trend")
                if _dp_is_trend and not _dp_was_trend:
                    self._dp_hyst = {"label": _dp_dt_raw, "bars": 0}; _dp_dt = _dp_dt_raw
                elif not _dp_is_trend and _dp_was_trend:
                    if _dp_dt_raw == self._dp_hyst.get("pending_label"):
                        self._dp_hyst["bars"] += 1
                    else:
                        self._dp_hyst["pending_label"] = _dp_dt_raw; self._dp_hyst["bars"] = 1
                    if self._dp_hyst["bars"] >= 2:
                        self._dp_hyst = {"label": _dp_dt_raw, "bars": 0}; _dp_dt = _dp_dt_raw
                    else:
                        _dp_dt = self._dp_hyst["label"]  # hold Trend
                else:
                    self._dp_hyst["label"] = _dp_dt_raw; _dp_dt = _dp_dt_raw
```

`self._dp_hyst` הוא **מצב-מופע של הגייטוויי**, מאותחל פעם אחת (`if not hasattr`) ו**לעולם
לא מאופס בגבול-ה-RTH** — בשונה מהמכונה, שכן מתאפסת (`16:30:06 FIX-9 RTH-boundary reset`).
לכן: אם `_dp_hyst["label"] == "Trend_Normal"` מ-05.10 ו-`_dp_dt_raw == ""` (המכונה UNKNOWN
אחרי האיפוס) ⇒ `_dp_is_trend=False`, `_dp_was_trend=True` ⇒ ענף `Trend→other` ⇒ `bars=1 < 2`
⇒ **`_dp_dt = self._dp_hyst["label"]` = התווית של אתמול, מוחזקת**.

**הקרי מגודר ל-2 ברים בדיוק:** `_dp_dt_raw` נשאר `""` בכל בר, ולכן בבר הבא
`_dp_dt_raw == pending_label` ⇒ `bars=2` ⇒ שחרור. זה **בדיוק** חלון 16:30→16:40 הנצפה.

**המשמעות לפריט 2 — "שורש אחד, תיקון אחד" אינו שלם:** `CLS_RESULT_SESSION_GUARD_V1`
מגדר את `_resolve_live_cls()` בלבד, שמזין את **`_dp_ot`** (סוג-פתיחה). `_dp_dt` **אינו עובר
דרך `_resolve_live_cls()` כלל** — הוא בא מ-`get_live_day_type()` + `_dp_hyst`. ⇒ הדגל יתקן
את סוג-הפתיחה ו**ישאיר את תווית-היום הישנה פתוחה**. שני נשאים, לא אחד.

### 7.3 · מה **לא** יוחס (Rule 1): מקור ה-`Variation` ב-16:40–17:05

`trade_context.py:565-572` (docstring גולמי): *"Returns the mapped day_type string (e.g.
"Trend_Normal", "Variation") **or None if unavailable/UNKNOWN/FORMING**. Gated by
DAYTYPE_GATE_LIVE_V1 flag; returns None when OFF."*

⇒ שני המשטחים שההזמנה מונה **אינם יכולים** לייצר `Variation` כשהמכונה UNKNOWN:
1. `get_live_day_type()` מחזיר `None` על UNKNOWN/FORMING ⇒ `_dp_dt_raw = ""`.
2. `_dp_hyst` **מחזיק רק תווית שמתחילה ב-"Trend"** (ענף-ההחזקה דורש `_dp_was_trend`);
   `"Variation"` אינו כזה, ולכן הוא נופל לענף האחרון ⇒ `_dp_dt = _dp_dt_raw = ""`.

⇒ קיים **מקור שלישי**, ואין לו מדידה. **אינו מיוחס.** המועמד הצר ביותר, ובדיקה זולה
וקריאה-בלבד לביצוע הבא: `trade_context.py:592` — נקודת-הקריאה של `DAYTYPE_GATE_LIVE_V1`,
שה-FLAG_INDEX מתאר כ-*"the LIVE in-memory promoted attribute
(`app.state.day_type_machine.day_type`)"*. כלומר **התכונה** של המכונה עשויה להחזיק
`Variation` בעוד **לוג-הסיווג** אומר UNKNOWN — שני משטחים על אותו אובייקט, בדיוק
תצפית (ב) של ריצה 327 (הפער לא נסגר ב-17:05 אחרי הסיווג ב-17:00). להימדד, לא להסיק.

### 7.4 · מצבי-הדגלים — מהמשטח הקנוני, אחרי שהמשטח הלא-נכון נזרק

`ps eww -o command= -p 2030` החזיר `<not in proc env>` לכל חמשת המפתחות. **זו אינה ראיה
שהם כבויים** — macOS אינו מאפשר קריאת סביבה של תהליך אחר, והבקאנד טוען `.env` בתוך
התהליך דרך dotenv, כך ש-`os.getenv` רואה אותם בלי שיופיעו בסביבת-הקרנל. המשטח הקנוני
(`flag_guard`, גולמי) ו-`docs/FLAG_INDEX.md`:

| דגל | מצב | משטח |
|---|---|---|
| `DALTON_PLAYBOOK_V1` | ✓ `expected=1 actual=1` | flag_guard ⇒ בלוק `_dp_dt`/`_dp_hyst` **חי** |
| `DECISION_TREE_V3` | ✓ `expected=1 actual=1` | flag_guard |
| `DAYTYPE_HONEST_PRELOCK_V1` | ✓ `expected=1 actual=1` | flag_guard |
| `DAYTYPE_GATE_LIVE_V1` | ✅ ON `1` (.env), ברירת-קוד `""`→OFF | FLAG_INDEX · `trade_context.py:592` |
| `CLS_RESULT_SESSION_GUARD_V1` | אינו ב-flag_guard ואינו ב-FLAG_INDEX ⇒ ברירת-קוד `"0"` = כבוי | `trading_gateway.py:231` |

**אפס הדלקה.** הפסיקה על `CLS_RESULT_SESSION_GUARD_V1` — ועל כך שהוא כנראה **אינו מספיק
לבדו** (7.2) — היא של מייקל.

### 7.5 · חצי-הריפליי — עדיין **NOT-DONE**, והשער שריצה 327 קבעה **אינו מתקיים**

ריצה 327 קבעה בלוג-המשימות: *"לפני כל נגיעה: `ps | grep fwd_harness` ⇒ 0"*.
נמדד ב-23:35–23:37, גולמי:
```
82251  00:24  PY scripts/fwd_harness.py --session 2024-05-13 --variant hist_k \
                 --out harness_out/t466/hist_k_2024-05-13.json --quiet
82264  00:24  PY scripts/fwd_harness.py --session 2024-05-14 --variant hist_k \
                 --out harness_out/t466/hist_k_2024-05-14.json --quiet
11157  03:44:36  bash chain11.sh
51046  06:33:55  bash /Users/michael/mems26_hist/chain8.sh
95626  00:58:51  bash harness_out/t586/hist/run_hist.sh hist_k TREE_SKIP_KINDS=REVERSAL,EDGE_FADE
```
⇒ **לא 0 אלא 2 עובדים חיים**, ו-`--out` שלהם הוא `harness_out/t466/` — **בדיוק** ספריית
הקריאה/כתיבה של פריט 1. ה-PID התחלפו בתוך ~90 שנ' (81239/81480 ⇒ 82251/82264), כלומר
סריקה פעילה שבה כל עובד חדש **טוען את `fwd_harness.py` מהדיסק בהפעלה** — הוספת שורת-INFO
ב-`:790` הייתה משנה את הפלט של סוכן אחר על מאות סשנים, בשקט, בלי קונפליקט-git ובלי שגיאה.
בעלות-העריכה על הקובץ טרייה ושל אותו סשן: `git log -1 -- scripts/fwd_harness.py ⇒
3e1a9b40 2026-10-18 19:52 T-597`. בנוסף: swap 3,006M/4,096M, RAM פנוי 39M, load 7.02.

⇒ **אפס claim, אפס סוכן-משנה, אפס נגיעה** ב-`fwd_harness.py` וב-`harness_out/`.
השער של ריצה 327 נשאר בתוקף ו**לא התקיים** גם בריצה 328 (ריצה שנייה ברצף). מלכודת 38
(קומיט = ראיה בדיעבד, תהליך = ראיה בזמן-אמת) מאוששת פעם שנייה, ממדידה עצמאית.

**מה כן נמסר במקום:** ציר-הקוד של פריט 3 (7.1–7.4) — קריאה-בלבד, אפס תחרות-CPU, ועונה
על הצעד-הבא של ריצה 327 **ומתקן טעות-קריאה בהזמנה** (ה-`*( )`).

### 7.6 · אפס-נגיעה (ריצה 328)

ריסטארט · GO/NO-GO · דגלים · דגלי-גודל · `.env` · פוזיציות · פקודות · `op=EXIT` ·
קוד-פרודקשן · DLL · סיירה · עץ-ההחלטות · כתיבות-DB · `broker_truth --write` ·
`fwd_harness.py` · `harness_out/` · הטלפון. `ruled_contracts() = 1` לדיווח בלבד.
