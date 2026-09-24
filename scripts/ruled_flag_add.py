#!/usr/bin/env python3
"""Add or replace ONE entry in config/RULED_FLAGS.yaml (the enforcing memory of Michael's rulings).

    python3 scripts/ruled_flag_add.py FLAG --expected 1 --ruled-by מייקל --date 2026-09-24 \
        --note '...' --measured '...'

Appends a flow-style entry under `ruled:` (or replaces the existing line for FLAG), then re-parses
the file so a broken YAML never lands. Prints the resulting line. Idempotent.
"""
import argparse, os, re, sys, yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "config", "RULED_FLAGS.yaml")


def _q(s: str) -> str:
    """single-quoted YAML scalar"""
    return "'" + str(s).replace("'", "''") + "'"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("flag")
    ap.add_argument("--expected", required=True)
    ap.add_argument("--ruled-by", default="מייקל")
    ap.add_argument("--date", required=True)
    ap.add_argument("--note", required=True)
    ap.add_argument("--measured", default=None)
    a = ap.parse_args()
    if not re.fullmatch(r"[A-Z0-9_]+", a.flag):
        print("bad flag name", a.flag); return 2
    line = f"  {a.flag}: {{expected: {_q(a.expected)}, ruled_by: {_q(a.ruled_by)}, date: {_q(a.date)}, note: {_q(a.note)}"
    if a.measured:
        line += f", measured: {_q(a.measured)}"
    line += "}"
    src = open(PATH, encoding="utf-8").read()
    pat = re.compile(rf"^  {re.escape(a.flag)}:\s*\{{.*\}}\s*$", re.M)
    if pat.search(src):
        new = pat.sub(lambda m: line, src, count=1); action = "replaced"
    else:
        new = src.rstrip("\n") + "\n" + line + "\n"; action = "appended"
    try:
        doc = yaml.safe_load(new)
        assert a.flag in (doc.get("ruled") or {}), "entry not under ruled:"
    except Exception as e:
        print("REFUSED — resulting YAML invalid:", e); return 1
    open(PATH, "w", encoding="utf-8").write(new)
    print(f"{action}: {line[:160]}…" if len(line) > 160 else f"{action}: {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
