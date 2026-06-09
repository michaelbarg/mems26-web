# CC MEGA PROMPT — GAP-3 (R:R selection) · GAP-4 (MAX_CONTRACTS) · GAP-6 (ZLR)

**תאריך:** 2026-05-31 · **מקור:** Cowork (Michael אישר לאחד threads 1+2+4 לפרומפט אחד)
**מצב:** SHADOW בלבד · flags default OFF · אפס נגיעה ב-order/risk/sizing/polling
**סוג העבודה:** READ-ONLY / diagnose-first. **אסור** לשנות קוד לוגיקת-מסחר במשימה הזו.
משימה A מפיקה **טיוטת D-decision לאישור Michael** — לא מימוש.

---

## חוקי-על (חובה — מ-CLAUDE.md + mems26-pre-live-protocol.mdc)

1. **Diagnose-first.** קרא את הקוד הנוכחי לפני כל אבחנה. אל תאבחן מהזיכרון.
2. **Rule 5 — Verification quote, not assertion.** כל קביעה ("עובד" / "0 כשלים" /
   "לא נאכף") חייבת להגיע עם **הפקודה + הפלט הגולמי** מודבק בדוח. ללא פלט = לא קביל.
3. **אפס שינויי קוד** במשימות A/B/C חוץ מהרצת בדיקות קריאה. אם מתחשק לתקן — **עצור**
   ורשום כ-finding. שינוי trading-logic/risk/sizing = strategic-stop + אישור Michael.
4. **שלושה דוחות נפרדים** ב-`docs/reports/` (שמות למטה) + טיוטת D ב-`docs/decisions/`.
5. כל ממצא/החלטה → עדכן `STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html` בסוף (smallest correct change).

---

## משימה A — GAP-3: טיוטת D-decision לבחירת היורה לפי R:R (DRAFT בלבד)

**רקע מאומת (Cowork קרא את הקוד 31/5):**
- `backend/v9/gateway/trading_gateway.py:123-141` = **first-wins** טהור. DEMO: `if self.demo_slot is None:` ממלא slot, אחרת לוג "slot occupied, skipping". LIVE: אותו דבר + `passes_strict_checks`.
- **אין** buffering, אין השוואה, אין ranking, אין חישוב R:R בשום נקודה.
- ה-setup dict שמגיע ל-`route_setup` מכיל: `entry_price`, `stop`, `t1`, `t2`, `t3`, `direction`, `confidence`, `classification`, `firing_system`, `metadata`. (אמת מול `_build_trade:296-313` ומול ה-emitters של S2/S3/S4.)
- כוונת Michael (STATUS_BOARD §⚙️3, FULL_PATH_MEGA_TABLE GAP-3): לבנות חישוב **רווח/הפסד בדולרים** ולבחור את היורה לפיו — במקום first-wins. **פיצ'ר חדש שמשנה התנהגות מסחר → דורש D-decision + אישור לפני מימוש.**

**מה לעשות (READ-ONLY + כתיבת טיוטה):**

A1. **Audit הנתיב הנוכחי.** מ-emit (S2 `five_min/setup_emitter.py`, S3 `footprint_system.py`, S4 `woodies/decision_tree.py`) → `route_setup`. תעד: איפה בדיוק כל מערכת קוראת ל-gateway, האם setups מתחרים יכולים להגיע באותו בר/חלון, ומה גודל החוזים (sizing) שכל setup נושא ומאיפה (Auth Table?). הדבק grep/קוד גולמי.

A2. **אמת את ערך הדולר-לנקודה ממקור-אמת.** אל תניח $5/נקודה ל-MES. חפש בקוד/spec את הקבוע (tick value / point value) והדבק את המקור. אם אינו קיים בקוד — רשום זאת כפער (צריך קבוע מתועד-TZ/units לפני מימוש).

A3. **כתוב טיוטת `docs/decisions/D-094_RR_FIRE_SELECTION.md` (DRAFT · status=PROPOSED, ממתין לאישור Michael)** הכוללת:
   - **נוסחה:** `risk_usd = |entry − stop| × contracts × point_value`. `reward_usd` = רווח פוטנציאלי **משוקלל לפי contract split** (T1/T2/T3 — לפי כמה חוזים יוצאים בכל target; הצג את הנוסחה המדויקת ואיך split נקבע). `R:R = reward_usd / risk_usd`.
   - **כלל בחירה:** מה בדיוק מנצח (R:R הגבוה? סף R:R מינימלי? composite עם confidence?). הצג ≥2 חלופות עם trade-offs, וסמן את המומלצת — **בלי להחליט במקום Michael.**
   - **חלון buffering:** כמה זמן/כמה ברים לאסוף setups מתחרים לפני בחירה, ומה קורה ל-SHADOW בינתיים (SHADOW תמיד מתעד הכל — אסור לפגוע). הצג trade-off latency מול completeness.
   - **tie-breaking:** מה קורה כש-R:R שווה (confidence? firing_system priority? first-wins כ-fallback?).
   - **אינטראקציה עם הקיים:** איך זה מתיישב עם cluster_guard/cooldown/SSV/chop gates (שרצים *לפני* slot fill) ועם first-wins ב-DEMO/LIVE. האם הבחירה היא רק על ה-slot של DEMO/LIVE או גם משפיעה על SHADOW.
   - **שאלות פתוחות ל-Michael** (רשימה ממוספרת לאישור).
   - **אפס קוד.** זו טיוטה לאישור.

**Deliverable A:** `docs/reports/GAP3_RR_SELECTION_AUDIT_2026-05-31.md` (ה-audit + ראיות) + `docs/decisions/D-094_RR_FIRE_SELECTION.md` (טיוטה PROPOSED).

---

## משימה B — GAP-4: audit אכיפת MAX_CONTRACTS (READ-ONLY)

**רקע מאומת (Cowork 31/5):**
- `backend/v9/gateway/risk_checks.py:20` → `MAX_CONTRACTS = 2`. **לא מופיע בשום `if` בתוך `passes_strict_checks`** (הבדיקות שם: time-cutoff, daily-loss, max-trades/day, consecutive-losses בלבד). כלומר הקבוע **מוגדר ולא נאכף** (GAP-4 + P30_L4_RISK_AUDIT R2 BLOCKER).
- **אי-התאמה תלת-כיוונית לאמת:** קוד=2 · Auth Table max=3/setup (`auth_table_v1.py` / `S2_AUTH_TABLE_V1.md`) · החלטת Michael 31/5=5. שלושה מספרים שונים.

**מה לעשות (READ-ONLY):**

B1. **מה MAX_CONTRACTS אמור לשלוט עליו?** אמת בקוד: per-trade (גודל עסקה בודדת) מול מצטבר (סך חוזים פתוחים בו-זמנית) מול מקבילי (כמה slots). הדבק grep של כל שימוש ב-`MAX_CONTRACTS` ושל מאיפה מגיע `contracts`/size בנתיב (Auth Table → setup → gateway → DB). קבע איזו סמנטיקה מתאימה לכוונת "תקרה".

B2. **אכיפה.** אשר שאין אכיפה כיום (הדבק את `passes_strict_checks` המלא + grep). תאר היכן *תוכל* להיאכף (`passes_strict_checks` ל-LIVE? gateway routing? sizing?) — **תיאור בלבד, ללא מימוש.**

B3. **יישוב מול Auth Table.** אם תקרה=5 אך Auth Table מקסימום 3/setup — עסקה בודדת לעולם לא תעבור 3 אלא אם משנים גם את Auth Table. הצג את ההשלכות: האם 5 = תקרה מצטברת על כמה setups? תעד את שלושת המספרים (2/3/5) ומה צריך להשתנות בכל תרחיש פרשנות.

B4. **שאלת החלטה ל-Michael:** נסח 2-3 שאלות חדות (סמנטיקה: per-trade/מצטבר/מקבילי? · ערך: 2/3/5? · האם לשנות Auth Table?). **אל תכריע.**

**Deliverable B:** `docs/reports/GAP4_MAX_CONTRACTS_AUDIT_2026-05-31.md`.

---

## משימה C — GAP-6: יישוב 39 ZLR failures מול pytest GREEN (verify-first)

**רקע מאומת:**
- `FULL_PATH_MEGA_TABLE` GAP-6: "39 ZLR test failures unresolved (P-W3)" ב-`tests/v9/systems/woodies/`, severity INFO, "no production impact".
- אבל `PYTEST_GREEN_FINAL_2026-05-31.md` מדווח **0 failed, 2535 passed**.
- **סתירה לכאורה.** אסור להניח. צריך להוכיח: האם ה-ZLR נתקנו, דולגו (skip/xfail), או לא נאספים בכלל (not collected).
- מקור היסטורי: `docs/reports/W5_ZLR_FAILURE_AUDIT.md`.

**מה לעשות (verify-first, הרצת בדיקות קריאה מותרת):**

C1. הרץ את חבילת ה-ZLR/woodies והדבק **פלט גולמי**:
   - `python3 -m pytest tests/v9/systems/woodies/ -v -rsxX` (rs כדי לראות skip/xfail reasons).
   - `grep -rn "ZLR\|zlr" tests/v9/systems/woodies/ | head -50` — כמה טסטי ZLR קיימים בפועל.
   - השווה: passed / failed / skipped / xfailed / **deselected/not-collected**.

C2. הסבר את הפער בין "39 failures" ל-"0 failed": מה קרה ל-39? (תוקנו ב-commit X? markו כ-skip? נמחקו? לא נאספים בגלל marker/conftest?). הדבק ראיה לכל קטגוריה.

C3. **שיפוט:** האם ה-ZLR באמת ירוקים, או שהירוק מושג ע"י דילוג שמסתיר רגרסיה (Rule 4/5 — דילוג שקט אסור). אם דילגו — האם זה מתועד ומכוון? תן verdict ברור עם ראיה.

**Deliverable C:** `docs/reports/GAP6_ZLR_RECONCILE_2026-05-31.md`.

---

## פלט סופי מצופה מ-CC

1. שלושה דוחות (`GAP3_...`, `GAP4_...`, `GAP6_...`) ב-`docs/reports/`.
2. טיוטת `docs/decisions/D-094_RR_FIRE_SELECTION.md` (PROPOSED).
3. עדכון `STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html` עם finding+evidence לכל פריט (Rule 5).
4. **אפס שינויי קוד מסחר.** אם משהו דורש תיקון — finding + strategic-stop, לא תיקון.

**שערים:** A→מימוש רק אחרי אישור Michael ל-D-094. B/C→דיווח בלבד; כל שינוי קוד בעקבותיהם = פרומפט נפרד אחרי אישור.
