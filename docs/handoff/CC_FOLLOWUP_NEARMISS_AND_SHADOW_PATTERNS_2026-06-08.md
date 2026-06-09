# CC — המשך: near-miss/ראיות + Pattern-Detection ב-Shadow tab לפי מערכת · 2026-06-08

פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md` + `CC_VERIFICATION_PROTOCOL.md`. כל "DONE" = פקודה + **פלט גולמי** (Rule 5) + NOT-DONE.
המשך ישיר ל-`CC_COMPREHENSIVE_NO_FIRE_AND_FRONTEND_2026-06-08.md` (הטבלה כבר נמסרה; Cowork ביקר וזיהה 4 גאפים + פיצ'ר חדש).

═══════════════════════════════════════════════════
## חלק 1 — להשלים את חקירת "למה לא ירה" (4 גאפים מהביקורת)
═══════════════════════════════════════════════════

**א · עמודת "חוסם בחלון-ההזדמנות" ל-S4 (הכי חשוב).**
הטבלה צילמה את 20:10 (GRAY) ואמרה "כל 9 ה-S4 חסומים ב-GRAY" — אבל היום היו חלונות-trend אמיתיים
(BLUE 18:05-18:20 · RED 18:50-19:10) שבהם Stage A1 **עבר**. שחזר מ-`v9_bars_5min_woodies` (היסטוריית-היום) +
ה-snapshots/לוגים את החוסם-האמיתי של כל תבנית-S4 **בתוך חלונות-ה-trend**, לא ברגע-הצילום.
לכל S4 הוסף עמודה: **"חוסם בחלון-ההזדמנות"** — לדוגמה ל-ZLR: *"חלון RED: CCI הגיע ל-98.2- ופספס את סף ה-100- ב-1.8 נק'"*,
ולא "GRAY". אם תבנית לא היתה רלוונטית גם בחלון (כיוון הפוך) — ציין זאת.

**ב · ראיות Phase 0 + Phase 2 גולמיות (חסרו לגמרי).** מסור raw של:
- Phase 0: `git log --oneline -4` (commit לשינויי-Cowork), פלט 2 הטסטים החדשים GREEN, ופלט restart-verify
  (`S2_CHOPPINESS_GATE`/`LAYER0_CHOP_GATE` unset · readiness לא `dead: tick_reversal_15,tpo`).
- Phase 2: 2 צילומי Build-Status (לפני/אחרי) של ניקוי ה-frontend.
בלי אלה Cowork לא יכול לאשר שהתיקונים committed+חיים (Rule 5).

**ג · סיבת-ה-DEGRADED.** ה-readiness עלה BLOCKED→DEGRADED — מה **עדיין** מוריד אותו? הדבק את מערך
`readiness.checks` המלא מ-`build/pattern-status` וסמן איזה check ב-severity≠pass (כנראה `opening_type=UNKNOWN`
/ `imbalance` stale). קבע: תקלת-תצוגה או אמיתי.

**ד · רשימת near-misses לכיול (לעין של Michael).** לכל תבנית armed/scanning שלא ירתה — טבלה:
**תבנית | סף-נדרש | ערך-בפועל | פער**. דוגמאות: Initiative range נדרש 11.4 / בפועל 8.25 · ZLR סף 100- / בפועל 98.2-.
זו שאלת-ה-K: לסמן אילו היו "כמעט" (פער קטן) — מועמדים לכיול-סף מול מה ש-Michael היה נכנס אליו.
→ `docs/reports/PATTERN_NEARMISS_2026-06-08.md`. **אל תשנה K בקוד** — רק תעד; Michael מאשר כיול.

═══════════════════════════════════════════════════
## חלק 2 — Pattern-Detection ב-Shadow tab, מקובץ לפי מערכת (פיצ'ר חדש, אישור Michael)
═══════════════════════════════════════════════════
Michael רוצה לראות את זיהוי-התבניות בדאשבורד, **בטאב ה-SHADOW, מקובץ לפי המערכת הרלוונטית**.

**2a · אודיט קודם (CLAUDE.md — אל תבנה כפילות).** סווג KEEP/ADAPT/REPLACE:
- `frontend/v9/src/v9/components/sidebar/tabs/PatternsTab.tsx` (tab `patterns`/תבניות) — מה הוא מציג היום?
- `components/build_tree/BuildTreeView.tsx` + hook `hooks/useBuildStatus.ts` — כבר צורכים `/api/v9/build/pattern-status`.
- `tabs/TraderTab.tsx`/`TradeTab.tsx` — הם נושאי כותרת **"Per-System P&L (SHADOW)"** = ה-Shadow view. **ודא עם Michael/הקוד איזה tab הוא "ה-Shadow".**

**2b · יישום.** בטאב ה-SHADOW (זה עם "Per-System P&L (SHADOW)") הוסף פאנל **"זיהוי תבניות"** המקובץ לפי מערכת:
- כותרת-קבוצה לכל מערכת: **S2 · Five-Min** (10 תבניות) · **S4 · Woodies** (9 תבניות). (אם S3 מושתק — לא להציג, או "disabled (S3_MUTE)" נפרד.)
- לכל תבנית שורה: שם · badge-סטטוס (🟢 fired / 🟡 armed / ❌ blocked) · **החוסם-היחיד** (reason/blocker) · תג **REAL/DISPLAY**.
- מקור: `useBuildStatus` הקיים (`/api/v9/build/pattern-status`) — **בלי שינוי-backend**, בלי endpoint חדש.
- רענון: לפי המוסכמה הקיימת של `useBuildStatus` (manual-refresh, Michael 2026-05-26) — **לא** auto-poll חדש (רצפות-ה-polling ב-CLAUDE.md).
- REAL/DISPLAY: השתמש באותה לוגיקת-סיווג מהטבלה (זרם-מושתק/freshness-label = DISPLAY; auth-SKIP/trend-GRAY/detection = REAL).

**2c · עקביות עם ניקוי-ה-frontend (Phase 2 הקודם).** הפאנל החדש לא יציג זרמים-מושתקים כאדומים, ולא את תקלת
day_type-freshness. אם BuildTreeView כבר עבר ניקוי — עשה reuse לרכיבים, לא העתקה.

## Acceptance Criteria (בינארי ✓/✗)
- [ ] א: לכל 9 תבניות-S4 עמודת "חוסם בחלון-ההזדמנות" עם ערך-CCI-בחלון (לא רק GRAY).
- [ ] ב: raw של commit + 2 טסטים GREEN + restart-verify + 2 צילומי Build-Status.
- [ ] ג: מערך `readiness.checks` מודבק + ה-check שמוריד ל-DEGRADED מסומן + סיווג display/real.
- [ ] ד: `PATTERN_NEARMISS_2026-06-08.md` — טבלת סף/בפועל/פער לכל תבנית armed.
- [ ] 2: פאנל "זיהוי תבניות" בטאב ה-SHADOW, מקובץ S2/S4, סטטוס+חוסם+REAL/DISPLAY לכל תבנית, מ-`useBuildStatus` (בלי backend). צילום-מסך.
- [ ] אודיט KEEP/ADAPT/REPLACE של PatternsTab/BuildTreeView מתועד (אין כפילות).

## anti-tautological
פיצ'ר-ה-frontend לא דורש טסט-לוגיקה (הוא צורך endpoint קיים) — האימות = צילום-מסך עם נתוני-endpoint אמיתיים.
אם תוסיף לוגיקת-סיווג REAL/DISPLAY בקוד-frontend → טסט שמייבא אותה (לא משכפל). חלק-1 = raw מ-endpoint/DB אמיתיים, לא ניחוש.

## NOT-DONE (חובה)
מה לא נבדק · איזה tab זוהה כ-"Shadow" · האם א שוחזר מהיסטוריה אמיתית או מ-snapshots · כל סטייה.

## דוח + מה Cowork יבקר אחריך
מסור: git log · raw טסטים+restart · עמודת-א מעודכנת · readiness.checks · near-miss table · צילום פאנל-ה-SHADOW + אודיט.
**Cowork יצליב (Rule 5):** עמודת-א מול היסטוריית-woodies האמיתית · ראיות Phase 0/2 שלא נמסרו קודם · ש-near-miss תואם ספי-הקוד · שפאנל-ה-SHADOW לא משכפל את PatternsTab ולא מציג זרמים-מושתקים/day_type-freshness שגוי.
