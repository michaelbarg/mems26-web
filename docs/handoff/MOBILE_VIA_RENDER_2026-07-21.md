# מוניטור-כיס דרך Render — רק הלינק, לא המערכת (מייקל 2026-07-21 ~19:50)

**הבקשה:** "שהלינק לפלאפון יעבוד דרך Render — רק הוא, לא כל המערכת" (ה-ZT בפלאפון נופל שוב ושוב ב-iOS).

## הארכיטקטורה (display-only, כלל-הברזל שמור)
```
Mac (מסחר, מקומי)                         Render (ענן, תצוגה-בלבד)          פלאפון (סלולרי/כל-רשת)
backend :8000 ──/api/v9/mobile/data──┐
                                     │ relay: POST כל 5ש' (outbound HTTPS)
LaunchAgent com.mems26.mobile_relay ─┴──► /api/v9/mobile/snapshot (in-memory) ──► GET /api/v9/mobile?key=…
```
- **שירות-Render מינימלי חדש** (קובץ FastAPI יחיד): מקבל snapshot (auth: מפתח ייעודי חדש `MOBILE_PUSH_KEY`,
  לא סודות-המערכת), שומר **בזיכרון בלבד** (בלי DB בענן), ומגיש את אותו עמוד-HTML-קל הקיים מ-`mobile_monitor.py`
  + באדג' "עדכון לפני Xש'" (ואדום כשה-snapshot מעופש >30ש').
- **במק:** LaunchAgent קטן שדוחף את פלט `/api/v9/mobile/data` המקומי ל-Render כל 5ש'. **outbound בלבד** —
  שום פתח-כניסה למק.
- **מה לא קורה:** ה-bridge לא נוגע ב-Render (כלל-Local-Only שמור) · אין DB בענן · אין פקודות/מסחר בענן —
  snapshot-תצוגה בלבד (פוזיציה, P&L, עסקאות-פעילות, מחיר) · **לא** מעירים את הפריסה-הישנה (503 היום) —
  מחליפים אותה בשירות-המינימלי או שירות חדש.

## מה הפלאפון מקבל
Bookmark חדש: `https://mems26-web.onrender.com/api/v9/mobile?key=<MOBILE_ACCESS_KEY>` — עובד מכל רשת
(סלולרי!), בלי ZeroTier, HTTPS. ה-ZT/Wi-Fi נשארים כגיבויים.

## הסתייגויות כנות
- Free-tier של Render נרדם אחרי ~15 דק' חוסר-פעילות → אבל ה-relay דוחף כל 5ש' ומחזיק אותו ער בשעות-מסחר
  (ה-relay רץ רק כשה-backend המקומי חי). קולד-סטארט ראשון בבוקר: ~30-50ש'.
- הנתונים בענן = תצוגה בלבד, מוגני-מפתח, ללא סודות-מערכת. ה-snapshot לא כולל dll/פקודות/מבנה.

## ביצוע (הלילה אחרי 23:00 — לא תוך-מסחר)
1. `render_mobile_relay/app.py` (שירות-מינימלי) + עדכון ה-Procfile/deploy ל-Render (git push).
2. `scripts/mobile_relay.py` + LaunchAgent `com.mems26.mobile_relay` (snapshot-push, backoff-שקט כש-Render ישן).
3. מפתח `MOBILE_PUSH_KEY` חדש ב-.env (מק) + env-var ב-Render. snapshot לפני (change-safety).
4. אימות חוק-5: פלאפון על סלולרי (בלי ZT/Wi-Fi) → 200 + נתונים חיים; ניתוק-relay → באדג'-מעופש אדום.
מבצע: cowork (זה infra-תצוגה, לא לוגיקת-מסחר). cursor מודע.
