#!/bin/bash
# read-only: count behaviour tags in the backend log since the last boot (line N)
START=${1:-207084}
LOG=/tmp/backend.err.log
tail -n +$START $LOG > /tmp/t645_since_boot.log 2>/dev/null || true
echo "lines since boot: $(wc -l < /tmp/t645_since_boot.log)"
for t in "OpeningV2\] bar" "T-638 OPENING_ENTRY" "NOT confirmed" "opening_half_range" "opening_type_mismatch" \
         "MID_VALUE_EDGE_TEST" "mid_value_edge" "WAIT_FOR_TEST" "wait_for_test" "LADDER_221" "T612" "ladder_collapse" \
         "SWING_TRAIL" "side_guard" "S1DayDir" "CEILING_FLIP_TOUCH2" "TREND_STEP" "NORMAL_DAY_RUNNER" "OPENING_DRIVE_STRICT" \
         "STRUCTURAL_ANCHOR" "T1_FRONT_RUN" "TOUCH2_EDGE_TOL" "DAYTYPE_SIDES" "BE_AFTER_T1" "BE_BEFORE_T1" "BE_PRE_T1" \
         "RISK_HALT" "daily loss" "DEMO trade TM id" "SCALE_IN" "TPO_LETTER" "S1_PROVISIONAL" "CLS_RESULT_SESSION" \
         "OPENING_LOCK_PRIOR" "DAYTYPE_MACHINE_CLOSED" "wall_ahead" "prior_value_target" "SESSION_CLOCK" "RISK_BUDGET"; do
  c=$(grep -c -- "$t" /tmp/t645_since_boot.log)
  f=$(grep -m1 -- "$t" /tmp/t645_since_boot.log | cut -c1-19)
  echo "$t | count=$c | first=$f"
done
