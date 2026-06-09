# CC — טאב Shadow: תצוגת "מצב-בנייה" פר-תבנית (S1/S2/S4/S5)

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.**

**מטרה אחת (UI, display-only):** תחת טאב **Shadow**, לכל מערכת (1,2,4,5) להציג את
**כל התבניות האפשריות**, ולכל תבנית: (א) **הסבר חישוב-הירי הנדרש** (השערים),
(ב) מולו **המצב החי**, (ג) **מצב-בנייה** = ספירת-שערים-שעברו, מדורג בתוך המערכת
(הקרובה-ביותר-לירי ראשונה). **תצוגה בלבד — בלי לגעת ב-fire/gate/risk logic.**
**Source-of-truth: `/api/v9/build/pattern-status`** — אל תסנתז ערכים; קרא משם בלבד.

> **החלטות Michael (2026-06-08):** תוצר=handoff · S1/S5 ייכללו עם משמעות-מותאמת ·
> מדד-בנייה = **ספירת שערים שעברו (X/Y ✓)**, דירוג לפי הכי-הרבה-עברו (= הכי מעט נותרו).

---

## ראיות/אודיט (מה כבר קיים — לסווג KEEP/ADAPT/REPLACE/DEFER ב-Phase 0)
- **Endpoint קיים:** `/api/v9/build/pattern-status` → `systems[].patterns[].components[]`
  שכל אחד נושא `{stage, key, spec, value, live, required, present(✓/✕)}` + `blockers[]`,
  `reason`, `status`, `armed`. ⇒ "נדרש מול חי" כבר שם. (אומת חי 2026-06-08: S2 10
  תבניות, S4 7, footprint 4; `components[]` כולל למשל `choppiness_ok`,
  `b1_sellers`, `pattern_specific` עם spec+live+present.)
- **Frontend קיים:** `components/build_status/BuildStatusTab.tsx`,
  `build_status/SystemSection.tsx`, `build_status/types.ts`,
  `build_tree/BuildTreeView.tsx`, hook `hooks/useBuildStatus.ts`,
  `app/build/page.tsx`, `sidebar/tabs/PatternsTab.tsx`. טאב **Shadow** כבר קיים
  בפאנל-הצד (`components/layout/SidePanel.tsx` — Now|Plan|Shadow|Hist|Chart).
- ⇒ זו **ADAPT** (להרחיב את הרינדור הקיים + להוסיף build-score+דירוג + לחבר תחת
  Shadow + לכסות S1/S5), **לא בנייה מאפס.** אל תיצור endpoint/קומפוננטה כפולים.

---

## Phases (אטומיים)

### Phase 0 — אודיט + מיפוי
- מה `pattern-status` מחזיר **לכל** מערכת — בפרט: האם `day_type` (S1) ו-`tpo` (S5)
  מופיעים עם `patterns[]`/`components[]`, או רק bridge/five_min/woodies/footprint?
  (חי: `systemsCount=5`.) סווג כל קומפוננטה קיימת KEEP/ADAPT/REPLACE/DEFER.
- היכן ה-Shadow tab מרונדר וכיצד נבחר (`SidePanel.tsx`), ומה `BuildStatusTab`/
  `SystemSection` כבר מציגים.
- **AC:** טבלת-מיפוי (system → יש patterns[]? יש components[]? מה ה-UI מציג היום) +
  הכרעה ADAPT/REPLACE לכל חלק. *evidence: grep/קטעי-קוד + פלט pattern-status.*

### Phase 1 — build-score + דירוג (לוגיקה, frontend-side)
- לכל תבנית: `passed = count(components.present===true)`, `total = components.length`,
  `build_score = passed/total` ⇒ הצג **`X/Y`**. דרג תבניות **בתוך כל מערכת** לפי
  `passed` יורד (שובר-שוויון: פחות blockers / armed). הקרובה-ביותר ראשונה.
- העדף חישוב ב-frontend מ-`components[]` הקיים (smallest-change). רק אם S1/S5 חסרי
  `components[]` — הרחב את ה-endpoint לחשוף אותם (Phase 3), לא להמציא ב-UI.
- **AC:** טסט-יחידה שמייבא את פונקציית-הציון ומריץ על fixture של pattern-status
  אמיתי (לא מועתק), assert על הדירוג. *if reverted (ציון/מיון) → RED because הסדר/‏X/Y משתנה.*

### Phase 2 — רינדור תחת טאב Shadow
- לכל מערכת (1,2,4,5): כותרת-מערכת + רשימת-תבניות **מדורגת**, כל שורה:
  `שם תבנית · X/Y ✓ · status`. הרחבה (expand) מציגה את כל השערים:
  `key · spec (=החישוב הנדרש) · required · live · ✓/✕`.
- חבר תחת ה-Shadow tab הקיים (אל תיצור טאב חדש אם קיים). שמור עיצוב/tokens קיימים.
- **AC:** צילום/DOM של ה-Shadow tab עם ≥1 מערכת מורחבת המציגה spec+live+✓/✕ לכל שער,
  והתבניות ממוינות לפי X/Y. *evidence: screenshot + הקומפוננטה.*

### Phase 3 — S1/S5 משמעות-מותאמת
- **S1 (Day Type):** "תבניות" = שלבי/שערי-הסיווג — למשל `day_type_known`,
  `auth/stage B2`, votes/lock — כל אחד spec+live+✓/✕, ו-X/Y. (קשור ל-I-1: אם
  `session_min=0`/instance-split, להציג את המצב האמיתי, לא להמציא.)
- **S5 (TPO):** "תבניות" = מצב-TPO (POC/VAH/VAL/shape). כש-feed מת (I-24/I-11 —
  stream `tpo` DEAD) להציג **"לא-זמין / feed dead"** במפורש, לא ✓ מזויף (CLAUDE.md
  Rule 1: honest failure > synthetic).
- **AC:** S1+S5 מופיעים בטאב עם שורות-אמת; כש-feed מת → תצוגת "unavailable" מפורשת.

### Phase 4 — polling/ביצועים
- השתמש ב-`useBuildStatus` הקיים; **אל תוריד** את רצפת-ה-polling (CLAUDE.md §Frontend
  Polling Floors — backend single-worker). בלי קריאות-רשת חדשות אגרסיביות.
- **AC:** אישור שה-interval לא ירד + אין endpoint-call נוסף בלולאה.

### Phase 5 — דוח לפי חלק C
טבלת phases (DONE/PARTIAL/NOT-DONE + Evidence) · *"if reverted → RED because ___"*
לכל טסט · **NOT DONE / DEVIATIONS** · **Open**. עדכן `STATUS_BOARD.md` (+ I-24 אם
S5-feed עלה כנושא). אל תתקדם בלי דוח.

---

## אסור לגעת (risk surface)
- אין שינוי fire/gate/risk/threshold; זו **תצוגה בלבד**. אל תוריד polling-floors.
- אל תסנתז ערכי-שער/חי — רק מ-`pattern-status` (Sierra=SoT במעלה-הזרם). feed מת =
  להציג "לא-זמין", לא ✓.
- אל תיצור endpoint/קומפוננטה/טאב כפולים — ADAPT את הקיים.

## קבצים רלוונטיים
- Frontend: `components/build_status/{BuildStatusTab,SystemSection,types}.tsx`,
  `components/build_tree/BuildTreeView.tsx`, `hooks/useBuildStatus.ts`,
  `components/layout/SidePanel.tsx`, `sidebar/tabs/PatternsTab.tsx`, `app/build/page.tsx`
- Backend (data, אם צריך להרחיב S1/S5): `systems/build_status/s2_inspector.py`,
  `systems/woodies/decision_tree.py`, ה-route של `build/pattern-status`
- Endpoint: `/api/v9/build/pattern-status` (`systems[].patterns[].components[]`)
