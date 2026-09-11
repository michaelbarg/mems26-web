# אימות-קדם-פתיחה 11.09 16:02 — סוכן-מתוזמן `mems26-preopen-restart-1109`

**מסקנה: GO. לא ביצעתי ריסטארט — הוא כבר בוצע ב-15:56:18 ע"י סוכן-cowork מקביל
(קומיט `7e435905` 15:59:25 + רשומת-ערוץ `[id:f4fa7cc9]`). זו אימות-עצמאי שלו, לא
ריסטארט שני.**

## 0. הסוכן-המקביל — למה לא הרמתי שוב
המשימה-המתוזמנת ירתה ב-15:56:44. אתחול-הסשן מצא מאזין-8000 שכבר חי מ-15:56:18,
ו-`git log` הראה קומיט שנוצר **תוך כדי** הסשן שלי:

```
7e435905 09-11 15:59:25 ops(cowork): pre-open restart 11.09 GO on 1df53fd7 — PID 25376 15:56:18, fire_drill GO
```

"אל תרים פעמיים" חל כאן במלואו — הרמה שנייה 28 דק' לפני הפתיחה היא סיכון בלי
תמורה. מה שכן נדרש היה **להוכיח** שהתהליך החי נושא את תיקוני-היום, ולא להניח.

## 1. הראיה שהתהליך החי נושא את התיקונים (לא "כתוב" — **רץ**)

```
pid=25376  (lsof -nP -iTCP:8000 -sTCP:LISTEN -t)
ps -o lstart= -p 25376  ⇒  Fri Sep 11 15:56:18 2026
2026-09-11 15:56:23 [INFO] [mems26.boot] [boot] logging OK level=INFO pid=25376 commit=1df53fd7 stream=stderr
curl localhost:8000/api/v9/health ⇒ {"status":"ok","version":"v9.0.0"}
```

`commit=1df53fd7` הוא HEAD — קומיט-האימות של T-319b-lite מעל `f77edbd1`. כלומר
**כל תיקוני-היום בתוך התהליך הרץ**: T-311 · T-313 · T-314 · T-315 · T-319b-lite.

אימות-צולב על מקורות-הקוד (mtime מול שעת-התהליך 15:56:18) — כולם ישנים ממנה, אין
קובץ שנכתב אחרי העלייה:

```
backend/v9/gateway/trading_gateway.py     09-11 14:27:16   (החדש ביותר ב-backend/)
backend/main.py                           09-11 11:11:17
backend/v9/systems/day_type/opening_lock.py 09-11 11:10:47
.env                                      09-10 11:27:41   (לא נגעו בו היום)
```

`.env` ישן מהתהליך ⇒ התהליך טען את תוכן-ה-.env הנוכחי (304 vars),
ובו `DALTON_PLAYBOOK_V1=1` (.env:124). שורת-הבוט מדפיסה תת-קבוצה של דגלים
ולכן `grep DALTON_PLAYBOOK_V1` עליה מחזיר 0 — זו לא ראיה לכיבוי אלא למחרוזת
שלא מודפסת שם; המפריד הוא `stat .env` מול `ps -o lstart`.

## 2. הגולדנים על HEAD `1df53fd7` — 5/5 ירוקים

`python3 scripts/fwd_harness.py --session <s> --variant head --quiet --push-mode firstpush`
(`/tmp/preopen1109/`, 15:57:03–15:58)

| # | מבחן | תוצאה |
|---|------|-------|
| a | `would_write` 10.09 ריק | `len = 0` ✓ |
| b | 17:30:09 `INITIATIVE_LONG` חסום `dalton_intent:*` | ✓ |
| c | 20:30:03 `DOUBLE_TOP_AA_SHORT` חסום `dalton_intent:*` | ✓ |
| d | `T-314: NEGATED OPEN_REJECTION_REVERSE` | `grep -c` ⇒ **1** ✓ |
| e | `Traceback` | 10.09 ⇒ **0** · 09.09 ⇒ **0** ✓ |
| f | 09.09 כתיבה **אחת** בלבד | ✓ (למטה) |

שורות גולמיות:

```
il=17:30:09 et=10:30 INITIATIVE_LONG entry=7606.5 blocked_by='dalton_intent:location'
   reason: zone=near_vah price=7606.50 vah=7609.25 val=7589.00 poc=7602.75 (Normal: edge-fade only, no entries at POC)
il=20:30:03 et=13:30 DOUBLE_TOP_AA_SHORT entry=7605.25 blocked_by='dalton_intent:location'
   reason: zone=mid_value price=7605.25 vah=7615.25 val=7597.75 poc=7604.75 (Normal: edge-fade only, no entries at POC)
09.09 would_write: len=1 — SELL REACTIVE_SHORT price=7644.25 contracts=5
   -> route il=20:40:03 et=13:40 blocked_by=None result={'shadow':'FWD-shadow-4','demo':'FWD-demo-5','live':'FWD-live-6'}
```

**מלכודת-שעון שנתפסה:** שדה `et` ב-routes הוא **שעון-מזרחי** (`10:30`), לא שעון-ישראל.
מבחן על `et == "17:30:09"` מחזיר אפס-התאמות ונקרא בטעות ככשל. השדה הנכון הוא `il`.
המפריד נגזר מהראיה שבפריט עצמו: `_dbg_clock.now_et = 2026-09-10 09:34:58-04:00`.

מפקד-חוסמים מלא 10.09 (33 routes, `uniq -c` על הערך — לא grep על מילה מנוחשת):

```
  24  dalton_intent:location      1  dalton_intent:bias
   2  dalton_intent:stand_down    1  dalton_intent:kind
   2  rr_entry_gate               1  entry_location_quality
   1  entry_not_confirmed         1  None
```

ה-`None` היחיד אינו "עבר": `il=17:15:03 FAILED_BREAK_LONG shadow_only=True
result={'shadow':True,'demo':None,'live':None}` — מפיק-צל, ולכן `would_write` ריק.

## 3. שערי-קדם — כולם rc=0

```
flag_guard      rc=0   FLAG-GUARD: PASS — all 252 ruled flags match.
task_log_guard  rc=0   317 items, last committed 0.1 days ago
wire_guard      rc=0   56 call sites bound against 11 guarded signatures
guard_tests     rc=0   160 passed, 42 warnings in 8.65s
stat -f "%Sm" .env  ⇒  Sep 10 11:27:41 2026   (ללא שינוי)
```

(כל `rc` נמדד לפני כל צינור — `cmd > file; echo rc=$?` — כי `guard | tail` מחזיר
את קוד-היציאה של `tail` ותמיד 0.)

## 4. `fire_drill.py` — 🟢 GO (16:01:48, גולמי)

```
  160 passed, 42 warnings in 9.15s
  ✅ GUARDS GREEN — sizing, entry_stop, VA sanity, entry location, slot, patterns
  ✓ guard_tests · ✓ wire_guard (56/11) · ✓ task_log_guard (317)
— שלב D · מצב חי —
  ✓ backend health
  ✓ T-61 שכבת-INFO בלוג — 15:56:23 [boot] pid=25376 commit=1df53fd7 · 281 שורות INFO אחריה
  ✓ T-61 רמת-INFO זורמת בפועל
  ✓ feed טרי (<30s) — age=847ms
  ✓ live_slot פנוי — slot=None
  ✓ live_enabled == [2,4]
  ✓ day_type קיים — UNKNOWN conf=0.0
🟢 GO — כל שרשרת ההחלטה כשרה לירי.
```

`live_slot=None` — אין חסימה-שקטה מסוג T-178/T-309.

## 5. מצב-חי בפתח (16:01:17)

```
sierra.position_qty            = 0        (שטוח)
sierra.order_placement_armed   = 1        (דרוך — החלטת-מייקל, לא נגעתי)
dalton                          = קיים
dalton keys: bias, day_type, ext_dir, ext_dn_pts, ext_up_pts, kinds_allowed,
             last_intent_reason, negated_at, opening_locked_at, opening_source,
             opening_type, phase, runner, size_frac
dalton.day_type = None · phase = 16:01 · bias = NONE      (טרם-פתיחה — צפוי)
```

## 6. 🟠 ממצא NOT-DONE יחיד — תצוגה בלבד, לא חוסם

**`zone` ו-`entry_rule` חסרים מבלוק-ה-dalton ב-`mobile/data`.** סעיף 4 של מפרט
T-319b-lite ("`mobile_monitor` dalton-block: להוסיף `zone` ו-`entry_rule`") לא מומש.
ראיה: `backend/v9/api/v9/mobile_monitor.py` mtime `09-11 10:13:13` — לפני קומיטי
T-319b-lite (14:52–14:56), ורשימת-המפתחות למעלה לא מכילה אותם.

**מה זה כן / מה זה לא:** *כן* — מייקל לא יראה בטלפון באיזה אזור המערכת ממקמת את
המחיר ולפי איזה כלל השורה נבחרה. *לא* — השער עצמו חי ופועל: ההרנס על אותו HEAD
מייצר `dalton_intent:location` עם `zone=near_vah`/`mid_value` ב-24 מתוך 33 routes.
פער-דיווח, לא פער-אכיפה. לסגירה הלילה, לא לפני הפתיחה.

---
נמדד ע"י `cowork-dev` (סוכן-מתוזמן), 11.09 15:56:44–16:02. לא נגעתי בקוד, ב-`.env`,
בדגל, בפוזיציה, בהוראה ובסלוט. סנפשוט נלקח לפני הבדיקות:
`/Users/michael/mems26_snapshots/20260911T125951Z_preopen-restart-1109`.
