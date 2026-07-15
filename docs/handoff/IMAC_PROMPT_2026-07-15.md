# פרומפט ל-Claude במק-השני (iMac) — עדכון מלא + הכנה למסחר · 2026-07-15

**הקשר:** אתה ‏cc-imac. מק-הפיתוח (cowork-dev) סיים היום חבילת-תיקונים גדולה אחרי פורנזיקת-14/07.
המסחר רץ היום על מק-הפיתוח; תפקידך — ליישר את ה-iMac לגרסה האחרונה ולאמת **מוכנות-מסחר מלאה**,
כך שיוכל לשמש גיבוי-חם מיידי (ה-cutover עצמו נשאר בשער-הכתוב של ‏SECOND_MAC_SETUP.md ‏§10 — אל תדליק מסחר בלי GO של מייקל).

## שלב 1 — עדכון (פרוטוקול §10, או פשוט: מסך-ההפעלה → "עדכן לגרסה האחרונה")
1. ‏`git pull --ff-only` על ‏stabilize/mems26-local-truth-2026-05-16 (עשרות קומיטים מ-07-13→15).
2. ‏`python3 scripts/sync_env_from_ruled.py --apply` — מיישר את ‏.env לפסיקות (כולל החדשות מהיום:
   ‏FIXED_CONTRACTS_4=1 · ‏T0_TARGET_PTS=3.5 · ‏SYSTEM6_AUTOCORRECT=protective · ‏OPENING_WINDOW_FIRE_V1=1 ·
   ‏STOP_FLOOR_ROTATION_ATR=0.8 · ‏SSV_GATE_V1=0 · ‏FIXED_CONTRACTS_3=0).
3. ‏`python3 scripts/flag_guard.py` → חובה ‏PASS על כל הפסוקים (69+). כשל = עצור ודווח, אל תתקן דגלים לבד.

## שלב 2 — DLL
1. ‏`./scripts/build_monolithic_cpp.sh --deploy` (פורס ‏ACS_Source מקומי).
2. בסיירה: ‏Analysis → Build Custom Studies DLL → **Remote Build** → ‏reload לסטאדי.
3. **חובה אחרי כל בילד: לחמש מחדש ‏Input 22 ("Enable Order Placement")** — מתאפס בשקט (החוסם מ-07-13, ראה ‏4326112).
4. אם ‏sc_study כולל את הרחבת-4-החוזים (חפש ‏"t4" ב-‏MES_AI_DataExport.cpp) — ודא שהבילד כולל אותה.

## שלב 3 — אימות מוכנות (‏Rule 5: הדבק פקודה+פלט גולמי לכל סעיף)
1. ‏`scripts/mems26_verify.sh` → ‏OK (‏DLL==ריפו, פיד טרי, ‏DB עדכני).
2. ‏`python3 scripts/fire_drill.py` → ‏🟢 GO, ‏effective_contracts==4.
3. עין-סיירה: ‏sierra_state.json מתעדכן ≤2ש', ‏is_sim תואם את מצב-סיירה שם, ‏order_placement_armed=true.
4. **הוכחת-סים** (רק אם סיירה-iMac על SIM!): ‏BUY 4 → ‏4 זוגות-OCO (‏C1 יעד ‏±3.5=T0) → ‏FLATTEN_ACCOUNT → ‏qty=0.
   אם ה-DLL עוד בלי-t4 — הוכחה על 3 (‏contracts=3 בפקודה ידנית) וציין ‏NOT-DONE.
5. ‏Teton שם: מחובר? (ללייב-גיבוי חובה; לסים לא).

## שלב 4 — דיווח
‏append חתום+מתוארך ל-‏docs/handoff/AGENT_SYNC.md (‏LOG + סגירת שורת-ה-OPEN הרלוונטית) עם:
מה-עבר · מה-נכשל · ‏NOT-DONE מפורש · פלטים גולמיים. ‏commit+push. אל תיגע בעסקאות/מסחר — ‏read-only מלבד העדכון עצמו.

## מלכודות ידועות בדרך (חסוך לעצמך)
- ‏sot_health מציג ‏DB-🔴 כוזב (קורא SQLite מת) — האמת ב-‏postgresql://localhost/mems26.
- הריפו שם ב-‏~/mems26/mems26_web_git (לא Downloads); קיצורי-הדסקטופ כבר יודעים.
- ‏launchd חסום-TCC מ-.env בכמה הקשרים — הפידר רץ עם ‏--account auto (פותר לבד).
- אחרי ‏SetDefaults-שינויים ב-DLL נדרש לפעמים ‏remove+re-add לסטאדי — ואז ‏Input 4 (נתיב-ייצוא) + ‏Input 22 (חימוש) מתאפסים; בדוק את שניהם.
