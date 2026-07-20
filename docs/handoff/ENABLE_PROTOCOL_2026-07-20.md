# הנחיית-הדלקה מסודרת — הכשרת המערכת לדלתון (מייקל 2026-07-20)

**איפה הבעיה?** לא בקוד. **fix-1 (סטופ-מבני) + fix-2 (require_with_trend=כיוון-יום) בנויים ומאומתים
(28 טסטים, flag_guard 97/97) — אבל OFF.** המערכת רצה על ההתנהגות-הישנה כי הדגלים כבויים. הצעד האחרון =
**הדלקה-מסודרת + ריסטארט-אחד**, לפי התהליך, **מבוצע ע"י cc על מכונת-המסחר** (cursor מאמת, cowork חוק-5).
**בלי thrashing, בלי ריסטארטים חוזרים, בלי הדלקות-חלקיות.**

## מי עושה מה (בלי בלאגן)
- **cc (מכונת-המסחר):** מבצע את ההדלקה + הריסטארט-האחד (הוא בעל-המכונה + ה-buffer).
- **cursor:** מאמת כל צעד בחוק-5 + כותב/מריץ את הטסטים תחת-דגל.
- **cowork (אני):** אימות-סופי חוק-5 לפני "ירוק". **לא נוגע ב-.env/ריסטארט בעצמי.**

## תנאי-סף (כולם מולאו ✅)
- fix-1: `STRUCTURAL_STOP_ORIGIN_V1` + `STOP_WINDOW_COMPLETED_V1` + `STOP_WIDEN_TO_STRUCTURE_V1` — בנוי, 17+ טסטים.
- fix-2: `REQUIRE_WITH_TREND_DAY_DIRECTION_V1` — בנוי, 11 טסטים (RULED unset_or_0).
- flag_guard PASS 97/97 · 0 באגי-אמת ברגרסיה · byte-identical כש-OFF.

## פרוצדורת-ההדלקה (cc, צעד-אחר-צעד — רק אחרי פסיקת-מייקל "מאשר הדלקה")
1. `git pull` · `scripts/mems26_snapshot.sh "enable-dalton-block"`.
2. `.env`: הדלק את 4 הדגלים =1:
   `STRUCTURAL_STOP_ORIGIN_V1=1 · STOP_WINDOW_COMPLETED_V1=1 · STOP_WIDEN_TO_STRUCTURE_V1=1 · REQUIRE_WITH_TREND_DAY_DIRECTION_V1=1`
3. `config/RULED_FLAGS.yaml`: הוסף את 3 דגלי-הסטופ (expected "1") + עדכן REQUIRE_WITH_TREND ל-"1". `flag_guard` PASS.
4. **ריסטארט אחד** (`launchctl kickstart -k gui/$UID/com.mems26.backend`). **זה הריסטארט היחיד.**
5. אמת (חוק-5, פקודה+פלט):
   - `get_live_day_type=Variation` · `day_type/state` תקין.
   - **fire_readiness / dry-run:** short@VAH-Variation-down = **would_fire** (require_with_trend לא-SKIP).
   - סטופ על setup-אמיתי = **מעל שיא-המבנה + 6T** (לא בתוכו).
   - `rr_entry_gate` עובר (R:R נכון מהסטופ-הנכון).
   - health+phone 200 · fire_drill GO · חשבון תואם.
6. buffer-S2 יתמלא (~15-20 דק' — זה הריסטארט האחרון, בלי עוד). ואז המערכת יורה את השורט עם סטופ-מבני.

## גבולות-בטיחות
- מקס-הפסד היום **$800** · בלי op=EXIT · ORPHAN-auto OFF (גיבוי=FLATTEN ידני מהכיס) · is_sim לפי מייקל.
- **אם משהו לא עומד בחוק-5 בצעד 5 → עצור, אל תדליק, דווח.** לא "מדליקים ומקווים".

## מה נשאר ל-EOD (לא חוסם את הטרייד-היום)
Task#5 (מקור-יחיד+גלאי-הרחבה — מבטל את ה-override הידני) · Task#6 (רקונסיליאציה) · T2/T3-מבני · Task#3 (אזור-מת) ·
Task#8 (גיוס-buffer-בבוט — שריסטארט לא יסמא). כל אלה בנויים-בחלקם עם טסטים; הדלקה-מסודרת אחרי הטרייד.

**השורה:** הבעיה = הדגלים כבויים. פסיקת-"מאשר הדלקה" שלך → cc מבצע את הפרוצדורה → אני מאמת → השורט יורה נכון.
