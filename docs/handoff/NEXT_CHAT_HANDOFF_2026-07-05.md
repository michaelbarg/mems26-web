# MEMS26 · הנדאוף לצ'אט הבא — 2026-07-05 (ראשון)

_קרא אותי ראשון בצ'אט חדש. מטרה: להתחיל מהמצב האמיתי בלי לחזור על עבודה שכבר נעשתה._

## ⚠️ קודם כול — אמת-זמן (Rule 2)
אמת את התאריך לפני כל דבר: `date` (Mac) + `SELECT max(ts) FROM v9_bars_5min_woodies`. אל תסמוך על תאריך שמופיע בסיכום-סשן — הצ'אט הקודם רץ יומיים על סיכום ישן וכמעט בנה תמונה שגויה. **HEAD הנוכחי = `c5bf5da`, ענף `stabilize/mems26-local-truth-2026-05-16`, מסונכרן ל-origin.** יום-המסחר הבא: **שני 2026-07-06** (פתיחה 16:30 IL).

## מצב חי (שני ייפתח כך)
- **סוחר DEMO מלא**, ניהול-פר-חוזה, contracts=3, יעדים-מבניים, SMART_BE, טריילינג.
- דגלים חיים: `RR_ENTRY_GATE_V1=1` · `DAYTYPE_TARGETS_STRUCTURAL=1` · `DAYTYPE_PLAYBOOK=1` · `S1_NEW_CLASSIFIER=1` · `FIXED_CONTRACTS_3=1` · `HFE_DISABLED=1` · `DAYTYPE_POSITION_GATE=0` · `RISK_DAILY_LOSS_CAP=450` (השער `RISK_HALT_V1` עצמו OFF עד חלון-מדידה).
- באגים סגורים וחיים: I-57/58/59/60/61/62 (סלוט · fills · sanitize · dedup · צד-יעד · סגירה-על-fill-סיארה בלבד).
- **item-10 יודלק אוטומטית שני 15:40 IL** (משימה `enable-item10-opening-window-monday`) — לצפות באימות שלה.

## הפעלה נכונה (חשוב)
- **ריסטארט-בקאנד = `launchctl kickstart -k gui/$UID/com.mems26.backend`** — לא `nohup` ידני (יש LaunchAgent עם respawn; nohup מתנגש ב-bind).
- לפני ריסטארט: לוודא 0 עסקאות פתוחות (`state NOT IN ('CLOSED','closed')`) + demo_slot.
- לפני שינוי .env/DLL/LaunchAgent: `scripts/mems26_snapshot.sh "label"`.
- psql: `/Applications/Postgres.app/Contents/Versions/18/bin/psql postgresql://localhost/mems26`.

## נבנה-כבוי, ממתין (לא סיכון — מוכן)
item-21 EOD-window · item-19 halt (−$450, עד חלון-מדידה) · item-6 S4-confirm · item-22 target-zones · item-20 Sierra-reconcile (**חיווט-לולאה חסר**) · **System-6 supervisor** (b0bcac8, **חיווט-לולאה חסר**) · **item-4 Stop-Resolver** (backtest ✓, **חיווט+net חסר — lever מס' 1**).

## חוב-CC (תור מ-`CC_EOD_PROMPT_2026-07-03.md`)
4→9→11→18→16→6→13→12→22→17→20 + חיווט item-20/System-6 ללולאת-הפולינג + item-11 איחוד-sizing (calculate_size הישן עוד רץ).

## פתוח מולך (מיכאל)
- מערכת-3 עצמאית על tick-reversal-16 — 3 שאלות ממתינות (הרעיון במשפט · מחליף-S3-footprint או חדש · עדיפות מול מסלול-LIVE).
- item-8 pullback-retest — הגדרה. item-7 phase-detector דינמי — מחקר.
- להדליק item-21/item-6/item-22? (פסיקה ליום-מסחר מלא).

## מקורות-אמת
`docs/reports/MEMS26_EXECUTION_REVIEW_2026-07-05.md` (הסקירה המלאה) · `STATUS_BOARD.md` (מקור) · `MICHAEL_ISSUES_LEDGER.md` (פנקס) · `FLAG_INDEX.md` (דגלים) · `SYSTEM_TREE.html` · `SOURCE_OF_TRUTH.md`. **כלל:** index-first, verify-don't-trust, smallest-correct-change, flag-OFF-default + פסיקת-מיכאל, טסט-נכשל-על-הישן לכל תיקון, snapshot לפני out-of-git.
