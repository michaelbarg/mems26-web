# S2 Five-Minute System — Archived Modules

Archived 2026-05-27 per D-090 (Path A canonical) + spec audit findings.

## confluence.py
**Reason:** `/api/v9/killzone/current` endpoint does not exist in the v9 API.
The killzone +1 bonus would always be skipped silently. First-hour matrix
endpoint (`/api/v9/open_type/current`) is also absent.
**Status:** ARCHIVED — restore if/when killzone API is implemented.

## q0_dispatcher.py
**Reason:** Fully redundant with `FiveMinMode` + `SessionClassifier` which already
handle the PRE_LOCK (09:30-10:30 ET) / POST_LOCK (10:30+) branching via
`FIRST_HOUR_TACTICAL` and `DAY_TYPE_MODE` transitions.
**Status:** ARCHIVED — logic already covered.

## first_hour_matrix.py
**Reason:** Calls `/api/v9/open_type/current` which does not exist in the v9 API.
Matrix lookups would always fall back to the conservative default (0.5, 45)
and provide no signal value.
**Status:** ARCHIVED — restore if/when open_type API is implemented.
