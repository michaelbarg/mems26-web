"""Tests for HistoricalReplay."""
import asyncio
import sqlite3
from backend.v9.services.historical_replay import HistoricalReplay


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class FakeBarRouter:
    def __init__(self):
        self.published = []
    async def publish(self, bar_type, bar_data, mode="LIVE"):
        self.published.append({"type": bar_type, "mode": mode, "data": bar_data})


class TestHistoricalReplay:
    def test_missing_table_no_crash(self, tmp_path):
        db = str(tmp_path / "test.db")
        sqlite3.connect(db).close()  # create empty DB
        router = FakeBarRouter()
        replay = HistoricalReplay(db_path=db, bar_router=router)
        _run(replay.warm_all_systems(hours=12))
        assert router.published == []

    def test_replay_publishes_warmup_mode(self, tmp_path):
        db = str(tmp_path / "test.db")
        conn = sqlite3.connect(db)
        conn.execute("""CREATE TABLE v9_bars_tick_reversal (
            id INTEGER PRIMARY KEY, ts TEXT, bar_id TEXT, payload TEXT, created_at TEXT
        )""")
        conn.execute("""INSERT INTO v9_bars_tick_reversal (ts, bar_id, payload, created_at)
            VALUES ('2026-05-12T08:00:00', 'tr_1', '{"close":7400}', '2026-05-12T08:00:00')""")
        conn.commit()
        conn.close()

        router = FakeBarRouter()
        replay = HistoricalReplay(db_path=db, bar_router=router)
        _run(replay.replay_table("v9_bars_tick_reversal", "tick_reversal_15", hours=24*365))

        assert len(router.published) >= 1
        assert router.published[0]["mode"] == "WARMUP"
        assert router.published[0]["type"] == "tick_reversal_15"

    def test_stats_tracking(self):
        router = FakeBarRouter()
        replay = HistoricalReplay(db_path="/nonexistent.db", bar_router=router)
        stats = replay.get_stats()
        assert "tables_read" in stats
        assert "bars_replayed" in stats

    def test_replay_multiple_rows(self, tmp_path):
        db = str(tmp_path / "test.db")
        conn = sqlite3.connect(db)
        conn.execute("""CREATE TABLE v9_bars_footprint (
            id INTEGER PRIMARY KEY, ts TEXT, bar_id TEXT, created_at TEXT
        )""")
        for i in range(5):
            conn.execute(f"""INSERT INTO v9_bars_footprint (ts, bar_id, created_at)
                VALUES ('2026-05-12T0{i}:00:00', 'fp_{i}', '2026-05-12T0{i}:00:00')""")
        conn.commit()
        conn.close()

        router = FakeBarRouter()
        replay = HistoricalReplay(db_path=db, bar_router=router)
        _run(replay.replay_table("v9_bars_footprint", "footprint", hours=24*365))

        assert len(router.published) == 5
        assert replay.get_stats()["bars_replayed"] == 5
