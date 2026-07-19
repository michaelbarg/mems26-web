# W6 — Phone App Audit (2026-07-19)

**בעלים:** cursor-agent · **קריאה+הצעה** · `.env` = פסיקת-מייקל (לא נגעתי)

## חוק-5 — ראיה גולמית

```
.env:286  MOBILE_REMOTE_URL=http://10.1.118.70:8000   # iMac (סים)
ZeroTier: MacBook inet 10.1.118.147 · iMac 10.1.118.70 · phone 10.1.118.31

curl -m3 http://10.1.118.70:8000/api/v9/mobile/data
  → timeout / Host is down

curl -m3 "http://127.0.0.1:8000/api/v9/mobile/data?key=***"
  → _src=local  _remote_err=<urlopen error timed out>
     mid=0.0  day_type=None  contracts_cfg=4  patterns=14
     has direction? False  has paint/trend? False
     sierra.is_sim=0 qty=0 age≈48450s  (סופ״ש / פיד-קובץ ישן)

curl -m3 "http://10.1.118.147:8000/api/v9/mobile/data?key=***"
  → אותו _src=local + _remote_err (Host is down על 70)
```

`live_price.json`: `price=7557.5` אבל `bid=0 ask=0` · `_price()` במוניטור משתמש ב-(bid+ask)/2 → **mid=0.0**.

## (1) לאן ה-fetch הולך

| שלב | קוד | מה קורה עכשיו |
|---|---|---|
| פלאפון פותח | `http://10.1.118.147:8000/api/v9/mobile?key=…` (ZT MacBook) | נכון ל-cutover |
| `GET /mobile/data` | `mobile_monitor.py:58-73` `_remote_data()` | **קודם** מנסה `MOBILE_REMOTE_URL` = **iMac:70** |
| iMac למטה | timeout | `_remote_err` |
| fallback | `:81-87` | מחזיר **local** (MacBook) עם badge `⚠ מקומי (מכונת-המסחר לא-זמינה)` |
| `POST /flatten` | `:218-233` | כש-`MOBILE_REMOTE_URL` מוגדר ונכשל → **מחזיר error בלי flatten מקומי** |

**מסקנה:** הנתונים בפועל (אחרי timeout) הם של ה-MacBook — נכון בטעות. אבל:
1. כל רענון מחכה ~3ש' ל-timeout של iMac (חוויית-כיס איטית).
2. ה-badge **משקר** — "מכונת-המסחר לא-זמינה" בזמן שה-local **הוא** מכונת-המסחר.
3. **כפתור FLATTEN שבור** כל עוד ה-URL מצביע ל-iMac מת (לא נופל ל-local).

## (2) האם משקף את התיקונים?

| אות | בפלאפון? | הערות |
|---|---|---|
| **day-type override-aware** | ✅ קוד | `get_live_day_type()` ב-`:120` · הערב `null` (pre-RTH / סופ״ש) — צפוי |
| **מחיר טרי** | 🔴 | `_price()` = (bid+ask)/2 · כש-bid/ask=0 → `mid=0` למרות `price` בקובץ; גם age~13ש' (סופ״ש) |
| **כיוון** (`direction_now` / sustained) | 🔴 חסר | HTML לא מציג dir בכלל — רק day_type + patterns |
| **paint / trend CCI** | 🔴 חסר | אין שדה paint ב-JSON ובדף |
| **תבניות / שער** | ✅ | `patterns` + `gate` מ-build-status + decisions |
| **חוזים** | ✅ | `contracts_cfg=4` תחת FIXED_4 |

## (3) הצעת-תיקון (לפסיקת-מייקל — cowork מיישם `.env`)

### A · מיידי (שורש)
על **MacBook (מסחר)** אחרי cutover 07-17:

```bash
# אופציה מומלצת: רוקן — הפלאפון מדבר ישירות עם מכונת-המסחר
MOBILE_REMOTE_URL=
```

כתובת-כיס קבועה (ZeroTier, לא אפמרי, לא Tailscale):

`http://10.1.118.147:8000/api/v9/mobile?key=<MOBILE_ACCESS_KEY>`

**אל** תגדיר `MOBILE_REMOTE_URL=http://10.1.118.147:8000` על אותו MacBook — זה יוצר פרוקסי-לעצמו / רקורסיה.

`MOBILE_REMOTE_URL` נשאר רלוונטי **רק** אם מגישים את הדף ממכונה שאינה המסחר (dev) ומפרוקסים ל-MacBook.

### B · קוד סיכון-נמוך (cursor/cc אחרי פסיקה — לא מסחר)
1. `_price()`: אם bid/ask חסרים/0 → fallback ל-`lp["price"]` (או `/api/v9/live_price`).
2. כש-`MOBILE_REMOTE_URL` ריק: badge `מקומי=מסחר` לא אזהרה.
3. אופציונלי FE-כיס: שורת `direction_now` + `dir_sustained` (fetch קיים) — כדי לשקף T12.

### C · מה לא לעשות
- לא Tailscale.
- לא Cloudflare אפמרי כברירת-מחדל (ZT כבר הפסיקה).
- לא להצביע ל-iMac:70 אחרי cutover.

## Verdict
🔴 **שורש מאומת:** `.env` מצביע ל-iMac-סים. הכיס "עובד חלקית" דרך fallback איטי+מבלבל, ו-**FLATTEN שבור**.  
תצוגה: day-type ✅ בקוד · מחיר/כיוון/paint 🔴.  
פעולה הבאה: פסיקת-מייקל על `MOBILE_REMOTE_URL=` + לינק ZT 147 · אז cowork מעדכן `.env` + snapshot.
