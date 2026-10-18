# -*- coding: utf-8 -*-
"""T-260 / BRIEF §3.5 — phone_reply.py verifies the delivery on Render instead of printing "ok" unconditionally.

Two silent-loss paths (TASK_LOG T-260): (1) Render /reply rejects > 2000 chars with 400 and the POST sat inside
`except Exception: pass` (victim: 04.09 21:17:28Z, 2402 chars, reported as sent); (2) /reply is RAM on a
free-tier service that cold-starts / is wiped by every deploy, so "POST returned" ≠ "the page shows it"
(05.10 13:07 dark page). The fix: refuse > 2000 before anything is written; after the POST read GET /chat back
and report `ok render=verified` (exit 0) or `UNVERIFIED render=<why>` (exit 2) — with the explicit instruction
NOT to resend (the line is in PHONE_THREAD.jsonl; a second send is T-369).

In-process against a temp thread + temp .env, every HTTP call goes through the module seam `_urlopen` —
no network, the real thread and Render are never touched."""
import importlib
import io
import json
import os
import sys
import urllib.error

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class _Resp:
    def __init__(self, body, status=200):
        self._b = body.encode("utf-8") if isinstance(body, str) else body
        self.status = status
        self.code = status

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Net:
    """Fake urlopen: records every call; per-path behaviour is a callable or a response."""

    def __init__(self):
        self.calls = []       # (method, url)
        self.reply = lambda: _Resp('{"ok": true}')
        self.chat = lambda: _Resp('{"items": []}')
        self.ntfy = lambda: _Resp("{}")

    def __call__(self, req, timeout=None):
        url = req.full_url
        self.calls.append((req.get_method(), url))
        if "/reply" in url:
            return self.reply()
        if "/chat" in url:
            return self.chat()
        if "ntfy.sh" in url:
            return self.ntfy()
        raise AssertionError("unexpected url " + url)


@pytest.fixture
def mod(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(os.path.join(REPO, "scripts"))
    m = importlib.import_module("phone_reply")
    importlib.reload(m)
    monkeypatch.setattr(m, "P", str(tmp_path / "PHONE_THREAD.jsonl"))
    monkeypatch.setattr(m, "ROOT", str(tmp_path))
    monkeypatch.setattr(m.time, "sleep", lambda s: None)   # the cold-start retry must not slow the tests
    net = _Net()
    monkeypatch.setattr(m, "_urlopen", net)
    m._net = net
    return m


def _env(mod, key="k123", ntfy=""):
    with open(os.path.join(mod.ROOT, ".env"), "w", encoding="utf-8") as f:
        f.write(f"MOBILE_ACCESS_KEY={key}\n")
        if ntfy:
            f.write(f"NTFY_TOPIC={ntfy}\n")


def _rows(mod):
    p = mod.P
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p, encoding="utf-8").read().splitlines() if l.strip()]


def _run(mod, monkeypatch, text, sender="fix-agent"):
    monkeypatch.setattr(sys, "argv", ["phone_reply.py", sender, text])
    out = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    code = 0
    try:
        mod.main()
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
        if not isinstance(e.code, int):
            out.write(str(e.code))
    return code, out.getvalue()


def _chat_with(sender, text):
    return lambda: _Resp(json.dumps({"items": [
        {"sender": "מייקל", "text": "שלום", "ts": "2026-10-18T07:00:00Z", "status": ""},
        {"sender": sender, "text": text, "ts": "2026-10-18T21:00:00Z", "status": ""}]}, ensure_ascii=False))


# ── (1) the 2000-char ceiling ─────────────────────────────────────────────────────────────────────────────────
def test_over_2000_chars_is_refused_before_anything_is_written_or_sent(mod, monkeypatch):
    _env(mod)
    code, out = _run(mod, monkeypatch, "א" * 2001)
    assert code != 0
    assert "2001 chars > 2000" in out and "nothing was written or sent" in out
    assert _rows(mod) == [], "a refused text must not reach PHONE_THREAD.jsonl (the relay would push it)"
    assert mod._net.calls == [], "a refused text must not reach ntfy or Render"


def test_exactly_2000_chars_is_sent_and_verified(mod, monkeypatch):
    _env(mod)
    text = "ב" * 2000
    mod._net.chat = _chat_with("fix-agent", text)
    code, out = _run(mod, monkeypatch, text)
    assert code == 0, out
    assert out.strip().startswith("ok render=verified reply=200"), out
    assert "len=2000" in out
    assert [r["text"] for r in _rows(mod)] == [text]


def test_length_is_measured_in_chars_not_bytes(mod, monkeypatch):
    """1,131 Hebrew chars = 1,838 bytes (TASK_LOG 07.09): a byte check would refuse a legal message."""
    _env(mod)
    text = "ש" * 1131
    mod._net.chat = _chat_with("fix-agent", text)
    code, out = _run(mod, monkeypatch, text)
    assert code == 0 and out.startswith("ok render=verified"), out


# ── (2) the delivery is what Render shows ─────────────────────────────────────────────────────────────────────
def test_reply_400_is_reported_as_unverified_not_ok(mod, monkeypatch):
    _env(mod)

    def _400():
        raise urllib.error.HTTPError("u", 400, "text required (max 2000 chars)", {}, None)
    mod._net.reply = _400
    code, out = _run(mod, monkeypatch, "דוח-לילה")
    assert code == 2
    assert out.startswith("UNVERIFIED"), out
    assert "reply=http=400" in out and "render=not-in-chat items=0" in out
    assert "do NOT resend" in out and "T-369" in out
    assert len(_rows(mod)) == 1, "the thread line is the durable record — written once, before the POST"


def test_cold_render_empty_chat_is_unverified_with_exit_2(mod, monkeypatch):
    _env(mod)
    code, out = _run(mod, monkeypatch, "שער 15:35 ירוק")
    assert code == 2
    assert out.startswith("UNVERIFIED render=not-in-chat items=0 reply=200"), out
    methods = [m for m, _ in mod._net.calls]
    assert methods == ["POST", "GET"], mod._net.calls


def test_chat_timeout_retries_once_then_unverified(mod, monkeypatch):
    _env(mod)

    def _to():
        raise OSError("The read operation timed out")
    mod._net.chat = _to
    code, out = _run(mod, monkeypatch, "בדיקה")
    assert code == 2 and "render=chat timeout" in out, out
    gets = [u for m, u in mod._net.calls if m == "GET"]
    assert len(gets) == 2, "one retry after the GET itself failed (cold start), then stop"


def test_chat_answering_without_us_does_not_retry(mod, monkeypatch):
    _env(mod)
    code, out = _run(mod, monkeypatch, "בדיקה")
    assert code == 2
    assert len([u for m, u in mod._net.calls if m == "GET"]) == 1


def test_verified_when_our_line_is_in_chat_exact_sender_and_text(mod, monkeypatch):
    _env(mod)
    mod._net.chat = _chat_with("fix-agent", "לילה: §2.3 — Δ נטו +1$")
    code, out = _run(mod, monkeypatch, "לילה: §2.3 — Δ נטו +1$")
    assert code == 0 and out.startswith("ok render=verified reply=200 ntfy=off len="), out


def test_same_text_from_another_sender_is_not_our_delivery(mod, monkeypatch):
    _env(mod)
    mod._net.chat = _chat_with("supervisor", "סיכום-יום")
    code, out = _run(mod, monkeypatch, "סיכום-יום")
    assert code == 2 and "render=not-in-chat" in out


# ── the paths that must stay as they were ─────────────────────────────────────────────────────────────────────
def test_no_key_means_no_render_path_and_ok(mod, monkeypatch):
    code, out = _run(mod, monkeypatch, "נמדד {NOW} בדיקה")
    assert code == 0 and out.startswith("ok render=no-key ntfy=off len="), out
    assert mod._net.calls == []
    rows = _rows(mod)
    assert len(rows) == 1 and "{NOW}" not in rows[0]["text"]


def test_ntfy_failure_is_reported_not_hidden(mod, monkeypatch):
    _env(mod, ntfy="mems26-topic")

    def _boom():
        raise OSError("name resolution failed")
    mod._net.ntfy = _boom
    mod._net.chat = _chat_with("fix-agent", "x1")
    code, out = _run(mod, monkeypatch, "x1")
    assert code == 0 and out.startswith("ok render=verified reply=200 ntfy=err=OSError"), out


def test_help_and_bare_switch_still_refused(mod, monkeypatch):
    for argv in (["phone_reply.py", "--help"], ["phone_reply.py", "cowork", "--dry-run"], ["phone_reply.py", "--frm", "cowork", "t"]):
        monkeypatch.setattr(sys, "argv", argv)
        with pytest.raises(SystemExit):
            mod.main()
    assert _rows(mod) == [] and mod._net.calls == []
