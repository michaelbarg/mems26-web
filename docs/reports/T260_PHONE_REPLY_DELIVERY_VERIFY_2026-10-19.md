# T-260 · BRIEF §3.5 — ערוץ-הטלפון: `phone_reply.py` מאמת מסירה מ-Render בכל שליחה (ליל 18→19.10, fix-agent 23:40)

**סוג-עבודה:** (ג) תיקון-באג — התנהגות שנפסקה בכתב ואינה מתקיימת: T-260 ("`phone_reply.py` מדפיס `ok` בשני מסלולי-האובדן") + הצעד-הבא שנרשם בו (א)/(ג)/(ד) + BRIEF §3.5 ("אימות-מסירה מ-Render בכל שליחה; מבחן"). **סטטוס: תוקן — ממתין לאימות** (השליחה הבאה של סוכן-08:30 / supervisor היא האימות-בתנאי-המקור; אני לא שולח הודעת-טלפון — BRIEF §6).

## 1 · הממצא (מה היה)
`scripts/phone_reply.py` (94 שורות, אחרון 21.09): כותב את השורה ל-`PHONE_THREAD.jsonl`, שולח ל-ntfy ול-`POST /reply` ב-Render — **שניהם בתוך `except Exception: pass`** — ואחר-כך `print("ok")` **ללא תנאי**. שני מסלולי-אובדן שקטים (T-260, 06.09):
1. **תקרת 2000 תווים:** `render_mobile_relay/app.py::post_reply` ⇒ `HTTP 400` על `len(text) > 2000`. קורבן: `2026-09-04T21:17:28Z`, דוח-סיום תור-הלילה, 2,402 תווים — נדחה, מייקל לא קיבל, הסוכן דיווח "נשלח".
2. **`_REPLIES` הוא RAM** על מופע-Render חינמי שנרדם ונמחק בכל deploy (= כל `git push`): "POST חזר" ≠ "העמוד מראה". 05.10 13:07 (BRIEF §3.5): `GET /chat ⇒ {"items":[]}` בארבע מדידות — "דף חשוך" — כשחלון-הרלה סגור אין מי שימלא את `_PUSHED_THREAD`; הסוכנים אימתו ידנית ב-`GET /chat` (supervisor 08.10 22:39, cowork 07.09) — אבל הסקריפט עצמו לא.
3. `timeout=10` ל-POST מול cold-start שנמדד 22.9 שנ׳ (T-260 ג) — ודווקא הודעת-08:30 יוצאת מחוץ ל-`RELAY_WINDOW_IL=10:00-23:30`, כלומר על מופע קר.

## 2 · מה תוקן (`scripts/phone_reply.py`, 169 שורות)
- **(1) סירוב לפני כתיבה:** `len(text) > 2000` (תווים בפייתון, לא בתים — 1,131 תווים עבריים = 1,838 בתים) ⇒ `sys.exit("refusing: text is N chars > 2000 … nothing was written or sent — shorten and send once")`. לא נכתב לשרשור, לא נשלח ל-ntfy/Render ⇒ אין כפילות בשליחה-החוזרת.
- **(2) אימות-מסירה:** אחרי `POST /reply` — `GET /chat?key=…` (peek, לא pop) וחיפוש השורה שלנו (`sender` + `text` זהה). שורת-הפלט האחרונה:
  - `ok render=verified reply=200 ntfy=<200|off|err=…> len=N` — exit 0;
  - `UNVERIFIED render=<not-in-chat items=K | chat timeout | chat http=…> reply=<200|http=400|timeout> ntfy=… len=N — the line IS in PHONE_THREAD.jsonl (the relay re-pushes it inside RELAY_WINDOW_IL); do NOT resend (T-369) — re-check: GET /chat` — exit 2;
  - בלי `MOBILE_ACCESS_KEY` ב-`.env` (מבחנים): `ok render=no-key …` — exit 0 (כמו קודם: אין מסלול-Render).
- **(3) זמנים:** POST 10→30 שנ׳; GET 12 שנ׳ + ניסיון-חוזר אחד אחרי 3 שנ׳ **רק** כשה-GET עצמו נכשל (cold-start) — לא כשענה בלעדינו. גרוע-ביותר 30+12+3+12 = 57 שנ׳ < מגבלת-60 של הכלי.
- ntfy: הכישלון מדווח (`ntfy=err=…`) במקום להיבלע; השליחה עצמה ללא שינוי.
- ללא שינוי: שומרי-המתגים (15.09/21.09), `{NOW}`, פורמט שורת-השרשור, `channel_post.py`, `mobile_relay.py`, `app.py` של Render.

## 3 · ראיות
- **מבחנים:** `tests/v9/regression/test_t260_phone_reply_delivery.py` — 12 (in-process, אפס רשת: סירוב >2000 בלי כתיבה/שליחה · 2000 בדיוק נשלח ומאומת · תווים-לא-בתים · `reply=http=400` ⇒ UNVERIFIED exit 2 · Render קר (`items=[]`) ⇒ UNVERIFIED + "do NOT resend" · timeout ⇒ ניסיון-חוזר אחד · ענה-בלעדינו ⇒ בלי ניסיון-חוזר · התאמת שולח+טקסט מדויקת · אותו טקסט משולח אחר ≠ מסירה שלנו · בלי מפתח ⇒ `ok render=no-key` · כשל-ntfy מדווח · `--help`/מתג-חשוף/`--frm` עדיין מסורבים) + 4 הקיימים (`test_phone_reply_switch_guard.py`) ⇒ **16 ירוקים**.
- **מול Render האמיתי (קריאה-בלבד, 23:5x):** `verify_on_render` על השורה האחרונה בשרשור (supervisor `2026-10-18T19:40:05Z`, 491 תווים) ⇒ `True items=30` ב-0.4 שנ׳; בקרת-שלילה (טקסט שלא נשלח) ⇒ `(False, 'not-in-chat items=30')` ב-0.4 שנ׳.
- `flag_guard` rc=0 (האזהרה הידועה FOOTPRINT_DISABLED בלבד). לא נשלחה הודעת-טלפון.

## 4 · מה לא נעשה, ולמה
- T-260 (ב) "פיצול אוטומטי >1,900 לחלקים ממוספרים" — **לא**: פיצול = שתי הודעות-טלפון = הפרת כלל "בדיוק שתיים ביום" (BRIEF §6); הסוכן מקצר ושולח אחת.
- (ה) T-259 (`mobile_relay`) — הרלה חיה (pid 1629, run 327) — לא בתחום-הלילה (launchctl, חלון-שבת).
- אין שינוי ב-`app.py` של Render (עמידות `_REPLIES` לדיסק אינה אפשרית ב-free-tier; המקור-העמיד נשאר `PHONE_THREAD.jsonl` + הרלה).

## 5 · אימות-בתנאי-המקור (למי שבא אחרי)
השליחה הבאה (סוכן-08:30 ב-08:30 — מופע קר, מחוץ לחלון-הרלה): לצטט את שורת-הפלט האחרונה של `phone_reply.py` ב-LIVE_CHANNEL. `ok render=verified` = T-260 נסגר בתנאי-המקור; `UNVERIFIED render=chat timeout` = cold-start > 57 שנ׳ — נרשם כמדידה, בלי שליחה שנייה.
