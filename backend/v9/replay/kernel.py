"""Stage 0B Replay Kernel validation CLI (read-only, no candidates yet)."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Tuple

from .data_source import ValidatedDBSource
from .manifest import (
    canonical_json,
    flags_hash,
    git_identity,
    sha256_value,
)
from .report import build_validation_report
from .scid_validator import SCIDValidator
from .types import ReplayManifest, ReplayRequest


ROOT = Path(__file__).resolve().parents[3]


def _parse_split(value: str) -> Tuple[int, ...]:
    try:
        result = tuple(int(piece.strip()) for piece in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "contract split must be comma-separated integers") from exc
    if not result or any(piece < 0 for piece in result):
        raise argparse.ArgumentTypeError(
            "contract split must contain non-negative integers")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate one session for Replay Kernel judgeability")
    parser.add_argument("command", choices=["validate"])
    parser.add_argument("--session", required=True)
    parser.add_argument("--dsn", default="postgresql://localhost/mems26")
    parser.add_argument("--source", choices=["validated-db"],
                        default="validated-db")
    parser.add_argument("--scid-validator", required=True)
    parser.add_argument("--require-rth-bars", type=int, default=78)
    parser.add_argument("--min-cvd-coverage", type=float, default=0.50)
    parser.add_argument("--seam-limit-points", type=float, default=15.0)
    parser.add_argument("--contracts", type=int, default=4)
    parser.add_argument("--contract-split", type=_parse_split,
                        default=(1, 1, 1, 1))
    parser.add_argument("--slippage-entry", type=int, default=1)
    parser.add_argument("--slippage-exit", type=int, default=1)
    parser.add_argument("--commission-rt", type=float, default=1.50)
    parser.add_argument("--slots", type=int, default=1)
    parser.add_argument("--json")
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    session_date = dt.date.fromisoformat(args.session)
    # Stage 0B validates data only; no detector/day-type flags are effective.
    # Stage 0C must require a secret-free effective-flags snapshot.
    flags = {}
    head, dirty_hash = git_identity(ROOT)

    source = ValidatedDBSource(args.dsn)
    validator = SCIDValidator(args.scid_validator)
    request = ReplayRequest(
        session_date=session_date,
        expected_rth_bars=args.require_rth_bars,
        min_cvd_coverage=args.min_cvd_coverage,
        seam_limit_points=args.seam_limit_points,
    )
    session = source.load_session(
        request,
        scid_validator=validator,
        fail_closed=False,
    )
    data_hash = sha256_value({
        "session": args.session,
        "sources": session.source_hashes,
        "quality": session.quality.to_dict(),
    })
    manifest = ReplayManifest(
        schema_version="1",
        run_id=str(uuid.uuid4()),
        created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        git_commit=head,
        dirty_tree_hash=dirty_hash,
        machine_tag=os.getenv("MACHINE_TAG", "local"),
        data_source_id=args.source,
        data_snapshot_hash=data_hash,
        date_start=args.session,
        date_end=args.session,
        session_dates=(args.session,),
        timezone_policy="America/New_York",
        rth_window="09:30<=t<16:00",
        rth_end_inclusive=False,
        candidate_engine_id="none-stage0b",
        candidate_source="validation_only",
        policy_id="validation-only",
        execution_model_id="none-stage0b",
        contracts=args.contracts,
        contract_split=args.contract_split,
        commission_round_turn=args.commission_rt,
        slippage_ticks_entry=args.slippage_entry,
        slippage_ticks_exit=args.slippage_exit,
        intrabar_event_order=("none-stage0b",),
        slot_count=args.slots,
        entry_budget_policy="none-stage0b",
        feature_flags=tuple(sorted(flags.items())),
        detector_flags_hash=flags_hash(flags),
        daytype_mode="none-stage0b",
        daytype_flags_set_id=sha256_value(sorted(flags.items())),
        cvd_source="v9_bars_cumulative_delta",
        cvd_alignment_rule="exact-minute-collapse-identical-fail-conflict",
        cvd_min_coverage=args.min_cvd_coverage,
        tpo_source="v9_tpo_history.created_at_as_observed_availability",
        same_bar_ranking="none-stage0b",
        entry_cutoff="none-stage0b",
        max_entries_per_day=None,
        mae_scratch_mode="none-stage0b",
        is_window="none-stage0b",
        oos_window="none-stage0b",
        lookahead_layers=(),
        random_seed=None,
    )
    report = build_validation_report(manifest, session=session)
    rendered = json.dumps(
        json.loads(canonical_json(report)),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    if args.json:
        Path(args.json).write_text(rendered + "\n")
    print(rendered)
    return 0 if session.quality.judgeable else 2


if __name__ == "__main__":
    sys.exit(main())
