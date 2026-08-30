-- T-153: unified shadow ledger view across all three shadow tables.
-- A VIEW, not a fourth table (the work order explicitly forbids a fourth table).
-- Used by scripts/shadow_promotion_board.py for the pre-Monday shadow audit.
--
-- Each source contributes: ts, source_table, flag, trade_id, pattern, direction,
-- price, decision (would_apply/blocked), pnl_sim (score when available).
-- Missing fields → NULL (Rule 1: honest missing, not synthetic).

CREATE OR REPLACE VIEW v9_shadow_ledger AS

SELECT
    ts,
    'S7' AS source,
    'SYSTEM7_SCORE' AS flag,
    trade_id,
    pattern,
    direction,
    entry_price AS price,
    CASE WHEN blocked THEN 'BLOCKED' ELSE 'PASSED' END AS decision,
    score AS pnl_sim,
    outcome
FROM v9_s7_shadow_log

UNION ALL

SELECT
    ts,
    'TSF' AS source,
    'TREND_STEP_ENTRY_V1' AS flag,
    trade_id,
    day_type AS pattern,
    direction,
    NULL AS price,
    CASE WHEN would_apply THEN 'WOULD_APPLY' ELSE 'NO_CHANGE' END AS decision,
    delta_pts AS pnl_sim,
    NULL AS outcome
FROM v9_tsf_shadow_log

UNION ALL

SELECT
    ts,
    'DAYTYPE' AS source,
    'DAY_TYPE_TRANSITIONS' AS flag,
    NULL AS trade_id,
    from_type || ' -> ' || to_type AS pattern,
    NULL AS direction,
    price,
    trigger AS decision,
    NULL AS pnl_sim,
    NULL AS outcome
FROM v9_day_type_shadow_transitions

ORDER BY ts DESC;
