🟢 **[cowork · 18.10 09:38→09:45 IL · T-585 מעבר-הבקאנד לדמו — ביצוע "העברתי לדמו" (מייקל 09.10 19:2x)]**

```raw
date ⇒ 2026-10-18 09:40:16 IDT (Sun) · sierra_state: trade_account Sim1 · is_sim 1 · position_qty 0 · working_orders 0
scripts/mems26_snapshot.sh "T-577-demo-switch" ⇒ /Users/michael/mems26_snapshots/20261018T064016Z_T-577-demo-switch
.env ⇒ 14: MEMS26_MODE=live→demo · 279: LIVE_TRADING_V1=1→0
diff 20261007T121639Z_manual/env/.env .env | cut -d= -f1 ⇒ MEMS26_MODE, LIVE_TRADING_V1 בלבד (אפס מפתח אחר)
python3 scripts/flag_guard.py ⇒ rc=0 (אזהרת FOOTPRINT_DISABLED plist≠.env הידועה, דיווח-בלבד)
launchctl kickstart -k gui/$(id -u)/com.mems26.backend ⇒ rc=0 · pid 69665 → 2030 (lstart Sun Oct 18 09:40:38 2026) · health=200
/tmp/backend.err.log ⇒ 09:40:43 [boot] logging OK pid=2030 commit=a3c66d1c · 09:40:44 [Main] Demo mode enabled: systems [2, 4]
GET /api/v9/gateway/status ⇒ live_enabled [] · demo_enabled [2, 4] · live_slot None · demo_slot None · trades_today 0 · daily_pnl 0.0
scripts/post_restart_verify.sh ⇒ 🔴 רק (c) day_type: no rows — הפיד מת מ-09.10 22:15 (woodies max ts); ייצוא-סיירה חי מ-09:43 היום · (a)(d) ✅ · (b)(e) מחוץ ל-RTH
scripts/fire_drill.py --no-live ⇒ 🟢 GO (guard_tests 170 passed / 1 skipped) · rc=0
```

⇒ אפס כסף-אמת בסיכון מעכשיו גם אם הצ׳ארט יוחזר לחשבון-האמת (LIVE_TRADING_V1=0). **לא נגעתי:** עץ, LaunchAgents, ספרים (#3402/#3406 — פקודות-לייב 09.10 18:10/18:15 שנדחו ע״י הברוקר ונרשמו mode=live בלי תמחור — נשארות לסימון בפסיקה). ניסיונות קודמים 09.10 23:11/23:33, 10.10 00:16/07:31/12:01 — המחשב לא היה מחובר לסשן. **פתוח לשני 19.10:** הפיד — אין ברים ב-DB מ-09.10 22:15 (TS-OFFSET-GATE, ריצה 308); בלי ברים אין יום-דמו ואין מדידת לייב≈ריפליי. ההנחיה של מייקל 18.10 (סימולציה מלאה, תיקון עד שהמערכת נכונה, דיווח-מוכנות לכסף-אמת) — תוכנית-העבודה ב-`docs/plans/WORK_PLAN_2026-10-18.md`.

