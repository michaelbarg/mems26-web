"""Regression: .env is loaded into the environment on every launch path.

Root incident (2026-06-06): SHADOW calibration flags fell to OFF because the
backend only got them when `scripts/start_all.sh` did `source .env`. A
LaunchAgent auto-restart / bare uvicorn never sourced it, so the flags silently
defaulted False. `backend/main.py` now calls `load_dotenv_file()` before any
`backend.v9` import. These tests pin that loader's contract.

Litmus:
- if the loader stops applying file keys -> test_loads_missing_keys RED.
- if it starts clobbering explicit env -> test_does_not_override_explicit_env RED.
"""

import os
import tempfile

from backend.env_loader import load_dotenv_file


def _write(tmp, text):
    p = os.path.join(tmp, ".env")
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


def test_loads_missing_keys():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, "S3_RELATIVE=true\nS1_CVD_OPENING=true\n")
        env = {}
        applied = load_dotenv_file(p, env)
        assert env["S3_RELATIVE"] == "true"
        assert env["S1_CVD_OPENING"] == "true"
        assert applied == {"S3_RELATIVE": "true", "S1_CVD_OPENING": "true"}


def test_does_not_override_explicit_env():
    """An explicit export (start_all.sh / LaunchAgent / shell) wins over the file."""
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, "S2_ATR_RELATIVE=false\n")
        env = {"S2_ATR_RELATIVE": "true"}  # already set explicitly
        load_dotenv_file(p, env)
        assert env["S2_ATR_RELATIVE"] == "true"  # not clobbered


def test_override_flag_forces_file_value():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, "K=0.75\n")
        env = {"K": "1.0"}
        load_dotenv_file(p, env, override=True)
        assert env["K"] == "0.75"


def test_comments_blanks_quotes_and_missing_file():
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(tmp, "# a comment\n\nMODE='shadow'\nV9_EXPORT_DIR=\"/x/y\"\nNOEQ\n")
        env = {}
        load_dotenv_file(p, env)
        assert env["MODE"] == "shadow"       # single quotes stripped
        assert env["V9_EXPORT_DIR"] == "/x/y"  # double quotes stripped
        assert "NOEQ" not in env               # line without '=' ignored
    # missing file is a no-op, not an error
    assert load_dotenv_file(os.path.join(tmp, "gone.env"), {}) == {}


def test_real_dotenv_has_shadow_flags_on():
    """The actual repo .env must enable the SHADOW calibration flags (so a
    LaunchAgent restart brings them up). Skips cleanly if .env is absent."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    env_path = os.path.join(repo_root, ".env")
    if not os.path.exists(env_path):
        return  # .env is gitignored; nothing to assert in a clean checkout
    env = {}
    load_dotenv_file(env_path, env)
    for flag in ("S2_ATR_RELATIVE", "S3_RELATIVE", "S1_CVD_OPENING",
                 "S1_IB_WIDTH_ATR", "S1_DAYTYPE_STAGING"):
        assert env.get(flag, "").lower() in ("1", "true", "yes"), f"{flag} not ON in .env"
