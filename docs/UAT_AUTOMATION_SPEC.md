# MEMS26 — UAT Automation Architecture

## 3-Tier Architecture

### Tier 1: Bash UAT Scripts
**Directory:** `scripts/`

| Script | Purpose |
|--------|---------|
| `uat_lib.sh` | Shared helpers (source, don't execute) |
| `uat_prompt_1.sh` | Prompt 1 concrete checks (11 checks) |
| `uat_template.sh` | Template for Prompts 2-16 |

**Helpers in uat_lib.sh:**
- `check_process(pattern)` — is a process running?
- `check_file_fresh(path, max_age_sec)` — is file recent?
- `check_redis_xlen(stream, min_val)` — Redis Stream length check
- `check_http(url, expected_status)` — HTTP health check
- `check_port(port)` — is port listening?
- `check_log_pattern(file, regex)` — grep log tail
- `check_json_field(url, field, expected)` — JSON field check
- `report_result(name, expected, actual, status)` — log a check
- `print_summary()` — final table + exit code
- `write_report(prompt_num, output_dir)` — markdown report

### Tier 2: Git Hooks
| Hook | Script | Purpose |
|------|--------|---------|
| `pre-commit` | `scripts/pre-commit-hook.sh` | Block test mocks + secrets |
| `post-commit` | `scripts/post-commit-hook.sh` | Auto-run UAT + Slack notify |

**Install:** Both installed as symlinks:
```bash
ln -sf ../../scripts/pre-commit-hook.sh .git/hooks/pre-commit
ln -sf ../../scripts/post-commit-hook.sh .git/hooks/post-commit
```

### Tier 3: Status Dashboard (future)
`GET /api/v9/status` returns 5-layer health JSON. Used by UAT scripts
and humans. Can be extended for CI/CD health gates.

## How to Add Checks for a New Prompt

1. Copy `scripts/uat_template.sh` to `scripts/uat_prompt_N.sh`
2. Set `PROMPT_NUM=N` and add check blocks
3. Use helpers from `uat_lib.sh`
4. Run: `./scripts/uat_prompt_N.sh`
5. Reports auto-write to `docs/UAT_REPORTS/`

## How to Skip Checks When Sierra is Closed

```bash
./scripts/uat_prompt_1.sh --skip-sierra
```

Sierra-related checks gracefully degrade to SKIP status when:
- `--skip-sierra` flag is passed
- `live_price.json` is missing or stale (market closed)

## Slack Channel Mapping

Set `SLACK_UAT_WEBHOOK` env var to post results to #uat-results.
Format:
- Pass: `:white_check_mark: Prompt N UAT — ALL PASS`
- Fail: `:x: Prompt N UAT — FAILED at: <first failure>`

### One-Way Ops Summaries

The repo now supports three one-way Slack notifications:

| Trigger | Script | Message |
|---------|--------|---------|
| Any commit without prompt number | `scripts/post-commit-hook.sh` | Commit hash + UAT skipped |
| Prompt commit with UAT script | `scripts/post-commit-hook.sh` | UAT pass/fail + first failure |
| BLOCKED report | `scripts/report_blocked.sh docs/reports/BLOCKED.md` | First 12 lines of BLOCKED file |

Generic notifier: `scripts/slack_notify.sh "Title" "Body" "good|warn|fail|info"`.

Secrets rule: webhook values stay in environment only. Do not commit `.env` or
webhook URLs.

## Performance Budget

- Each individual check: < 5 seconds
- Total UAT runtime: < 90 seconds
- Status endpoint: < 1 second
