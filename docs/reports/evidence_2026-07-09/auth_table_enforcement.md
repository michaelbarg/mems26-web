# Auth Table Enforcement Verification — 2026-07-09

## Check 1: Zero S2 "no auth cell" warnings post-restart

```
# Post-restart (line 24673+) S2 pattern warnings:
$ awk 'NR>24673 && /no auth cell/ && (/Reactive|REACTIVE|Initiative|INITIATIVE|OFA/)' /tmp/backend.err.log | wc -l
0
```

The key fix (51d531c) works: `_auth_cell()` now normalizes `"Reactive"` + `"LONG"` →
`"REACTIVE_LONG"` to match the AUTH_TABLE_V1 keys. Before the fix, every S2 lookup
missed → "using max" all day.

**Residual:** S4 patterns (ZLR, GHOST) still warn "no auth cell" (16 times post-restart) —
these are S4/Woodies patterns that are intentionally absent from the S2 auth table; their
sizing comes from the daytype playbook.

## Check 2: INITIATIVE × Neutral SKIP enforcement

**Auth table (hardcoded + YAML verified):**
```python
("INITIATIVE_LONG",  "Neutral_Extreme"): ("SKIP", 0, 0, 0)
("INITIATIVE_LONG",  "Neutral_Center"):  ("SKIP", 0, 0, 0)
("INITIATIVE_LONG",  "Normal"):          ("SKIP", 0, 0, 0)
("INITIATIVE_LONG",  "Nontrend"):        ("SKIP", 0, 0, 0)
# same for INITIATIVE_SHORT
```

**Pre-restart evidence (16:45:02 — day_type=UNKNOWN fell back to Neutral_Center → SKIP):**
```
2026-07-08 16:45:02 [INFO] [S2] T1Setup skipped: pattern=INITIATIVE_LONG day_type=UNKNOWN tier=HIGH · Auth Table SKIP
```

**Post-restart:** No INITIATIVE detection coincided with a Neutral day type (day was
Variation after restart). The SKIP mechanism verified working via the pre-restart log + code
path confirmed by reading `setup_emitter.py:82-106` and `sizing.py:75-84`.

## Code path verification

1. `setup_emitter.py:78-82` — verdict `SKIP` → short-circuits, returns None (no setup emitted)
2. `sizing.py:79-80` — verdict `SKIP` → returns None (no sizing result)
3. Both paths prevent the trade from proceeding when auth cell = SKIP.
