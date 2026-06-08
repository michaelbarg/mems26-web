# CC — הדלקת Stop-Anchor V2 ב-SHADOW (אחרי אימות-Cowork)

Cowork אימת את החיווט (63 טסטים + הצלבת-קוד) ותיקן באג offset (`0a82128`).
המשימה: אישור-סופי בסביבה האמיתית, ואז הדלקה **ב-SHADOW בלבד**. Rule 5 לכל שלב,
פלט גולמי ל-`docs/reports/STOP_ANCHORS_ENABLE_2026-06-08.txt`.

## שלב 1 — שער מתוקן: "אפס כשלים חדשים מול baseline" (לא "ירוק מלא")
החבילה המלאה מכילה ~40 כשלים **קיימים-מראש** (fixture-only, residual מתועד) שלא
קשורים ל-V2. Cowork אישר: V2 לא נגע באף אחד מאזורי-הטסטים האלה. השער הנכון =
V2 לא הוסיף **אף** כשל חדש.
```bash
cd /Users/michael/Downloads/mems26_web_git
git log --oneline -1      # חייב 0a82128 (או צאצא)
# א. טסטי-V2 — חייבים 100% ירוקים:
pytest tests/v9/regression/test_stop_anchor_resolver.py \
       tests/v9/regression/test_woodies_stop_v2.py \
       tests/v9/regression/test_adaptive_stop_v2.py \
       tests/v9/regression/test_stop_anchor_sizing.py \
       tests/v9/regression/test_stop_anchor_e2e.py \
       tests/v9/regression/test_stop_anchor_wiring_s4_cont.py \
       tests/v9/regression/test_stop_anchor_offset_exact.py -q 2>&1 | tail -4
# ב. אפס כשלים חדשים: השווה את סט-הכשלים של HEAD מול ה-baseline שלפני V2:
pytest tests/ backend/v9/tests/ -q 2>&1 | grep -E "failed|passed" | tail -1 > /tmp/head_result.txt
git stash; git checkout 00aa717~1 2>/dev/null
pytest tests/ backend/v9/tests/ -q 2>&1 | grep -E "failed|passed" | tail -1 > /tmp/base_result.txt
git checkout - 2>/dev/null; git stash pop 2>/dev/null || true
echo "BASELINE:"; cat /tmp/base_result.txt; echo "HEAD:"; cat /tmp/head_result.txt
```
**שער:** (א) טסטי-V2 = ‏100% ירוק · (ב) מספר ה-failed ב-HEAD = מספר ה-failed ב-baseline
(אפס חדשים). אם V2 הוסיף ולו כשל אחד — **עצור ודווח**. אם זהה — המשך.
(אם השוואת-ה-baseline מסובכת — לפחות ודא ש-(א) ירוק, ושאף כשל אינו בקובץ stop_anchors/woodies/five_min.)

## שלב 2 — אישור שהדגל כרגע כבוי (baseline)
```bash
ps eww $(pgrep -f "uvicorn backend.main"|head -1) | tr ' ' '\n' | grep STOP_ANCHORS || echo "OFF (baseline)"
```

## שלב 3 — הדלקה ב-SHADOW בלבד
```bash
grep -q '^MEMS26_MODE=shadow' .env && echo "mode=shadow OK" || { echo "NOT shadow — STOP"; exit 1; }
grep -q 'STOP_ANCHORS_V2' .env || echo 'STOP_ANCHORS_V2=1' >> .env
# Michael אישר 2026-06-08: הדלק גם את S4_EXTREME_TREND_RELABEL (מתייג-מחדש trend
# ל-extreme כש-|CCI|>=200 ב-GRAY/YELLOW). משנה לוגיקת-מגמה — SHADOW בלבד.
grep -q 'S4_EXTREME_TREND_RELABEL' .env || echo 'S4_EXTREME_TREND_RELABEL=true' >> .env
# ודא הערכים:
grep -E 'STOP_ANCHORS_V2|S4_EXTREME_TREND_RELABEL' .env
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
