"""ReversalBarHandler — subscribes to tick_reversal_15 via BarRouter.

On each bar:
  1. Identify cluster (volume profile per bar)
  2. Identify empty zone (low-volume area for stop placement)
  3. Persist enrichment to v9_reversal_enrichment
  4. Expose via get_current() for API

Per Constitution V3 D-047 Layer 3.
"""

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Optional

from .cluster_detection import identify_cluster
from .empty_zone_detection import identify_empty_zone

logger = logging.getLogger(__name__)

DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"


class ReversalBarHandler:
    """Processes 15-tick reversal bars for cluster/empty-zone enrichment."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._last_enrichment: Optional[Dict] = None
        self._bars_processed: int = 0
        self._bars_enriched: int = 0

    def subscribe(self, bar_router) -> None:
        """Register with BarRouter for tick_reversal_15 events."""
        bar_router.subscribe("tick_reversal_15", self.process_bar)
        logger.info("[ReversalHandler] subscribed to tick_reversal_15 via BarRouter")

    async def process_bar(self, event) -> None:
        """Process a tick_reversal_15 bar: cluster + empty zone detection."""
        try:
            bar = event.payload if hasattr(event, "payload") else event
            if isinstance(bar, dict):
                bar_data = bar
            else:
                bar_data = dict(bar)

            self._bars_processed += 1

            cluster = identify_cluster(bar_data)
            empty_zone = identify_empty_zone(bar_data, cluster) if cluster else None

            bar_ts = bar_data.get("ts", "")

            if cluster:
                self._bars_enriched += 1
                enrichment = {
                    "bar_ts": str(bar_ts),
                    "bar_type": "tick_reversal_15",
                    "cluster": cluster,
                    "empty_zone": empty_zone,
                }
                self._last_enrichment = enrichment

                mode = getattr(event, "mode", "LIVE")
                if mode == "LIVE":
                    self._persist(bar_ts, cluster, empty_zone)

        except Exception as e:
            logger.error("[ReversalHandler] process_bar error: %s", e, exc_info=True)

    def _persist(self, bar_ts, cluster: dict, empty_zone: Optional[dict]) -> None:
        """Write enrichment to v9_reversal_enrichment."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """INSERT OR REPLACE INTO v9_reversal_enrichment
                (bar_ts, bar_type, cluster_top, cluster_bottom, cluster_volume,
                 empty_zone_top, empty_zone_bottom, empty_zone_volume, poc_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(bar_ts),
                    "tick_reversal_15",
                    cluster["cluster_top"],
                    cluster["cluster_bottom"],
                    cluster["cluster_volume"],
                    empty_zone["empty_zone_top"] if empty_zone else None,
                    empty_zone["empty_zone_bottom"] if empty_zone else None,
                    empty_zone["empty_zone_volume"] if empty_zone else None,
                    cluster["poc_price"],
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("[ReversalHandler] persist failed: %s", e)

    def get_current(self) -> dict:
        """Return latest enrichment + handler stats."""
        return {
            "running": True,
            "bars_processed": self._bars_processed,
            "bars_enriched": self._bars_enriched,
            "last_enrichment": self._last_enrichment,
        }
