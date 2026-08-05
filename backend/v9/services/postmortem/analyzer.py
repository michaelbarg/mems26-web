"""POST_MORTEM_V1 — automatic loss diagnosis on trade close.

Pure observability: writes a markdown report + DB summary row for every
losing trade (live or shadow). Does NOT change trading behavior.
Must never raise or block the trade-close path — all errors are caught
and logged.

Root verdicts (closed taxonomy):
  WRONG_CLASS   — day-type at entry differs from EOD truth
  LATE_ENTRY    — entry in top/bottom 15% of day range (chasing)
  TIGHT_STOP    — stop < 6pt on a trend day (Dalton floor violation)
  MANAGEMENT    — T1 hit but stopped at BE (management cost)
  NORMAL_NOISE  — none of the above; acceptable loss
"""

from __future__ import annotations

import logging
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# The postmortem report directory (relative to repo root)
_REPORT_DIR = "docs/reports/postmortem"


def on_trade_closed(trade_id: int, db: Session) -> None:
    """Called after a trade is closed with outcome=LOSS.

    Catches all exceptions — must never block the trading loop.
    """
    try:
        _run_postmortem(trade_id, db)
    except Exception:
        logger.warning(
            "POST_MORTEM_V1: failed for trade %s: %s",
            trade_id, traceback.format_exc(),
        )


def _run_postmortem(trade_id: int, db: Session) -> None:
    from backend.v9.db.models.trades import V9Trade
    from backend.v9.db.models.postmortem import V9Postmortem

    trade = db.query(V9Trade).filter(V9Trade.id == trade_id).first()
    if trade is None:
        logger.warning("POST_MORTEM_V1: trade %s not found", trade_id)
        return
    if trade.outcome != "LOSS":
        return  # only analyze losses

    # ── 1. Gather context ──
    entry_ctx = _extract_entry_context(trade)
    excursion = _compute_excursion(trade, db)
    s7 = _compute_s7(trade, entry_ctx)
    eod_day_type = _get_eod_day_type(trade)
    range_pos = _compute_range_position(trade)

    # ── 2. Determine root verdict ──
    verdict, detail = _classify_root_cause(
        trade, entry_ctx, eod_day_type, excursion, range_pos,
    )

    # ── 3. Write DB row ──
    pm = V9Postmortem(
        trade_id=trade.id,
        mode=trade.mode,
        firing_system=trade.firing_system,
        day_type_at_entry=entry_ctx.get("day_type"),
        day_type_eod=eod_day_type,
        day_type_mismatch=1 if (
            entry_ctx.get("day_type") and eod_day_type
            and entry_ctx["day_type"] != eod_day_type
        ) else 0,
        pattern_id=entry_ctx.get("pattern_id"),
        session_at_entry=entry_ctx.get("session"),
        direction=trade.direction,
        entry_price=trade.entry_price,
        exit_price=trade.exit_price,
        stop=trade.stop,
        exit_reason=trade.exit_reason,
        pnl_usd=trade.pnl_usd,
        pnl_r=trade.pnl_r,
        mae_pts=excursion.get("mae_pts"),
        mfe_pts=excursion.get("mfe_pts"),
        range_position=range_pos,
        s7_score=s7.get("score") if s7 else None,
        s7_sizing=s7.get("sizing") if s7 else None,
        s7_components=s7.get("components") if s7 else None,
        gates_passed=entry_ctx.get("gates"),
        exit_mechanism=trade.exit_reason,
        root_verdict=verdict,
        root_detail=detail,
    )

    # Upsert: if a postmortem already exists for this trade, update it
    existing = db.query(V9Postmortem).filter(
        V9Postmortem.trade_id == trade.id
    ).first()
    if existing:
        for col in (
            "mode", "firing_system", "day_type_at_entry", "day_type_eod",
            "day_type_mismatch", "pattern_id", "session_at_entry", "direction",
            "entry_price", "exit_price", "stop", "exit_reason", "pnl_usd",
            "pnl_r", "mae_pts", "mfe_pts", "range_position", "s7_score",
            "s7_sizing", "s7_components", "gates_passed", "exit_mechanism",
            "root_verdict", "root_detail",
        ):
            setattr(existing, col, getattr(pm, col))
        pm = existing
    else:
        db.add(pm)

    # ── 4. Write report file ──
    report_path = _write_report(trade, pm, entry_ctx, excursion, s7)
    pm.report_path = report_path

    db.flush()
    logger.info(
        "POST_MORTEM_V1: trade #%s → %s (%s)",
        trade_id, verdict, report_path or "no-file",
    )


# ── helpers ──

def _extract_entry_context(trade) -> Dict[str, Any]:
    """Pull day_type, pattern, session, gates from trade fields + cross_context."""
    ctx: Dict[str, Any] = {}
    # Promoted fields first
    ctx["day_type"] = getattr(trade, "day_type_at_entry", None)
    ctx["pattern_id"] = getattr(trade, "pattern_id_at_entry", None)
    ctx["session"] = getattr(trade, "session_at_entry", None)

    # Fall back to cross_context JSON
    cc = trade.cross_context
    if isinstance(cc, list) and cc:
        cc = cc[0]  # first snapshot
    if isinstance(cc, dict):
        if not ctx["day_type"]:
            systems = cc.get("systems", {})
            dt = systems.get("day_type", {})
            ctx["day_type"] = dt.get("day_type") if isinstance(dt, dict) else None
        ctx["gates"] = cc.get("gates")
    return ctx


def _compute_excursion(trade, db: Session) -> Dict[str, Any]:
    """MAE/MFE from bars during trade."""
    try:
        from backend.v9.services.trade_excursion import compute_trade_excursion
        return compute_trade_excursion(trade, db=db)
    except Exception:
        return {"mae_pts": None, "mfe_pts": None}


def _compute_s7(trade, entry_ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """S7 score at trade time (computed even when flag is OFF)."""
    try:
        from backend.v9.systems.system7_score import score as s7_score
        setup = {
            "direction": trade.direction,
            "pattern": entry_ctx.get("pattern_id", ""),
            "entry_price": trade.entry_price,
        }
        return s7_score(setup=setup, bar_ts=trade.entry_ts)
    except Exception:
        return None


def _get_eod_day_type(trade) -> Optional[str]:
    """EOD ground-truth day type from the DB history table."""
    try:
        from backend.v9.db.read import read_one
        if trade.entry_ts is None:
            return None
        date_str = trade.entry_ts.strftime("%Y-%m-%d")
        row = read_one(
            "SELECT day_type FROM v9_day_type_state "
            "WHERE ts::date = :d ORDER BY ts DESC LIMIT 1",
            {"d": date_str},
        )
        if row:
            return row.get("day_type")
        # Fallback to history table
        row = read_one(
            "SELECT day_type FROM v9_day_type_history "
            "WHERE date = :d",
            {"d": date_str},
        )
        return row.get("day_type") if row else None
    except Exception:
        return None


def _compute_range_position(trade) -> Optional[float]:
    """Entry position in the day's range (0.0=low, 1.0=high)."""
    try:
        from backend.v9.db.read import read_one
        if trade.entry_ts is None or trade.entry_price is None:
            return None
        date_str = trade.entry_ts.strftime("%Y-%m-%d")
        row = read_one(
            "SELECT MAX(high) as hi, MIN(low) as lo "
            "FROM v9_bars_5min_woodies "
            "WHERE (ts AT TIME ZONE 'America/New_York')::date = :d",
            {"d": date_str},
        )
        if not row or row["hi"] is None or row["lo"] is None:
            return None
        hi, lo = float(row["hi"]), float(row["lo"])
        rng = hi - lo
        if rng < 1.0:
            return None
        return round((float(trade.entry_price) - lo) / rng, 3)
    except Exception:
        return None


def _classify_root_cause(
    trade, entry_ctx, eod_day_type, excursion, range_pos,
) -> tuple:
    """Closed taxonomy: WRONG_CLASS / LATE_ENTRY / TIGHT_STOP / MANAGEMENT / NORMAL_NOISE."""

    dt_entry = entry_ctx.get("day_type") or ""
    dt_eod = eod_day_type or ""

    # 1. Wrong classification
    if dt_entry and dt_eod and dt_entry != dt_eod:
        # Significant mismatch (not just confidence change)
        entry_family = dt_entry.split("_")[0] if "_" in dt_entry else dt_entry
        eod_family = dt_eod.split("_")[0] if "_" in dt_eod else dt_eod
        if entry_family != eod_family:
            return "WRONG_CLASS", f"Entry: {dt_entry}, EOD: {dt_eod}"

    # 2. Late entry (chasing — entry in extreme 15% of range)
    if range_pos is not None:
        is_long = trade.direction == "LONG"
        if (is_long and range_pos > 0.85) or (not is_long and range_pos < 0.15):
            return "LATE_ENTRY", f"Range position: {range_pos:.1%}"

    # 3. Tight stop on trend day
    if dt_eod.startswith("Trend") or dt_entry.startswith("Trend"):
        if trade.entry_price is not None and trade.stop is not None:
            stop_width = abs(trade.entry_price - trade.stop)
            if stop_width < 6.0:
                return "TIGHT_STOP", f"Stop width {stop_width:.1f}pt on trend day (Dalton floor 6pt)"

    # 4. Management issue (hit T1 then stopped at BE)
    if trade.t1_hit_ts is not None and trade.exit_reason == "STOP_HIT":
        return "MANAGEMENT", "T1 hit then stopped at BE"

    # 5. Normal noise
    return "NORMAL_NOISE", "Acceptable loss — no structural issue detected"


def _write_report(trade, pm, entry_ctx, excursion, s7) -> Optional[str]:
    """Write markdown post-mortem to docs/reports/postmortem/."""
    try:
        repo_root = Path(__file__).resolve().parents[4]
        report_dir = repo_root / _REPORT_DIR
        report_dir.mkdir(parents=True, exist_ok=True)

        filename = f"PM_{trade.id}.md"
        filepath = report_dir / filename

        lines = [
            f"# Post-Mortem: Trade #{trade.id}",
            "",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| Mode | {trade.mode} |",
            f"| Direction | {trade.direction} |",
            f"| System | S{trade.firing_system} |",
            f"| Entry | {trade.entry_price} @ {trade.entry_ts} |",
            f"| Exit | {trade.exit_price} @ {trade.exit_ts} |",
            f"| Stop | {trade.stop} |",
            f"| PnL | ${trade.pnl_usd} ({trade.pnl_r}R) |",
            f"| Exit Reason | {trade.exit_reason} |",
            "",
            "## Day Type",
            f"- At entry: **{pm.day_type_at_entry or 'UNKNOWN'}**",
            f"- EOD truth: **{pm.day_type_eod or 'UNKNOWN'}**",
            f"- Mismatch: {'YES' if pm.day_type_mismatch else 'NO'}",
            "",
            "## Excursion",
            f"- MAE: {excursion.get('mae_pts', '?')} pts",
            f"- MFE: {excursion.get('mfe_pts', '?')} pts",
            f"- Range position: {pm.range_position or '?'}",
            "",
            "## S7 Score" + (" (computed, flag OFF)" if not os.getenv("SYSTEM7_SCORE_V1") else ""),
            f"- Score: {pm.s7_score or '?'}/100",
            f"- Sizing: {pm.s7_sizing or '?'}",
        ]
        if s7 and s7.get("components"):
            for k, v in s7["components"].items():
                lines.append(f"  - {k}: {v}")

        lines.extend([
            "",
            "## Root Verdict",
            f"**{pm.root_verdict}**: {pm.root_detail}",
            "",
            f"---",
            f"*Generated: {datetime.now(timezone.utc).isoformat()} | POST_MORTEM_V1*",
        ])

        filepath.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return f"{_REPORT_DIR}/{filename}"
    except Exception:
        logger.warning("POST_MORTEM_V1: report write failed: %s", traceback.format_exc())
        return None
