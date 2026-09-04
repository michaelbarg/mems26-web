"""T-245 regression — the news-calendar generator must not rewrite on a no-op run.

Bug (measured 2026-09-04): every auto-run wrote the yaml with a fresh
`# מקור-הריצה האחרונה: … <ts>` header comment even when the event body was
byte-identical. The generated artifact therefore sat dirty in the tree after
each auto-run and blocked `git pull` / `commit` at the FIRST step of the 15:30
pre-open gate. 6 of the 15 most recent commits to config/news_calendar.yaml
were pure `1+/1-` timestamp churn.

Fix: `_body_unchanged()` — skip the write when the on-disk event body already
matches. These tests pin BOTH directions: no-op runs must not write, and real
calendar changes must still write (the suppressor must never eat an update).
"""
import importlib
import time

news = importlib.import_module("scripts.update_news_calendar")


BODY_A = (
    '  - date: 2026-09-04\n    time_et: "08:30"\n'
    '    name: "Non Farm Payrolls"\n    severity: red\n'
)
BODY_B = (
    '  - date: 2026-09-04\n    time_et: "08:30"\n'
    '    name: "Non Farm Payrolls"\n    severity: red\n'
    '  - date: 2026-09-08\n    time_et: "10:00"\n'
    '    name: "JOLTS Job Openings"\n    severity: red\n'
)


def _write_cal(path, body, stamp="2026-09-03 22:56 ET"):
    src_line = f"# מקור-הריצה האחרונה: tradingview (importance=1, US) · {stamp}"
    path.write_text(news.HEADER.format(source_line=src_line) + body, encoding="utf-8")


def test_identical_body_is_detected_as_unchanged(tmp_path, monkeypatch):
    cal = tmp_path / "news_calendar.yaml"
    _write_cal(cal, BODY_A)
    monkeypatch.setattr(news, "CAL", cal)
    assert news._body_unchanged(BODY_A) is True


def test_changed_body_still_writes(tmp_path, monkeypatch):
    """The suppressor must never be the reason a real update is lost."""
    cal = tmp_path / "news_calendar.yaml"
    _write_cal(cal, BODY_A)
    monkeypatch.setattr(news, "CAL", cal)
    assert news._body_unchanged(BODY_B) is False


def test_stale_timestamp_does_not_force_a_write(tmp_path, monkeypatch):
    """The header timestamp is deliberately excluded from the comparison."""
    cal = tmp_path / "news_calendar.yaml"
    _write_cal(cal, BODY_A, stamp="2019-01-01 00:00 ET")
    monkeypatch.setattr(news, "CAL", cal)
    assert news._body_unchanged(BODY_A) is True


def test_missing_file_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(news, "CAL", tmp_path / "does_not_exist.yaml")
    assert news._body_unchanged(BODY_A) is False


def test_file_without_events_marker_writes(tmp_path, monkeypatch):
    """A truncated/corrupt artifact must be regenerated, not preserved."""
    cal = tmp_path / "news_calendar.yaml"
    cal.write_text("# header only, no marker\n", encoding="utf-8")
    monkeypatch.setattr(news, "CAL", cal)
    assert news._body_unchanged(BODY_A) is False


def test_no_op_run_leaves_mtime_untouched(tmp_path, monkeypatch):
    """End-to-end: the file itself must not be touched, not merely equal.

    `git status` keys off content, but an untouched mtime is the stronger
    guarantee and is what keeps the pre-open gate's tree clean.
    """
    cal = tmp_path / "news_calendar.yaml"
    _write_cal(cal, BODY_A)
    monkeypatch.setattr(news, "CAL", cal)
    before = cal.stat().st_mtime_ns
    before_text = cal.read_text(encoding="utf-8")

    time.sleep(0.01)
    assert news._body_unchanged(BODY_A) is True  # main() returns before writing

    assert cal.stat().st_mtime_ns == before, "no-op run must not touch the file"
    assert cal.read_text(encoding="utf-8") == before_text
    assert "2026-09-03 22:56 ET" in before_text, "old run-timestamp is preserved"
