# רשימת פערים — Frontend שלב‑1 (Trades redesign) · 2026‑06‑04

בדיקת מוכנוּת לפני מסירה למפתח. נבדק מול הקוד בפועל (לא מהזיכרון).
**מסקנה כללית: שלב‑1 בנוי ~90% ממה שכבר קיים — אין חוסם קשיח.** למטה 7 פערים/הכרעות
שכדאי למסור למפתח **לפני** שמתחיל, כדי למנוע rework. כל סעיף מסומן: 🟢 קיים/אין פער ·
🟡 פער קטן (תוסיף helper/באנר) · 🔵 הכרעה למייקל/בק‑אנד.

---

## A. תשתית בדיקות + verify (🟡 — הפרומפט דורש, חסר script)
הפרומפט (§2) דורש *"paste typecheck + build raw"* + *"regression test לכל תיקון"*, אבל
ב‑`frontend/v9/package.json` יש רק `dev / build / start / lint` — **אין `test` ואין `typecheck`**.
- הבדיקות הקיימות רצות דרך `node --test src/v9/lib/__tests__/*.test.ts` (Node 22 מפשיט TS לבד).
  אימתתי: `node --test src/v9/lib/__tests__/tradeMath.test.ts` → **6 pass / 0 fail**.
- typecheck: `npx tsc --noEmit` (יש `tsconfig.json`); או להסתמך על `next build` שמטפס.
- **למסור למפתח:** פקודות ה‑verify המוסכמות הן `npx tsc --noEmit`, `npm run build`,
  ו‑`node --test <file>`. כדאי להוסיף scripts `typecheck`/`test` ל‑package.json (smallest change).

## B. 1a — מסנן תאריך ET (🟡 — חצי‑helper קיים)
`lib/tradeTime.ts` כבר מכיל המרות ET (`fmtDateET`, `toTradeDate`, ET_TZ) — **אבל אין פורמטר
`YYYY-MM-DD`**. הפרומפט מבקש בדיוק `Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York'})`.
- **פעולה:** הוסף helper קטן `etDateKey(ts)` ל‑`tradeTime.ts` והשתמש בו ב‑`tradeStore.ts:115`
  במקום `slice(0,10)`. שני צידי ההשוואה יהיו אז `YYYY-MM-DD` בזמן ET (כולל `<input type="date">`
  שכבר מחזיר `YYYY-MM-DD`). אין פער נתונים — רק helper חסר אחד.

## C. 1c — gating של day_type/killzone (🔵 — ניואנס‑חוזה, לאשר)
- `day_type` **כבר קיים** כשדה על `Trade` (`types/index.ts`, runtime מ‑cross_context).
  לפי החוזה (§4 בערכה) צריך **בכל זאת לגייט אותו "pending G1"** עד שתנחת `day_type_at_entry`.
  → לוודא שהמפתח **לא** מחווט את `t.day_type` הקיים, אלא משאיר אפור — אחרת זה שובר את
  ה‑seam מול G1.
- `killzone/session` — **אין שדה כלל** על `Trade`. gating הוא הברירה היחידה ממילא. ✅ תואם חוזה.
- **הכרעה למייקל:** מאשר לגייט גם את `day_type` הקיים? (הערכה: כן, לפי הכוונה ב‑KIT.)

## D. 1e — Heat MAE/MFE **לא** צריך gating (🔵 — בשורה טובה, לתקן הנחה)
הפרומפט אמר "MAE/MFE מצרפי אם זמין, אחרת pending G4". בפועל השדות **קיימים** על `Trade`:
`mae_pts`, `mfe_pts`, `price_high`, `price_low`, `t1_closest_pts`, `t1_at_mfe_pts`, `t1_reached`.
→ לבנות אותו **חי מהשדות הקיימים, בלי gate G4**. הערה: היחידות הן **נקודות (pts), לא R**.

## E. 1e — Equity Curve אין תלות endpoint (🟢 — אין פער)
`EquityCurveStrip.tsx` כבר client‑side מלא (`equityCurveByClose(trades)` מה‑store), `recharts`
ב‑deps. רק **mount** ל‑TradesView + באנר *"≤500 שורות — אינדיקטיבי"*. אימתתי: `fetchTrades`
default `limit = 500` → המספר בבאנר הוא 500.

## F. 1f — ציר price/time: הפער האמיתי היחיד (🔵 — הכרעת בק‑אנד)
על `Trade` הבסיסי **אין חותמות‑זמן לכל יעד**: רק `entry_ts` ו‑`exit_ts` נושאים `ts`;
`t1/t2/t3` הם מחירים + בוליאני `*_hit` בלבד, **בלי זמן‑פגיעה**. ⇒ ציר‑זמן אמיתי יכול למקם
רק entry + exit. זמני הפגיעה של T1/T2/T3 **אולי** זמינים ממסך‑הפרטים: `fetchTradeById` מחזיר
`management_log[]` שיש לו `ts`, וגם `lifecycle[]` — אבל ה‑interface `LifecycleEvent` כיום ללא `ts`,
ואוצר‑המילים של אירועי ה‑log לא מתועד כאן.
- **הכרעה למייקל/בק‑אנד:** האם `management_log`/`lifecycle` נושאים timestamp לפגיעת T1/T2/T3?
  - אם כן → 1f ממקם אותם על ציר‑הזמן.
  - אם לא → ציר‑הזמן = entry+exit בלבד, ו‑T1/T2/T3 נשארים על ה‑R‑path (`TradePathVisual`),
    **בלי לסנתז** קו‑זמן (= Rule 1). זה הפריט היחיד שבו "+ ה‑ts שלהן כעמודות" אינו מלא משדות קיימים.

## G. 1h — Scratch/BE כבר נכון, תוספת זעירה (🟢/🟡)
המימוש הקנוני הנכון כבר קיים ב‑`PatternPerformanceStrip.tsx:71‑81` (סופר scratch כש‑`pnl==0`).
לשמר אותו ב‑Edge Matrix. **תוספת קטנה:** הפרומפט רוצה `pnl==0` **או** `outcome==BE`; כיום נספר
רק `pnl==0`. להוסיף `outcome==='BE'` לדלי ה‑scratch.

---

## פריטים שאין בהם פער (לאישור מהיר)
- **1b presets** 🟢 — client‑side מעל ה‑helper של 1a, ללא backend.
- **1d exec‑mode** 🟢 — `auxStatus.{liveEligible,isParallel,blockedBy}` קיימים; יש כבר פילטר
  `liveGated` ב‑store. רק UI, אפס לוגיקת‑gating חדשה.
- **1g stops panel** 🟢 — `stopMovement()` מחזיר moved/t1_no_be/static משדות קיימים.

## הערת‑רוחב (caveat אחד למסור)
`fetchTrades()` נקרא **ללא ארגומנטים → כל ה‑modes, `limit=500`**. כל אגרגציה client‑side
(Edge Matrix / equity / presets) היא מעל ≤500 העסקאות האחרונות. ⇒ preset כמו MTD/30d מסנן
**בתוך** ה‑500 הטעונים, לא בשרת; אם בחלון יש >500 עסקאות, הישנות חסרות בשקט. סינון‑תאריך
שרת‑צד = DEFERRED. זה בדיוק התוכן של באנר ה‑"אינדיקטיבי".

---
**שורה תחתונה למייקל:** אפשר לשלוח את פרומפט ה‑frontend כמו שהוא. 3 ההכרעות שדורשות תשובה
לפני/תוך‑כדי עבודה: **C** (לגייט day_type הקיים? כן), **D** (לבטל gate ל‑MAE/MFE — קיים), **F**
(האם ל‑log יש זמני T1/T2/T3 — קובע אם ציר‑הזמן מלא או entry+exit בלבד). השאר הוא תוספת
helper אחת (B) + באנר (E) + scripts (A).
