# MEMS26 · פרוטוקול קבוע לפני מסחר (Pre-Trade Health & Connectivity)

**מטרה:** לוודא לפני כל יום מסחר שהמערכת **עובדת, מחוברת, ומסונכרנת** מקצה-לקצה — לפני שמסתמכים על נתוני SHADOW/DEMO/LIVE.
**מתי:** T-30 דק' לפני פתיחת RTH (16:00 IL / 09:00 ET), שוב ב-T-0 (פתיחה), ו-T+60 (נעילת IB ~10:30 ET).
**איך:** רוץ כל phase, סמן PASS/FAIL עם ראיה גולמית (Rule 5). FAIL = לעצור ולתקן לפני שסומכים על הנתונים.
**עיקרון:** source-of-truth — כל ערך מ-Sierra (חי), אפס סינתוז. אם ערך לא תואם Sierra → תקלת חיבור/סנכרון, לא "כמעט נכון".

---

## Phase 0 · שירותים למעלה (T-30)
- [ ] **Backend:** `curl -s localhost:8000/health` → `alive:true, mode:shadow`. `lsof -i :8000` → uvicorn יחיד (לא כפול).
- [ ] **Frontend:** `lsof -i :3000` → Node מאזין. הדאשבורד נטען.
- [ ] **LaunchAgents:** `launchctl list | grep mems` → `com.mems26.backend` **וגם** `com.mems26.bridge` פעילים (auto-restart).
- [ ] **Sierra פתוח:** chart 12 (Woodies/DLL) · chart 3 (TPO/Value-Area) · chart 5 (24h רציף) — כולם רצים.
- 🚩 *FAIL נפוץ:* backend מת בלי auto-restart → DISCONNECTED. (תוקן ע"י LaunchAgent — לוודא שעדיין שם.)

## Phase 1 · גשר + streams טריים (T-30)
- [ ] `python3 scripts/sot_health.py --strict` → אין 🔴.
- [ ] כל קבצי ה-export ב-`~/SierraChart_Data/v9_export/` FRESH (<5s): `5min`, `woodies_5min`, footprint, `tick_reversal`, `tpo`, `5min_continuous`, `cumulative_delta_continuous`, `live_price`.
- [ ] Bridge heartbeat: `streams=N/N`, **0 push errors** מאז ה-restart. **local-only** (אין `push FAILED to https://...`).
- 🚩 *FAIL:* קובץ stale / stream DEAD → לאבחן (DLL? path? chart לא רץ?).

## Phase 2 · חיבור + מחיר חי (T-30)
- [ ] דאשבורד = **LIVE** (לא DISCONNECTED), שני האינדיקטורים.
- [ ] מחיר עליון זז ("1s ago"), ותואם Sierra (±tick).
- [ ] פאנל Woodies מציג מחיר חי (לא תקוע על ערך ישן).
- 🚩 *FAIL:* מחיר תקוע = מקור live קפוא (sc.Close overnight) — `_best_price` midpoint אמור לתפוס.

## Phase 3 · סנכרון מול Sierra (T-30 + T-0) — הליבה
לכל ערך: **Sierra (ground-truth) == export == backend == dashboard**. סמן כל מקום שמתפצל.
- [ ] **מחיר** = Sierra.
- [ ] **IB** (chart 12 Study ID:6): high/low/width = Sierra.
- [ ] **POC/VAH/VAL** (chart 3 — **לא chart 12!**): = Sierra chart 3. 🚩 אם תקוע/שגוי → לבדוק שהגשר קורא מ-chart 3 הנכון.
- [ ] **Woodies studies** (chart 12): CCI/TCCI/SWI/CZI/LSMA/EMA/Proj/trend = Sierra. ב-RTH `studies_stale=false`. 🚩 overnight = "Last RTH" badge (תקין); ב-RTH חייב חי.
- [ ] **נרות 5-דק'** רציפים (chart 5, 24h), OHLC overnight אמיתי (לא O=H=L=C קפוא).
- 🚩 *FAIL:* ערך ≠ Sierra → תקלת גשר/סנכרון/chart-source, לא להתעלם.

## Phase 4 · 6 המערכות מקבלות + מסווגות (T-0 → T+60) — קריטי
- [ ] **S1 Day Type:** `bar_count` **עולה** (המנוי `_day_type_on_bar` יורה!) · opening_type מסווג · **IB מזוהה ונועל ~10:30 ET** · day-type מתקדם A1→C ומסווג **לפי האפיון** · confidence. 🚩 *FAIL נפוץ:* bar_count=0 = המנוי נשבר באתחול (כשל שקט — לבדוק לוג init).
- [ ] **S2/S3/S4 יכולים לירות:** כל מערכת — חסומה-באג מול אין-setup (תקין). לפחות אחת יורה ב-session פעיל.
- [ ] **רוב התבניות ARMED שעות אל תוך RTH:** אם לא — 🚩 בדוק wiring: S4 `bar_count` עולה + `trend_state` לא תקוע GRAY (אחרת A1 חוסם הכל) · S2 `opening_type≠NA` (S1 מפרסם classification event). הבחן wiring-bug מ-"אין setup לגיטימי".
- [ ] **S5 TPO / S6 Killzone:** מציגים נתון.
- [ ] **Build Status:** section S1 מציג opening/IB/day_type/lock/confidence/stage (לא "—").
- 🚩 *FAIL:* day-type/IB "—" אחרי שיש ברים = כשל אתחול/מנוי, לא חוסר-בשלות.

## Phase 5 · דגלים + בטיחות
- [ ] **5 דגלי כיול** ON ב-runtime (לא רק ב-.env — LaunchAgent קורא מ-plist!): `S2_ATR_RELATIVE, S3_RELATIVE, S1_IB_WIDTH_ATR, S1_CVD_OPENING, S1_DAYTYPE_STAGING`. ואימות **שינוי-התנהגות** (לא רק True).
- [ ] **mode=shadow**, demo/live=null. 5 שערי סיכון ירוקים.
- [ ] **firing RTH-gated:** overnight אפס fires (6 השערים). **frozen-tail:** ב-RTH CCI משתנה על ברים שונים (לא frozen).

## Phase 6 · עסקאות + DB
- [ ] עסקאות נרשמות (fires=rows, אפס drops). management-log מתמלא (stop moves/BE/targets).
- [ ] synthetic מסומן "TEST" (לא מזהם סטטיסטיקות). אפס synthetic חדשות בפרוד.
- [ ] DB: אין future-ts, אין flat-stale, אין @5900.

---

## 🚩 כשלים ידועים (מה לחפש קודם)
| סימפטום | שורש סביר | תיקון |
|---|---|---|
| DISCONNECTED | backend מת | LaunchAgent / restart |
| מחיר תקוע | sc.Close קפוא overnight | `_best_price` midpoint / chart 5 |
| POC/VAH/VAL שגוי | גשר קורא מ-chart לא נכון (לא chart 3) | תיקון גשר (לא DLL) |
| Woodies stale | chart 12 RTH-only | badge overnight / חי ב-RTH |
| day-type/IB "—", bar_count=0 | מנוי `_day_type_on_bar` נשבר (כשל init שקט) | לחשוף שגיאה (print/INFO) → לתקן subscribe |
| דגל ON אך לא משפיע | .env לא נטען ב-LaunchAgent / wiring חלקי | plist EnvironmentVariables + לאמת שינוי-התנהגות |
| נרות לא רציפים | export RTH-only | chart 5 24h |
| **תבניות לא נדרכות (ARMED) שעות אל תוך RTH** | S4 `_bar_count` לא נספר → trend תקוע GRAY/YELLOW → **A1 חוסם את כל 9 התבניות** | WoodiesSystem להגדיל `_bar_count` בכל בר → trend מתקדם BLUE/RED |
| S2 `opening_type=NA` → תבניות S2 חסומות | S1 לא מפרסם `day_type_classification` event ל-BarRouter | S1 לפרסם event (opening_type+day_type) → S2 צורך |

## הערות
- **.env לא נטען ב-LaunchAgent** — משתנים קריטיים חייבים להיות ב-plist `EnvironmentVariables`. תקלות init מושתקות אם הלוגינג לא ב-INFO.
- כל אימות = ראיה גולמית (curl/SQL/screenshot/Sierra-vs-dashboard). אל תאשר "נראה בסדר".
- FAIL ב-Phase 0-3 = לא לסמוך על נתוני היום עד תיקון. FAIL ב-Phase 4-6 = הנתונים חלקיים/מזוהמים.

*פרוטוקול קבוע — לעדכן כשמתגלים כשלים/שערים חדשים.*
