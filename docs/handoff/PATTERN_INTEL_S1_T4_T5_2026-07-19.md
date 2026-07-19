# S1 INTEL — T4 trend paint + T5 classifier · 2026-07-19

**מבצע: cursor-agent** · מקור: `GET /api/v9/chart/replay` + `classify_replay` + `day_type/history`  
(חיבור-PG ישיר נכשל — Postgres.app trust-dialog; API דרך הבקאנד החי).

## T4 · BLUE/RED/GRAY/YELLOW (G-13)

| date | BLUE | RED | GRAY | YELLOW | n_bars |
|---|---:|---:|---:|---:|---:|
| 2026-07-15 | 63 | 54 | 48 | **0** | 165 |
| 2026-07-16 | 22 | 97 | 39 | **0** | 158 |
| 2026-07-17 | 61 | 94 | 49 | **0** | 204 |

**מסקנה G-13:** YELLOW **לא הופיע** באף בר ב-15/16/17 ב-`chart/replay.trend`.  
→ נעילת-YELLOW ב-`woodies_system.py` (~:619) כנראה **inert** על חלון זה (או שה-DLL לא מייצא YELLOW לטבלה שמגיעה ל-replay).

```
# raw
curl -sS 'http://127.0.0.1:8000/api/v9/chart/replay?date=2026-07-17' | jq '[.bars[].trend]|group_by(.)|map({(.[0]):length})'
```

## T5 · classify_replay מול history

### classify_replay finals + segments

| date | final | status | dir_bias | segments (time → type) |
|---|---|---|---|---|
| 2026-07-15 | **Normal_Variation** | CLASSIFIED | UP | 09:30 FORMING → 09:35 NV PROV → 11:10 Trend_Normal → 11:55 NV → 14:25 NV CLASSIFIED |
| 2026-07-16 | **Trend_Normal** | CLASSIFIED | DOWN | 09:30 FORMING → 09:45 NV → 10:05 Normal → 10:30 NV → 10:45 Normal → 11:05 Trend_Normal CLASSIFIED |
| 2026-07-17 | **Normal_Variation** | CLASSIFIED | DOWN | 09:30 FORMING → 09:55 Normal → 10:25 Normal CLASS → 13:15 Normal → 13:25 NV → 14:25 Trend_Normal → 14:30 NV → 15:55 NV CLASSIFIED |

### v9_day_type_history (via `/day_type/history?limit=30`)
- חלון-חי מכיל בעיקר **07-17 → 07-19** (אין שורות 07-15/07-16 בדגימה).
- דוגמה 07-18: `day_type=Normal` LOCKED_LOW_CONF (לא אותו מקור כמו classify_replay).

### מול הטענה "16/07: Normal→Neutral_Center→Neutral_Extreme"
**לא תואם.** ב-classify_replay ל-16/07: Normal_Variation / Normal → **Trend_Normal**.  
**אפס** מקטעי `Neutral_Center` / `Neutral_Extreme` בשלושת הימים.

### הערות-דוקטרינה
- 15+17: `ib_source=bars_fallback_sierra_inconsistent` + `invalidated=True` — IB לא-Sierra-נקי.
- 16: `acceptance-reclass` ל-Trend על PDL — תואם מגמת-DOWN בפלט.
