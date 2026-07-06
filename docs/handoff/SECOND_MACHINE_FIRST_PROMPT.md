# פרומפט-פתיחה למכונה השנייה — העתק-הדבק לסוכן שם

_הדבק את הבלוק הבא ל-Claude Code או ל-Cowork **על המכונה השנייה** (זו שסיארה עליה, שבה הרצת את
`RUN_ME.command`). אם הסוכן לא יודע איפה הריפו — אמור לו: בד"כ `~/mems26/mems26_web_git`._

---

```
אתה סוכן שמפעיל את מערכת-המסחר MEMS26 על מכונת-מסחר שנייה שלי (מאק, סיארה מותקנת).
הרצתי את RUN_ME.command מחבילת-ההתקנה ונתקעתי. אני רוצה שתסיים את ההתקנה ותפעיל הכל.

עבוד כך, בדיוק בסדר הזה:

1. מצא את הריפו (בד"כ ~/mems26/mems26_web_git) ועבור אליו.
2. הרץ שוב את המתקין — הוא idempotent ולא דורס .env, ומשלים כל מה שחסר
   (venv, תלויות, DB, סכימה, frontend, LaunchAgents):
      bash install/install_mems26.sh --repo "$PWD"
   קרא את כל הפלט; אם משהו נכשל, זהו נקודת-ההיתקעות — טפל בה.
3. אבחון (אם scripts/mems26_doctor.sh קיים — הרץ אותו; קורא-בלבד, מסתיים ב-"NEXT STEP →"):
      bash scripts/mems26_doctor.sh
   אם הוא לא קיים אצלך עדיין, השתמש בבדיקה-העצמית שכן קיימת:
      bash scripts/mems26_startup_check.sh
4. בצע את ה-NEXT STEP, הרץ שוב, חזור — עד שאין ❌.
5. אמת סופית:  curl -s localhost:8000/api/v9/health   → אמור להחזיר {"status":"ok"}
6. אם אין feed מסיארה — הדרך אותי בשלבי-הסיארה מ-install/SIERRA_SETUP_CHECKLIST.md.
7. אם קיים docs/handoff/SECOND_MACHINE_AGENT_GUIDE.md — קרא אותו למדריך-התפעול המלא.

חוקים מחייבים:
- הכל localhost בלבד; אל תדחוף ל-git מהמכונה הזו.
- אל תדליק שום דגל trading-risk (LIVE/halt/OPENING_WINDOW_FIRE_V1/EOD...) בלי אישור מפורש שלי.
- החלטות-סטנדינג נשארות כבויות (chop/cooldown/COT-AMT).
- לפני כל שינוי ב-.env/DLL/LaunchAgent: scripts/mems26_snapshot.sh "סיבה".
- ראיה-ולא-טענה: כל "תוקן/עובד" → הדבק את הפקודה והפלט הגולמי.

התחל עכשיו מ-mems26_doctor.sh והראה לי את הפלט + מה ה-NEXT STEP.
```

---

**אם אתה מעדיף Cowork:** אותו פרומפט עובד. ודא ש-Cowork קיבל גישה לתיקיית הריפו (`~/mems26/mems26_web_git`).

**אם הסוכן צריך את כל ההקשר של הפרויקט:** הכל כבר בריפו — `CLAUDE.md` (כללי-העל),
`docs/handoff/SECOND_MACHINE_AGENT_GUIDE.md` (התפעול), `install/README_INSTALL.md` (ההתקנה).
לא צריך לשלוח קבצים בנפרד; חבילת-ההתקנה כבר הביאה את כולם.
