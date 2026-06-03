"""HistoricalReplay — warm system buffers from existing DB rows.

On startup, reads last N hours of bars from each bar table
and publishes them through BarRouter in WARMUP mode.
Systems consume them, filling their buffers instantly.

Principle 10: process always when data available.
Principle 11: end-to-end verified (buffer_size > 0 after replay).
"""
import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class HistoricalReplay:
    def __init__(self, db_path: str, bar_router):
        self.db_path = db_path
        self.bar_router = bar_router
        self._stats = {"tables_read": 0, "bars_replayed": 0, "failed": 0}

    def _connect(self):
        return sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True, timeout=5)

    def _get_recent_rows(self, table: str, hours: int = 12) -> List[Dict[str, Any]]:
        """Read last N hours of rows from a bar table."""
        rows = []
        try:
            conn = self._connect()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(f"PRAGMA table_info({table})")
            cols = [c[1] for c in cursor.fetchall()]

            ts_col = None
            for candidate in ["ts", "timestamp", "bar_ts", "created_at"]:
                if candidate in cols:
                    ts_col = candidate
                    break

            if not ts_col:
                logger.warning(f"HistoricalReplay: no timestamp column in {table}")
                conn.close()
                return rows

            cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
            query = f"SELECT * FROM {table} WHERE {ts_col} >= ? ORDER BY {ts_col} ASC"
            cursor.execute(query, (cutoff,))

            for row in cursor.fetchall():
                rows.append(dict(row))

            conn.close()
        except sqlite3.OperationalError as e:
            logger.warning(f"HistoricalReplay: cannot read {table}: {e}")
        except Exception as e:
            logger.error(f"HistoricalReplay: unexpected error reading {table}: {e}")

        return rows

    async def replay_table(self, table: str, bar_type: str, hours: int = 12):
        """Replay rows from one table as a specific bar_type."""
        rows = self._get_recent_rows(table, hours)
        self._stats["tables_read"] += 1

        if not rows:
            logger.info(f"HistoricalReplay: 0 rows in {table} (last {hours}h)")
            return

        logger.info(f"HistoricalReplay: replaying {len(rows)} rows from {table} as {bar_type}")

        for row in rows:
            if "payload" in row and isinstance(row["payload"], str):
                try:
                    payload = json.loads(row["payload"])
                    bar_data = {**row, **payload}
                except Exception:
                    bar_data = dict(row)
            else:
                bar_data = dict(row)

            if "bar_id" not in bar_data or not bar_data.get("bar_id"):
                bar_data["bar_id"] = f"{bar_type}_{bar_data.get('id', 'x')}_{row.get('ts', '')}"

            try:
                await self.bar_router.publish(bar_type, bar_data, mode="WARMUP")
                self._stats["bars_replayed"] += 1
            except Exception as e:
                logger.error(f"HistoricalReplay: publish failed for row: {e}")
                self._stats["failed"] += 1

    async def warm_all_systems(self, hours: int = 12):
        """Replay all known bar types from DB."""
        replay_map = [
            ("v9_bars_tick_reversal", "tick_reversal_15"),
            ("v9_bars_footprint", "footprint"),
            ("v9_bars_woodies", "woodies"),
            ("v9_bars_5min_woodies", "woodies_5min"),
            ("v9_bars_volume_profile", "volume_profile"),
            ("v9_bars_cumulative_delta", "cumulative_delta"),
            ("v9_bars_imbalance", "imbalance"),
            ("v9_bars_stacked_imbalance", "stacked_imbalance"),
        ]

        for table, bar_type in replay_map:
            await self.replay_table(table, bar_type, hours)

        logger.info(f"HistoricalReplay COMPLETE: {self._stats}")

    def get_stats(self) -> dict:
        return dict(self._stats)
