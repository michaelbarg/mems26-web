# CC PROMPT — הדלקת דגלי הכיול ב-SHADOW (flag-ON) · 2026-06-01

**מקור:** Cowork (Michael: "להדליק את הכיול") · **מצב:** SHADOW בלבד
**הקשר:** 5 דגלי הכיול מחווטים ומאומתים (`70848a6` + הצלבת Cowork). כעת להדליק flag-ON **לפני RTH** (~16:30 IL) כדי שהאיסוף יהיה על הלוגיקה החדשה. ⚠️ **הדוח ציין ש-`.env` לא נטען ב-LaunchAgent** — לכן הדגלים שב-.env לא חלים ב-runtime; ההדלקה חייבת להיות ב-plist.
**משמעת:** Rule 5 (לאמת ב-runtime, לא רק לערוך קובץ) · אפס שינוי order/risk/sizing · firing נשאר RTH-gated.

## משימות
1. **אמת מצב נוכחי:** הראה את ערך 5 הדגלים כפי שה-backend קורא אותם ב-runtime (endpoint/לוג/`/api/v9/.../flags` או הדפסה מ-`shared/atr.py`). צפוי: OFF (כי .env לא נטען).
2. **הדלק ב-plist:** הוסף ל-`~/Library/LaunchAgents/com.mems26.backend.plist` תחת `EnvironmentVariables` (כמו ש-CLOUD_URL מקודד שם):
   `S2_ATR_RELATIVE=true · S3_RELATIVE=true · S1_IB_WIDTH_ATR=true · S1_CVD_OPENING=true · S1_DAYTYPE_STAGING=true`.
   שמור גם את `.env` מסונכרן (כבר =true). **אל תיגע** ב-KeepAlive/CLOUD_URL/V9_DISABLE_WATCHDOG הקיימים.
3. **Restart** ה-backend (launchctl unload/load) כך שהדגלים ייטענו. בדוק listeners קודם (אל תכפיל).
4. **אמת ב-runtime (Rule 5 — פלט גולמי):**
   - 5 הדגלים נקראים **True** ב-backend החי.
   - **בדיקת שינוי-התנהגות** לכל אחד (לא רק שהם True): S3 → `min_level_vol=0.3×median` (median>0); S1_IB_WIDTH_ATR → tiers ATR (כולל EXTREME); S1_CVD_OPENING → opening מ-CVD; S1_DAYTYPE_STAGING → conf capped לפני 60min; S2_ATR_RELATIVE → expansion=1.5-2×ATR. הדבק ראיה (לוג/endpoint).
5. **תוכנית החזרה per-flag:** אם דגל מתנהג רע ב-RTH → false ב-plist + restart. תעד.

## פלט
עדכון קצר ב-`docs/reports/` או שורת STATUS_BOARD: ערכי הדגלים לפני/אחרי + ראיית runtime + שינוי-התנהגות. 

**שערים:** SHADOW בלבד · flag-ON משנה התנהגות detection (צפוי — לצפות בקצב ירי/התפלגויות ב-RTH) · אפס שינוי order/risk/sizing · firing RTH-gated ללא שינוי. **המלצה:** לתקן בנפרד את טעינת `.env` ב-LaunchAgent (follow-up, לא חוסם — בינתיים plist הוא מקור-האמת).
