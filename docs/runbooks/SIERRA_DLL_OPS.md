# Sierra DLL — תפעול, מיקומים, הגדרות, באגים (MEMS26)

**עדכון:** 2026-05-19 (P30.10 Woodies HUD + נתיבי Mac + Export 8b)  
**קהל:** Michael, Cursor, **Claude Code** (CC מעדכן מסמך זה אחרי בדיקה מול לוגים אחרים)

> **ל-Claude Code:** לפני עריכה — חפש עדכונים ב־`docs/PROMPT_1_HOTFIX_REPORT.md`, `docs/ENVIRONMENT.md`, `docs/reports/PROMPT30_8_5MIN_JSON_EXPORT.md`, `docs/handoff/P30_WOODIES_PANEL_AGENT_HANDOFF.md`, `docs/v9/dll_changes.md`. אם יש סתירה — הלוג **החדש יותר** מנצח; עדכן כאן וציין מקור.

---

## 1. שרשרת אמת — איפה הקוד חי

| שלב | מיקום | הערה |
|-----|--------|------|
| **מקור ב-repo** | `sc_study/v9_types.h`, `v9_exports.h`, `v9_woodies_export.h`, `MES_AI_DataExport.cpp` | עריכה רק כאן |
| **מונולית (גנרציה)** | `sc_study/MES_AI_DataExport_merged.cpp` | `scripts/build_monolithic_cpp.sh` — לא לערוך ידנית |
| **מקור לסיירה** | `~/SierraChart/ACS_Source/MES_AI_DataExport.cpp` | `--deploy` מעתיק את המונולית לכאן |
| **DLL מקומפל** | `~/SierraChart/Data/MES_AI_DataExport_64.dll` | נטען על ידי CrossOver / Sierra |
| **פלט JSON** | `~/SierraChart_Data/v9_export/*.json` | גשר + Cockpit קוראים מכאן |

**סיירה לא מקמפלת את ה-.h בנפרד.** תמיד: ערוך repo → `./scripts/build_monolithic_cpp.sh --deploy` → Remote Build → Reload study.

```bash
cd /Users/michael/Downloads/mems26_web_git
./scripts/build_monolithic_cpp.sh --deploy
# Sierra: Analysis → Build Custom Studies DLL → Remote Build (SUCCESS)
```

---

## 2. איפה שמים / איך שומרים

### קבצים שכן נשמרים ב-git (repo)

- `sc_study/*.h`, `sc_study/MES_AI_DataExport.cpp`
- `scripts/build_monolithic_cpp.sh`

### קבצים מחוץ ל-repo (מקומיים למכונה)

| קובץ | תפקיד |
|------|--------|
| `~/SierraChart/ACS_Source/MES_AI_DataExport.cpp` | מקור שהסיירה בונה |
| `~/SierraChart/Data/MES_AI_DataExport_64.dll` | בינארי — מתעדכן רק אחרי Build מוצלח |
| `~/SierraChart/ACS_Source/MES_AI_DataExport_merged.cpp.disabled-*` | עותק ישן שהוסר מהדרך (אל תשחזר) |

**אל תערוך ישירות את `~/SierraChart/ACS_Source/`** בלי לשקף חזרה ל-repo — השינוי יימחק ב-deploy הבא.

### אימות אחרי Build

```bash
# DLL חדש יותר מהמקור + גרסה נכונה
stat -f '%Sm' ~/SierraChart/ACS_Source/MES_AI_DataExport.cpp ~/SierraChart/Data/MES_AI_DataExport_64.dll
strings ~/SierraChart/Data/MES_AI_DataExport_64.dll | grep -E 'p30\.|SierraChart_Data'

# ייצוא חי
ls -lt ~/SierraChart_Data/v9_export/woodies_5min.json
python3 -c "import json; d=json.load(open('/Users/michael/SierraChart_Data/v9_export/woodies_5min.json')); print(d['version']); print(d['current_bar'].get('ccidiff_h'))"
```

---

## 3. הגדרות בתוך הסטאדי — איך נשמרות

ברירות המחדל מוגדרות ב־`sc.SetDefaults` ב־`MES_AI_DataExport.cpp` (Input 0–12).  
**סיירה שומרת ערכים לכל מופע סטאדי על הגרף** — בקובצי הגדרות הגרף / Study Settings, **לא** בתוך ה-DLL.

| Input | שם ב-UI | ברירת מחדל (Mac) |
|-------|---------|------------------|
| 0 | Export JSON Path | `/Users/michael/SierraChart_Data/v9_export/mes_ai_data.json` |
| 1 | Export Interval (seconds) | 3 |
| 4 | **V9 Export Directory** | `/Users/michael/SierraChart_Data/v9_export/` |
| 5–6 | Tick Reversal 15/12 | on |
| 7 | V9 Lookback Bars | 200 |
| 8 | V9 Woodies History Bars | 50 |
| 9–10 | Live Price | on, 200ms |
| 11–12 | Trade command/result paths | תחת `v9_export/` |

**אחרי שינוי נתיבים בקוד:** גרפים **ישנים** עדיין מחזיקים `C:\...` עד שמעדכנים ידנית:

1. גרף → Study Settings → `MES AI Data Export v9.4.0-p30.10`
2. Input 4 = `/Users/michael/SierraChart_Data/v9_export/` (סלאש בסוף)
3. או: הסר סטאדי והוסף מחדש (מושך defaults מה-DLL החדש)

`static V9_EXPORT_DIR` ב־`v9_types.h` משמש קוד פנימי; **הנתיב האמיתי לכתיבה** הוא `V9ExportPath.GetString()` (Input 4).

---

## 4. באגים שנמנעים (לקחי P30.10)

| באג | סימפטום | מניעה |
|-----|---------|--------|
| עריכת `.h` בלי deploy | JSON ללא שדות חדשים | תמיד `build_monolithic_cpp.sh --deploy` |
| `MES_AI_DataExport_merged.cpp` ישן ב־ACS_Source | Build מקוד p30.8, `SCDLLName` כפול | הסקריפט מזיז אותו ל־`.disabled-*` ב-deploy |
| פונקציה לפני הגדרה | `v9_cci_predictor was not declared` | `v9_woodies_json_hud_fields` **אחרי** `v9_cci_predictor` |
| חסר `v9_write_json(..., woodies_5min.json)` | קובץ קפוא, שאר JSON מתעדכן | Export 8b ב־`MES_AI_DataExport.cpp` |
| נתיבי `C:\` | כתיבה לנתיב שגוי ב-Wine | Mac paths ב־`SetDefaults` + Input 4 על הגרף |
| `std::max` / `min` | קומפילציה / מאקרו Sierra | `v9_max` / `v9_min` בלבד |
| DLL לא נטען מחדש | `version` ישן ב-JSON | Reload study אחרי Build; בדוק mtime DLL > cpp |
| בדיקת `version` ב־`current_bar` | תמיד `None` | `version` בשורש JSON: `d['version']` |
| Backend ישן | API בלי `ccidiff_h` | הפעלה מחדש uvicorn אחרי `woodies_chart_routes.py` |

### גיבוי זמני (עד DLL תקין)

```bash
python3 /Users/michael/Downloads/mems26_web_git/scripts/patch_woodies_5min_hud.py
```

לא מחליף Build — רק ממלא HUD בקובץ קיים.

---

## 5. ייצואים קריטיים (D-074 / P30)

| קובץ | נקרא מ־ | הערה |
|------|---------|------|
| `woodies_5min.json` | Cockpit Woodies panel, `GET /api/v9/woodies/chart` | Export 8b — HUD: `ccidiff_*`, `prev_ohlc`, `predictor_cci_high/low` |
| `5min.json` | Bridge `bars_5min` | היסטוריית 5m |
| `live_price.json` | Live price API | |
| `woodies_30min.json` | S4 legacy / replay | Export 8 |

**ProjHigh/ProjLow** — עדיין לא ב-DLL; subgraph מסיירה → `proj_hi` / `proj_lo` (ראה handoff matrix).

---

## 6. CC — צ'קליסט עדכון מסמך

- [ ] חפש `p30.10`, `woodies_5min`, `build_monolithic` ב־`docs/reports/` ו־`docs/handoff/`
- [ ] עדכן טבלת גרסאות / תאריך בראש מסמך זה
- [ ] אל תשנה `CLOUD_URL` / bridge לענן
- [ ] דווח ל-Michael: DLL mtime, `woodies_5min.json` version, שורת Build log אם נכשל

---

## 7. קישורים

- `scripts/build_monolithic_cpp.sh`
- `docs/ENVIRONMENT.md` § Sierra Chart DLL Rules
- `docs/PROMPT_1_HOTFIX_REPORT.md` (נתיבי Mac מקוריים)
- `docs/reports/PROMPT30_8_5MIN_JSON_EXPORT.md` (מונולית + 5min)
- `docs/handoff/P30_WOODIES_PANEL_AGENT_HANDOFF.md` § Export fields matrix

## חימוש-מסחר אחרי Build (07-13 — לקח BLOCKER)
- **"Enable Order Placement"** = `sc.Input[21]` (קוד, 0-based) = **"In:22"** בתצוגת-סיירה (1-based). זהה **לפי השם**, לא מספר.
- כל **Remote Build / reload / re-add** מאפס אותו ל-0 (OFF) בשקט. חובה להעמיד **1 (DEMO)** אחרי כל בילד.
- אימות מ-`sierra_state.json`: `order_placement_armed:1` + `send_orders_to_trade_service` (סים→0/לייב→1).
- `armed=0` = המערכת אילמת ולא תפתח פוזיציה. `result` ריק על BUY = בינארי מיושן מהמקור → Remote Build שוב.
- toggle של Trade Simulation אמצע-סשן עלול לשבור state (SendOrders/account) → הפתרון: Remote Build + reload (מאפס state נקי) ואז חימוש-מחדש.
