# Slack Channel Bootstrap — MEMS26-OPS

Bootstraps 13 channels for the MEMS26-OPS Slack workspace.  
Decision reference: **D-048** (MEMS26_FIRST.md V2 — Slack Workspace)

## Prerequisites

1. A Slack Bot Token (`xoxb-...`) with these scopes:
   - `channels:manage` — create channels, set topic/purpose
   - `channels:read` — list channels for idempotency checks

2. Python 3.10+

## Setup & Run

```bash
cd tools/slack-setup
pip install -r requirements.txt
export SLACK_BOT_TOKEN=xoxb-your-token-here
python bootstrap_channels.py
```

## CLI Flags

| Flag | Description |
|------|-------------|
| `--dry-run` | Show what would happen, no API writes |
| `--force` | Skip workspace name confirmation |
| `--validate` | Only validate existing channels match config |

## Output

- **stdout**: Summary table of all 13 channels with IDs and status
- **channels_state.json**: Machine-readable state (gitignored)

## Troubleshooting

| Error | Fix |
|-------|-----|
| `not_authed` / `invalid_auth` | Token expired or wrong. Re-export `SLACK_BOT_TOKEN` from Slack App → OAuth & Permissions |
| `name_taken` | Not an error — script treats it as existing channel (idempotent) |
| `missing_scope` | Bot lacks a required permission. Go to api.slack.com/apps → OAuth & Permissions → add the scope → Reinstall app to workspace |
| `ratelimited` | Script auto-retries once. If persistent, wait a few minutes and re-run |

| "Only N channels visible" | All channels exist but aren't in your Slack sidebar. Click **Browse Channels** (or `+` next to Channels) to find them. The bot creates channels but doesn't auto-join other workspace members — you need to manually join each channel. |

## Diagnostics

Run `diagnose_workspace.py` to compare workspace state against `channels_config.yaml`:
```bash
cd tools/slack-setup
python diagnose_workspace.py
```
Outputs: `DIAGNOSIS_REPORT.md` (findings) + updated `channels_state.json` (validated state).

## How to Undo

Channel deletion is not automated for safety. To remove channels:
1. Open each channel in Slack
2. Channel Settings → Archive Channel

## Files

- `channels_config.yaml` — Declarative source of truth for all 13 channels
- `bootstrap_channels.py` — Idempotent creation script
- `channels_state.json` — Output state (gitignored)
- `.env` — Optional, for `SLACK_BOT_TOKEN` (gitignored)
