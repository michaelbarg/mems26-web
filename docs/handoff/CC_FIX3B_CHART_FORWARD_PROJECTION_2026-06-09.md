# CC — FIX 3B: ה-"+" עדיין מופיע — תיקנת את הקובץ הלא-נכון · 2026-06-09 לילה

**FIX 3 (`tpoLevels.ts:535`) לא פתר — Michael עדיין רואה את ה-"+" המוקרנים בצ'art (5דק' + CVD).** Cowork אבחן מחדש מול הקוד+נתונים (raw). השורש **לא** ב-`tpoLevels.ts`.

**Root (raw, אומת):**
1. **`frontend/v9/src/v9/components/chart/v5b/TpoContinuityOverlay.tsx:67-72`** — *"Extend last point to current time so the step continues to now"* → דוחף נקודה ב-`nowUnix = Math.floor(Date.now()/1000)` (שעון-נוכחי). זה מותח את קווי POC/VAH/VAL **קדימה אל מעבר לבר האחרון**. זה ה-"+" בפאנל-המחיר.
2. **pane ה-CVD** (`CvdChartPane.tsx` / `CumulativeDeltaPane.tsx`) — אותה הקרנה-קדימה ל-CVD (ה-"+" התחתון).
3. **מחריף ע"י פיד-תקוע:** הבר האחרון `ts=1781016600` (17:50), עכשיו 22:54 → **304 דק' stale**. ה-overlay מאריך ל-`nowUnix` (22:54) → קו של 5 שעות קדימה + ציר-זמן כפול (13:00/14:00 פעמיים).
4. הנתונים **נקיים ומיושרים** (cvd ו-5min נגמרים ב-ts זהה) — זו **לא** בעיית-TZ/נתונים. רינדור-frontend בלבד.

**הפועל היחיד שתיקן `tpoLevels.ts` לא נגע ב-`TpoContinuityOverlay` ולא ב-CVD pane → לכן עדיין מופיע.**

═══════════════════════════════════════════════
## התיקון — חתוך את ההקרנה לבר-האחרון, לא ל-nowUnix
═══════════════════════════════════════════════
**עיקרון:** סדרות-overlay (TPO continuity + CVD) ימשכו **רק עד זמן הבר האחרון בפועל** (`lastBarTime`), **לא** עד `Date.now()`. כך אין הקרנה-קדימה גם כשהפיד מפגר/תקוע.

1. **`TpoContinuityOverlay.tsx:67-72`** — החלף את `nowUnix` בהארכה ב-`min(nowUnix, lastBarUnix)` (או פשוט `lastBarUnix`). העבר את זמן-הבר-האחרון כ-prop מ-`ChartV5b.tsx` (יש לו את מערך-הברים). אל תאריך מעבר ל-`lastBarUnix`.
2. **CVD pane** (`CvdChartPane.tsx`) — ודא שאין whitespace/extension מעבר ל-`lastBarUnix`; חתוך באותה צורה.
3. **`tpoLevels.ts:535`** — ה-`rightEdge = min(close, nowUnix + STEP_SEC)` עדיין מאפשר עד `now` — שנה ל-`min(close, lastBarUnix)` לעקביות (אחרת על פיד-תקוע גם הוא יקרין).
4. **חובה: rebuild + hard-refresh.** ודא שה-Next dev server קימפל מחדש ושה-browser נטען נקי (לא bundle ישן). אחרת השינוי לא חי.

**הוכחה נדרשת (Rule 5):** **צילום-מסך אחרי rebuild** שבו ה-"+" נעלמו וכל הסדרות (נרות, TPO lines, CVD) נגמרות **באותו בר אחרון** — בלי קו-קדימה ובלי ציר-זמן כפול.

═══════════════════════════════════════════════
## בנפרד (לבדוק, לא frontend) — פיד תקוע 5 שעות
═══════════════════════════════════════════════
הבר האחרון 17:50, עכשיו 22:54 → אין בר-5דק' חדש כבר 5 שעות. בדוק: האם RTH הסתיים (לגיטימי) או שהגשר/Sierra-export נעצר? `tail /tmp/bridge.err.log` + mtime של `~/SierraChart_Data/v9_export/5min.json`. אם הגשר נפל — זו בעיה נפרדת (§Bridge). דווח raw, אל תתקן בלי לאבחן.

**מה ש-Cowork יבדוק:** צילום אחרי-rebuild בלי "+"/ציר-כפול · diff של `TpoContinuityOverlay` + CVD pane (לא רק tpoLevels) · סיבת הפיד-התקוע.
