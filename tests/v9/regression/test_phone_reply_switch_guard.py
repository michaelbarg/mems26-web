"""Regression: `phone_reply.py --help` must NOT send "--help" to Michael's phone.

Incident (three times): 2026-09-03 09:15, 2026-09-04 15:44, 2026-09-15 15:09 —
an agent ran the script to discover its usage. `text = sys.argv[-1]` turns ANY
single argument into the message body, so the word "--help" was appended to
PHONE_THREAD.jsonl and POSTed to Render. Render has no delete endpoint, and a
correction message to the phone is itself a phone-rule violation, so the noise
is permanent. Per the learning doctrine an incident becomes a regression case,
not a flag.

The guard must (a) refuse help switches, (b) refuse any bare switch token, and
(c) leave a real message body untouched — including the {NOW} substitution.
"""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
SCRIPT = os.path.join(REPO, "scripts", "phone_reply.py")
THREAD = os.path.join(REPO, "docs", "handoff", "PHONE_THREAD.jsonl")


def _thread_len():
    if not os.path.exists(THREAD):
        return 0
    with open(THREAD, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def _run(args):
    return subprocess.run([sys.executable, SCRIPT] + args,
                          capture_output=True, text=True, cwd=REPO)


def test_help_switches_do_not_append_to_thread():
    for switch in ("--help", "-h", "help", "-?"):
        before = _thread_len()
        proc = _run([switch])
        after = _thread_len()
        assert after == before, (
            f"{switch!r} appended a row to PHONE_THREAD.jsonl "
            f"({before} -> {after}) — it would have been pushed to the phone")
        assert proc.returncode != 0, f"{switch!r} should exit non-zero"


def test_bare_switch_token_is_refused():
    before = _thread_len()
    proc = _run(["--dry-run"])
    assert _thread_len() == before, "a bare switch token was sent as a message"
    assert proc.returncode != 0
    assert "refusing to send bare switch token" in (proc.stdout + proc.stderr)


def test_no_args_is_refused():
    before = _thread_len()
    _run([])
    assert _thread_len() == before, "a no-arg invocation appended a row"


def test_real_message_still_builds_the_expected_row(tmp_path, monkeypatch):
    """The guard must not change the happy path. Exercised in-process against a
    temp thread file so the test never touches the real thread or Render."""
    monkeypatch.syspath_prepend(os.path.join(REPO, "scripts"))
    import importlib

    mod = importlib.import_module("phone_reply")
    target = tmp_path / "PHONE_THREAD.jsonl"
    monkeypatch.setattr(mod, "P", str(target))
    monkeypatch.setattr(mod, "ROOT", str(tmp_path))  # no .env => no POST
    monkeypatch.setattr(sys, "argv", ["phone_reply.py", "cowork", "נמדד {NOW} בדיקה"])

    mod.main()

    rows = [json.loads(l) for l in target.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(rows) == 1
    assert rows[0]["sender"] == "cowork"
    assert "{NOW}" not in rows[0]["text"], "the {NOW} token was not stamped"
    assert rows[0]["text"].startswith("נמדד ")
    assert rows[0]["text"].endswith(" בדיקה")
