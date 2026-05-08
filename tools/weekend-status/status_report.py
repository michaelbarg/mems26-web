#!/usr/bin/env python3
"""
MEMS26 Weekend Status Reporter

Generates a progress report for the feature/weekend-foundation branch.
Shows commits, files changed, new decision entries, and new specs.

Usage:
    python3 status_report.py                # Print to terminal
    python3 status_report.py --json         # Output as JSON
    python3 status_report.py --slack        # Format for Slack
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
BRANCH = "feature/weekend-foundation"
BASE_BRANCH = "feature/slack-setup"


def run(cmd: str, cwd: str | None = None) -> str:
    """Run a shell command and return stdout."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=cwd or str(REPO_ROOT)
    )
    return result.stdout.strip()


def get_commits() -> list[dict]:
    """Get commits on this branch since base."""
    log = run(f"git log {BASE_BRANCH}..{BRANCH} --oneline --format='%h|%s'")
    if not log:
        return []
    commits = []
    for line in log.split("\n"):
        if "|" in line:
            hash_, msg = line.split("|", 1)
            commits.append({"hash": hash_.strip("'"), "message": msg})
    return commits


def get_diff_stats() -> dict:
    """Get diff statistics vs base branch."""
    stat = run(f"git diff {BASE_BRANCH}..{BRANCH} --stat")
    shortstat = run(f"git diff {BASE_BRANCH}..{BRANCH} --shortstat")

    # Parse file list
    files = run(f"git diff {BASE_BRANCH}..{BRANCH} --name-only")
    file_list = [f for f in files.split("\n") if f]

    return {
        "files_changed": len(file_list),
        "file_list": file_list,
        "shortstat": shortstat,
    }


def get_uncommitted() -> str:
    """Get uncommitted changes."""
    return run("git status --short")


def get_new_decisions() -> list[str]:
    """Find D-XXX entries in MEMS26_FIRST.md that are new on this branch."""
    diff = run(f"git diff {BASE_BRANCH}..{BRANCH} -- MEMS26_FIRST.md")
    entries = re.findall(r"^\+## (D-\d+:.+)$", diff, re.MULTILINE)
    return entries


def get_new_specs() -> list[str]:
    """Find new spec files in docs/specs/."""
    files = run(f"git diff {BASE_BRANCH}..{BRANCH} --name-only -- docs/specs/")
    return [f for f in files.split("\n") if f]


def generate_report() -> dict:
    """Generate full status report."""
    commits = get_commits()
    diff = get_diff_stats()
    uncommitted = get_uncommitted()
    decisions = get_new_decisions()
    specs = get_new_specs()

    return {
        "branch": BRANCH,
        "base": BASE_BRANCH,
        "commits": commits,
        "commit_count": len(commits),
        "files_changed": diff["files_changed"],
        "file_list": diff["file_list"],
        "shortstat": diff["shortstat"],
        "uncommitted": uncommitted or "Clean",
        "new_decisions": decisions,
        "new_specs": specs,
    }


def format_terminal(report: dict) -> str:
    """Format report for terminal output."""
    lines = [
        "=" * 60,
        f"MEMS26 Weekend Status Report",
        f"Branch: {report['branch']} (from {report['base']})",
        "=" * 60,
        "",
        f"COMMITS: {report['commit_count']}",
    ]

    for c in report["commits"]:
        lines.append(f"  {c['hash']} {c['message']}")

    lines.extend([
        "",
        f"FILES CHANGED: {report['files_changed']}",
        f"  {report['shortstat']}",
        "",
        "FILE LIST:",
    ])

    for f in report["file_list"]:
        lines.append(f"  {f}")

    lines.extend([
        "",
        f"UNCOMMITTED: {report['uncommitted']}",
        "",
        f"NEW DECISIONS: {len(report['new_decisions'])}",
    ])

    for d in report["new_decisions"]:
        lines.append(f"  {d}")

    lines.extend([
        "",
        f"NEW SPECS: {len(report['new_specs'])}",
    ])

    for s in report["new_specs"]:
        lines.append(f"  {s}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_slack(report: dict) -> str:
    """Format report for Slack posting."""
    commits_text = "\n".join(
        f"  `{c['hash']}` {c['message']}" for c in report["commits"]
    )
    decisions_text = "\n".join(f"  - {d}" for d in report["new_decisions"]) or "  None"
    specs_text = "\n".join(f"  - `{s}`" for s in report["new_specs"]) or "  None"

    return f"""*MEMS26 Weekend Status* — `{report['branch']}`

*Commits:* {report['commit_count']}
{commits_text}

*Files changed:* {report['files_changed']} | {report['shortstat']}
*Uncommitted:* {report['uncommitted']}

*New Decisions:*
{decisions_text}

*New Specs:*
{specs_text}"""


if __name__ == "__main__":
    report = generate_report()

    if "--json" in sys.argv:
        print(json.dumps(report, indent=2))
    elif "--slack" in sys.argv:
        print(format_slack(report))
    else:
        print(format_terminal(report))
