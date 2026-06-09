# CC PROMPT — סידור הכיול: תיקון wiring דגלים + scaffolding לכיול SHADOW

**תאריך:** 2026-05-31 · **מקור:** Cowork · **מצב:** SHADOW בלבד · diagnose-first · Rule 5 · smallest correct change
**רקע:** Michael אישר 31/5 להדליק 5 דגלים ב-`.env` (`S2_ATR_RELATIVE`, `S3_RELATIVE`, `S1_CVD_OPENING`, `S1_IB_WIDTH_ATR`, `S1_DAYTYPE_STAGING`). אבל audit (Cowork 31/5) מצא ש**חלק מהדגלים מתים בענפים שחשובים לכיול** → SHADOW יאסוף נתונים על הלוגיקה הישנה. הפרומפט הזה מתקן את ה-wiring **לפני** שמתחילים לאסוף, ואז מוסיף scaffolding לכיול.

> **עיקרון (חובה):** דגל/שינוי-החלטה חייב להגיע ל**כל** ענף מושפע — לא רק למודול שבו הוא נקרא ראשון. אסור wiring חלקי/מת.

---

## חלק A · audit + תיקון wiring דגלים (diagnose-first)

לכל אחד מ-5 הדגלים: grep את **כל** הצרכנים, ולכל ענף החלטה מושפע ודא שהדגל אכן משנה התנהגות שם. הדבק grep גולמי + ממצא KEEP/BROKEN לכל אתר.

**חשדות מאומתים מראש (Cowork) — לאמת ולתקן:**

1. **`S2_ATR_RELATIVE` מת ב-OFA.** `backend/v9/systems/five_min/five_min_system.py` — `get_expansion_range`/`get_poc_return_tolerance` קיימים (~:40-60) אך `_detect_initiative` (~:561,:570) עדיין קורא לקבועים הסטטיים `EXPANSION_MIN/MAX_PT` / `POC_RETURN_TOLERANCE_PT`. **תקן:** ה-detector יקרא ל-helpers היחסיים כשהדגל ON (fallback לקבוע כש-ATR=None). flag-OFF = זהה.

2. **`S3_RELATIVE` מת בזיהוי.** `backend/v9/systems/footprint/` — `get_min_level_vol` (`signals/stacked_imbalance.py`) ו-`get_range_ticks` (`detectors.py`) מוגדרים אך **לא נקראים**; הזיהוי משתמש ב-`MIN_LEVEL_VOL=10` קשיח ו-`range_ticks=15.0` קבוע. **תקן:** לחבר את ה-helpers לנתיב הזיהוי כשהדגל ON. flag-OFF = זהה.

3. **לאמת שלושת הנותרים אכן חיים בכל הענפים:** `S1_CVD_OPENING` (detector.py:255 — האם מחליף סיווג חי מקצה-לקצה, לא רק reasoning_notes?), `S1_IB_WIDTH_ATR` (detector.py:65 + decision_matrix EXTREME), `S1_DAYTYPE_STAGING` (detector.py:78-114). אם מתגלה ענף מת נוסף — תקן באותו אופן.

**כללי תיקון:** מאחורי הדגל הקיים (default OFF = קוד נוכחי, golden identical). **אל תשנה ספים/priors** — רק חיווט. כל תיקון = regression test (flag OFF=identical · flag ON=הנתיב היחסי נקרא). הדבק פלט pytest גולמי.

---

## חלק B · scaffolding לכיול (observability — לא משנה החלטות)

ה-priors נעולים; הכיול ייעשה אחרי soak. כדי שיהיה ניתן לכייל מנתונים אמיתיים, ודא ש-SHADOW **רושם את המטריקות שעליהן מכיילים** (ב-`cross_context`/quality של ה-trade או טבלת audit ייעודית — בחר את הקיים, אל תיצור כפילות):

- **S2 Expansion:** ה-range בפועל של B1 ביחס ל-ATR5m (ratio), גם כשלא ירה — כדי לכייל את [1.5,2.0]×ATR.
- **S1 Opening (CVD):** `PE_30`, `net_CVD/total`, `range_exp`, וה-label שנבחר (CVD מול price) — לכיול ספי DRIVE/AUCTION.
- **S1 day_type staging:** החלטת כל checkpoint (30/60/90) + confidence — לכיול אינטראקציית staging↔נעילה.
- **S3:** strength + aux_count + confluence score לכל אות — לכיול ספי הגלאים.

**אל תרשום** סודות/מחירים מיותרים; הוסף רק מטריקות-כיול. כל שדה חדש = מתועד + נבדק.

---

## פלט מצופה
1. `docs/reports/CALIBRATION_WIRING_2026-05-31.md`: לכל דגל — grep צרכנים + KEEP/BROKEN + diff התיקון; פלט golden flag-OFF identical; פלט טסטי flag-ON; רשימת מטריקות-הכיול שנרשמות + היכן.
2. commits נפרדים (A wiring · B scaffolding). עדכון `STATUS_BOARD.md` (finding→fix→evidence, Rule 5).

**שערים:** flag default OFF — אפס שינוי בלי הדלקה. התיקון מממש את כוונת ההדלקה שאושרה (הדגל נעשה חי בענפים שהיו אינרטיים) — **לצפות בשינוי קצב/התפלגות מחר**. אל תשנה priors/ספים (strategic-stop אם נדרש). אל תיגע ב-Auth Table V2 / D-094 / order (threads נפרדים).
