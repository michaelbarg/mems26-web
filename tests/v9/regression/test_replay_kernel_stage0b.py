"""Stage 0B anti-tautological tests for the read-only Replay Kernel."""
from __future__ import annotations

import datetime as dt
import os
from dataclasses import replace
from pathlib import Path

import pytest

from backend.v9.replay.data_source import ValidatedDBSource
from backend.v9.replay.kernel import _parser
from backend.v9.replay.manifest import (
    canonical_result_hash,
    git_identity,
    manifest_hash,
)
from backend.v9.replay.scid_validator import SCIDValidator
from backend.v9.replay.types import ReplayManifest, ReplayRequest


ROOT = Path(__file__).resolve().parents[3]
SCID = Path.home() / "SierraChart" / "Data" / "MESU26_FUT_CME.scid"
DSN = os.getenv("DATABASE_URL", "postgresql://localhost/mems26")


def _manifest(**changes):
    values = dict(
        schema_version="1",
        run_id="run-1",
        created_at="2026-08-24T00:00:00+00:00",
        git_commit="a" * 40,
        dirty_tree_hash="b" * 64,
        machine_tag="test",
        data_source_id="validated-db",
        data_snapshot_hash="c" * 64,
        date_start="2026-08-18",
        date_end="2026-08-18",
        session_dates=("2026-08-18",),
        timezone_policy="America/New_York",
        rth_window="09:30<=t<16:00",
        rth_end_inclusive=False,
        candidate_engine_id="none-stage0b",
        candidate_source="validation_only",
        policy_id="validation-only",
        execution_model_id="none-stage0b",
        contracts=4,
        contract_split=(1, 1, 1, 1),
        commission_round_turn=1.5,
        slippage_ticks_entry=1,
        slippage_ticks_exit=1,
        intrabar_event_order=("none-stage0b",),
        slot_count=1,
        entry_budget_policy="none-stage0b",
        feature_flags=(("S1_TEST", "1"),),
        detector_flags_hash="d" * 64,
        daytype_mode="none-stage0b",
        daytype_flags_set_id="e" * 64,
        cvd_source="v9_bars_cumulative_delta",
        cvd_alignment_rule="fail-conflict",
        cvd_min_coverage=0.5,
        tpo_source="v9_tpo_history.available_at",
        same_bar_ranking="none-stage0b",
        entry_cutoff="none-stage0b",
        max_entries_per_day=None,
        mae_scratch_mode="none-stage0b",
        is_window="none-stage0b",
        oos_window="none-stage0b",
        lookahead_layers=(),
        random_seed=None,
    )
    values.update(changes)
    return ReplayManifest(**values)


def test_manifest_fails_when_required_identity_is_missing():
    with pytest.raises(ValueError, match="policy_id"):
        _manifest(policy_id="")


def test_manifest_fails_when_split_does_not_match_contracts():
    with pytest.raises(ValueError, match="contract_split"):
        _manifest(contract_split=(1, 1, 1))


def test_manifest_rejects_negative_split_cost_and_slippage():
    with pytest.raises(ValueError, match="negatives"):
        _manifest(contract_split=(5, -1))
    with pytest.raises(ValueError, match="commission"):
        _manifest(commission_round_turn=-1)
    with pytest.raises(ValueError, match="slippage"):
        _manifest(slippage_ticks_entry=-1)


def test_manifest_rejects_invalid_candidate_source():
    with pytest.raises(ValueError, match="candidate_source"):
        _manifest(candidate_source="none")


@pytest.mark.parametrize("field", [
    "dirty_tree_hash",
    "machine_tag",
    "same_bar_ranking",
    "is_window",
    "oos_window",
])
def test_manifest_rejects_blank_required_identity(field):
    with pytest.raises(ValueError, match=field):
        _manifest(**{field: ""})


def test_manifest_rejects_empty_intrabar_event_order():
    with pytest.raises(ValueError, match="intrabar_event_order"):
        _manifest(intrabar_event_order=())


def test_request_rejects_zero_cvd_coverage_threshold():
    with pytest.raises(ValueError, match="min_cvd_coverage"):
        ReplayRequest(dt.date(2026, 8, 18), min_cvd_coverage=0.0)


def test_request_has_no_cvd_conflict_bypass():
    with pytest.raises(TypeError):
        ReplayRequest(
            dt.date(2026, 8, 18),
            require_clean_cvd=False,  # type: ignore[call-arg]
        )


def test_official_cli_requires_scid_validator():
    with pytest.raises(SystemExit):
        _parser().parse_args(["validate", "--session", "2026-08-18"])


def test_remote_postgres_dsn_is_rejected():
    with pytest.raises(ValueError, match="local Postgres"):
        ValidatedDBSource("postgresql://example.com/mems26")
    with pytest.raises(ValueError, match="local Postgres"):
        ValidatedDBSource(
            "postgresql:///mems26?host=example.com")
    with pytest.raises(ValueError, match="local Postgres"):
        ValidatedDBSource("service=remote_prod")
    with pytest.raises(ValueError, match="local Postgres"):
        ValidatedDBSource(
            "hostaddr=203.0.113.7 dbname=mems26")
    with pytest.raises(ValueError, match="local Postgres"):
        ValidatedDBSource(
            "postgresql:///mems26?hostaddr=203.0.113.7")


def test_implicit_remote_pghost_is_rejected(monkeypatch):
    monkeypatch.setenv("PGHOST", "example.com")
    with pytest.raises(ValueError, match="local Postgres"):
        ValidatedDBSource("dbname=mems26")


def test_implicit_remote_pghostaddr_is_rejected(monkeypatch):
    monkeypatch.setenv("PGHOSTADDR", "203.0.113.7")
    with pytest.raises(ValueError, match="local Postgres"):
        ValidatedDBSource("dbname=mems26")


def test_result_hash_ignores_only_volatile_run_fields():
    base = {"created_at": "one", "run_id": "one", "value": 7.25}
    rerun = {"created_at": "two", "run_id": "two", "value": 7.25}
    changed = {"created_at": "two", "run_id": "two", "value": 7.5}
    assert canonical_result_hash(base) == canonical_result_hash(rerun)
    assert canonical_result_hash(base) != canonical_result_hash(changed)


def test_result_hash_keeps_nested_domain_created_at():
    first = {"data": {"created_at": "one", "value": 7.25}}
    second = {"data": {"created_at": "two", "value": 7.25}}
    assert canonical_result_hash(first) != canonical_result_hash(second)


def test_manifest_hash_ignores_run_instance_metadata():
    first = _manifest(run_id="one", created_at="one")
    second = _manifest(run_id="two", created_at="two")
    assert manifest_hash(first) == manifest_hash(second)


def test_git_identity_hash_includes_staged_diff(monkeypatch, tmp_path):
    staged = {"value": b"staged-one"}

    def fake_check_output(command, **kwargs):
        if command[:3] == ["git", "rev-parse", "HEAD"]:
            return "a" * 40 + "\n"
        if "--cached" in command:
            return staged["value"]
        if command[:2] == ["git", "diff"]:
            return b"unstaged"
        if command[:3] == ["git", "ls-files", "--others"]:
            return ""
        raise AssertionError(command)

    monkeypatch.setattr(
        "backend.v9.replay.manifest.subprocess.check_output",
        fake_check_output)
    _, first = git_identity(tmp_path)
    staged["value"] = b"staged-two"
    _, second = git_identity(tmp_path)
    assert first != second


def test_runtime_entrypoints_do_not_import_replay_package():
    for relative in (
        "backend/main.py",
        "backend/v9/app.py",
        "backend/v9/gateway/trading_gateway.py",
    ):
        text = (ROOT / relative).read_text(errors="ignore")
        assert "backend.v9.replay" not in text


@pytest.mark.skipif(not SCID.exists(), reason="local Sierra SCID unavailable")
@pytest.mark.parametrize("date", ["2026-08-18", "2026-08-17", "2026-08-20"])
def test_green_anchor_is_judgeable(date):
    session = ValidatedDBSource(DSN).load_session(
        ReplayRequest(dt.date.fromisoformat(date)),
        scid_validator=SCIDValidator(str(SCID)),
        fail_closed=False,
    )
    assert session.quality.judgeable, session.quality.to_dict()
    assert len(session.bars) == 78
    assert session.quality.metrics["scid_ohlc_mismatches"] == 0
    assert session.quality.metrics["scid_volume_mismatches"] == 0


@pytest.mark.skipif(not SCID.exists(), reason="local Sierra SCID unavailable")
def test_0715_fails_closed_on_cardinality_and_scid_truth():
    session = ValidatedDBSource(DSN).load_session(
        ReplayRequest(dt.date(2026, 7, 15)),
        scid_validator=SCIDValidator(str(SCID)),
        fail_closed=False,
    )
    assert not session.quality.judgeable
    assert "RTH_CARDINALITY" in session.quality.reason_codes
    assert "SCID_TIMESTAMP_MISMATCH" in session.quality.reason_codes


@pytest.mark.skipif(not SCID.exists(), reason="local Sierra SCID unavailable")
def test_0714_fails_closed_on_cvd_conflicts():
    session = ValidatedDBSource(DSN).load_session(
        ReplayRequest(dt.date(2026, 7, 14)),
        scid_validator=SCIDValidator(str(SCID)),
        fail_closed=False,
    )
    assert not session.quality.judgeable
    assert "CVD_CONFLICTS" in session.quality.reason_codes


@pytest.mark.skipif(not SCID.exists(), reason="local Sierra SCID unavailable")
def test_zero_cvd_coverage_fails_closed():
    session = ValidatedDBSource(DSN).load_session(
        ReplayRequest(dt.date(2026, 8, 12)),
        scid_validator=SCIDValidator(str(SCID)),
        fail_closed=False,
    )
    assert not session.quality.judgeable
    assert "CVD_COVERAGE" in session.quality.reason_codes


@pytest.mark.skipif(not SCID.exists(), reason="local Sierra SCID unavailable")
def test_scid_validator_detects_corrupt_db_delta():
    session = ValidatedDBSource(DSN).load_session(
        ReplayRequest(dt.date(2026, 8, 18)),
        fail_closed=False,
    )
    index = next(i for i, bar in enumerate(session.bars)
                 if bar.delta is not None)
    session.bars[index] = replace(session.bars[index], delta=999999.0)

    quality = SCIDValidator(str(SCID)).validate(session)

    assert not quality.judgeable
    assert "SCID_DELTA_MISMATCH" in quality.reason_codes


def test_identical_cvd_duplicate_with_later_null_keeps_value():
    class Cursor:
        def execute(self, sql, params):
            return None

        def fetchall(self):
            stamp = dt.datetime(
                2026, 8, 18, 13, 35, tzinfo=dt.timezone.utc)
            return [
                {"id": 1, "ts": stamp, "delta": 10.0, "cumulative": 20.0},
                {"id": 2, "ts": stamp, "delta": None, "cumulative": None},
            ]

    result = ValidatedDBSource._load_cvd(
        Cursor(), dt.date(2026, 8, 18))

    assert result["conflict_timestamps"] == 0
    assert result["values"][
        dt.datetime(2026, 8, 18, 13, 35, tzinfo=dt.timezone.utc)
    ] == {"delta": 10.0, "cumulative": 20.0}
