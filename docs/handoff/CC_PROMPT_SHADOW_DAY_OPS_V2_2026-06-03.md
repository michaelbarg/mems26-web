# CC PROMPT — Shadow-Day Ops V2 (פוסט תיקון-שורש) · 2026-06-03

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** אוטונומי, פלט גולמי לכל בדיקה. **מחליף את `CC_PROMPT_SHADOW_DAY_OPS_2026-06-03.md`** (שער ה-DB שלו כבר עבר).

## מצב נכון להיום (מה כבר נסגר)
- ✅ DB root fix + soak → integrity backend-כבוי=ok (`9255bfa`).
- ✅ B4 — `v9_bars_5min` **RTH-only** (time-gate 09:30-16:00 ET, `bars.py:315,646`); is_synthetic ל-19 ברים; VSA מסנן is_synthetic (`five_min_system.py:202`); CVD מ-RTH מיושר (`0ece0fa`).
- ✅ sc_study v9.4.5 (SWI local, TrendUp SG4, bars-from-chart12) — committed (`816dd1a`).
- ⚠️ **RTH-only מתוכנן:** מחוץ ל-RTH `v9_bars_5min` ריק (ברי-לילה מדולגים). הטבלה הרציפה = משימה עתידית. **אין מסחר אמיתי** — SHADOW/paper בלבד (Pipeline 5 לא נבנה).

## 🚦 שער מקדים (חוסם) — feed חי
לפני כל איסוף, אמת (פלט גולמי):
- backend רץ (port :8000, אחד בלבד).
- Sierra מייצא `5min.json` (mtime עדכני) + bridge דוחף ל-`localhost:8000` (אין `API push FAILED` ב-`/tmp/bridge.err.log`).
- בפתיחת RTH: `MAX(ts)` ב-`v9_bars_5min` **מתקדם**. אם לא מתקדם ב-RTH → STOP, אבחן upstream (זה task #10), אל תאסוף.

## PHASE 1 — Pre-Trade (בפתיחת RTH 09:30 ET / 16:30 IL)
הרץ `docs/runbooks/PRE_TRADE_PROTOCOL.md`. אמת (פלט גולמי, Rule 5):
- `readiness = READY` (לא BLOCKED).
- bridge fresh · Sierra connected · health <100ms.
- `integrity_check` (אם אפשר backend-כבוי רגע לפני, או soak קצר) = ok.
- **S2 armed + יורה בשני הנתיבים** (Reactive+Initiative — B1 בשני האתרים).
- נרות + CVD זורמים ומיושרים (RTH).
- **שדות-הסטאדי per-system מאוכלסים** (work-by-system-needs): S1 (opening/IB/POC/CVD) · S2 (volume נקי ≤~72K, COT/AMT, CVD) · S4 (CCI/trend/SWI/EMA/LSMA/ProjHL). S3 disabled.
- `MAX(volume) WHERE is_synthetic=0` נשאר שפוי (לא 1M) גם תחת זרימה חיה.

## PHASE 2 — איסוף (09:30–16:00 ET)
- ניטור כל ~30-60 דק' (פלט): health, fires/setups per system, future-ts=0, frozen-tail (cci משתנה על ברים שונים), אין `malformed` בלוגים.
- אם `malformed`/write-error → **עצור איסוף, השבת את הכותב האשם, דווח** (לא להמשיך לתוך DB מושחת).

## PHASE 3 — EOD (אחרי 16:00 ET)
1. **עצור backend → `integrity_check`** (אוטוריטטיבי, פלט גולמי).
2. דוח יום `docs/reports/SHADOW_DAY_2026-06-03_EOD.md`: #trades, WR, setups per S1/S2/S4, התפלגויות, frozen-tail, slippage, corruption?
3. עדכן STATUS_BOARD/ROADMAP (finding+fix+verification).

## Invariants
get_db לא נועל · safe_writer-only · Sierra=SoT (לא לסנתז) · B2/B3 ללא שינוי · אל תיגע sc_study/LaunchAgent/polling. **אחרי הדוח Cowork מאמת בלתי-תלוי.**
