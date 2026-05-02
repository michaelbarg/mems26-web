# MEMS26 Pre-Flight Checklist

Run before market sessions to verify system health. Designed for Sunday ~22:00 IL
(1 hour before CME re-opens) or any pre-session check.

## Usage

```bash
cd /Users/michael/Downloads/mems26_web_git
bash tools/preflight/check.sh             # normal output
bash tools/preflight/check.sh --verbose   # includes raw API responses
bash tools/preflight/check.sh --quiet     # exit code only (CI mode)
```

## What It Checks

| Section | Check | Pass | Warn | Fail |
|---------|-------|------|------|------|
| Environment | Git branch | main | other branch | - |
| Environment | Working tree | clean | dirty | - |
| Bridge | Process running | yes | not running | - |
| Bridge | Log freshness | <5min | >5min | - |
| Sierra Chart | mes_ai_data.json | exists + fresh | missing/stale | - |
| Backend | /health reachable | yes | - | unreachable |
| Backend | Mode | SIM | other | LIVE |
| Backend | Entry mode | DEMO | STRICT/LIVE | - |
| Backend | Killzone required | false | true | - |
| Backend | Bridge heartbeat | <60s | <300s | >300s |
| Backend | Redis | OK | - | NOT OK |
| Backend | News guard | healthy | not available | - |
| Activity | 24h setup count | >2000 | >0 | - |
| Activity | Direction balance | <5x | >5x | - |
| Configs | MEMS26_MODE | SIM | - | - |

## Exit Codes

- `0` — All pass or only warnings
- `1` — One or more critical failures
- `2` — Script error (couldn't run)

## Output

Reports saved to `tools/preflight/output/preflight_YYYYMMDD_HHMMSS.txt`

## Environment Variables

- `MEMS26_API_URL` — Override API URL (default: https://mems26-web.onrender.com)
- `MEMS26_REPO` — Override repo path (default: /Users/michael/Downloads/mems26_web_git)
