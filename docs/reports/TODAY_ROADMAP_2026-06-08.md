# רודמאפ-היום · 2026-06-08 — מה נעשה ומה הוסכם בפועל

מצב-יום: עברנו מ-`verdict=BLOCKED, 0 armed` ל-`DEGRADED` + שלושה גייטי-ירי הוסרו + זוהה שורש-עומק (בר-חלקי).
כל שינויי-Cowork **flag-gated, reversible, default = ההתנהגות-החדשה, דורשים restart + אישור-Michael לשחזור**.

---

## 1 · שינויי-קוד (Cowork, uncommitted — CC יעשה commit+restart)
| # | שינוי | קובץ | דגל (default) | מצב |
|---|-------|------|---------------|-----|
| 1 | S2 `choppiness_ok` כובה | `s2_inspector.py` | `S2_CHOPPINESS_GATE` (off) | ✅ + טסט |
| 2 | Layer0 chop veto ב-gateway כובה | `trading_gateway.py:111` | `LAYER0_CHOP_GATE` (off) | ✅ + טסט |
| 3 | `tick_reversal_15`+`tpo` הוצאו מ-critical-streams (לא חוסמים verdict) | `aggregator.py` | — | ✅ + טסט |
| 4 | **S2 עצמאי מ-S3** — תלות COT/AMT הוסרה | `five_min_system.py` | `S2_REQUIRE_COT_AMT` (off) | ✅ + טסט |
| — | תיעוד | `CLAUDE.md` (§Chop Gates · §S2⟂S3) · `.env` | — | ✅ |
| — | טסטים | `test_chop_gates_disabled` · `test_readiness_noncritical_s3_streams` · `test_s2_independent_of_s3` | — | ✅ אומתו ב-sandbox |

## 2 · commits של CC היום
- `4a073c6` choppiness — חלון-מתגלגל (`bars[-6:]` במקום `[:6]`) — **בוקרה ואומתה ע"י Cowork**.
- `3b06a5d` + `4b5faf9` — שער `b1_expansion` יחסי לממוצע-טווח (לא מכפיל-ATR קבוע).
- `b1b4400` — מסמך-החלטה D-CHOP (choppiness→opening-only/advisory) + D-093 killzone=observer.

## 3 · החלטות שהוסכמו בפועל (היום)
1. **Killzone = observer בלבד** — לא חוסם ירי (אומת, לא שונה).
2. **שני שערי-chop כבויים** עד אישור-מפורש (S2 inspector + Layer0 gateway).
3. **tick_reversal_15/tpo = לא-קריטיים** ל-verdict — S3 מושתק (`S3_MUTE`) / S5 לא-מחווט. (תיקון טענת-Cowork: הם חסמו רק תצוגה, לא ירי.)
4. **S2 עצמאי לחלוטין מ-S3 בשלב זה** — COT/AMT לא נדרש לירי-S2.
5. **day_type freshness = תקלת-תצוגה** (observer, לא זרם-360s) — לתיקון ב-frontend.
6. **Build-Status נקי** — רק פריטים בנתיב-הירי; מושתקים/לא-מחווטים לא אדומים-BLOCKED.
7. **near-miss / K-ים** — לתעד, **לא** לשנות סף בלי אישור.

## 4 · ממצאי-שורש (אבחון)
- **🔴 בר-חלקי (השורש העמוק, CC מצא + Cowork אישר):** detection רץ על ה-push הראשון של בר חדש ⇒ **b4 (בר-הקונפירמציה) תמיד חלקי** → הקונפירמציה לא מתקיימת → S2 כמעט אף פעם לא יורה. תיקון בפרומפט (4 תנאים). **גם אחרי chop+COT/AMT — בלי תיקון זה S2 לא יירה.**
- **GRAY של היום = חוסר-מגמה אמיתי** (CCI סביב-אפס, לא קיצוני) — ה-extreme-relabel (±200, מ-06-02) נכון שלא ירה. תיקון-שישי היה GRAY-תצוגה (I-15), לא עצירת-GRAY אמיתי.
- **טבלת-19 (CC):** 0 חסומות ב-DISPLAY אחרי התיקונים; החוסמים ה-REAL = trend-GRAY (9×S4) · auth-SKIP×Trend_Normal (4) · detection/near-miss (6×S2).

## 5 · פתוח / הצעד הבא (נשלח ל-CC)
פרומפט מאוחד `CC_COMBINED_DETECTION_FIX_AND_SHADOW_2026-06-08.md`:
- **A** תיקון בר-חלקי (4 תנאים: engine+inspector אותו חלון · כירורגי+emit · flag+test · הוכחת-פרמיסה חיה).
- **B** השלמת חקירה (עמודת-חלון-הזדמנות S4 · ראיות Phase 0/2 · סיבת-DEGRADED · near-miss table).
- **C** פאנל "זיהוי תבניות" בטאב SHADOW לפי מערכת + ניקוי-frontend.

**ממתין לאחר CC:** ביקורת-Cowork (Rule 5) על כל פלט גולמי לפני אישור.
