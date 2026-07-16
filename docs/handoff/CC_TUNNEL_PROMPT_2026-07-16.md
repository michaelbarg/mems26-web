# פרומפט ל-cc-imac — לינק-כיס מכל-מקום דרך Cloudflare Tunnel · 2026-07-16

**מטרה:** מייקל צריך לפתוח את מוניטור-הכיס מהטלפון **מכל רשת (כולל סלולר)**, בלי ZeroTier/VPN.
‏ZeroTier נכשל בנייד (MTU 2800 בתוכנית-חינם, לא ניתן לשנות). הפתרון: **Cloudflare quick tunnel** —
פרוקסי-קריאה מוצפן מול הבקאנד המקומי, נותן כתובת ‏https ציבורית. **הנתונים נשארים מקומיים** (לא מפר bridge-local-only).

**בטיחות — לפני חשיפה ציבורית:** ‏cowork הוסיף שער-סיסמה (‏commit `a402257`, ‏`MOBILE_ACCESS_KEY`).
בלי המפתח בכתובת → ‏401. חובה לפרוס אותו לפני שהטאנל עולה, אחרת כפתור-ההשטחה חשוף.

## צעדים (‏iMac, ~10 דק', בלי ריסטארט-מסחר; אפשר תוך-כדי הצ'ק-ליסט)

1. **משוך את השער:** ‏`git pull` (חייב לכלול `a402257` — ‏`grep MOBILE_ACCESS_KEY backend/v9/api/v9/mobile_monitor.py`).

2. **הגדר מפתח-גישה + הפעל:** צור מחרוזת אקראית והוסף ל-.env, ואז ריסטארט-בקאנד **רק אם אתה FLAT**
   (אם לא-flat — דחה עד flat; אין דחיפות-מסחר בזה):
   ```
   KEY=$(python3 -c "import secrets;print(secrets.token_urlsafe(9))")
   grep -q '^MOBILE_ACCESS_KEY=' .env && sed -i '' "s|^MOBILE_ACCESS_KEY=.*|MOBILE_ACCESS_KEY=$KEY|" .env || echo "MOBILE_ACCESS_KEY=$KEY" >> .env
   echo "KEY=$KEY"   # דווח אותו ל-SYNC (מייקל צריך אותו בלינק)
   ```
   ריסטארט → אמת: ‏`curl -s localhost:8000/api/v9/mobile/data` → **401** (שער פעיל) · ‏`curl -s "localhost:8000/api/v9/mobile/data?key=$KEY" | head -c 60` → ‏JSON (מפתח עובד).

3. **התקן cloudflared** (בלי brew — בינארי ישיר):
   ```
   curl -L -o /usr/local/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-$([ "$(uname -m)" = arm64 ] && echo arm64 || echo amd64)
   chmod +x /usr/local/bin/cloudflared && cloudflared --version
   ```
   (הורדת-בינארי לכלי-רשמי — לפי כללי-הבטיחות מותר; מקור=github הרשמי של cloudflare.)

4. **הרם טאנל-מהיר** (רקע, קבוע-חי):
   ```
   nohup cloudflared tunnel --url http://localhost:8000 > /tmp/cf_tunnel.log 2>&1 &
   sleep 8 && grep -Eo 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/cf_tunnel.log | head -1
   ```
   זה מדפיס כתובת כמו ‏`https://random-words.trycloudflare.com`.

5. **בנה את הלינק הסופי + אמת מבחוץ:**
   ‏`URL="https://<...>.trycloudflare.com/api/v9/mobile?key=$KEY"` — ‏`curl -s "$URL" | grep -c מוניטור` (≥1).

6. **דווח ל-SYNC + מייקל:** את הלינק המלא (עם ‏?key=). **זה הלינק שמייקל שומר למסך-הבית — עובד מסלולר, בלי אפליקציה.**
   ‏NOT-DONE אם משהו נכשל, עם הפלט הגולמי.

## הערות
- טאנל-מהיר מקבל כתובת חדשה בכל הרצה. אם הוא נופל — הרם שוב ודווח כתובת חדשה. (טאנל-קבוע-בעל-שם = שלב-הבא, דורש חשבון-Cloudflare חינם; לא היום.)
- אם ‏cloudflared חסום ברשת — נסה ‏`--edge-ip-version 4`. עדיין נכשל → דווח, ניפול חזרה ל-ZeroTier MTU דרך חשבון בתשלום.
- אין נגיעה בלוגיקת-מסחר, בדגלים, או בפוזיציה. קריאה-בלבד + טאנל.
