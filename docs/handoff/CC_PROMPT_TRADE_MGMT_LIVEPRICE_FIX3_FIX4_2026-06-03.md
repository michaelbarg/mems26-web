# CC PROMPT — Trade Mgmt on Live Price (PRIMARY, active) + Stale-Bar Guard | 2026-06-03

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** thread נפרד · commit אטומי · **לא `git add -A`** · פלט גולמי. **חוסם-LIVE class (בטיחות P-L0).**
מקור: `docs/handoff/CONSULT_TRADE_MGMT_LIVEPRICE_2026-06-03.md`. **אישור Michael 2026-06-03.**

## הבעיה (מאומת היום)
ניהול-עסקה רץ על **אירועי-בר** מ-DB. כשייצוא 5-דק' קופא (frozen-tail — חזר היום), סטופים/טרגטים לא נבדקים → 5 עסקאות צפו לא-מנוהלות 11:50→12:29 ET בעוד `live_price` חי (200ms). ב-LIVE = הפסד לא-חסום.

## הכרעת Michael — דגם פעיל primary מההתחלה
ניהול-עסקה עובר ל-**live_price כמקור ראשון (primary) שמנהל בפועל**, **active מההתחלה** (לא shadow). אירועי-בר → secondary/reconciliation. **סטופ/טרגט מתנהלים על טיק — לא על סגירת-בר** (זה המודל הנכון; תופס intrabar).

## Fix 3 — Trade mgmt on live_price (Option A, PRIMARY active)
1. TradeManager **נרשם ל-stream של `live_price`** (ה-Redis channel ש-`/live_price` כבר מפרסם — אמת את שם ה-channel ב-`bars.py`/`publish_event`). על כל טיק: בדוק סטופ/טרגט/T1/BE לכל העסקאות הפתוחות מול המחיר הנוכחי.
2. **primary:** הנתיב הזה שולט בניהול. נתיב אירוע-הבר הקיים (`main.py:~390`) → secondary/reconciliation בלבד (או הסר אם מיותר אחרי אימות) — **אל תשאיר שני נתיבים שמתחרים על אותה החלטה** (single-source).
3. **כתיבות hit** (STOP_MOVE/T1/T2/BE/EXIT, management_log) → **`safe_writer`** בלבד, לא ORM.
4. **דגל:** `TRADE_MGMT_LIVE_PRICE` **call-time** (`flag()` בתוך הפונקציה, לא module-level — להימנע מ-D1), **default ON**. קיים ל-emergency-revert בלבד, **לא** shadow-toggle.
5. errors בנתיב הטיק: `logger.warning` (rate-limited), **לא** swallow, **לא** לשבש את קליטת המחיר.

### 🛡️ bad-tick guard (חובה — כי active-from-start)
טיק שסוטה מעבר לסף מהמחיר האחרון המקובל (למשל `> k×ATR5m` או סף-נקודות) **נדחה** מהבדיקה. חציית-מפלס נדרשת על **טיק שפוי** — tick-חריג בודד לא יפעיל false-stop. (אמת מול `_best_price`/bid-ask הקיים — BAR_CONTINUITY 1/6.)

### 🛡️ live_price-staleness guard
אם אין טיק > ~15-30ש' ב-RTH → `logger.warning`/alert ("management blind — live_price stale"). **אין auto-flatten** (heartbeat=alert-only נעול).

## Fix 4 — Stale-bar guard (חוסם כניסה, RTH-scoped)
כש-`MAX(ts) FROM v9_bars_5min` מפגר > **10 דק'** מ-now **בתוך RTH בלבד** (09:30-16:00 ET — כי B4 הפך את הטבלה ל-RTH-only; מחוץ ל-RTH אין ברים = לא לבדוק):
- `can_fire()` של S2/S4 → False · `logger.warning("bars stale Xmin — firing blocked")`.
- מונע **כניסה** על תבנית מנתון ישן. (Fix 3 מנהל קיימות על מחיר-חי; Fix 4 מונע חדשות על ברים תקועים — משלימים.)
- TZ מפורש ET (Rule 4).

## טסטים (אנטי-טאוטולוגיים + litmus)
- **core:** מחיר חוצה סטופ **בזמן שהברים קפואים** → הסטופ נתפס (קורא ל-TradeManager האמיתי על live_price). *"if reverted → RED because bar-only mgmt misses the stop while bars frozen"*.
- **bad-tick:** טיק חריג בודד → **לא** מפעיל סטופ; חזרה למחיר תקין → לא נסגר בטעות.
- **Fix 4:** ברים stale 12דק' ב-RTH → can_fire=False; טריים → True; מחוץ ל-RTH → לא חוסם.

## Invariants
safe_writer לכתיבות · אין silent errors · אל תשבש ingestion · single-source (לא שני נתיבי-ניהול מתחרים) · get_db לא נועל · B2/B3 ללא שינוי · אל תיגע sc_study/LaunchAgent/polling. **strategic-stop: Michael אישר active-from-start; אחרי מימוש — Cowork מאמת בלתי-תלוי לפני שמסמנים.**

## Acceptance (בינארי + פלט גולמי)
- [ ] live_price=primary mgmt active (default ON); bar-path=secondary. ✓/✗
- [ ] hit-writes דרך safe_writer. ✓/✗
- [ ] bad-tick guard + live_price-staleness guard מחווטים. ✓/✗
- [ ] Fix 4: firing blocked כש-bars stale>10min ב-RTH (RTH-scoped). ✓/✗
- [ ] 3 הטסטים ירוקים + litmus revert→RED. ✓/✗
- [ ] regression ירוק · commit · `git log -1`.
