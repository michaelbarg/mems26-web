# EOD Fire Analysis — 2026-06-03 (Agent B, SHADOW)

**מצב:** קריאה-בלבד. לא שונה קוד/DB/שירות/דגל. כל מספר מגובה בשאילתה על
`file:data/mems26_local.db` (`mode=ro` / `immutable=1`).
**חלון:** היום UTC = 2026-06-03. RTH נסגר 20:00 UTC; הניתוח רץ ~20:18 UTC.

---

## ⚠️ הערות מצב מקדימות — לקרוא קודם (top-of-report, Rule 5)

### 0a. 🔴 STRATEGIC STOP — ה-DB **באמת corrupt**, לא false-positive של mount

`PRAGMA quick_check` החזיר מאות שגיאות B-tree אמיתיות:
```
Page 76860: btreeInitPage() returns error code 11
On tree page 76859 cell 1: Rowid 3984423 out of order
On tree page 76823 cell 174: Child page depth differs
On tree page 76846 cell 167: 2nd reference to page 71443
... (100+ שורות: rowid out of order / 2nd reference to page / depth differs)
```

**זה שונה מהדוח של 2026-06-02.** אתמול ההנחה הייתה ש-`malformed` הוא false-positive
של קריאה חיה מעל mount מסונכרן. **היום ההנחה הזו נשללת בנתונים:**

1. השגיאה **נשארת זהה גם ב-`immutable=1`** (עוקף WAL/lock לגמרי) — לא חתימת mount.
2. השגיאה **ממוקדת בטבלאות-bar עתירות-נפח בלבד** (rowid ~3.98M מ-`quick_check`),
   בעוד טבלאות אחרות נקראות נקי. זו corruption מקומית אמיתית, לא קריאה-מעל-mount.

טבלאות שמחזירות `database disk image is malformed` בקריאה (גם immutable):

| טבלה | סטטוס קריאה | מזינה את |
|---|---|---|
| `v9_bars_5min` | ❌ malformed | S2 Five-Min, S1 |
| `v9_bars_5min_woodies` | ❌ malformed | S4 Woodies (CCI) |
| `v9_bars_30min_woodies` | ❌ malformed | S4 Woodies |
| `v9_bars_cumulative_delta` | ❌ malformed | S1 CVD-opening (`S1_CVD_OPENING`) |

טבלאות שנקראו נקי: `v9_trades`, `v9_woodies_signals`, `v9_system_signals`,
`v9_bars_imbalance`, `v9_day_type_*`.

**המלצה (לא מימוש):** להריץ `integrity_check` עם backend מושבת לפני כל הצהרת GO,
ולשחזר את זרמי ה-bar מ-Sierra exports / backup. **אל תצהיר GO.**

### 0b. 🔴 STRATEGIC STOP — סתירה מול CLAUDE.md §DB (Postgres root-fix)

CLAUDE.md §DB (2026-06-03) מצהיר שכל מחלקת ה-corruption של SQLite **נסגרה היום** במעבר
ל-local Postgres. **בפועל הסטאק החי עדיין כותב ל-SQLite הזה, והוא corrupt:**

- `.env` **אין בו שורת `DATABASE_URL`** → הקוד נופל לברירת-המחדל
  `sqlite:///./data/mems26_local.db` (אומת ב-`grep DATABASE_URL`).
- כתיבות חיות נוחתות כאן ברגע זה: `MAX(ts)` של `v9_woodies_signals` = `20:18:38`,
  `v9_system_signals` = `20:10:10`, `v9_bars_imbalance` = `20:10:10`; `-wal` 4.1MB פעיל.

כלומר או שה-Postgres לא באמת deployed, או שרץ writer ישן שעדיין מזין את ה-SQLite.
**המלצה:** לאמת איזה DB ה-backend החי באמת משתמש בו לפני LIVE. **דווח, לא תיקון.**

### 0c. ה-backend חי על המק אך לא נגיש מה-sandbox
`curl localhost:8000` מה-sandbox המבודד לא מגיע למק. לכן snapshot מ-
`/api/v9/build/pattern-status` **לא נשלף** — כל הניתוח מבוסס-DB.

---

## 1. סיכום ירי היום (`entry_ts` date = 2026-06-03, כל הרשומות `is_synthetic=0`)

| מערכת (firing_system) | #fires (אירועים ייחודיים) | shadow | demo | setups | תוצאות |
|---|---|---|---|---|---|
| **S4 Woodies** (`fs=4`) | **2** | 2 | 2 | n/a | 1 LOSS (CLOSED), 1 PARTIAL (פתוח) |
| **S2 Five-Min** (`fs=2`) | **2** | 2 | 1 | **0** | 2 PARTIAL (פתוחים), שניהם SHORT |
| **S3 Footprint** (`fs=3`) | **0** | 0 | 0 | — | מושתק (`FOOTPRINT_DISABLED`) |
| **S1 day_type** | n/a (מסווג, לא סוחר) | — | — | — | Normal / LOCKED_LOW_CONF — §3 |

7 שורות ב-`v9_trades` היום = זוגות demo/shadow. אירועים ייחודיים:

```
14:30  fs4  LONG   CLOSED  LOSS   (id 399 shadow / 400 demo)
14:46  fs4  SHORT  PARTIAL פתוח   (id 401 shadow / 402 demo)
15:45  fs2  SHORT  PARTIAL פתוח   (id 403 shadow / 404 demo)
15:50  fs2  SHORT  PARTIAL פתוח   (id 405 shadow — ללא מקביל demo)
```

> מיפוי `firing_system→מערכת` הוא **הסקה** (אין טבלת-מקור): `fs=4`↔Woodies, `fs=2`↔Five-Min,
> `fs=3`↔שושלת Footprint (374/405 הטריידים אי-פעם). **strategic-stop:** לאמת מיפוי לפני הסתמכות.
> היסטורית: `fs3` shadow=374, `fs4` shadow=16/demo=12, `fs2` shadow=2/demo=1 — S2 ירה **3 פעמים בסה"כ אי-פעם**, 2 מהן היום.

---

## 2. לכל תבנית — נדרך (armed) · ירה · הסיבה החוסמת

### 2a. S4 Woodies — 9 תבניות (armed proxy = `v9_woodies_signals`, 4,751 אותות היום)

| תבנית | אותות היום (armed) | conf ממוצע | conf קבוע? | ירה לטרייד |
|---|---|---|---|---|
| ZLR | 1,978 | 0.763 | משתנה (0.50–0.90) | — |
| TLB | 1,026 | 0.756 | משתנה (0.45–0.85) | — |
| GHOST | 644 | 0.700 | **קבוע 0.70** | — |
| FAMIR | 562 | 0.649 | משתנה (0.46–0.80) | — |
| HTLB | 528 | 0.650 | **קבוע 0.65** | — |
| VEGAS | 8 | 0.750 | **קבוע 0.75** | — |
| HFE | 4 | 0.700 | **קבוע 0.70** | — |
| GB100 | 1 | — | — | — |
| **TT** | **0** | — | — | **לא נדרך כלל היום** |

פילוח session של האותות: `CASH_HOURS` 3,307 · `AFTER_HOURS` 719 · `MAINTENANCE` 695 ·
`OVERNIGHT` 13 · `FIRST_HOUR` 9 · `CASH_OPEN` 7.
→ **רק 16 אותות (9+7) נפלו בחלונות killzone הראשוניים**; הרוב המכריע מחוץ ל-prime.
`persistence_bars=50` **קבוע בכל השורות** — נראה capped/תקוע, לא מחושב.

**הסיבה החוסמת הדומיננטית: לא נרשמת ב-DB (honest failure, Rule 1).**
2 טריידי S4 בלבד יצאו מתוך 4,751 אותות, אך **שום טבלה לא מתעדת את שלב ה-gate**:
- `v9_woodies_patterns` ריקה (0 lifetime).
- `v9_system_signals` היום מכילה **רק S3 imbalance** (system_id=3), אפס החלטות S4.
- `v9_killzone_log` ו-`v9_chop_score` — **0 שורות היום**.

לכן **אי-אפשר לכמת את הבלוקר הדומיננטי per-pattern מה-DB.** השערות מבוססות-מבנה
(לא נטענות כעובדה): רוב האותות מחוץ ל-killzone + day_type Normal/LOW_CONF הם ה-gate
הסביר — אך אין רישום שמוכיח זאת. ראה המלצה §5.3.

### 2b. S2 Five-Min — 3 וריאציות (A_VSA / B_RVOL / C_STRICT)

- `v9_five_min_setups` ריקה (**0 lifetime**), `v9_five_min_state` ריקה (**0 lifetime**).
- ובכל זאת ירו **2 טריידי `fs=2`** היום (שניהם SHORT, 15:45 + 15:50).

→ **פער provenance:** S2 ירה בלי ולו setup row אחד. אי-אפשר לפצל armed/blocked לפי
וריאציה (A_VSA/B_RVOL/C_STRICT), ואי-אפשר לדעת למה הווריאציות האחרות לא ירו —
**הטלמטריה פשוט לא קיימת.** **strategic-stop:** §5.4.

---

## 3. day_type timeline (S1)

- **`v9_day_type_history` היום:** `Normal` · status `LOCKED_LOW_CONF` · confidence `68.0` ·
  `opening_type=OPEN_AUCTION_IN` · **`ib_width_ticks=NULL`** (חסר, למרות `S1_IB_WIDTH_ATR=true`).
- **`v9_day_type_shadow_transitions` היום: 0 מעברים.** המעברים האחרונים מ-2026-06-02
  (Normal→Variation, E_up≈0.49–0.85, R≈0.12–0.16).
- היסטוריה: 06-01 ו-06-02 שניהם `Normal / ROLLED_OVER / conf 68`.

**תואם מצופה?** רגיעה: Normal בביטחון נמוך ללא מעברים תוך-יומיים — עקבי עם יום שקט.
`ib_width_ticks=NULL` אומר שרוחב ה-IB לא נשמר → קלט מפתח ל-S1 חסר.

---

## 4. streams / data quality

| stream | MAX(ts) | רעננות | הערה |
|---|---|---|---|
| `v9_woodies_signals` | 2026-06-03T20:18:38 | ✅ טרי | זורם |
| `v9_system_signals` | 2026-06-03 20:10:10 | ✅ טרי | רק S3 imbalance (2,879 היום) |
| `v9_bars_imbalance` | 2026-06-03T20:10:10 | ✅ טרי | n=982 סה"כ, 13 היום |
| `v9_bars_5min` | — | ❌ **malformed** | קורסת בקריאה |
| `v9_bars_5min_woodies` | — | ❌ **malformed** | קורסת בקריאה |
| `v9_bars_30min_woodies` | — | ❌ **malformed** | קורסת בקריאה |
| `v9_bars_cumulative_delta` | — | ❌ **malformed** | קורסת בקריאה → CVD לא ניתן לאימות |
| `v9_bars_stacked_imbalance` | 2023-11-14T22:18:20 | 💀 מת | שורה אחת, ישנה משנים |
| `v9_bars_woodies` | — | 💀 ריק | 0 שורות |
| `v9_killzone_log` | — | ⚠️ 0 היום | לא נכתב היום |
| `v9_chop_score` | — | ⚠️ 0 היום | לא נכתב היום |

**הקריטי:** ארבעת זרמי ה-OHLC/CCI/CVD שמזינים את S1/S2/S4 **בלתי-קריאים בגלל
corruption.** האותות שכן זורמים (`woodies_signals`, imbalance) טריים, מה שמעיד שה-backend
חי וכותב — אבל היסטוריית ה-bars שעליה מתבססת לוגיקת הירי פגומה.

---

## 5. המלצות (המלצה בלבד — לא מימוש)

**5.1 🔴 STRATEGIC STOP (Michael) — corruption אמיתי.** השגיאה ממוקדת ב-4 טבלאות bar
ונשארת ב-`immutable=1` → לא false-positive של mount. המלצה: `integrity_check`
backend-down + שחזור הזרמים מ-Sierra exports/backup לפני GO. אל תצהיר GO.

**5.2 🔴 STRATEGIC STOP (Michael) — drift מקור-אמת DB.** CLAUDE.md אומר Postgres חי;
הכתיבות נוחתות ב-SQLite corrupt (`.env` ללא `DATABASE_URL`). לאמת איזה DB ה-backend
החי באמת משתמש בו, ולסגור את אחד מהשניים, לפני LIVE.

**5.3 פער טלמטריה (חוסם ניתוח EOD).** `v9_woodies_patterns` / `v9_five_min_setups` /
`v9_five_min_state` ריקות; `killzone_log` + `chop_score` לא נכתבו היום; אין רישום
reason/gate per-pattern. כל עוד זה כך, **"למה התבנית לא ירתה" לא ניתן לענייה מה-DB.**
המלצה: לחווט טלמטריית decision/gate שתשמר את הבלוקר הדומיננטי לכל תבנית
(ראה דפוס full-decision-pipeline-wiring).

**5.4 STRATEGIC STOP (S2 וריאציה).** 2 טריידי SHORT ירו עם 0 setup rows → לא ניתן
לייחס ל-A_VSA/B_RVOL/C_STRICT. לאמת ש-`v9_five_min_setups`/`_state` נשמרות בפועל
לפני שמסתמכים על S2 ב-SHADOW.

**5.5 Woodies confidence/persistence נראים hardcoded.** GHOST/HTLB/VEGAS/HFE פולטות
confidence קבוע, ו-`persistence_bars=50` ננעל בכל השורות. המלצה (data-grounded רק אחרי
שהזרמים קריאים): לאמת שחישוב ה-confidence וה-persistence לא תקוע — מועמד לסף יחסי.

**5.6 כיסוי תבניות.** TT לא נדרך כלל היום (0/9), GB100 רק פעם אחת. לתעד; לא בהכרח באג,
אך שווה מעקב אם נמשך מספר ימים.

---
*Agent B · read-only · אין שינוי קוד/DB/שירות/דגל · כל מספר מאומת בשאילתת DB.*
