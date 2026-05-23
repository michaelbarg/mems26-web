"""Trade time surfaces must show Israel time next to New York time.

Regression for the request: "ליד כל עסקה גם שעת עסקה בישראל".
Every place that renders a trade timestamp on the dashboard or journal
should pull from the shared `tradeTime` helper so ET / IL stay in sync.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HELPER = ROOT / "frontend/v9/src/v9/lib/tradeTime.ts"
TRADES_TABLE = ROOT / "frontend/v9/src/v9/components/trades/TradesTable.tsx"
JOURNAL = ROOT / "frontend/v9/src/app/journal/page.tsx"
ACTIVE_CARD = ROOT / "frontend/v9/src/v9/components/sidepanel/ActiveTradeCard.tsx"
DETAILS_MODAL = ROOT / "frontend/v9/src/v9/components/trades/TradeDetailsModal.tsx"
HISTORY_STRIP = ROOT / "frontend/v9/src/v9/components/strips/TradeHistoryStrip.tsx"


def test_trade_time_helper_exports_both_timezones():
    src = HELPER.read_text(encoding="utf-8")
    assert "Asia/Jerusalem" in src, "Israel timezone constant missing"
    assert "America/New_York" in src, "New York timezone constant missing"
    for sym in ("fmtTimeET", "fmtTimeIL", "fmtTimeETIL", "tradeWhen"):
        assert f"export function {sym}" in src, f"helper {sym} not exported"


def test_trade_time_helper_handles_unix_seconds_and_iso():
    """Journal feeds unix seconds, trades feed ISO — both must work."""
    src = HELPER.read_text(encoding="utf-8")
    assert "ts < 1e12" in src, "unix-seconds vs ms heuristic missing"
    assert "typeof ts === 'number'" in src
    assert "new Date(ts)" in src, "ISO string fallback missing"


def test_trades_table_when_column_shows_il_alongside_et():
    src = TRADES_TABLE.read_text(encoding="utf-8")
    assert "tradeWhen" in src, "TradesTable must import tradeWhen helper"
    assert "etTime" in src and "ilTime" in src, "Both ET and IL rendered"
    assert " IL" in src, "IL label visible in the When cell"


def test_journal_time_column_uses_dual_tz_helper():
    src = JOURNAL.read_text(encoding="utf-8")
    assert "from '@/v9/lib/tradeTime'" in src
    assert "Time (ET/IL)" in src, "Time column header must signal dual tz"
    assert "tradeWhen" in src, "Journal Time cell must use tradeWhen helper"
    assert "fmtHitTimeBoth" in src, "Planned-targets hit times must use dual tz"
    assert "tsToTimeBoth" in src, "Trade legs must use dual tz time"


def test_active_trade_card_shows_il_after_et():
    src = ACTIVE_CARD.read_text(encoding="utf-8")
    assert "fmtTimeET" in src and "fmtTimeIL" in src
    assert "entryTimeIl" in src, "ActiveTradeCard must compute IL time"
    assert " IL" in src, "IL label visible on entry-time chip"


def test_trade_details_modal_management_log_uses_dual_tz():
    src = DETAILS_MODAL.read_text(encoding="utf-8")
    assert "fmtTimeETIL" in src, "Management log must use dual-tz helper"


def test_trade_history_strip_tooltip_uses_dual_tz():
    src = HISTORY_STRIP.read_text(encoding="utf-8")
    assert "fmtTimeETIL" in src, "Strip tooltip must use dual-tz helper"
    # Old slice-based UTC tooltip must be gone — it confused IL traders
    assert "entry_ts.slice(11, 16)" not in src
