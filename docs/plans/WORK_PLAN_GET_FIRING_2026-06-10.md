# תוכנית‑עבודה — שהמערכת תירה כמו שצריך במסחר רציף (2026‑06‑10)

**מטרה:** עד סוף היום, setup תקף (ZLR/TLB/...) → עובר routing → נכתב ל‑`v9_trades` עם stop/T1 מהאפיון, sizing נכון, day_type נכון בזמן. הכל flag‑gated SHADOW · diagnose‑confirmed · regression‑test לכל תיקון · אישור‑Michael לשינויי‑classification.

## ✅ אבחון‑דגלים (Cowork, raw) — אף דגל לא חוסם
הריצה‑החיה (launchd) + `.env` (main.py `load_dotenv`):
- `STOP_ANCHORS_V2=1` (V2 targets פעיל) · `S1_DAYTYPE_STAGING=true` · `S1_DYNAMIC_RECLASS=true` · `S1_LIVE_RECLASS=true` · `S1_IB_WIDTH_ATR=true` — **כולם ON.**
- `S2_CHOPPINESS_GATE` / `LAYER0_CHOP_GATE` / `S2_REQUIRE_COT_AMT` = **OFF** (default · תקין · Standing Decisions).
- **מסקנה:** אין שער שחוסם ירי בטעות. **תכונות ה‑day_type‑staging + reclass דלוקות — אבל לא עובדות → באג‑קוד (לא config).** זה משנה את הפריוריטי: לתקן את לוגיקת‑ה‑S1, לא דגל.

## חוסמי‑ירי → סדר‑תיקון להיום (כל שורש אומת ע"י Cowork)

### P0 — לשחרר routing (בלי זה: 0 ירי גם ל‑setups תקפים)
1. **matrix "lookup error" — alias:** `day_type_gate.py:92` `self._matrix[(pattern_id, day_type)]` גישה‑ישירה ללא alias → KeyError כש‑`Variation ≠ NV`. תקן: נרמול/alias (כמו `_ALIASES` ב‑`targets_table`), single‑source. *(טסט: day_type=Variation → verdict חוזר, לא KeyError. revert→RED.)* **שחרור מיידי של `day_type_matrix` gate.**
2. **A7 `T2=None` — טסט‑רגרסיה:** התיקון בוצע (`832174e`) אבל **חסר טסט.** הוסף: `req.t2_price=None` → validator עובר, `ready_to_route` יכול True. *(revert→RED: TypeError.)*

### P1 — day_type נכון‑בזמן (כדי שהירי יקרה בזמן עם sizing נכון)
3. **S1 staging/reclass — באג‑קוד (דגלים ON, לוגיקה שבורה):** למרות `S1_DAYTYPE_STAGING`+`S1_DYNAMIC_RECLASS`+`S1_LIVE_RECLASS`=ON, היום: day_type=UNKNOWN ב‑30דק' + "Normal" שגוי (OPEN_DRIVE→Trend_Normal) + **אין reclass**. אבחן **למה ה‑staging/reclass לא יורה** למרות הדגלים (האם המנוי `_day_type_on_bar` רץ? bar_count עולה? נתיב‑הפרסיסט ב‑`main.py`? future‑ts מזיז את החלון?). **strategic‑stop + אישור Michael** (classification).
4. **provisional day_type → S4:** מחווט ל‑S2 (`five_min`), **חסר ב‑S4** (grep ריק). חווט אותו מקור → S4 מקבל day_type@30דק' (לא ממתין ל‑IB‑lock@60).

### P2 — היגיינת‑ירי
5. **dedup:** אמת **היכן** ~200x קורה (raw) → guard בודד `is_new_bar` בנתיב‑הירי (כמו S2), single‑source (dedup חלקי כבר קיים — אל תשכפל).
6. **future‑ts (I‑18):** ברי‑woodies בעתיד (~5.5h) — אבחן מקור (DLL/bridge/TZ/Globex‑leak). חשד‑שורש‑משותף לחלונות+זיהוי.

## ✅ הוכחת "יורה כמו שצריך" (Acceptance — Rule 5)
אחרי P0+P1, על המצב‑החי או replay:
- setup תקף (ZLR/TLB, trend≠GRAY) → `ready_to_route=True` → שורה ב‑`v9_trades` עם **stop+T1 מהאפיון** (לא טיקים‑קבועים) → מוצג בעמוד Trades.
- day_type≠UNKNOWN ב‑30דק' + תואם DECISION_MATRIX (OPEN_DRIVE→Trend_Normal).
- ירי **בודד** לבר (dedup).

## 🔬 משימת‑CC — סימולציית כל‑תבנית על מסחר‑אתמול הרציף (06‑09)
**Replay** את כל הסשן‑הרציף של **אתמול 06‑09** דרך `historical_replay` → לכל **S1/S2/S4**, לכל תבנית:
- **מתי היה נכנס** (ts הכניסה, entry/stop/T1 מהאפיון).
- **איך היה מנהל את העסקה** (BE אחרי T1? trail? time‑stop? יציאות B1‑B14) — צעד‑אחר‑צעד.
- **תוצאה ו‑$** (T1/סטופ/trail · MES $5/נק' · contracts מ‑auth).
- טבלה: `pattern · entry_ts · entry/stop/T1 · ניהול (BE/trail/exit) · תוצאה · $ · ΣP&L פר‑מערכת`.
- מנוע: זהה ל‑`eod_shadow_audit` §3 (`docs/handoff/CC_AGENT_EOD_SHADOW_AUDIT_2026-06-10.md`), מורץ ל‑06‑09. observability בלבד. **דוח** `docs/reports/SIM_PATTERNS_2026-06-09.md`.

## דיסציפלינה
diagnose→דוח→הצלבת‑Cowork→אישור‑Michael→תיקון flag‑gated→regression(RED‑on‑revert)→Rule 5→בורדים. **אסור:** Standing Decisions · §Polling Floors · sc_study/bridge ללא §7a · לסנתז.

## אימות‑Cowork חוזר
P0‑1: KeyError נעלם, day_type_matrix=allowed (live) · P0‑2: RED‑on‑revert · P1‑3: day_type≠UNKNOWN@30 + reclass עובד (DB) · P1‑4: S4 day_type@30 · P2‑5: ירי‑בודד · סימולציה: טבלת‑ניהול פר‑עסקה.
