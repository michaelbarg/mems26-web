# CC_NOW 2026-09-17 13:30 — תיקוני-סקירה לעץ ולסריקה (cowork-dev → cc-macbook) — 6 פריטים, ברצף, בלי לעצור

**הקשר:** ההזמנה של אתמול (`CC_NOW_2026-09-16_TREE_BUILD.md`) בוצעה ואומתה (routes זהים על 15.09+11.09, 98 טסטים). הקוד נטען היום 13:26 (pid 56123). הסקירה שלי + הריצה הראשונה של `gap_analysis.py` (11:50) מצאו **חמישה פערים** שהופכים את הפלט ללא-ראוי-להכרעה. אותם גבולות כמו אתמול: **אפס ריסטארט · אפס `.env` · אפס דגל · ריצות כבדות (הרנס/85 סשנים) רק אחרי 23:05** (בדיקה קצרה על סשן אחד עם `--dry` מותרת). קומיט-פר-פריט, טסטים, LOG עם פלט גולמי, בלי שאלות. ⚠️ **אל תטען שקובץ-טסט "קיים ועובר" בלי `ls` + `pytest` בפלט** — אתמול נטען `test_dalton_playbook.py 32/32` על קובץ שאינו קיים (LIVE_CHANNEL 23:46).

---

## F1 · T-389b — `day_type_final` מהברים, לא מה-`cross_context` (הדוח: 42 סשנים UNKNOWN + "None")

`gap_analysis.py` לוקח את תווית-היום מהעסקה הראשונה ⇒ UNKNOWN/None ברוב הסשנים ⇒ טבלת-סוגי-היום חסרת-ערך. **לתקן:** `day_type_final` = `classify_replay` על ברי-ה-RTH של הסשן (המנוע המאומת לפי `docs/SOURCE_OF_TRUTH.md`; אם החתימה דורשת IB/VA — לחשב מהברים כפי שההרנס עושה). `day_type_at_entry` (התווית החיה) נשמר כשדה נפרד לכל עסקה — **שניהם בדוח**: "מה היום היה" ו-"מה המערכת חשבה בכניסה". אם `classify_replay` לא מכריע ⇒ `UNRESOLVED` (לא None, לא ניחוש). **טסט:** סשן סינתטי עם הרחבה חד-כיוונית מעל 2×IB ⇒ Trend; סשן בתוך ה-IB ⇒ Normal/Neutral.

## F2 · T-389c — מסנן-שפיות לברים לפני הזיגזג (הדוח: 175 / 143 / 134 נק' ב-20 דק')

10.06 ו-29.07 מציגים תנועות בלתי-אפשריות ל-MES (‏104 נק' ב-5 דק'). **לתקן:** לפני הזיגזג — בר ש-`|close−prev_close| > max(25 נק', 6×ATR14-סיבתי)` או `high−low > 40 נק'` מסומן `SUSPECT`; סשן עם ≥1 בר-SUSPECT מקבל `data_quality: SUSPECT` ו**מוצא מהטבלאות המסכמות ומהענפים** (מדווח בנפרד ברשימת "סשנים שהוצאו + הסיבה"). **אל תתקן את הברים** (Rule 1 — אין סינתזה); רק לסמן ולהוציא. לבדוק גם `v9_bars_5min_woodies` מול `v9_bars_5min_continuous` באותם רגעים ולדווח מה מקור הקפיצה (גלגול-חוזה? טיק שגוי?). **טסט:** בר של 100 נק' ⇒ SUSPECT; בר של 12 נק' ⇒ נקי.

## F3 · T-389d — הסבר פער-המודל: "נלקח −1,030 נק' במודל" מול −45 נק' בברוקר

הדוח אומר שכניסות-הלייב הפסידו 1,030 נק' במודל הקבוע; הברוקר (‏`v9_trades.pnl_usd` לייב יולי-ספטמבר: −491 + 971 − 704 = −224$ = −45 נק'-חוזה) אומר אחרת פי-20. **לחקור ולדווח, לא לתקן את המודל:** (א) האם המודל סופר נק'×חוזים (5 חוזים בסולם) בעוד הברוקר סחר 2-5? — לדווח גם `pts_per_contract`; (ב) האם המודל מקצה סטופ-מלא לעסקאות שבפועל יצאו ב-BE/MAE-scratch (מערכת-6)? — לספור כמה מהעסקאות-החיות נסגרו `MAE_SCRATCH`/`BE`/`STRUCTURE_*` ומה המודל נתן להן; (ג) עסקאות עם `entry_ts` בלי בר תואם (Globex) — כמה. **הפלט:** סעיף בדוח "מודל מול ברוקר" עם שלושת המספרים. **כלל:** המודל הקבוע נשאר כמו שהוא (הוחלט 14.09) — הדוח מסביר את הפער, לא מזיז את המודל.

## F4 · T-390b — לחבר ברים לווקטור בשער (‏`vol_ratio` · `bars_since_high/low` · `atr_causal` יוצאים None בלייב)

ב-`trading_gateway.py` הווקטור מחושב עם `bars_rth_today=None, prior_sessions_bars=None` ("לא זמין בקלות") ⇒ שלושת השדות ש"ווליום וברים" נשענים עליהם ריקים. **לתקן:** (א) `bars_rth_today` — מהבאפר של `five_min_system` (‏`_cf_bars`, 120 ברים סגורים) מסונן ל-RTH של היום; (ב) `prior_sessions_bars` — קריאה אחת ל-DB לכל סשן (10 סשני-RTH קודמים, `v9_bars_5min_woodies`), **בקאש** במודול (‏`_PRIOR_CACHE[date]`), לא בכל החלטה; (ג) `atr_causal` על ברים סגורים בלבד. ולחשב גם את שורות-ה-**BAR** (החור שנשאר): ב-`bar_router` אחרי ה-handlers, על כל בר-RTH-5-דק' סגור — `log_decision_vector(kind='BAR', system=0, classification='BAR', vector=…)`. הכתיבה — **בתהליכון-רקע** (‏`threading.Thread(daemon=True)` או תור) — היום `safe_execute` סינכרוני על נתיב-השער; ו-`read_one` של `confidence` פעם-בבר (קאש), לא פעם-בהחלטה. **טסט:** וקטור על 3 ברים סינתטיים + 5 סשנים-קודמים ⇒ `vol_ratio` מספרי, `bars_since_low` נכון, וה-BAR-row נרשם.

## F5 · T-392b — `[TREE-DIFF]` משווה אוצר-מילים שונה + שורות-Placeholder + Rule A רחב מדי

(א) `_real_decision` הוא `blocked_by`-string או `"FIRED"`; `_tree_decision` הוא `allow/block/stand_down` ⇒ **כל** החלטה נרשמת כ-diff. **מיפוי:** real FIRED ≡ tree allow · real blocked ≡ tree block/stand_down; רק אי-התאמה אמיתית נרשמת, ובשורת-`TREE_SHADOW` נשמרים שני הערכים הגולמיים. (ב) `config/dalton_tree_v2_draft.yaml`: שתי שורות-Placeholder (T-329, T-355) — להוסיף ל-`SituationVector` את השדות שחסרים להן (‏`classification_prefix` = 12 התווים הראשונים של `classification`, ו-`prior_zone` כבר קיים) ולכתוב אותן כ-`expr:` אמיתי; (ג) **Rule A רחב מדי** — `day_type in [Variation…] and extension != 'none'` מתיר גם כניסה **נגד** ההרחבה. לתקן ל-`… and ((extension == 'down' and direction == 'SHORT') or (extension == 'up' and direction == 'LONG')) and entry_kind in ['BREAK','PULLBACK']`, ולהוסיף שורה: כניסה **נגד** ההרחבה ביום-Variation מותרת רק ב-`zone in ['above_value','below_value']` (הקיצון — פסיקת-מייקל 15.09 23:15 "לחכות שיגיע לקיצון"), אחרת `block`. **טסטים:** golden 15.09 19:10 GHOST SHORT (with-extension, mid_value) ⇒ allow; LONG באותו רגע ⇒ block; LONG ב-below_value ⇒ allow.

## F6 · T-392c — שתי שורות-טיוטה חדשות לעץ v2 מהלקח של 16.09 (צל בלבד, לא בנתיב-הירי)

מקור: [[T-397]] (פסיקת-מייקל 17.09 14:05, שלב D פתוח לימי-מגמה — כבר חי בפלייבוק מ-14:02) + ריפליי 16.09: העסקה שנתפסה (21:50 GHOST SHORT) לקחה 18 נק' מתוך mfe 81, ו-INITIATIVE_SHORT 21:30 @7678 (בר 25,987 חוזים מול ~4k) נשאר חסום כי התווית הייתה עדיין Variation.
1. **ראנר על המשך-מגמה בשלב D:** שורת-`expr:` ב-`config/dalton_tree_v2_draft.yaml`: `phase == 'D' and day_type in ['Trend_Normal','Trend_DD','Neutral_Extreme'] and ((extension == 'down' and direction == 'SHORT') or (extension == 'up' and direction == 'LONG'))` ⇒ `decision: allow`, שדה חדש `runner: true` (מידע לצל בלבד; `[TREE-DIFF]` מדפיס `runner=` כדי שנספור כמה פעמים זה היה חל). **לא** לשנות את הפלייבוק החי (`runner: false` נשאר — פסיקה).
2. **ענף-ווליום לשבירת-IB:** `entry_kind == 'BREAK' and vol_ratio >= 3.0 and ((extension == 'down' and direction == 'SHORT') or (extension == 'up' and direction == 'LONG') or extension == 'none') and zone in ['near_val','below_value','near_vah','above_value']` ⇒ `allow` (ה-21:30 של 16.09: הבר עצמו שובר את ה-IB-low, `vol_ratio ≈ 6`). דורש F4 (‏`vol_ratio` חי). ב-`gap_analysis.py` (F1-F3) לחשב `vol_ratio` היסטורי לכל setup מהברים (אותה הגדרה סיבתית: הבר מול חציון אותה-דקה ב-10 סשנים קודמים) כדי שהדוח ייתן N ו-Σ$ לענף הזה על 85 הסשנים.
טסטים: שתי השורות נטענות, golden 16.09 21:50 GHOST SHORT ⇒ allow+runner, golden 16.09 21:30 INITIATIVE_SHORT עם vector{vol_ratio:6.2, extension:'none', zone:'near_val', entry_kind:'BREAK'} ⇒ allow.

---

**דיווח:** אחרי כל פריט — LOG חתום עם פלט גולמי, `TASK_LOG` (‏T-389b/c/d כתת-שורות של T-389; T-390b; T-392b), commit+push, "סיים פריט N" **וממשיך**. אחרי F1-F3: להריץ `gap_analysis.py --dry --session 2026-09-15` ולהדביק את הפלט (סשן אחד — מותר בזמן RTH). הריצה על 85 הסשנים — cowork, הלילה אחרי 23:05; הקוד של F4/F5 נטען בריסטארט של מחר.
