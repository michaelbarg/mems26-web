# T17 — אימות סולם 4-חוזים + סטופ פר-שלב

**תאריך:** 2026-07-19 · cursor-agent · audit · אימות-סים מלא = cc-macbook

## 1. `effective_contracts == 4`?

| מקום | file:line | התנהגות |
|---|---|---|
| `.env` | `FIXED_CONTRACTS_4=1` · `T0_TARGET_PTS=3.5` | חי על המכונה (נבדק 2026-07-19) |
| `sizing.compute_v2_sizing` | `sizing.py:122-124` | contracts→4 כשדגל ON ו-contracts>0 |
| `effective_contracts` | `sierra_command.py:194-235+` | `_fc4_on` top precedence (אחרי exempt confluence) |
| `fire_drill.stage_c` | `fire_drill.py:102-109` | want=4 תחת FIXED_4 |
| `bar_level_detector` S6 | `bar_level_detector.py:67-68` | `_exp=4` תחת FIXED_4 |
| `system6_routes.py` | **:57 / :186** | ⚠️ עדיין fallback/`expected_contracts=3` במקום אחד — **פער תצוגה/אבחון** |

**מסקנה קוד:** נתיב-הירי הראשי כופה 4. יש שאריות le=3 ב-API S6 → לתקן ב-cc (לא שינוי-מסחר אם רק expected).

## 2. מיפוי 4 חוזים → יעדים

מ-`sierra_command.command_from_setup` :344-364 כש-`_contracts>=4` ו-`T0_TARGET_PTS>0`:

| חוזה | יעד | שדה DLL |
|---|---|---|
| **C1** | **T0** (entry ± T0_TARGET_PTS, כרגע 3.5) | `target_price` |
| **C2** | T1 (הישן) | `context.t2` |
| **C3** | T2 | `context.t3` |
| **C4** | T3 (runner) | `context.t4` |

בלי T0 (`T0_TARGET_PTS=0`): התנהגות 3-זוגות היסטורית (C1→T1…); עם 4 חוזים בלי T0 — לבדוק בסים שה-DLL מקבל t4.

ZLR_MGMT_V1 (OFF כברירת-מחדל): סולם 2×T1+1×T2 על 3 חוזים — לא רלוונטי ל-4 אלא אם יופעל.

## 3. סטופ לאורך המימוש

מ-`trade_manager/manager.py`:

| שלב | סטופ | הערות |
|---|---|---|---|
| Entry → לפני T1/T0-hit | סטופ מבני משותף לכל החוזים (attached OCO per lot בסיירה) | TM: "FIXED until T1" (`:584-585`) |
| אחרי **T1** hit | `_apply_smart_be_after_t1` → stop→BE | `:500-506` · **שימו לב:** עם T0, ה-hit הראשון הוא T0/C1 — האם BE אחרי T0 או אחרי T1 הישן? **פער לאימות-סים** |
| T2 / T3 | נשאר BE / trail לפי כללי pattern | runner trail נפרד |
| T4 (C4) | סגירה סופית כשכל החוזים יצאו | `:533+` C4 scale-out |

**סטופ-פר-חוזה:** המודל הוא **סטופ משותף** (כל ה-OCO lots מתעדכנים ב-MODIFY_STOP אחד), לא סטופ עצמאי לכל חוזה אחרי scale-out. אין נתיב "סטופ שונה ל-C3 vs C4" ב-TM.

## טבלת חוזה × יעד × סטופ (מצב נוכחי תחת FIXED_4+T0)

| חוזה | יעד | סטופ בכניסה | סטופ אחרי C1(T0) | סטופ אחרי C2(T1) |
|---|---|---|---|---|
| C1 | T0 | structural | (יצא) | — |
| C2 | T1 | structural | ? BE אם T0≡T1-hit path | BE |
| C3 | T2 | structural | ? | BE / trail |
| C4 | T3 runner | structural | ? | BE / trail |

**פער קריטי לסים:** האם `on_target_hit("T1")` נקרא על מילוי T0 או רק על T1 האמיתי — קובע מתי BE קורה. לא לשנות בלי סים+פסיקה.

## הצעות (לא מימוש כאן)
1. לתקן `system6_routes` expected_contracts לכבד FIXED_4.  
2. E2E סים: PLACE 4 · מילוי C1→C4 · לוג MODIFY_STOP בכל שלב · לאמת BE אחרי איזה hit.  
3. אם מייקל רוצה BE אחרי T0 (C1) — דגל OFF + טסט אנטי-טאוטולוגי.
