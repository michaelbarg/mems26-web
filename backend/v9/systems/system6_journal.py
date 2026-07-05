"""System 6 — decision journal + learning loop (Michael 2026-07-05).

"המערכת גם תזכור את זה כדי שנוכל לאורך זמן לתת למערכת לקבל את ההחלטות הנכונות
ביותר." Records each exit-signal event with its context, the recommendation, the
decision, and — filled at trade close — the OUTCOME (did exiting help?). Over
time `compute_hit_rates` turns that into a per-signal hit-rate the panel shows
and the weights can learn from.

Pure core (`build_record`, `compute_hit_rates`) is unit-tested; DB I/O is a thin,
fail-safe wrapper gated behind SYSTEM6_EXIT_JOURNAL (default OFF) — nothing is
written until Michael enables it. Advisory table only; never touches trading.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS v9_exit_decisions (
    id             BIGSERIAL PRIMARY KEY,
    trade_id       INTEGER,
    ts             TIMESTAMPTZ DEFAULT now(),
    signal_kind    VARCHAR(40),
    score          DOUBLE PRECISION,
    fired          BOOLEAN,
    recommendation VARCHAR(24),
    context_json   JSONB,
    decision       VARCHAR(24),
    decided_by     VARCHAR(24),
    outcome_json   JSONB,
    outcome_helped BOOLEAN
)
"""


def enabled() -> bool:
    return os.getenv("SYSTEM6_EXIT_JOURNAL", "0").lower() in ("1", "true", "yes")


def build_record(
    *,
    trade_id: int,
    signal_kind: str,
    score: float,
    fired: bool,
    recommendation: str,
    context: Optional[Dict] = None,
    decision: str = "pending",
    decided_by: str = "system",
) -> Dict:
    """Pure — the row to be inserted. No I/O."""
    return {
        "trade_id": int(trade_id),
        "signal_kind": str(signal_kind),
        "score": float(score),
        "fired": bool(fired),
        "recommendation": str(recommendation),
        "context_json": json.dumps(context or {}),
        "decision": str(decision),
        "decided_by": str(decided_by),
    }


def compute_hit_rates(rows: List[Dict]) -> Dict[str, Dict]:
    """Pure — per-signal stats from journal rows.

    A row 'counts' for hit-rate only once its outcome is known
    (outcome_helped is True/False). hit_rate = helped / decided.
    """
    agg: Dict[str, Dict] = {}
    for r in rows:
        k = r.get("signal_kind") or "?"
        a = agg.setdefault(k, {"n": 0, "fired": 0, "decided": 0, "helped": 0})
        a["n"] += 1
        if r.get("fired"):
            a["fired"] += 1
        helped = r.get("outcome_helped")
        if helped is not None:
            a["decided"] += 1
            if helped:
                a["helped"] += 1
    for k, a in agg.items():
        a["hit_rate"] = round(a["helped"] / a["decided"], 3) if a["decided"] else None
    return agg


# ── DB I/O (fail-safe, gated) ─────────────────────────────────────────────

def _conn():
    import psycopg2
    return psycopg2.connect(os.environ.get("DATABASE_URL", "postgresql://localhost/mems26"))


def ensure_table() -> bool:
    try:
        c = _conn(); cur = c.cursor(); cur.execute(_DDL); c.commit(); c.close()
        return True
    except Exception as e:
        logger.warning("[System6Journal] ensure_table failed: %s", e)
        return False


def record(rec: Dict) -> Optional[int]:
    """Insert one journal row (gated). Returns row id or None."""
    if not enabled():
        return None
    try:
        c = _conn(); cur = c.cursor()
        cur.execute(
            "INSERT INTO v9_exit_decisions "
            "(trade_id, signal_kind, score, fired, recommendation, context_json, decision, decided_by) "
            "VALUES (%(trade_id)s,%(signal_kind)s,%(score)s,%(fired)s,%(recommendation)s,"
            "%(context_json)s::jsonb,%(decision)s,%(decided_by)s) RETURNING id",
            rec)
        rid = cur.fetchone()[0]; c.commit(); c.close()
        return rid
    except Exception as e:
        logger.warning("[System6Journal] record failed: %s", e)
        return None


def fill_outcome(trade_id: int, *, outcome: Dict, helped: bool) -> int:
    """At trade close, stamp the outcome on this trade's pending journal rows."""
    if not enabled():
        return 0
    try:
        c = _conn(); cur = c.cursor()
        cur.execute(
            "UPDATE v9_exit_decisions SET outcome_json = %s::jsonb, outcome_helped = %s "
            "WHERE trade_id = %s AND outcome_helped IS NULL",
            (json.dumps(outcome), bool(helped), int(trade_id)))
        n = cur.rowcount; c.commit(); c.close()
        return n
    except Exception as e:
        logger.warning("[System6Journal] fill_outcome failed: %s", e)
        return 0


def get_hit_rates() -> Dict[str, Dict]:
    """Read the journal and compute per-signal hit-rates (for the panel)."""
    try:
        from backend.v9.db.read import read_all
        rows = read_all("SELECT signal_kind, fired, outcome_helped FROM v9_exit_decisions", {})
        return compute_hit_rates([dict(r) for r in rows])
    except Exception as e:
        logger.warning("[System6Journal] get_hit_rates failed: %s", e)
        return {}
