"""Dead S3/S5 streams must NOT drag the readiness verdict to BLOCKED.

Michael 2026-06-08: tick_reversal_15 is System 3 (footprint/tick-reversal),
which is MUTED (S3_MUTE=1) and not in the S2/S4 fire path. tpo is S5,
intentionally not-wired (I-24). A dead S3/S5 stream must be NON-critical for
the board verdict — only true fire-path streams (bars_5min, cumulative_delta,
volume_profile, imbalance) may block.

Litmus: if someone moves tick_reversal_15/tpo back to critical → test goes RED.
"""
from backend.v9.systems.build_status.aggregator import _compute_readiness
from backend.v9.systems.build_status.types import (
    SystemStatus, GlobalGate, RTBSession,
)


def _gate(key, present):
    return GlobalGate(key=key, spec=f"{key} fresh", present=present)


def _bridge(gates):
    return SystemStatus(id="bridge", name="Bridge", global_gates=gates)


def _bridge_check(readiness):
    return next(c for c in readiness.checks if c.key == "bridge_streams_fresh")


def test_dead_s3_s5_streams_do_not_block():
    """tick_reversal_15 + tpo dead, all fire-path streams fresh → PASS."""
    gates = [
        _gate("bars_5min", True),
        _gate("cumulative_delta", True),
        _gate("volume_profile", True),
        _gate("imbalance", True),
        _gate("woodies_5min", True),
        _gate("footprint", False),          # S3, muted → non-critical
        _gate("tick_reversal_15", False),   # S3, muted → non-critical
        _gate("tpo", False),                # S5, not-wired → non-critical
    ]
    readiness = _compute_readiness([_bridge(gates)], RTBSession(in_session=True))
    chk = _bridge_check(readiness)
    assert chk.passed is True, (
        f"Dead S3/S5 streams must not block; got detail={chk.detail!r}"
    )


def test_dead_fire_path_stream_still_blocks():
    """A truly-critical stream (bars_5min) dead → still BLOCKED (guard against
    over-excluding)."""
    gates = [
        _gate("bars_5min", False),          # fire-path → MUST block
        _gate("cumulative_delta", True),
        _gate("tick_reversal_15", False),
        _gate("tpo", False),
    ]
    readiness = _compute_readiness([_bridge(gates)], RTBSession(in_session=True))
    chk = _bridge_check(readiness)
    assert chk.passed is False
    assert "bars_5min" in (chk.detail or "")
    assert "tick_reversal_15" not in (chk.detail or "")
    assert "tpo" not in (chk.detail or "")
