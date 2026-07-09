# צ'אט-S1 — ריצוד סיווג חי + כותב-מצב מת (ראיות 2026-07-09, סשן LIVE)

**Onboarding:** `docs/handoff/START_HERE.md` + ‏`docs/spec_authority/DALTON_DOCTRINE.md`.
עבודה על ענף/קוד בלבד — **אין ריסטארט backend בלי אישור מייקל/Cowork** (פוזיציה חיה).

## ראיה 1 — ריצוד הסיווג שהזין את השערים (מתוך /tmp/backend.err.log)
- ‏17:00 ‏playbook: ‏"REACTIVE SKIP on **Nontrend**"
- ‏17:20 ‏TargetClamp: ‏"(SHORT **Normal**)"
- ‏17:40 ‏playbook: ‏"ZLR SKIP on **Nontrend**"
- ‏18:35+ ‏playbook/clamp: ‏"**Variation** (trend=BLUE)"

בעוד ‏classify_replay (המנוע המאומת, אותם ברים) על 2026-07-09: ‏FORMING → ‏Normal מ-09:55 ET
→ ‏final ‏Normal_Variation ‏with_extension ‏(rib 1.358). כלומר: הנתיב החי (‏get_live_day_type /
‏_NC_CACHE ב-`trade_context.py`) ריצד ‏Nontrend↔Normal↔Variation בשעה שהריפליי היה יציב.
כל ריצוד = שערי-מסחר קופצים (‏playbook ‏SKIP הרג ‏REACTIVE/ZLR ב-17:00/17:40 ביום עליה).

**משימה 1:** למצוא את מקור אי-ההתאמה בין הנתיב החי לריפליי (חלון ברים שונה? ‏cache?
‏bars חלקיים בזמן-אמת?) + **anti-flap**: היסטרזיס/אישור-2-ברים לשינוי סיווג בנתיב החי
(עקבי עם ‏P0-1 acceptance שבצנרת שלך). לא לשנות את מנוע-הריפליי.

## ראיה 2 — v9_day_type_state מת לפני הפתיחה
שורה אחרונה: ‏id 9103, ‏ts ‏2026-07-09 16:00:08, ‏"B2 Variation 0.26 LOCKED_LOW_CONF" —
**הכותב שתק מ-16:00 (חצי שעה לפני הפתיחה) כל הסשן.** במקביל ‏/api/v9/day_type/state
(הראפר הישן) מגיש את אותו ערך קפוא, ו-‏direction_context_live קורא ‏day_type מהטבלה המתה
(שורה ~107) לצורך ‏trend-day-override → מוזן זבל.

**משימה 2:** להחיות את הכותב (למה נעצר? ‏exception שקט = הפרת SYS-2 — להוסיף ‏WARNING),
וליישר את כל הקוראים למקור החי האחד (זה ‏P0-3 שלך — ‏DAY-3 בספר: מנוע=UI=שערים).

## הקשר
היום זה עלה כסף אמיתי: הריצוד + ‏Nontrend השגוי חסמו את כל תבניות-ההמשך ביום דרייב-אפ ‏+50 נק'.
דו"ח מלא של שאר השרשרת: `docs/handoff/CC_LIVE_INCIDENT_FIXPACK_2026-07-09.md` (בטיפול CC — לא שלך).
Rule 5: כל ממצא עם פקודה+פלט גולמי. סעיף NOT-DONE חובה בדיווח.
