"""Regression: hydrate_demo_slot SQL uses correct column names.

07-02 bug: query used `system_id` which doesn't exist in v9_trades
(correct column = `firing_system`). Every restart silently failed
→ demo_slot always None → GAP-5 warm-start inert.

Anti-tautological: validates the SQL column names against the real
v9_trades model. FAILS on `system_id`, PASSES on `firing_system`.
if reverted → RED because the model doesn't have system_id.

Contract: docs/handoff/CC_HANDOFF_CONTRACT.md
"""
import inspect
import re

from backend.v9.gateway.trading_gateway import TradingGateway


def test_hydrate_sql_columns_match_model():
    """Every column in the hydrate_demo_slot SELECT must exist in v9_trades.

    if reverted → RED because 'system_id' is not in the model's columns.
    """
    from backend.v9.db.models.trades import V9Trade
    model_columns = {c.name for c in V9Trade.__table__.columns}

    # Extract column names from the SQL string in hydrate_demo_slot source
    src = inspect.getsource(TradingGateway.hydrate_demo_slot)
    # The SQL is split across string literals; join and find SELECT...FROM
    # Collapse the source to a single line for regex
    flat = " ".join(src.split()).replace('" "', ' ')
    match = re.search(r'SELECT\s+(.+?)\s+FROM\s+v9_trades', flat, re.IGNORECASE)
    assert match, f"Could not find SELECT...FROM v9_trades in hydrate_demo_slot"

    select_clause = match.group(1).replace('"', '').replace("'", '')
    sql_columns = {col.strip() for col in select_clause.split(",")}

    for col in sql_columns:
        assert col in model_columns, (
            f"Column '{col}' in hydrate_demo_slot SQL does not exist in v9_trades model. "
            f"Available columns: {sorted(model_columns)}"
        )


def test_hydrate_sql_does_not_use_system_id():
    """The old broken column name 'system_id' must NOT appear in the SQL.

    if reverted → RED because the fix replaces system_id with firing_system.
    """
    src = inspect.getsource(TradingGateway.hydrate_demo_slot)
    assert "system_id" not in src, (
        "hydrate_demo_slot still uses 'system_id' — must be 'firing_system'"
    )


def test_hydrate_logs_failure_explicitly():
    """A query error must log '[Gateway] demo_slot hydration FAILED' (not silent).

    if reverted → RED because the old code logged a generic warning.
    """
    src = inspect.getsource(TradingGateway.hydrate_demo_slot)
    assert "hydration FAILED" in src, (
        "hydrate_demo_slot must log 'FAILED' on query error (not silent None)"
    )
