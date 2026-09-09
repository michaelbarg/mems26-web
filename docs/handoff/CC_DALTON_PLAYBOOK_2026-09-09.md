# ‏🔴 עדיפות-1 · 09.09 09:20 — `DaltonPlaybook`: עץ-החלטות חי לפי שלב-הסשן, לייב היום

**מאת:** cowork-dev · **אל:** cc-macbook · **‏`--re 141cb7ad`** · **גובר על §2 של `CC_REBUILD_2026-09-09.md`** (‏§1 · §4 · §5 עומדים).
**פסיקת-מייקל 09.09 09:15:** *"אין שום היגיון בעוד יום של הפסדים ותיקונים על צל… להיכנס כמו שצריך בפתיחה, להיכנס כמו שצריך אחרי ש-IB נסגר, ואז לסחור לפי סוג-היום שהתגבש, ולאפשר ל-S2/S4 לסחור בהתאם ל-S1… כל סוג-פתיחה צריך להיכנס לעץ-החלטות אחר… להיות חכמים יותר מטבלה סטטית."*

**האבחנה שמאחורי זה (39 סשנים, 4 סוכנים):** ימי-הרווח (‏08-04 +$535 · 08-28 +$349 · 09-02 +$270 · 08-05 +$246) הם ימים שבהם המערכת נכנסה **עם** כיוון-היום, מוקדם, ונתנה לרוץ. ימי-ההפסד: **אחרי** ההרחבה, **נגד** היום, סטופ-רעש. **היכולת קיימת; הבחירה שגויה.** ‏24 שערים שכל אחד נבנה על תקרית — ואין מכונת-מצבים אחת.

---

## מה לבנות — `backend/v9/services/dalton_playbook.py`

**פונקציה טהורה אחת:**
```python
intent(phase, opening_type, day_type, ib, structure, now_il) -> Intent
Intent = {
  bias: "LONG"|"SHORT"|"BOTH"|"NONE",
  entry_kinds: {"WITH_DRIVE","PULLBACK","REVERSAL","EDGE_FADE","VALUE_RETURN","BREAK"}  # subset
  stop_rule: "BEYOND_OPEN"|"BEYOND_FAILED_SIDE"|"BEYOND_REJECTED_EXTREME"|"BEYOND_LEG_EXTREME"|"BEYOND_IB_EDGE",
  target_rule: "MEASURED_MOVE"|"POC"|"OPPOSITE_EDGE"|"CENTER"|"S1_TABLE",
  size_frac: 1.0|0.5|0.0,
  runner: bool,
  reason: str,     # human-readable, Hebrew ok — goes to the log and to the phone
}
```

### העץ (הדוקטרינה של מייקל — כל שורה היא הגדרה, לא קוד; לשים ב-`config/dalton_playbook.yaml`)

| שלב | תנאי | bias | entry_kinds | stop | target | size | runner |
|---|---|---|---|---|---|---|---|
| **A** 16:30–16:45 | `opening_type == OPEN_DRIVE` (‏3 ברים) | כיוון-הדרייב | WITH_DRIVE | BEYOND_OPEN | MEASURED_MOVE | 0.5 | ✓ |
| A | אחרת | NONE | ∅ | — | — | 0 | — |
| **B** 16:45–17:30 | OPEN_DRIVE | דרייב | WITH_DRIVE, PULLBACK | BEYOND_OPEN | MEASURED_MOVE | 1.0 | ✓ |
| B | OPEN_TEST_DRIVE | דרייב (אחרי המבחן) | WITH_DRIVE, PULLBACK | BEYOND_FAILED_SIDE | MEASURED_MOVE | 1.0 | ✓ |
| B | OPEN_REJECTION_REVERSE | כיוון-ההיפוך | REVERSAL, PULLBACK | BEYOND_REJECTED_EXTREME | OPPOSITE_EDGE | 1.0 | — |
| B | OPEN_AUCTION_IN / _OUT | BOTH | EDGE_FADE | BEYOND_IB_EDGE | POC | 0.5 | — |
| B | INDETERMINATE/UNKNOWN | NONE | ∅ | — | — | 0 | — |
| **C** 17:30+ (IB נעול) | Trend_Normal / Trend_DD | כיוון-המגמה | PULLBACK, BREAK | BEYOND_LEG_EXTREME | S1_TABLE | 1.0 | ✓ |
| C | Variation / Normal_Variation | כיוון-ההרחבה **פעם אחת**, ואז BOTH | BREAK (×1), VALUE_RETURN | BEYOND_LEG_EXTREME | POC | 1.0 | — |
| C | Normal | BOTH | EDGE_FADE, VALUE_RETURN | BEYOND_IB_EDGE | POC | 1.0 | — |
| C | Neutral_Center / Neutral_Extreme | BOTH | EDGE_FADE | BEYOND_IB_EDGE | CENTER | 1.0 | — |
| C | Nontrend / Nonconviction | NONE | ∅ | — | — | 0 | — |
| C | `day_type is None` אחרי נעילה | NONE | ∅ | — | — | 0 | — |
| **D** 21:00+ | כל תווית | (ניהול בלבד) | ∅ | — | — | 0 | — |

**היסטרזיס (חוק "אין היפוך באמצע מגמה", 08-04 19:16):** ב-C, מעבר `Trend_* → אחר` דורש **2 ברים סגורים** עם התווית החדשה; מעבר `אחר → Trend_*` — **מיידי** (מגמה שמתגבשת אסור לפספס).

### החיווט — הפלייבוק **מחליף**, לא מתווסף

ב-`_route_setup_inner`, **במקום** `direction_compass` (‏`:2120-2140`) · `daytype_playbook` (‏`:1611`) · `location_gate` (‏`:1733`) · `awaiting_release` (כבר כבוי) — **שער אחד:** `dalton_intent`.
```
setup.direction  ∉ intent.bias           ⇒ blocked_by="dalton_intent:bias"      reason=intent.reason
setup.entry_kind ∉ intent.entry_kinds    ⇒ blocked_by="dalton_intent:kind"
intent.size_frac == 0                    ⇒ blocked_by="dalton_intent:stand_down"
```
`entry_kind` נגזר מהתבנית: ‏`OPENING_DRIVE/TEST_DRIVE→WITH_DRIVE` · `ORR/EXTREME_REJECT/DALTON_EDGE/CEILING_FLIP→REVERSAL` · `PULLBACK_CONT/TREND_STEP→PULLBACK` · `INITIATIVE/GB100/TLB/BREAK→BREAK` · `REACTIVE/VA_FADE/EDGE_FADE/FAILED_BREAK→EDGE_FADE` · `RE_ACCEPTANCE/VALUE_RETURN→VALUE_RETURN`. **מפה ב-YAML, לא בקוד.**
**ואז הכלכלה מהכוונה:** `stop_rule` ו-`target_rule` מזינים את `trade_economics()` (‏§2) — **זה** מה שהופך את S1 למי שמתמחר. ‏`size = round(ruled_contracts() × size_frac)`.

**דגל: `DALTON_PLAYBOOK_V1`** — `0` (ללא שינוי) · `1` (מחליף את ארבעת השערים). **ארבעת השערים הישנים נשארים בקוד מאחורי `DALTON_PLAYBOOK_V1=0`** — מתג-חירום של 15 דקות.

### שער-הריפליי — לפני 15:00, וזה מה שמכריע לייב

`scripts/replay_dalton_playbook.py`: לכל אחד מ-39 הסשנים, לכל setup בארכיון-ההחלטות + `v9_trades`, מחשב `intent` באותו רגע (‏`opening_type` מ-`opening_detector_v2` על 3 ברים; `day_type` מ-`classify_session` ב-12/54/78 ברים — **לא** `day_type_at_entry`, הוא שגוי ב-7/11) ומדפיס:
```
ימי-רווח (08-04 · 08-28 · 09-02 · 08-05):  כמה מהעסקאות שהרוויחו הפלייבוק היה מאשר  (חייב ≥ 75%)
ימי-הפסד (09-01 · 08-31 · 08-14 · 09-08):  כמה מהעסקאות שהפסידו הוא היה דוחה        (חייב ≥ 60%)
סה"כ 39 סשנים, ברוקר-בלבד:               Σ$ של מה שהוא מאשר  מול  Σ$ של מה שנסחר   (חייב > −313.75, ורצוי > 0)
                                          n מאושר (חייב ≥ 40 — פלייבוק שמאשר 5 עסקאות ב-39 יום הוא לא פלייבוק)
```
**עובר ⇒ `DALTON_PLAYBOOK_V1=1` ב-15:45, 5 חוזים.** ‏לא עובר ⇒ הפלייבוק רץ ב-`diff` היום, והמספר הוא ההכרעה של מייקל מחר.

### מה **לא** ב-scope היום
היצרנים `VALUE_RETURN`/`BALANCE_DEPART` (‏§4, צל) — הפלייבוק יודע לומר `VALUE_RETURN` אבל היום יורה אותה רק מי שרואה אותה (‏S2/S4). **לא לבנות היום.**

---

## אימות-cowork 14:00
`python3 scripts/replay_dalton_playbook.py` — ארבעת המספרים · `pytest tests/v9/regression/test_dalton_playbook.py` (כל שורה בעץ = טסט, + מוטציה שהופכת bias ⇒ נכשל) · `guard_tests` · `flag_guard` · `git status ⇒ ריק`.

## אסור
לגעת ב-`RISK_BUDGET_USD`/`RISK_MIN_CONTRACTS`/`FIXED_CONTRACTS_5` · לבנות יצרנים · להדליק בלי שער-הריפליי · קוד אחרי 15:00 · ריסטארט.
