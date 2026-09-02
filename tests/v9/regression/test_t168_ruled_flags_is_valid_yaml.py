"""T-168 — config/RULED_FLAGS.yaml must be loadable by a real YAML parser.

The file was not valid YAML (found 2026-08-31 while checking the flags Michael
asked about, 124b143d):

    yaml.parser.ParserError: while parsing a flow mapping,
    in "config/RULED_FLAGS.yaml"

It went unnoticed because `scripts/flag_guard.py` does NOT use `yaml.safe_load`
— it hand-parses the file — so the guard stayed green while every OTHER
consumer would have crashed, or worse, swallowed the error and returned an
empty mapping (which reads as "no ruled flags", i.e. no drift, i.e. a green
light nobody earned).

It parses again as of 2026-09-02. This test is the missing guard: without it
the next hand-edit can silently reintroduce the same break, since the tool that
runs before every session cannot see it.
"""
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

RULED = Path(__file__).resolve().parents[3] / "config" / "RULED_FLAGS.yaml"


def test_file_exists():
    assert RULED.is_file(), f"{RULED} is the ruled-flag memory — it must exist"


def test_parses_as_yaml():
    """The exact call that used to raise ParserError."""
    data = yaml.safe_load(RULED.read_text())
    assert isinstance(data, dict), type(data)
    assert data, "empty mapping reads as 'no ruled flags' — a false all-clear"


def test_has_the_ruled_section_with_real_entries():
    """Anti-tautology: valid YAML that lost its content is not a pass."""
    data = yaml.safe_load(RULED.read_text())
    ruled = data.get("ruled")
    assert isinstance(ruled, dict), "expected a top-level `ruled` mapping"
    assert len(ruled) >= 200, (
        f"only {len(ruled)} ruled flags parsed — flag_guard reports 230; a "
        f"large drop means the YAML parsed but lost entries")


def test_every_entry_carries_an_expected_value():
    """A ruled flag without `expected` cannot be checked against .env."""
    ruled = yaml.safe_load(RULED.read_text())["ruled"]
    missing = [k for k, v in ruled.items()
               if not isinstance(v, dict) or "expected" not in v]
    assert not missing, f"ruled flags with no `expected`: {missing[:10]}"
