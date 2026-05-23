# CC UAT — S2 5-Min Fires + AMT Rolling (P31-STRAT-S3 #2+#3 Verification)

**מתי:** להריץ ב-RTH (09:30–16:00 ET = 16:30–23:00 IL) עם Sierra+Bridge פעילים.
**מה בדקנו:** 2 תיקונים שנשלחו ב-commit `dcae75d` (2026-05-22):
1. **COT reset יומי** — `footprint_system.py::hydrate()` — session-aware
2. **AMT 90-min rolling** — `footprint_system.py::_update_flow()` — 18-bar window

---

## UAT 1 — AMT populated after RTH open

```bash
# לאחר 09:30 ET (RTH open), ממתין 10 דק' לvol:
curl -s http://127.0.0.1:8000/api/v9/footprint/current | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('cot :', d.get('cot'))
print('amt :', d.get('amt'))
print('bars:', d.get('bars_processed_today'))
"
```

**קריטריוני הצלחה:**
- `amt > 0` — הולידציה שהwindow מתמלא
- `amt` בטווח 50–500 (בMES RTH בדרך כלל)
- `cot` בין −5,000 ל-+5,000 בשעה הראשונה (יומי, לא היסטורי)
- `amt != cot` — הם שדות שונים

**קריטריון כישלון:** `amt == 0.0` אחרי 10 דק' RTH → הwindow לא מתמלא, יש בעיה ב-`_classify_forces_in_bar`.

---

## UAT 2 — S2 5-Min fires at least once in RTH session

```bash
# לאחר RTH:
grep "FiveMin.*FIRE" /tmp/backend.log | tail -5
# ואם לא:
grep "FiveMin.*detect" /tmp/backend.log | tail -5
sqlite3 /Users/michael/Downloads/mems26_web_git/data/mems26_local.db \
  "SELECT id, direction, state, entry_price FROM v9_trades WHERE firing_system=2 ORDER BY id DESC LIMIT 5;"
```

**קריטריוני הצלחה (RTH בלבד):**
- לפחות 1 שורה עם `firing_system=2` ב-`v9_trades` מהיום
- הלוג מציג `[FiveMin] FIRE: REACTIVE/INITIATIVE`
- `entry_price` הגיוני (בקרבת מחיר MES ב-RTH)

**קריטריון כישלון:** 0 trades מ-S2 אחרי 3 שעות RTH → 4-bar pattern לא נוצר, או pre_fire_validator חוסם. לדווח ב-CC prompt נפרד.

---

## UAT 3 — COT יומי (לא מצטבר)

```bash
# בסוף RTH (16:00 ET):
curl -s http://127.0.0.1:8000/api/v9/footprint/current | python3 -c "
import sys, json
d = json.load(sys.stdin)
cot = d.get('cot', 0)
print('cot:', cot)
if abs(cot) > 50000:
    print('WARNING: COT > 50K, might be accumulating across sessions')
elif abs(cot) < 20000:
    print('OK: COT looks like intraday only')
"
```

**קריטריון הצלחה:** `|cot| < 50,000` בסוף RTH (לא −144K כמו לפני).

---

## אם S2 לא יורה — 4 שלבי debug

```bash
# 1. בדוק AMT/COT:
curl -s http://127.0.0.1:8000/api/v9/footprint/current | python3 -m json.tool | grep -E "(cot|amt|bars)"

# 2. בדוק מה S2 אומר:
curl -s http://127.0.0.1:8000/api/v9/five_min/current | python3 -m json.tool
# חפש: mode, buffer_size, last_pattern, last_reasoning_notes

# 3. ברים חיים?
sqlite3 data/mems26_local.db "SELECT COUNT(*), MAX(ts) FROM v9_bars_5min WHERE date(ts)='$(date -u +%Y-%m-%d)';"

# 4. לוג S2:
grep -E "\[FiveMin\]" /tmp/backend.log | tail -20
```

**אבחנות אפשריות:**
- **mode=OVERNIGHT_MODE** → שוק לא RTH. S2 לא פועל בOvernightMode. נורמלי.
- **buffer_size < 4** → מעט ברים. צריך 4 ברים מינימום לpattern detection.
- **cot > 0 AND amt > 0 AND cot < amt** → תנאי LONG (`cot > amt`) לא מתקיים → S2 לא יורה LONG. תנאי SHORT (`cot < amt`) מתקיים → תלוי בpattern.
- **last_pattern = null** → הdetectors לא מוצאים 4-bar pattern → נרמל, דורש volume signature מסוים.

---

## דוח חזרה

כתוב `docs/reports/PROMPT_P31_S3_S2_UAT_RESULT.md` עם:
1. ערכי AMT/COT ב-3 נקודות זמן (RTH open, mid-RTH, RTH close)
2. האם S2 ירה (כמה trades, איזה direction, איזה pattern)
3. האם COT נשאר < 50K לאורך כל היום
4. 4 צירי UAT (Quality/Recency/Cardinality/Latency)
5. אם S2 לא ירה — לאיזה שלב הגיע ולמה נעצר

---

## הקשר

- Commits: `dcae75d` (footprint fix), `2bc6796` (types.ts)
- Bug שנותר פתוח: אין (Bug #1 = לא באג per D-082/D-086)
- Pre-LIVE blocker שנותר: S6 Killzone direction-aware (RCA-1 ב-`docs/reports/PROMPT_P31_CONFLUENCE_FILTER_RCA.md`)
