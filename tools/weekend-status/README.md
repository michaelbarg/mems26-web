# Weekend Status Reporter

Quick progress reports for when Michael checks in from mobile during CC autonomous work.

## Usage

### Terminal (direct)
```bash
python3 status_report.py           # Human-readable
python3 status_report.py --json    # Machine-readable
python3 status_report.py --slack   # Slack-formatted
```

### Post to Slack
```bash
export SLACK_BOT_TOKEN=xoxb-...
./report_to_slack.sh               # Post to #cc-master
./report_to_slack.sh --dry-run     # Preview without posting
```

## What It Reports

- Commit count and messages on the working branch
- Files changed (count + list)
- Diff stats (insertions/deletions)
- Uncommitted changes
- New D-XXX decision entries added to MEMS26_FIRST.md
- New spec files in docs/specs/

## Future: Slack Bot Auto-Response

When Slack bot infrastructure is in place, Michael can type `status please` in #cc-master and get an auto-response. For now, run `report_to_slack.sh` manually via terminal (TeamViewer from mobile if needed).
