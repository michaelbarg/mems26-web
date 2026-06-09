# CC PROMPT — B4 Volume Artifact · ROOT DIAGNOSE ONLY · 2026-06-03

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** **אבחון-שורש בלבד — אפס שינוי קוד/נתונים, אפס filter, אפס סימון.** המטרה: לזהות **למה** הנפח מנופח, כדי ש-Michael יחליט אם לתקן במקור או לסמן/לסנן (הפיך).

## רקע
`v9_bars_5min` כולל ברים בנפח 540K–1,000,000 (`is_synthetic=0`), בעיקר בחלון settlement (~15:15–18:00 ET). מקס' ב-Sierra = ~72K. פער ×10–50. מעוות את ה-`rolling_avg` של VSA → משפיע על אילו setups של S2 עוברים (B1/firing). **זה שער איכות-הנתונים האחרון לפני יום SHADOW נקי.**

## אבחון (read-only, הדבק ראיה גולמית לכל צעד)
1. **בודד דגימה:** בחר בר ספציפי עם נפח מנופח (ts + volume מ-`v9_bars_5min`, `mode=ro`). הדבק.
2. **הצלבה מול המקור (SoT):** מה הנפח של **אותו ts** ב-`~/SierraChart_Data/v9_export/5min.json` (ו/או `5min_continuous.json`)? הדבק.
   - אם Sierra-export כבר מראה ~930K → המקור הוא ה-DLL/Sierra (לא ingestion) → שאלת מקור-אמת אחרת.
   - אם Sierra-export מראה ~72K אבל ה-DB מראה 930K → **ה-ingestion מנפח**. המשך ל-3.
3. **נתיב ה-ingestion:** קרא את `/5min` ב-`api/v9/bars.py` (אחרי המרת safe_writer). האם הוא **מסכם** נפח על פני דחיפות (INSERT OR REPLACE אמור להחליף, לא לצבור)? האם יש enrichment/UPSERT שמוסיף? האם דחיפות כפולות של אותו ts נספרות פעמיים? בדוק גם את `bar_ingestion.py` ו-`5min_continuous`.
4. **השערת settlement:** האם בחלון settlement Sierra שולח **נפח-סשן מצטבר** (cumulative) במקום per-bar? או שדה נפח אחר? בדוק את ה-payload הגולמי שהגשר שולח (לוג/דגימה).
5. **קבע שורש אחד** עם ראיה: (א) DLL/Sierra מייצא מנופח · (ב) ingestion מסכם/מכפיל · (ג) נפח-סשן-מצטבר מתפרש כ-per-bar · (ד) אחר.

## דוח (חלק C)
| צעד | ממצא | ראיה גולמית (ts, Sierra-json value, DB value) |
+ **שורש מאומת** + **fix מוצע** (במקור אם אפשר; אם סימון/סינון — הפיך, `is_synthetic`, לא מחיקה) — **אבל אל תיישם.** strategic-stop, החלטת Michael.
**אל תיגע בנתונים/קוד. read-only בלבד.**
