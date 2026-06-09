# CC — אבחון: Build Status לא מתעדכן / גשר מת באמצע RTH (2026-06-08)

**ממצא-Cowork (חי, 13:43 UTC, session=FIRST_HOUR):** `/api/v9/build/pattern-status`
מחזיר 200 עם `ts` עדכני — **הלוח עצמו מתעדכן**. אבל הוא מדווח
`bridge: running:false, streams_active:0/11` בעוד `sierra: writing:true, age<1s`.
ב-12:48 הגשר **כן** דחף (`push #780`); עכשיו לא. **הגשר כנראה מת/נתקע** — לכן הלוח
מציג dead/stale. זה גם חוסם SHADOW (אין ברים → אין ירי). diagnose-first, read-only,
פלט גולמי ל-`docs/reports/BRIDGE_BUILDSTATUS_2026-06-08.txt`.

## 1 — האם הגשר חי בכלל?
```bash
pgrep -fl "json_bridge|v9_streams|bridge" | grep -v grep
screen -ls | grep -i bridge
launchctl list | grep -i mems26
tail -40 /tmp/bridge.err.log
tail -20 /tmp/bridge.log 2>/dev/null
```
**שאלות:** האם תהליך-הגשר רץ? מתי ההודעה האחרונה ב-bridge.err.log? יש
`push FAILED` / exception / "API push" שנפסק?

## 2 — אם הגשר מת → להרים מחדש (CLOUD_URL=localhost בלבד!)
```bash
# אם LaunchAgent — kickstart; אחרת דרך start_all (הוא בודק listeners קודם):
launchctl kickstart -k gui/$(id -u)/com.mems26.bridge 2>/dev/null || \
  (cd /Users/michael/Downloads/mems26_web_git && bash scripts/start_all.sh)
sleep 8
tail -15 /tmp/bridge.err.log    # אמור לחזור לדחוף; אין https
```

## 3 — אם הגשר חי אבל streams=0 → זו מסכת I-20/C-6 (TZ)
ראה `docs/reports` + ה-board: `bridge_inspector._parse_ts` ממיר שגוי ts →
streams נראים stale/future → `streams_active:0`. הצלב:
```bash
curl -s localhost:8000/api/v9/build/pattern-status | python3 -c "
import sys,json; d=json.load(sys.stdin)
b=[s for s in d.get('systems',[]) if s.get('id')=='bridge']
print(json.dumps(b[0].get('global_gates',[])[:8], ensure_ascii=False, indent=1) if b else 'no bridge sys')"
```
לכל gate: ts גולמי מול now — UTC נכון או ET/IL? (זה מה שמחליט אם streams=0 הוא
גשר-מת אמיתי או מסכת-TZ).

## 4 — Frontend: האם הדאשבורד מושך?
אם ה-endpoint טרי אבל ה-UI לא זז — בעיית-polling/render בצד-לקוח, נפרד מהגשר.
דווח אם ה-UI מציג נתון ישן בזמן שה-API טרי.

## NOT-DONE
- אם הגשר מת — זה החוסם המיידי; דווח שורש (תהליך מת? crash? export stall=I-21?).
- אל תדליק STOP_ANCHORS_V2 לפני שהגשר מזין שוב (אחרת SHADOW ריק).
- פלט גולמי לכל שלב → `BRIDGE_BUILDSTATUS_2026-06-08.txt` (Cowork קורא ומצליב).
