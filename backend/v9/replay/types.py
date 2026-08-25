"""Typed contracts for the read-only MEMS26 Replay Kernel.

This package is research infrastructure. Runtime trading code must not import it.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class QualityIssue:
    code: str
    detail: str
    fatal: bool = True


@dataclass
class SessionQuality:
    session_date: dt.date
    expected_bars: int = 78
    actual_bars: int = 0
    issues: List[QualityIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def judgeable(self) -> bool:
        return not any(issue.fatal for issue in self.issues)

    @property
    def reason_codes(self) -> List[str]:
        return [issue.code for issue in self.issues]

    def add(self, code: str, detail: str, *, fatal: bool = True) -> None:
        self.issues.append(QualityIssue(code=code, detail=detail, fatal=fatal))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_date": self.session_date.isoformat(),
            "expected_bars": self.expected_bars,
            "actual_bars": self.actual_bars,
            "judgeable": self.judgeable,
            "reason_codes": self.reason_codes,
            "issues": [asdict(issue) for issue in self.issues],
            "metrics": self.metrics,
        }


@dataclass(frozen=True)
class ReplayBar:
    ts: dt.datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    delta: Optional[float] = None
    cumulative_delta: Optional[float] = None

    def identity_tuple(self) -> Tuple[Any, ...]:
        return (
            self.ts.isoformat(),
            self.open,
            self.high,
            self.low,
            self.close,
            self.volume,
            self.delta,
            self.cumulative_delta,
        )


@dataclass(frozen=True)
class TPOEvent:
    market_ts: dt.datetime
    available_at: dt.datetime
    poc: Optional[float]
    vah: Optional[float]
    val: Optional[float]
    source: str = "v9_tpo_history"


@dataclass
class ReplaySession:
    session_date: dt.date
    symbol: str
    bars: List[ReplayBar]
    tpo_events: List[TPOEvent]
    quality: SessionQuality
    source_hashes: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ReplayRequest:
    session_date: dt.date
    symbol: str = "MES"
    expected_rth_bars: int = 78
    min_cvd_coverage: float = 0.50
    seam_limit_points: float = 15.0

    def __post_init__(self) -> None:
        if not 0.0 < self.min_cvd_coverage <= 1.0:
            raise ValueError("min_cvd_coverage must be within (0, 1]")


@dataclass(frozen=True)
class ReplayManifest:
    schema_version: str
    run_id: str
    created_at: str
    git_commit: str
    dirty_tree_hash: str
    machine_tag: str
    data_source_id: str
    data_snapshot_hash: str
    date_start: str
    date_end: str
    session_dates: Tuple[str, ...]
    timezone_policy: str
    rth_window: str
    rth_end_inclusive: bool
    candidate_engine_id: str
    candidate_source: str
    policy_id: str
    execution_model_id: str
    contracts: int
    contract_split: Tuple[int, ...]
    commission_round_turn: float
    slippage_ticks_entry: int
    slippage_ticks_exit: int
    intrabar_event_order: Tuple[str, ...]
    slot_count: int
    entry_budget_policy: str
    feature_flags: Tuple[Tuple[str, str], ...]
    detector_flags_hash: str
    daytype_mode: str
    daytype_flags_set_id: str
    cvd_source: str
    cvd_alignment_rule: str
    cvd_min_coverage: float
    tpo_source: str
    same_bar_ranking: str
    entry_cutoff: str
    max_entries_per_day: Optional[int]
    mae_scratch_mode: str
    is_window: str
    oos_window: str
    lookahead_layers: Tuple[str, ...]
    random_seed: Optional[int]

    def __post_init__(self) -> None:
        required_text = {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "git_commit": self.git_commit,
            "dirty_tree_hash": self.dirty_tree_hash,
            "machine_tag": self.machine_tag,
            "data_source_id": self.data_source_id,
            "data_snapshot_hash": self.data_snapshot_hash,
            "date_start": self.date_start,
            "date_end": self.date_end,
            "timezone_policy": self.timezone_policy,
            "rth_window": self.rth_window,
            "candidate_engine_id": self.candidate_engine_id,
            "candidate_source": self.candidate_source,
            "policy_id": self.policy_id,
            "execution_model_id": self.execution_model_id,
            "timezone_policy": self.timezone_policy,
            "rth_window": self.rth_window,
            "detector_flags_hash": self.detector_flags_hash,
            "daytype_mode": self.daytype_mode,
            "daytype_flags_set_id": self.daytype_flags_set_id,
            "cvd_source": self.cvd_source,
            "cvd_alignment_rule": self.cvd_alignment_rule,
            "tpo_source": self.tpo_source,
            "intrabar_event_order": ",".join(self.intrabar_event_order),
            "same_bar_ranking": self.same_bar_ranking,
            "entry_cutoff": self.entry_cutoff,
            "entry_budget_policy": self.entry_budget_policy,
            "mae_scratch_mode": self.mae_scratch_mode,
            "is_window": self.is_window,
            "oos_window": self.oos_window,
        }
        missing = [name for name, value in required_text.items() if not value]
        if missing:
            raise ValueError(
                "Replay manifest missing required fields: " + ", ".join(missing))
        if not self.session_dates:
            raise ValueError("Replay manifest requires at least one session date")
        if self.date_start > self.date_end:
            raise ValueError("Replay manifest date_start must be <= date_end")
        allowed_candidate_sources = {
            "redetect_live", "setups", "decisions", "trades", "oracle",
            "mixed", "validation_only",
        }
        if self.candidate_source not in allowed_candidate_sources:
            raise ValueError(
                "Replay manifest candidate_source is invalid: "
                f"{self.candidate_source}")
        if self.contracts <= 0:
            raise ValueError("Replay manifest contracts must be positive")
        if any(piece < 0 for piece in self.contract_split):
            raise ValueError(
                "Replay manifest contract_split cannot contain negatives")
        if sum(self.contract_split) != self.contracts:
            raise ValueError(
                "Replay manifest contract_split must sum to contracts")
        if self.slot_count <= 0:
            raise ValueError("Replay manifest slot_count must be positive")
        if self.commission_round_turn < 0:
            raise ValueError(
                "Replay manifest commission_round_turn cannot be negative")
        if self.slippage_ticks_entry < 0 or self.slippage_ticks_exit < 0:
            raise ValueError("Replay manifest slippage cannot be negative")
        if not 0.0 < self.cvd_min_coverage <= 1.0:
            raise ValueError(
                "Replay manifest cvd_min_coverage must be within (0, 1]")


class SessionNotJudgeable(RuntimeError):
    def __init__(self, quality: SessionQuality):
        self.quality = quality
        reasons = ", ".join(quality.reason_codes) or "UNKNOWN"
        super().__init__(
            f"{quality.session_date.isoformat()} NOT_JUDGEABLE: {reasons}")
