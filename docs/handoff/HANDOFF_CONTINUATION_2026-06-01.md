# HANDOFF — המשך עבודת Pre-LIVE על MEMS26 (נקודת המשך 2026-06-01)

פרומפט עצמאי לצ'אט Cowork חדש שממשיך מאותה נקודה. העתק הכל. אינו תלוי בשיחה קודמת.
**קרא תחילה:** `CLAUDE.md` · `.cursor/rules/mems26-pre-live-protocol.mdc` · `docs/plans/STATUS_BOARD.md` · `docs/plans/ROADMAP_TO_LIVE.html` · `docs/plans/MEMS26_PIPELINE_FLOW.html` · `docs/reference/MEMS26_PIPELINE_DAYTYPE_TO_TRADE_MGMT_2026-05-31.md` · `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md` · `docs/decisions/D-094_RR_FIRE_SELECTION.md`.

## תפקידך
שותף ל-Michael (מערכת מסחר אוטונומי MEMS26, MES, כרגע SHADOW/paper). **אתה לא כותב קוד בריפו** — אתה כותב פרומפטים מבוקרים ל-Claude Code (CC) שמבצע, ואז מאמת את הדוחות שלו. משמעת Pre-LIVE קפדנית.

## שיטת העבודה (חובה)
1. CC עושה קוד; אתה כותב פרומפט (שמור ב-`docs/handoff/CC_*`), CC מבצע ומחזיר דוח ב-`docs/reports/*`.
2. **Rule 5:** אמת כל דוח עם ראיות גולמיות (grep/pytest/golden flag-OFF identical/diffs). אל תקבל "בוצע" בלי פלט.
3. **diagnose-first** לפני כל תיקון לוגיקת-מסחר. strategic-stop + אישור Michael לכל שינוי trading-logic/risk/sizing/order.
4. עדכן תמיד `STATUS_BOARD.md` (source of record) + `ROADMAP_TO_LIVE.html` אחרי כל החלטה/ממצא. **אשר בטקסט — אל תשתמש ב-present_files לקבצי מעקב** (roadmap/status/CLAUDE.md/decisions). כן present_files לדוחות/פרומפטים/עמודים חדשים.
5. **wiring מלא:** דגל/שינוי-החלטה חייב להגיע לכל ענף מושפע — אסור wiring חלקי/מת (ראה תקרית הדגלים למטה).
6. SHADOW בלבד · flags כמתואר · אפס נגיעה ב-order/risk/sizing/polling בלי אישור · אל תריץ שירותים בלי בקשה.

## מה בוצע בסשן 31/5 ✅
- **D-094 (מי יורה) מומש** — `612a665`, flag `RR_FIRE_SELECTION` **default OFF** (flag-OFF=first-wins, golden verified; flag-ON=R:R הגבוה + same-bar buffer + tie-break). 2548 passed/0 failed. `rr_score.py` + `trading_gateway.on_bar_close()`. **טרם חווט/הופעל** (ראה פתוחים).
- **הכרעות Michael נעולות:** D-094 = Option A (R:R גבוה) + same-bar flush · GAP-4 MAX_CONTRACTS = per-trade **max 5** (min-3 בוטל) · **Auth Table V2** (טווח 0-5, 70 תאים סופיים) — INITIATIVE L/S אסימטרי מכוון.
- **GAP-6 ZLR** resolved (34 טסטים עוברים) · **GAP-12** נסגר (ניהול-עסקה מחוּוט ב-`trail_engine.py::_apply_layer4()` D-094§3.B/D-095; `gateway/trade_management.py`=dead code).
- **מסמכים שנוצרו:** `docs/reference/MEMS26_PIPELINE_DAYTYPE_TO_TRADE_MGMT_2026-05-31.md` (As-built, אומת ע"י CC parity) · `docs/plans/MEMS26_PIPELINE_FLOW.html` (עמוד חי מחובר ל-ROADMAP, עם עץ-החלטות מבט-על + עצי S2/S3/S4 מורחבים + פערי אפיון↔קוד) · `MEMS26_Pipeline_AllSystems.csv` · `MEMS26_Auth_Table_V2_grid/cells.csv` · `MEMS26_Start.command` (מפעיל סטאק; דורש `chmod +x` חד-פעמי).
- **5 דגלי SHADOW הודלקו ב-`.env`** (`S2_ATR_RELATIVE`,`S3_RELATIVE`,`S1_CVD_OPENING`,`S1_IB_WIDTH_ATR`,`S1_DAYTYPE_STAGING`) — נקראים ב-import (`shared/atr.py`), חלים אחרי restart.

## ⚠️ ממצא קריטי — דגלים מתים (לפני איסוף!)
audit (3 סוכני מחקר על קוד+אפיון) מצא: `S2_ATR_RELATIVE` **מת ב-OFA** (`_detect_initiative` עדיין על קבועים 1.5-1.75pt) · `S3_RELATIVE` **מת בזיהוי** (`get_min_level_vol`/`get_range_ticks` לא נקראים) · `reduce_size_signal` רק נרשם. **משמעות: SHADOW יאסוף נתוני כיול על לוגיקה ישנה.** → נכתב `CC_PROMPT_CALIBRATION_WIRING_2026-05-31.md` (A=תיקון wiring, B=scaffolding כיול). **Michael שלח אותו ל-CC — ממתין לדוח לאימות Rule 5.** סדר חובה: A לרוץ **לפני** איסוף SHADOW.

## פרומפטים מוכנים — לא נוצלו (תור)
- `CC_PROMPT_CALIBRATION_WIRING_2026-05-31.md` — **נשלח, ממתין לדוח+אימות.**
- `CC_PROMPT_AUTH_TABLE_V2_MAXCONTRACTS_2026-05-31.md` — Auth Table V2 (0-5) + MAX_CONTRACTS=5. (⚠️ מעלה sizing ~1.67× — מתנגש עם תקרת הפסד יומי $250.)
- `CC_PROMPT_TRADES_PAGE_AUDIT_EXPAND_2026-05-31.md` — ביקורת+הרחבת עמוד trades (חלק C דורש SHADOW חי; חשד: tזוזות סטופ לא נרשמות ל-`v9_trade_management_log`).
- `CC_PROMPT_ENABLE_FLAGS_SHADOW_2026-05-31.md` — monitoring/revert per-flag (ההדלקה בוצעה ב-.env).
- ישנים: `CC_IMPLEMENT_P32_BRIDGE_SOT_2026-05-29.md` (לא נשלח) · `BLOCKER_SWEEP_R2` (לבדוק אם נצרך) · Phase 3 (archive endpoints) ו-Phase 4 (DemoReadiness UI) — טרם נכתבו · Dual-machine — דחוי.

## פעולות-המשך (לא פרומפט)
- **הפעלת D-094:** `export RR_FIRE_SELECTION=true` + wire `bar_router.subscribe("5min", gw.on_bar_close)` ב-`main.py`. כרגע OFF + לא מחווט.
- **הפעלת Auth Table V2 / MAX_CONTRACTS=5** — רק אחרי שהפרומפט ירוץ ויאומת.

## החלטות/אימותים פתוחים
- **DB ריק (0 trades) + שרת לא רץ** → לא נאספים נתוני SHADOW. כיול הכל תלוי בהרצת SHADOW. לאשר אם ה-DB אופס מכוון.
- שערי-חובה לפני LIVE: תקרת סיכון מצטברת (P-L0a) · Pipeline 5 (P5-1…P5-8, נתיב order) · DLL frozen-tail RTH live verify.
- פערים פתוחים (לא חוסמי-SHADOW): GAP-1 (sizing labels מתים) · GAP-2 (news placeholder) · GAP-5 (conf threshold קוסמטי) · GAP-11 (S2 restart hydration) · Bug C (bar-open vs fill) · פערי-אפיון בעצים (S4 A4 advisory, A1 מלא לא נקרא, ZLR ±100 מול ±50, HFE→low, day-type matrix לא נאכף).

## הצעד הבא המומלץ
1. **אמת את דוח CC על calibration wiring** (grep ש-`_detect_initiative` קורא ל-helpers; footprint קורא ל-get_min_level_vol/get_range_ticks; golden flag-OFF identical; scaffolding רושם מטריקות).
2. כשמריצים SHADOW: **wiring (A) → סטאק → איסוף** (16:30 IL = RTH). לוודא Sierra מייצא + bring-up checklist.
3. במקביל: לתזמן Auth Table V2 + עמוד trades (אחרי שה-wiring ירוק).

כל החלטה/ממצא → עדכן STATUS_BOARD + ROADMAP מיד (טקסט, בלי present_files לקבצי מעקב).
