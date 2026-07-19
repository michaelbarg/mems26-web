# משימת-קורסור: דיבאג-מלא של המערכת — "האם הכל תקין" (GO/NO-GO ליום שני)

**פסיקת-מייקל 2026-07-19:** *"תייצר לקורסור בדיקה שהכל תקין — debug למערכת."*
**מבצע:** cursor-agent (קריאה-בלבד — לא משנה קוד/.env/DB, לא מריץ מסחר). **מאמת:** cowork-dev.
**תוצר:** `docs/reports/SYSTEM_DEBUG_2026-07-19.md` — טבלת בדיקות עם ✅/🔴 + פלט-גולמי לכל שורה,
ובראש **verdict אחד: GO / NO-GO ליום שני**, עם רשימת החוסמים אם NO-GO.

## החוק (חוק-5)
כל שורה = **פקודה + פלט-גולמי**. לא "אמור להיות תקין". `git pull` בהתחלה. אם בדיקה נכשלת —
**אל תתקן**, סמן 🔴 + הצע-תיקון בסוף כ**הצעה בלבד**.

---

## חלק א' — שירותים ותשתית
| # | בדיקה | פקודה | תקין = |
|---|---|---|---|
| A1 | backend חי | `curl -s -o /dev/null -w "%{http_code}" localhost:8000/api/v9/health` | `200` |
| A2 | frontend חי | `curl -s -o /dev/null -w "%{http_code}" localhost:3000` | `200` |
| A3 | אין מאזינים כפולים | `lsof -ti :8000; lsof -ti :3000` | PID יחיד לכל פורט |
| A4 | bridge רץ | `pgrep -fl v9_streams\|bridge` + `tail /tmp/bridge.err.log` | תהליך + אין `API push FAILED to https://` |
| A5 | DLL פרוס==ריפו | `scripts/mems26_verify.sh` | `deployed == repo`, אין drift |
| A6 | LaunchAgents | `launchctl list \| grep mems26` | bridge + backend טעונים |

## חלק ב' — שערים, דגלים, פסיקות
| # | בדיקה | פקודה | תקין = |
|---|---|---|---|
| B1 | flag_guard | `python3 scripts/flag_guard.py` | `PASS — all 90 ruled flags match` |
| B2 | 4 פסיקות-קוד נחתו | `git log --oneline -12 \| grep -E "ruling\|fix\(bars"` | cutoff · contamination · widen · A5 |
| B3 | דגלי-סיכון OFF-עד-סים | `grep -E "STOP_WIDEN_TO_FLOOR_ON_REJECT_V1\|ORPHAN_AUTO_STOP_V1" .env` | **לא מופיעים** (=OFF) |
| B4 | A5 חי | `grep S2_AUTH_MATRIX_SINGLE_SOURCE_V1 .env` | `=1` |
| B5 | סף-כניסות | `grep RISK_CUTOFF .env` | `HOUR_ET=15 MINUTE_ET=30` |

## חלק ג' — נתונים ומקורות-אמת (הלב — אחרי תקרית-הזיהום)
| # | בדיקה | פקודה | תקין = |
|---|---|---|---|
| C1 | **אין זיהום ב-v9_bars_5min** | ראה סקריפט למטה — קפיצות-close >15נק' מול woodies | **0 ברי-סתירה היום** |
| C2 | טריות-בָּרים | `SELECT max(ts) FROM v9_bars_5min_woodies` מול `now()` | פער < 2 בָּרים בשעות-מסחר |
| C3 | feed alive | `curl -s localhost:8000/api/v9/health \| jq .feed` (או is_feed_alive) | לא-HALT |
| C4 | shomer-הקליטה פעיל | `grep -c "cross-source guard" /tmp/backend.err.log` | קיים (או 0 אם אין זיהום) |
| C5 | TS-HOUR הודק | `grep "TS-HOUR-FIX SKIPPED\|applied" /tmp/backend.err.log \| tail` | applied רק על 3600±120 |
| C6 | 4 צירי-UAT לכל endpoint-נתונים | quality=0-bad · recency=latest==MAX(ts) · cardinality==limit · latency<סף | כולם ✅ |

**סקריפט C1 (הדבק ל-`SYSTEM_DEBUG`):**
```python
from backend.v9.db.read import read_all
w={r['ts']:float(r['close']) for r in read_all("SELECT ts,close FROM v9_bars_5min_woodies WHERE (ts AT TIME ZONE 'America/New_York')::date=CURRENT_DATE",{})}
bad=[]
for r in read_all("SELECT ts,close FROM v9_bars_5min WHERE (ts AT TIME ZONE 'America/New_York')::date=CURRENT_DATE",{}):
    wc=w.get(r['ts'])
    if wc and abs(float(r['close'])-wc)>15: bad.append((str(r['ts']),float(r['close']),wc))
print("contaminated bars today:",len(bad)); [print(b) for b in bad[:10]]
```

## חלק ד' — טסטים ובריאות-קוד
| # | בדיקה | פקודה | תקין = |
|---|---|---|---|
| D1 | טסטי-הפסיקות | `pytest tests/v9/regression/test_risk_cutoff_ruling.py tests/v9/regression/test_bars5min_contamination_guard.py tests/v9/regression/test_stop_widen_to_floor_reject.py tests/v9/regression/test_auth_matrix_single_source.py -q` | הכל pass |
| D2 | סוויטת-רגרסיה | `pytest tests/v9/regression -q` | pass (סמן פליקים ידועים) |
| D3 | **באג-איסוף ידוע** | `pytest backend/v9/tests/systems/woodies/stages/test_a1.py` | 🔴 `ImportError: A1Output` — **קדם-קיים, לא רגרסיה** → הצע לתקן/למחוק |
| D4 | index טרי | `python3 scripts/gen_index.py --check` ו-`gen_flag_index.py --check` | אין drift |

## חלק ה' — מסחר ובטיחות
| # | בדיקה | פקודה | תקין = |
|---|---|---|---|
| E1 | חשבון שטוח | `sierra_state.json` | `position_qty=0 working_orders=0` |
| E2 | מצב-סים נכון עכשיו | `sierra_state.json is_sim` | **לייב=0 / סים=1** — דווח מה יש |
| E3 | אין orphan/naked | `curl localhost:8000/api/v9/agent/sierra_live_check` | verdict 🟢, אין divergence |
| E4 | halt-cap שפוי | `grep RISK_DAILY_LOSS_CAP .env` | `=400` |

## תוצר
`SYSTEM_DEBUG_2026-07-19.md`: הטבלאות עם פלט-גולמי + **verdict GO/NO-GO** + סעיף
**"חוסמים ל-NO-GO"** (אם יש) + סעיף **"הצעות-תיקון (לא בוצע)"**. שורת-LOG ב-`LIVE_CHANNEL.md`:
`SYSTEM_DEBUG verdict=GO/NO-GO · N✅/M🔴 · <שורת-תמצית>`.

**אסור:** לשנות קוד/.env/DB · להריץ מסחר · לגעת ב-Sierra. **מותר:** כל קריאה, pytest, psql-קריאה,
mems26_verify.sh, sierra_live_check.
