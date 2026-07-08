# CC — סדר עבודה 2026-07-09 (בוקר → סשן) · הוכחות סיירה

**מצב פתיחה:** כל קוד 07-08 פרוס וחי (ריסטארט 21:43 אמש, flat): רצועת-סטופ, ‏auth-key fix,
יתומה/slot, לדג'ר+יומן, ‏TP-1 clamp ‏ON, ‏structure-trail ‏ON, ‏NEUTRAL_RESPONSIVE ‏ON.
‏flag_guard: ‏31/31 · ‏fire-drill: 🟢. ‏DLL לא השתנה — אין rebuild. צ'אט-S1 עובד על מערכת 1
(אל תיגע בה); צ'אט-מערכות על S6-alerts/UI. אתה = סיירה + הוכחות חיות. ‏Rule 5 על הכל —
ראיות ל-`docs/reports/evidence_2026-07-09/`.

## עדיפות 1 — לפני הפתיחה (עד 16:00)
1. `git push` (32+ קומיטים) · `scripts/mems26_verify.sh` · snapshot אם תיגע ב-out-of-git.
2. **הזנת TradeActivityLog ללדג'ר (L8 — הפריט הכבד):** ‏fills היסטוריים + ‏sierra_stop +
   היסטוריית stop-moves לפי `CC_SIERRA_LIVE_LEDGER_2026-07-07.md`. חובה כדי: (א) לזהות
   פעולות ידניות של מייקל, (ב) **לתקן את ה-P&L האמיתי של עסקה 310 מאמש** (נרשמה +$45 במחיר
   מקורב — להצליב מול הפילל האמיתי ולעדכן את הרשומה + הלדג'ר).
3. **‏SIM proof אחד, 2 חוזים** (מחוץ ל-RTH): ‏ORDER_SUBMITTED error=0 (חימוש) · לוג
   `registered order → trade` ב-ack (מפת ה-id חיה) · בראקט = בדיוק 2 קבוצות OCO ·
   ‏`/trades/active` מציג "0/2" · flatten נקי + slot משוחרר.
4. **אימות אכיפת הטבלה:** אפס אזהרות `no auth cell` לתבניות S2 בבוקר; נסה לוודא ש-SKIP
   נאכף (ה-cell ‏INITIATIVE×Neutral) — עדות מהלוג.

## עדיפות 2 — במהלך הסשן (על עסקאות אמיתיות)
5. **‏T1 אמיתי ראשון:** הדבק את שורת `sc.ModifyOrder` מה-message-log (הוכחת L2 החסרה) +
   ראיה שהסטופ חנה ב**מבנה** (structure-trail) ולא ב-BE — השווה ללוג `structure-trail anchor`.
6. **ירי ZLR ראשון:** מנותב מקצה לקצה, אפס `FIRE DROPPED` (סגירת L1 סופית).
7. **‏fill אמיתי ראשון:** נקלט בלי fallback (חפש `registered order`, לא `I-58`) — סגירת L4.
8. **הלדג'ר ב-`/board`:** העסקאות של היום מופיעות חיות + reconcile ללא CRITICAL (‏V1–V5).

## עדיפות 3 — לא חוסם
9. הבר הישן 06-09: ה-exports נקיים — בדוק את ה-stream הלא-רציף `bars_5min` של ה-bridge
   (נתיב קובץ/זיכרון תהליך) ונקה.
10. **מחקר המימושים המלא** על psql ‏(30 יום) לפי `RESEARCH_PROMPT_TP_AUDIT_2026-07-08.md` —
    ‏v1 של אמש נעצר על חלון-API קצר; ה-harness: `scripts/tp_audit.py` (הסב ל-psql).
11. טסט-guard ל-varchar overflow (שייר ea868cc).

**כללים:** אין שינויי דגלים (‏flag_guard חייב PASS) · אין ריסטארט כשעסקה פתוחה · תקלה חדשה
בנתיב-הכסף = עצירה + מייקל · כל סעיף שנסגר → עדכון `task_board.json` + היומן באותו קומיט.
