# Woodies Touch-Point Endpoints Status

Date: 2026-05-16
Audit: PROMPT 1 · 1.4

## Summary: 5/7 ready · 0 partial · 2 missing

| TP# | Stage | Endpoint | HTTP | Owner | Status | Notes |
|---|---|---|---|---|---|---|
| 1 | A2 | `/api/v9/day_type/current` | 200 | S1 | 🟢 READY | Returns day_type, confidence, ib_h, ib_l, classified |
| 2a | A4 | `/api/v9/tpo/current` | 200 | S5 | 🟢 READY | POC, VAH, VAL, ufl_ufh all present |
| 2b | A4 | `/api/v9/suffering_side/check` | 404 | TBD | 🔴 MISSING | Exact spec endpoint doesn't exist |
| 2b alt | A4 | `/api/v9/veto/state` | 200 | Gateway | 🟢 READY | suffering_side field + veto_active + reasoning_notes |
| 3 | A5 | `/api/v9/otf_clarity/state` | 404 | TBD | 🔴 MISSING | No OTF clarity endpoint exists |
| 4 | B4 | `/api/v9/tpo/current` (poc_migration) | 200 | S5 | 🟢 READY | direction, magnitude_pts, stuck_minutes |
| 5 | B5 | same as TP#3 | 404 | TBD | 🔴 MISSING | Same as TP#3 |
| 6 | B9 | `/api/v9/layer0/state` | 200 | Layer0 | 🟢 READY | chop_score, state (EXPANDING), 6 indicators |

## Sample Responses

**TP#1** `/day_type/current`:
```json
{"day_type":"Normal","confidence":70,"ib_h":7472.5,"ib_l":7172.5,"ib_range":300.0,"classified":true}
```

**TP#2a** `/tpo/current` (relevant fields):
```
poc=7462.0, ufl_ufh={ufl: 7172.5, ufh: 7473.5}
```

**TP#2b alt** `/veto/state`:
```json
{"suffering_side":null,"veto_active":false,"reasoning_notes":"D-049 SSV: suffering_side=NONE"}
```

**TP#4** `/tpo/current` poc_migration:
```
direction=STUCK, magnitude_pts=0.0, stuck_minutes=15
```

**TP#6** `/layer0/state`:
```json
{"chop_score":36.0,"state":"EXPANDING","indicators":{...}}
```

## Missing Endpoints

1. **`/api/v9/suffering_side/check`** — spec exact path. Alternative `/veto/state` exists and provides suffering_side. Recommend: Woodies reads `/veto/state` instead.

2. **`/api/v9/otf_clarity/state`** — no OTF clarity endpoint exists anywhere. OTF data partially in TPO system (tpo/detector.py has OTF Clarity logic per E3 stage). Recommend: build `/otf_clarity/state` endpoint in future wave, or read from `/tpo/current` if OTF fields added.
