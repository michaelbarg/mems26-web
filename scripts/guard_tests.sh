#!/usr/bin/env bash
# guard_tests.sh — run the regression guards that protect live trading behaviour.
#
# Michael 2026-09-01: "מה חסר, מה בוצע כמו שצריך."
#
# The gap this closes. On 01.09 seven fixes landed and every one of them carried
# tests — and NOTHING RAN THEM. `fire_drill.py` (the pre-session gate) never
# invokes pytest at all; the only pytest calls in scripts/ are old UAT shells
# pointing at `tests/`. Meanwhile half of today's guards live under
# `backend/v9/tests/`, a second test root with no `testpaths` entry anywhere.
# A guard nobody runs is not a guard — it is a comment that takes an afternoon
# to write. `test_entry_stop_immutable` is the sharpest example: its whole job
# is to fail the moment a second write site appears, and it had never executed.
#
# Deliberately NARROW. The full suite carries ~490 pre-existing failures, so
# gating a trading session on `pytest` wholesale would block the open for
# reasons unrelated to today's risk. This runs the named guards only — the ones
# whose failure means a live behaviour changed underneath us.
#
#   ./scripts/guard_tests.sh          # exit 0 = every guard green
#
# Adding a guard: put its path in GUARDS below, in the same commit as the fix.
set -uo pipefail
cd "$(dirname "$0")/.."

# .env first — conftest imports the app, which requires BRIDGE_TOKEN, and a
# script that quietly falls back to defaults reports a fiction (T-161).
set -a; . ./.env 2>/dev/null; set +a
[ -n "${BRIDGE_TOKEN:-}" ] || { echo "🔴 .env did not load — refusing to report green"; exit 2; }

GUARDS=(
  # ── sizing: how many contracts leave the building ──
  tests/v9/regression/test_risk_budget_sizing.py      # budget curve + reject gate
  backend/v9/tests/test_risk_budget_sizing.py         # cc's angle on the same flag
  # ── measurement integrity: columns that must not be rewritten ──
  backend/v9/tests/test_entry_stop_immutable.py       # single write site
  backend/v9/tests/test_va_sanity.py                  # impossible value areas
  # ── entry quality ──
  backend/v9/tests/test_entry_location_quality.py     # chaser / expensive / beyond-value
  # ── the slot: a stuck slot blocks every fire, silently ──
  tests/v9/regression/test_phantom_slot_release.py
  tests/v9/regression/test_stuck_live_slot_alarm.py
  # ── patterns ──
  tests/v9/regression/test_ceiling_floor_state.py
)

present=(); missing=()
for g in "${GUARDS[@]}"; do
  [ -f "$g" ] && present+=("$g") || missing+=("$g")
done

# A guard file that vanished is a failure, not a smaller test run — that is
# exactly how a deleted guard would slip past unnoticed.
if [ ${#missing[@]} -gt 0 ]; then
  printf '🔴 guard file missing: %s\n' "${missing[@]}"
  exit 1
fi

# Map hygiene — ADVISORY, deliberately not part of rc.
# The source-of-truth maps drifting is a documentation defect, not a change in
# live behaviour, and this script is what decides whether we arm. Gating a
# trading session on a stale document is the same mistake as gating it on the
# full suite: the open gets blocked for a reason unrelated to today's risk.
# It prints, loudly, and `sot_map_guard.py --strict` is the strict form for the
# nightly and for anyone about to trust a map.
python3 scripts/sot_map_guard.py || true

echo "── running ${#present[@]} guard files ──"
python3 -m pytest "${present[@]}" -q --tb=short
rc=$?

if [ $rc -eq 0 ]; then
  echo "✅ GUARDS GREEN — sizing, entry_stop, VA sanity, entry location, slot, patterns"
else
  echo "🔴 GUARDS RED (rc=$rc) — a live behaviour changed. Do not arm on this."
fi
exit $rc
