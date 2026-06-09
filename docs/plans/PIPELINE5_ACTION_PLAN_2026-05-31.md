# Pipeline 5 — תוכנית פעולה: ביקורת → אישור החלטות → מימוש

**נוצר:** 2026-05-31 (Cowork) · **בעלים:** Michael · **מקור:**
`docs/decisions/D-093_SIERRA_ORDER_ROUTING.md` + ממצאי Cowork (קריאת קוד חי 31/5).

**עיקרון:** לא נוגעים בנתיב ההזמנה לפני שלב הביקורת מסתיים ושכל ההחלטות ננעלו.
שום קוד order/risk לא משתנה אד-הוק. סדר קשיח: **שלב 1 → שלב 2 → שלב 3.**

---

## תנאי כניסה (לפני שלב 1)
- שער SHADOW (P-S0) — צריך להיפתח. P5-0/P5-6/P5-7 יכולים לרוץ במקביל ל-SHADOW.
- E2E 2/2 (S1/S2/S3) — לנחות (כרגע S2 ירוק, S3/S1 בתהליך).
- חוסמי §1 הרלוונטיים (gateway כפול 1.2) — נסגרים דרך שלב 1.

---

## שלב 1 — ביקורת (read-only · אפס שינוי קוד)

**P5-0 · Gateway audit** — CC קורא במלואם את שני הנתיבים + executors + shared +
tests, ומסווג KEEP/ADAPT/REPLACE/DEFER. תוצר: `docs/reports/P5_0_GATEWAY_AUDIT.md`.

**ממצאי Cowork מקדימים (לאימות ב-audit):**
- **Legacy** (`backend/v9/gateway/trading_gateway.py`, רץ ב-production): מחוברים בו
  cooldown / SSV (D-049) / cluster_guard (D-037) / chop gate / strict_checks. כותב
  פקודת DEMO — אבל מקודד `PA-APEX-125218-01` (מת). LIVE = stub.
- **New** (`backend/v9/services/trading_gateway/gateway.py`, לא מחובר): מבנה נקי
  (executors + thread-safe) + RiskValidator (W14), אבל **חסרים** cooldown/SSV/
  cluster/chop. לא כותב פקודה לסיירה. docstring מפנה ל-Apex מת.
- **מסקנה מקדימה:** cutover ישיר ל-New = **רגרסיה במסנני סיכון** → נוטה ל-**Merge**
  (מבנה+RiskValidator של New + ניוד הגייטים של Legacy). ה-audit יכריע סופית.

**בנוסף בשלב הביקורת:**
- Heartbeat: להעריך פשוט (stale>30s) מול ladder (§4.3: 5s emit · 30s WARN-if-flat /
  KILL-if-open · 120s critical).
- Bridge handler: לאשר ש-P5-7 הוא "just wire" (193 שורות מוכנות).
- אימות תצורת סיירה: IronBeam `37138283`, אין נתיב `[simulation]` נפרד, התנהגות
  `sc.GlobalTradeSimulationIsOn()`.

**פלט שלב 1:** דוח audit עם **המלצה לכל אחת מ-4 ההחלטות** + מפת Apex (כל מופעי
`PA-APEX-125218-01` למחיקה).

---

## שלב 2 — אישור החלטות (Michael נועל הכל לפי הביקורת)

| # | החלטה | אפשרויות | חוסם |
|---|--------|----------|------|
| 1 | **D-093.Q1 — Gateway קנוני** | Legacy / New / **Merge** (נטיית Cowork) | כל נתיב P5 |
| 2 | **Re-lock 1 — bracket** | `sc.BuyEntry/SellEntry`+Attached / SubmitOCOOrder | P5-1 |
| 3 | **Re-lock 2 — modify** | `sc.ModifyOrder` / Cancel+Submit | P5-5 |
| 4 | **Heartbeat** | פשוט 30s / ladder (KILL-if-open = החלטת סיכון) | P5-6 |
| ✅ | **D-093.Q2 — חשבון** | 🔒 נעול: IronBeam 37138283 (Apex מת) | — |
| — | **הסרת Apex** | להחליף כל `PA-APEX-125218-01` → IronBeam 37138283 | מאושר עקרונית |

**שער:** שום דבר בשלב 3 לא מתחיל עד שכל 4 ננעלו **ו**-SHADOW ירוק.

---

## שלב 3 — מימוש (אחרי נעילה · בסדר · עם בקרות)

| חבילה | מה | בקרה / שער |
|-------|-----|------------|
| **P5-0c** | מחיקת הנתיב הלא-קנוני + 3 executor stubs מתים + מופעי Apex | אחרי נעילת Q1 |
| **P5-7** | חיבור `TradeCommandHandler` ל-bridge startup + health metric | "just wire", לא לגעת ב-handler |
| **P5-6** | DLL heartbeat כל bar + `dll_watchdog.py` | לפי החלטה #4 |
| **P5-1** | DLL DEMO order: `sc.BuyEntry/SellEntry`+Attached (#2), החלפת `MES_AI_DataExport.cpp:813-816` | **mode=demo בלבד · HARD-GATE: `sc.GlobalTradeSimulationIsOn()==true` או refuse · IronBeam 37138283 · sc_study רק בבלוקים המותרים** |
| **P5-2** | מיפוי תוצאה (FILLED/REJECTED/PARTIAL/WORKING/CANCELLED + order_id/fill) | — |
| **P5-3** | נתיב LIVE בבקאנד (gateway קנוני) | מאחורי `BRIDGE_LIVE_ENABLED` (default off) |
| **P5-4** | position reconciliation (`position_state.json` + `position_reconciler.py`) | DRIFT_ALERT |
| **P5-5** | שינוי הזמנות (#2 re-lock) | — |
| **P5-8** | E2E UAT — 3 הרצות (SHADOW/DEMO/LIVE-על-demo), 4 צירי UAT | שער אחרון |

**בקרות רוחביות (כל שלב 3):**
- DEMO לפני LIVE; LIVE רק מאחורי env flag.
- רגרסיה + דוח לכל package (אוטומטי, באותו פורמט).
- אסור לשנות `sc_study/` מחוץ לבלוקים המותרים (P5-1: 813-855 · P5-4: T2.4 · P5-6: T2.5).
- אפס שינוי risk/sizing מעבר למה שנעול; sizing מבוסס-תנודתיות = **לא מאושר**.
- עצירה אסטרטגית + דיווח בין packages.

---

## רצף ביצוע מסכם
1. **שלב 1** (audit) → דוח עם המלצות. *(אפשר עכשיו, read-only)*
2. **שלב 2** — Michael נועל את 4 ההחלטות + מאשר הסרת Apex.
3. **שלב 3** — מימוש P5-0c → P5-7 → P5-6 → P5-1 → P5-2 → P5-3 → P5-4 → P5-5 → P5-8.

הצעד המעשי הראשון: מגה-פרומפט ל**שלב 1 (P5-0 audit)** — read-only, מייצר את
הבסיס ל-4 ההחלטות, לא נוגע בקוד.
