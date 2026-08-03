# מעבר-ירי למחשב-השני — מחר בוקר (פסיקת-מייקל 02.08)

**עיקרון-על: לעולם לא שתי מכונות חמושות-לייב על אותו חשבון.** קודם מנטרלים כאן, אז מחמשים שם.

## מה מייקל עושה (לפי סדר, ~30 דק', לפני 16:00 IL)

1. **במחשב-השני:** לוודא ש-Sierra מותקנת ומחוברת; לפתוח טרמינל בריפו
   (`~/mems26/mems26_web_git` בד"כ) ולהריץ:
   `git pull && bash scripts/mems26_doctor.sh` — לעקוב אחרי `NEXT STEP →` עד שהדוקטור ירוק.
   (המדריך המלא לסוכן שם: `docs/handoff/SECOND_MACHINE_AGENT_GUIDE.md`.)
2. **העתקת הדגלים (קריטי — ‎.env לא בגיט):** להעביר את `.env` מהמקבוק (AirDrop/USB) לשורש-הריפו
   במחשב-השני. הוא כולל את פסיקות-היום: **2 חוזים T1+T2**, MAE-scratch, דלתא, LEG_RIDE, כל התקרות.
   אימות שם: `python3 scripts/flag_guard.py` → חייב `150/150 PASS`.
3. **DLL מעודכן (פסיקת-מייקל 03.08 — "חסר לי הנושא של DLL מעודכן"):** המקור היחיד הוא
   הריפו — `sc_study/MES_AI_DataExport_merged.cpp` מגיע עם `git pull` (כל תיקוני 08/‏07 בפנים).
   במחשב-השני: `./scripts/build_monolithic_cpp.sh --deploy` (עושה snapshot אוטומטית) →
   ‏Sierra שם: ‏Analysis ▸ Build Custom Studies DLL ▸ Remote Build → הסרה+הוספה מחדש של
   הסטאדי על הצ'ארט → ‏Input 4 = נתיב-הייצוא המקומי של אותה מכונה → לוודא ייצוא חי תחת
   `~/SierraChart_Data/v9_export/` (עדכון-שניה) + `scripts/mems26_verify.sh` שם חייב להראות
   ‏deployed==repo. **אימות-זהות:** אותו checksum כמו במקבוק (`shasum` על ה-cpp בשתי המכונות).
4. **נטרול המקבוק (המכונה הזו):** ב-Sierra המקומית — Trade ▸ Auto Trading OFF + מעבר לחשבון SIM.
   המקבוק נשאר פיתוח: backend/bridge ממשיכים לרוץ לצרכי-פיתוח, אבל לא חמוש ולא על חשבון-האמת.
5. **חימוש המחשב-השני (מייקל בלבד — cowork לא מחמש):** Sierra שם על חשבון-האמת 37138283,
   ‏Auto Trading ON, ולוודא `order_placement_armed` ברדאר (localhost:3000 שם).
6. **בדיקת-קצה שם:** `bash scripts/mems26_verify.sh` + `curl -s localhost:8000/api/v9/context/radar`
   — ‏day_type/פתיחה/שערים חיים, `is_sim` נכון, `contracts_allowed≈2`.

## מה הסוכנים עושים

- ‏cc במחשב-השני: מריץ את הדוקטור, סוגר פערי-התקנה, מריץ startup_check, מדווח ל-LIVE_CHANNEL.
- ‏cowork (כאן): ממשיך פיתוח; כל שינוי-קוד מגיע למחשב-השני רק דרך `git pull` + ריסטארט מכוון שם.
- ‏watch-חצי-שעתי/17:30: ⚠️ מכוונים ל-localhost — אחרי המעבר חייבים לרוץ **על המחשב-השני**
  (או להסב ל-ZeroTier-URL שלו). לא לסמוך על ריצה מהמקבוק.

## GO-gate (מתוך DEV_PLAN §P5)
דוקטור ירוק שם · flag_guard 150/150 שם · DLL==repo שם · פיד חי שם · המקבוק מנוטרל — רק אז חימוש.
