# MEMS26 · מיפוי עץ-החלטות לכל תבנית — מה יש / מה חסר (משימה)

**הממצא (אומת בקוד, תואם ל-UI "מערכת ללא עץ A1–A7 מלא — רק Woodies"):**
רק **S4/Woodies** חושף עץ-החלטות מובנה (`woodies/decision_tree.py` + שלבי `stages/a1..a7`
לפני-ירי + `b1..b14` תוך-עסקה + `woodies_inspector.py` ל-build_status). **S2 ו-S3
אין להם עץ A1–A7 מובנה** — ההחלטה מפוזרת ב-detectors+gates, ולכן אין "TO FIRE" מסודר ב-UI.

מטרת-המשימה: לכל תבנית — לרשום את שלבי-העץ (תנאי TO FIRE), לסמן **יש** (קיים בקוד) /
**חסר** (לא קיים או לא חשוף ב-UI), כדי שכל תבנית תציג A1–A7-שקול עם מה-מתקיים/מה-חסר.

מקרא: ✅ קיים+חשוף · 🟡 קיים-בקוד-לא-חשוף-ב-UI · ❌ חסר.

---

## S4 · Woodies — עץ מלא ✅ (תבנית-ייחוס)
שלבי-העץ (פר תבנית: ZLR/TLB/TT/GB100/HFE/HTLB/FAMIR):
| שלב | תוכן | מצב |
|-----|------|-----|
| A1 strategic_gate | שער-אסטרטגי (trend/market state) | ✅ |
| A2 day_type_query | שאילתת day_type (S1) | ✅ (תלוי I-1: day_type=UNKNOWN משבית) |
| A3 pattern_detection | זיהוי התבנית (ZLR: extreme≤-100→pullback→trigger; AP1/AP8) | ✅ |
| A4 poc_suffering_query | POC/suffering touch-point | ✅ |
| A5 otf_clarity_query | בהירות-OTF — **advisory בלבד, לא חוסם** | ✅ (אבל מוצג כחוסם — I-2) |
| A6 entry_classification | סיווג-כניסה + stop/targets | ✅ |
| A7 universal_checks | בדיקות-על (news/cooldown/risk) | ✅ |
| B1–B14 | ניהול תוך-עסקה (stop/T1-3/trail/EOD/flip) | ✅ |
**חסר ל-S4:** רק תיקון-תצוגה A5 (I-2), ותלות ב-day_type (I-1).

## S2 · 5-Min — אין עץ מובנה ❌ (לבנות)
ההחלטה היום: FHB eligibility (Tree V3.3 §Stage B) → detectors → day-type gate →
pre_fire_validator → gateway. **אין עץ A1–A7 אחד.**
תבניות: REACTIVE L/S · INITIATIVE L/S · INV_HNS · HNS_TOP · DOUBLE_BOTTOM_EE ·
DOUBLE_TOP_AA · BULL_FLAG · BEAR_FLAG.
| שלב-שקול | מה קיים | מצב |
|----------|---------|-----|
| eligibility (FHB) | bars 1-3 ACCUMULATING→bar4 EARLY וכו' | 🟡 קיים, לא כעץ ב-UI |
| day_type gate | Pkg 5a/b/c gated על day_type | 🟡 (משובת כש-UNKNOWN, בשקט — I-1) |
| pattern detection | reactive/initiative/chart detectors (`stage:4`) | 🟡 |
| pre_fire_validator | side/order/R:R/conf | 🟡 |
| universal/gateway | session/killzone/chop/cooldown/cluster | 🟡 (`blocked_by`) |
**חסר ל-S2:** עץ A1–A7-שקול אחיד פר-תבנית + חשיפה ל-build_status ("TO FIRE" rows).

## S3 · Footprint — אין עץ מובנה ❌ (לבנות)
ההחלטה: signal detector → `_fire` → pre_fire_validator → gateway. **אין שלבים מובנים.**
תבניות: ABSORPTION · STACKED_IMBALANCE · SWEEP_RETURN · EXHAUSTION.
| שלב-שקול | מה קיים | מצב |
|----------|---------|-----|
| signal detection | ratio/imbalance/sweep/exhaustion | 🟡 בקוד |
| dedup gate | level+direction+bar_ts | 🟡 |
| pre_fire_validator | — | 🟡 |
| universal/gateway | `blocked_by` | 🟡 |
**חסר ל-S3:** עץ-שלבים מובנה + חשיפה ל-UI; גם S3 מושתק כרגע (S3_MUTE).

---

## המשימה (מסודרת)
1. **לכל תבנית** (8×S2 · 4×S3 · 7×S4) — לרשום את שורות ה-"TO FIRE" (התנאים) ולסמן
   ✅/🟡/❌ + מקור-קוד + ערך-Sierra החי שמתקיים/חסר. (סוכן-הדיאגנוסטיקה ממלא 5-שאלות פר-תבנית.)
2. **לבנות עץ A1–A7-שקול ל-S2 ו-S3** (כמו S4) + חשיפה ב-`build_status` כך שכל תבנית
   מציגה עץ אחיד עם מה-מתקיים/מה-חסר/מה-חוסם. (trading-surface → אישור Michael לפני מימוש.)
3. **הערה בדאשבורד (Setup&Fire):** במקום "מערכת ללא עץ A1–A7 מלא" — להציג את העץ-השקול
   או הערה ברורה אילו שלבים זמינים פר-מערכת.

**נכנס ל:** `MEMS26_ISSUES_REGISTER.md` (I-10) · roadmap פאזה-0 · סוכן-EOD מכין עיצוב.
