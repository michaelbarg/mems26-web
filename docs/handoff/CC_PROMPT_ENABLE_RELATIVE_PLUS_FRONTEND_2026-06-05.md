# CC — הדלקת מצב-יחסי (אישור Michael) + double_bt wiring + commit frontend · 2026-06-05

חוזה + `CC_VERIFICATION_PROTOCOL`. **Michael אישר** הדלקת המצב-היחסי ב-SHADOW. בסיום:
`VERIFY_RELATIVE_2026-06-05.md` + raw output.

═══════════════════════════════════════
## A · מצב-יחסי = default-ON (לא רק env-flag)
═══════════════════════════════════════
1. **`backend/v9/shared/atr.py:93`** — `S2_ATR_RELATIVE = flag("S2_ATR_RELATIVE")` →
   **default ON**: שהדגל יחזיר True גם בלי env (`os.environ.get("S2_ATR_RELATIVE","1")...`
   או `flag(..., default=True)`). היחסי הופך לקבוע-בפועל. **השאר את היכולת לכבות** (env=0)
   — לא לזרוק את הדגל (ה-K-ים עוד לא כוילו).
2. **`export S2_ATR_RELATIVE=1`** ב-`scripts/start_all.sh` (מפורש, SHADOW) + restart.
3. **תקן `double_bt.py:98,115`** — כתוב קשיח `tolerance = TICK_SIZE * 2`; **החלף ל-
   `get_trough_tolerance(atr_5m)`** (הפונקציה הקיימת, שורה 44). ודא ש-`atr_5m` זמין בנתיב-הזיהוי
   (מ-`_current_atr_5m` של S2) — אם לא מועבר, חווט אותו. זה מה שעושה את ה-double-bottom יחסי (I-17).
4. **אימות:** `flag("S2_ATR_RELATIVE")=True` בשרת הרץ · ה-tolerance של double_bottom עכשיו
   **ATR-יחסי** (הדבק את הערך מול ATR נוכחי, לא 0.50 קבוע).

⚠️ ה-K-ים (`_TROUGH_TOL_ATR_K=0.75`, מכפילי-ATR לסטופ) **לא כוילו** — כיול מול ground-truth
(8:36) ב-soak. כאן רק מדליקים את המצב; לא משנים K.

═══════════════════════════════════════
## B · commit תיקוני-frontend (Cowork תיקן ישירות — uncommitted)
═══════════════════════════════════════
- `tpoLevels.ts` — guard ל-`base.priceRange` null + tpoPrices ריק (chart crash).
- `TradesView.tsx` + `BuildTreeView.tsx` roots — `height:100vh + overflowY:auto` (scroll).
- `BuildTreeView.tsx` tabStyle — non-shorthand (console-error 1/4).
- **commit נקי** + הדבק `git log`. (אם נשארו 3 console-errors נוספים — מצא+תקן, console נקי.)

═══════════════════════════════════════
## VERIFY (raw output)
═══════════════════════════════════════
- A: `flag(S2_ATR_RELATIVE)=True` · double_bottom tolerance=ATR-value · grep ש-double_bt קורא get_trough_tolerance.
- B: `/build`+`/trades` גוללים (screenshot) · console נקי (screenshot) · `git log --oneline -6`.
- NOT-DONE: כיול-K (soak) · 3 console-errors אם נשארו.
