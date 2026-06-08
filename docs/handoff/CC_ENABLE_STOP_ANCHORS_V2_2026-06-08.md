# CC — הדלקת Stop-Anchor V2 ב-SHADOW (אחרי אימות-Cowork)

Cowork אימת את החיווט (63 טסטים + הצלבת-קוד) ותיקן באג offset (`0a82128`).
המשימה: אישור-סופי בסביבה האמיתית, ואז הדלקה **ב-SHADOW בלבד**. Rule 5 לכל שלב,
פלט גולמי ל-`docs/reports/STOP_ANCHORS_ENABLE_2026-06-08.txt`.

## שלב 1 — pytest מלא (עם conftest+DB, מה ש-Cowork לא יכול)
```bash
cd /Users/michael/Downloads/mems26_web_git
git log --oneline -1      # חייב 0a82128 (או צאצא)
pytest tests/ -q 2>&1 | tail -8
```
**שער:** חייב להיות ירוק לחלוטין (0 failed). אם נופל משהו — **עצור ודווח**, אל תדליק.

## שלב 2 — אישור שהדגל כרגע כבוי (baseline)
```bash
ps eww $(pgrep -f "uvicorn backend.main"|head -1) | tr ' ' '\n' | grep STOP_ANCHORS || echo "OFF (baseline)"
```

## שלב 3 — הדלקה ב-SHADOW בלבד
```bash
grep -q '^MEMS26_MODE=shadow' .env && echo "mode=shadow OK" || { echo "NOT shadow — STOP"; exit 1; }
grep -q 'STOP_ANCHORS_V2' .env || echo 'STOP_ANCHORS_V2=1' >> .env
# ודא שהערך 1:
grep STOP_ANCHORS_V2 .env
pkill -f "uvicorn backend.main:app"; sleep 3
bash scripts/start_all.sh; sleep 10
```
⚠️ רק אם `MEMS26_MODE=shadow`. **לעולם לא להדליק ב-DEMO/LIVE בלי אישור Michael.**

## שלב 4 — אימות חי שהדגל פעיל + המערכת בריאה
```bash
{
echo "== flag ON in process =="
ps eww $(pgrep -f "uvicorn backend.main"|head -1) | tr ' ' '\n' | grep STOP_ANCHORS_V2
echo "== health =="; curl -s localhost:8000/health; echo
echo "== loader picked up the YAML? (לוג) =="; tail -40 /tmp/backend.log | grep -iE "stop_anchor|STOP_ANCHORS|ConfigLoader" || echo "(no loader log lines)"
echo "== sqlite errors? =="; tail -30 /tmp/backend.log | grep -iE "sqlite|malformed|Traceback" || echo clean
} > docs/reports/STOP_ANCHORS_ENABLE_2026-06-08.txt 2>&1
cat docs/reports/STOP_ANCHORS_ENABLE_2026-06-08.txt
```

## שלב 5 — מעקב-soak (Cowork מצליב יום-יום)
מרגע ההדלקה: כל עסקת-SHADOW חדשה צריכה לשקף את ה-V2 — סטופ-מבני (לא ATR-מקוצץ),
T1 לפי הסולם, חוזים=min(סולם,auth,מצב). Cowork ישווה עסקאות חדשות מול ה-SPEC
(`MEMS26_MASTER_TRADE_SPEC_ONE_TABLE.xlsx`) ומול מה שהמנוע הישן היה עושה.

## NOT-DONE / כללים
- אל תדליק אם שלב 1 לא ירוק לחלוטין, או אם MODE≠shadow.
- שינוי-כיול = עריכת `config/stop_anchors.yaml` + restart (לא קוד).
- כיבוי-חירום: הסר/אפס `STOP_ANCHORS_V2` ב-.env + restart → חוזרים מיד להתנהגות-היום.
- אחרי הדלקה, ספר ל-Cowork ל-`STOP_ANCHORS_ENABLE_2026-06-08.txt` — הוא מאמת.
