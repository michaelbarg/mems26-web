# CC — Pattern Economics Package · 5 פריטים מאושרי-Michael (2026-07-02)

**Owner:** Michael · **Prepared by:** Cowork · **אישור:** Michael 2026-07-02 (~14:00 IL, צ'אט Cowork): "כן" על חמשת הפריטים כמקשה.
**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` — טסטים אנטי-טאוטולוגיים · פלט גולמי · NOT-DONE חובה.
**רקע ואסמכתאות:** `docs/spec_authority/PATTERN_RECONCILIATION_2026-07-02.md` (F-1..F-8, D-1..D-9) · `RESOLVER_TARGETS_BY_DAYTYPE.html` (ספק-07-01) · `S1_TRADE_MANAGEMENT_3CONTRACTS.md` (06-20) · נתוני מימון-סטופים שנמדדו היום (בגוף המסמך).
**עקרונות-על:** הכל flag-gated default-OFF (למעט עריכות-תאים בפריט 1 — ראה אזהרה שם) · SHADOW-first · לפני כל enable: חישוב-אחורה גולמי לפני/אחרי · בנייה ואקטיבציה אחרי-שעות בלבד · אף רמה סינתטית — כל מדרגה = קצה בר/מבנה אמיתי ±3 טיקים (Michael).

---

## פריט 1 · שמונת פסקי-התאים (D-1) — `config/daytype_playbook.yaml` + קוד נקודתי

⚠️ **ה-playbook פעיל ברנטיים עכשיו** (short-circuit ל-FULL רק כש-`DAYTYPE_POSITION_GATE=1`, והוא =0) ⇒ עריכת-תאים = שינוי-התנהגות-חי בריסטארט הבא. לבצע אחרי-שעות, ליידע את Michael לפני הריסטארט.

1. **REACTIVE×Variation = עם-הכיוון בלבד** — קוד: ב-`daytype_playbook.py:117` הבדיקה `require_with_trend` חלה רק על `_TREND_DAYS`; להרחיב ל-Variation (עבור תבניות עם `require_with_trend`). מקור-כיוון: `trend_state` (RED/BLUE); None → fail-open + log.
2. **HNS = כמו-REACTIVE** — `require_with_trend` נשאר, תאי TN/TDD: REDUCED→**SKIP** (יישור ל-auth), Variation נשאר FULL אך תחת ההרחבה מסעיף 1.
3. **INITIATIVE×Normal = SKIP** — תא playbook: REDUCED→SKIP (יישור ל-auth-code שכבר חוסם בפליטה). + לתקן את כרטיס-INITIATIVE ב-`PATTERN_PLAYBOOK_CANDLES.html` (סולם-Normal מוצג שם — להסיר/לסמן SKIP).
4. **HTLB = עם-המגמה בלבד** — להוסיף `require_with_trend: true` ל-HTLB (תאי TN/TDD נשארים FULL).
5. **TT+GB100×TN/TDD: REDUCED→FULL** ("לא מוקטן — לתקן את ההגדרה שלהן").
6. **DBDT×TDD: REDUCED→SKIP** (תמיכה בסוג-היום; יישור ל-auth).
7. **ZLR×NeuC: נשאר SKIP** (אשרור — אין שינוי).
8. **אבחון-TT (בלי שינוי-התנהגות):** למה 0 ירי אי-פעם — להשוות את תנאי `patterns/tt.py` מול שורת-TT ב-`S4_WOODIES_TABLE_A` ולדווח (טריגר תופס ~0.23% מהברים). כל שינוי → Michael.

הערת-scope: verdict=REDUCED אינרטי בגייטוויי (רק `.allow` נבדק, `trading_gateway.py:281`) — **לא** לחווט את `Decision.contracts` במסגרת החבילה הזו.

## פריט 2 · D-3 — יישור הרזולבר לספק-07-01 (`structural_targets.py`)

חוקי-הבסיס לכל סוגי-היום (היום קיימים רק ב-`_resolve_variation`):
- **C1 = ה-swing המבני הראשון** בכיוון (Williams K=2, close-confirm) — להרחיב את `_find_swing_t1` ל-Normal/NeuE/NeuC/Trend_Normal/Trend_DD. ב-Trend: ה-checkpoint הרחוק (IBH+2×IBw) עובר להיות חומר ל-C2/C3 — ספק-07-01 גובר על 06-20 (פסק D-3).
- **C2 = מבנה קרוב** (POC / IB-center / ½ext / swing-ביניים) הקרוב מקצה-הערך; **C3 = קצה-ערך/extension (רנר)**.
- **קאפים לפי הספק (min, לא max):** C1 ≤ `min(2×ATR₅ₘ, 0.30×dATR)` ≈14 · רצפת-C1 `0.5×ATR₅ₘ` ≈3.5 · רנר ≤ `min(1.5×dATR, 3×IBw)`. להחליף את `max(2×ATR, 2×risk)` הנוכחי (`:417-419`).
- **ATR חי** — לא 7.0 קשיח (`:411`); מקור: ATR₅ₘ שוטף + dATR-RTH נמדד.
- **אכיפת-מונוטוניות:** אחרי הרזולוציה — `|C1−entry| < |C2−entry| < |C3−entry|`, אחרת מיון/תיקון + log. לתקן את ה-fallback שבו `swing_t1=None` ⇒ C1=half_ext העמוק (`:225,239`) — ה-fallback בוחר את המדרגה הקרובה בתוך הרצועה. **טסט-רגרסיה חובה על הדגימה מ-07-02 13:00:** HTLB SHORT C1=7560.5 C2=7569.5 C3=7568.0 (הפוך) חייב להפוך מונוטוני.
- fail-safe ל-R-based נשאר. שדות `contracts`/`time_stop` שהרזולבר מחזיר נשארים לא-נצרכים (מחוץ ל-scope).

## פריט 3 · שער-R:R בכניסה — דגל חדש `RR_ENTRY_GATE_V1` (default OFF)

בגייטוויי, **אחרי** הצבת-היעדים המבניים (סדר קריטי — צריך C1 סופי וסטופ סופי): אם `|C1−entry| < |entry−stop|` → block (`blocked_by="rr_entry_gate"`) + log של שני המרחקים. חל על כל 16 התבניות, S2+S4. fail-open אם C1/סטופ חסרים. זהו כלל-06-20 של Michael ("מרחק ל-C1 קטן ממרחק-הסטופ → דלג") — הבלם הישיר של מימון-סטופים. ראיה מהיום: מאז 06-20 רק 8/55 עסקאות פגעו ב-T1; יחסי C1:סטופ נעו מ-0.77 (BULL_FLAG/ZLR — מימון ישיר) עד 17.6 (HTLB — יעד שלא נפגע).

## פריט 4 · Stop Resolver V1 — דגל חדש `STOP_RESOLVER_V1` (default OFF, SHADOW-first)

**רצועה:** רצפה `0.5×ATR₅ₘ` (≈3.5) · תקרה `1.2×ATR` ל-CONT / `1.5×ATR` ל-REV (מקדמי Table C — היום size-gate בלבד, כאן הם בוחרי-מדרגה) · hard-cap 25pt נשאר.
**כלל:** הולכים על סולם-המדרגות מהקרובה לרחוקה ובוחרים את הראשונה שמרחקה (קצה-מבנה ±3T) בתוך הרצועה. קרובה-מדי → מדרגה הבאה החוצה (משחרר את ההדוקים — I-55). כולן מעל התקרה → **אין עסקה** (`no_stop_in_band`, log). אף רמה סינתטית.

**סולמות ראשוניים (אושרו עקרונית; אשרור-סופי פר-תבנית בהמשך ההליכה):**

| תבנית | קרובה → רחוקה |
|---|---|
| REACTIVE | שפל-b3 → שפל-b2 (שפל-ההיפוך) → אזור-w4 |
| INITIATIVE | שפל-בר-הפריצה (w1) → שפל-b2 → הרמה-השבורה ∓3T |
| BULL/BEAR_FLAG | שפל-בר-הפריצה → **השפל של הבר-הנמוך-ביותר בחלק הצובר** (תיקון-Michael: לא "חצי-דגל") — אין מדרגה שלישית; מעבר=skip |
| VEGAS/GHOST | קצה-נר-ההיפוך → פתיל/כתף → קצה-הקאפ |
| ZLR/TLB/TT/GB100 | העוגנים הנוכחיים (כבר ברצועה) — עוברים דרך הרזולבר כמדרגה-יחידה |
| HTLB | consolidation_extreme הנוכחי |
| DBDT/HNS | second_bottom_top / shoulder הנוכחיים — לוודא התאמה לרצועה ולדווח |

**לפני enable (חובה):** חישוב-אחורה על כל הירי מאז 06-20 — טבלה גולמית תבנית × (סטופ-ישן, סטופ-רזולבר, מדרגה שנבחרה, %-בתוך-רצועה). בסיס-המדידה מהיום (חציוני, אחרי סינון BE-artifacts): REACTIVE 10.8-12 · FLAGS 15.6 · GHOST 13 · FAMIR 11.3 · VEGAS 11 · ZLR 8.5 · INITIATIVE 6.5-8.3 · HTLB 5.3.

## פריט 5 · ווליום-b4 ל-REACTIVE — דגל חדש `S2_B4_VOL_V1` (default OFF)

הכרטיס דורש "b4 עם ווליום עולה" — הקוד לא בודק (`five_min_system.py:690-693` — אין תנאי-ווליום על b4). תנאי: `b4_vol > b3_vol`, אחרת reject + log (עקבי עם וריאנטי-ה-VSA הקיימים). לשקול log-only שבוע ראשון.

---

## סדר-בנייה מומלץ + אימות
2 (רזולבר) → 1 (תאים) → 3 (שער-R:R, תלוי ב-2) → 4 (Stop Resolver) → 5 (b4-vol). כל פריט: טסט שנכשל-על-הישן ועובר-על-החדש · אין tautology · פלט גולמי. הפעלת דגלים: Michael בלבד, אחד-אחד, אחרי SHADOW.

## NOT-DONE (למלא בכנות)
- [ ] מה לא הושלם + סיבה
