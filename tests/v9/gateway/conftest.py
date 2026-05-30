"""Gateway test isolation — prevent tests from writing to the live DB.

Root cause (2026-05-30): TradingGateway uses raw sqlite3 with a module-level
DB_PATH that defaults to the live mems26_local.db. Gateway tests create
TradingGateway() without db_path, so route_setup() writes SHADOW trades
(entry=5900) into the live DB. This fixture patches the module-level default
so any TradingGateway() created during tests uses an in-memory DB.
"""

import sqlite3
import pytest


@pytest.fixture(autouse=True)
def _isolate_gateway_db(monkeypatch, tmp_path):
    """Redirect gateway DB writes to a temp file (not :memory: — needs
    multi-connection support for _persist_trade's separate connect calls)."""
    temp_db = str(tmp_path / "gateway_test.db")

    # Create the v9_trades table in the temp DB
    conn = sqlite3.connect(temp_db)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS v9_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mode TEXT, firing_system INTEGER, direction TEXT, state TEXT,
            entry_ts TEXT, entry_price REAL, stop REAL, t1 REAL, t2 REAL, t3 REAL,
            t1_hit_ts TEXT, t2_hit_ts TEXT, t3_hit_ts TEXT, stop_hit_ts TEXT,
            exit_ts TEXT, exit_price REAL, exit_reason TEXT,
            pnl_usd REAL, pnl_r REAL, outcome TEXT, quality TEXT,
            cross_context TEXT, sierra_bracket_id TEXT,
            created_at TEXT, updated_at TEXT, is_synthetic INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

    # Patch the module-level DB_PATH so TradingGateway() defaults to temp
    import backend.v9.gateway.trading_gateway as gw_mod
    monkeypatch.setattr(gw_mod, "DB_PATH", temp_db)
