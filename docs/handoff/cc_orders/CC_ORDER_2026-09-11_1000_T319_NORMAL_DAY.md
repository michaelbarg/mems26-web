## T-319 — דוקטרינת-מייקל 11.09 ~09:50 ליום Normal: "לסחור את ההיפוך ב-VAH/VAL עד ל-POC, או כל עוד הוא ממשיך — עד הצד השני; לא נכון להיכנס באזור ה-POC." מדידה קודם, אחר-כך בנייה. משתלב ב-T-316 (kind לפי מיקום).

### מה יש היום (KEEP/ADAPT — לא לבנות מחדש)
- שורת Normal בפלייבוק כבר אומרת את זה בכוונה: `bias BOTH · kinds [EDGE_FADE, VALUE_RETURN] · stop BEYOND_IB_EDGE · target POC · runner false`.
- **אבל** שלושה חיווטים חסרים בין הכוונה לביצוע:
  1. **מיקום-הכניסה** נגזר משם-התבנית (T-316): REACTIVE ב-POC עובר כ-EDGE_FADE; ZLR ב-VAL נחסם. וה-`mid_value` של `location_gate.zone_of()` (`backend/v9/systems/location_gate.py:150-165`, טולרנס יחסי ל-IB) + `daytype_position_gate` ("Normal: LONG רק מתחת ל-POC ליד VAL · SHORT רק מעל POC ליד VAH") — **מעוקפים כש-`_dp_active`** (`trading_gateway.py:1472, 1838`). הפלייבוק החליף אותם ולא נשא את כלל-ה-POC איתו.
  2. **היעדים**: `target_rule: POC` נפתר ב-`trade_economics.py:133` ל-`t1=POC, t2=2R, t3=3R` — לא "הצד השני"; ו-`TRADE_ECONOMICS_AUTHORITY_V1=diff` ⇒ היעדים האלה רק נרשמים, בפועל חיים היעדים של `#68 structural` + `STEP_SCALED_LADDER` + `STRUCT_TARGETS_WIN`.
  3. **R:R**: אתמול 20:30 REACTIVE SHORT @7605.5 נחסם `rr_entry_gate` (T1 3.5 מול סטופ 7) — כי הכניסה הייתה ב-POC. עם כניסה בקצה, T1=POC הוא ~חצי-רוחב-ערך והיחס מסתדר מעצמו.

### T-319a — המדידה (לפני כל דגל)
ריפליי על כל ימי-Normal (תווית-סופית מ-`v9_day_type_state`, `created_at`) מאז 01.08, לייב = `pnl_sierra` בלבד, תאומים = סימן: לכל סטאפ שהגיע לשער — `zone_of(entry)` (near_vah / near_val / mid_value / above / below) × כיוון × תוצאה. שלוש שורות-מספר: (i) כמה כניסות-לייב היו ב-`mid_value` וכמה הן עלו; (ii) כניסות בקצה נגד הקצה (fade) — Σ$; (iii) על אותן כניסות-קצה: יעד-POC-ואז-קצה-נגדי מול הסולם הנוכחי — הפרש Σ$ (יציאה סימולטיבית על ברי-5דק', לציין שזה סימולציה).

### T-319b — הבנייה (אחרי שמייקל רואה את המספר)
- **אזור-POC אסור לכניסה ביום Normal**: `zone_of(anchor)=="mid_value"` ⇒ `blocked_by=dalton_intent:location` (טולרנס `_tol(ib_width)` הקיים, לא נקודות קבועות). מיושם דרך T-316 (kind לפי מיקום): רק near_vah∧SHORT / near_val∧LONG (וגם above/below-value נגד המתיחה) = EDGE_FADE.
- **שרשרת-היעדים ל-Normal**: T1=POC · T2=קצה-הערך הנגדי (VAL/VAH) · T3=קצה-ה-IB הנגדי · runner=false. "כל עוד הוא ממשיך לצד השני" = הרגליים אחרי T1 נשארות עד T2/T3 עם סטופ ב-BE אחרי T1 (כלל 07-14). לממש ב-`trade_economics.resolve_targets("POC")` ולהפוך אותו **סמכותי לשורת-Normal בלבד** (`TRADE_ECONOMICS_AUTHORITY_V1` — לפתוח ערך `normal` או שקול; T-298 של המשמרת אמרה ש-`=1` לא ממומש — לא להדליק `=1` גלובלית).
- **סטופ**: `BEYOND_IB_EDGE` כפי שכתוב בשורה — מעבר לקצה שנכשל (VAH/VAL או IB) + טיק, לא סולם.
- golden מ-10.09 (Normal מ-17:35): 17:20 CEILING_FLIP_LONG (עוגן 7585.5=VAL/IB-low) ⇒ admitted, T1=POC 7602.75 · 20:35 DOUBLE_TOP_AA_SHORT (עוגן 7617.75≈VAH 7615.5) ⇒ admitted, T1=POC 7604.75, T2=VAL 7598.5 · ZLR LONG @7609–7614 (mid/near-VAH, LONG) ⇒ blocked location · REACTIVE SHORT 20:30 @7605.5 (mid_value) ⇒ blocked location (לא rr).
- `fwd_harness.py` על 08-03 · 08-04 · 09-09 · 10.09 + `RULED_FLAGS.yaml` עם הציטוט של מייקל ו-`measured:` מ-T-319a.
