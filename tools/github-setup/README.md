# GitHub-Slack Integration

## Overview

Routes GitHub events (PRs, pushes, CI status) to appropriate Slack channels.

## Two Integration Options

### Option A: GitHub Slack App (Recommended for start)
- Zero-code setup
- Install via Slack App Directory
- See `setup_github_app.md` for step-by-step guide
- Covers 80% of use cases

### Option B: Custom Webhook Handler (Advanced)
- More granular filtering control
- Custom message formatting
- Uses `webhook_handler.py` + `webhook_filter.yaml`
- Requires deployment (separate Render service or add route to existing backend)

## Event Routing

| GitHub Event | Slack Channel | Why |
|-------------|---------------|-----|
| PR opened | #cc-master | Coordinator tracks work |
| Review requested | #checkpoints | Michael's approval gate |
| PR merged (main) | #strategic + #daily-reports | Leadership visibility |
| Push to feature/* | Silent | Noise reduction |
| CI failed | #alerts-critical | Immediate attention |
| Issue opened | #methodology | Discussion thread |

## Deploying webhook_handler.py

When ready to deploy:

1. Add to existing Render backend or create new service:
   ```bash
   uvicorn webhook_handler:app --host 0.0.0.0 --port 8001
   ```

2. Set environment variables:
   ```
   SLACK_BOT_TOKEN=xoxb-...
   GITHUB_WEBHOOK_SECRET=<random-string>
   ```

3. Configure webhook in GitHub repo settings (see `setup_github_app.md` Step 3)

4. Test with a PR on a feature branch

## Files

| File | Purpose |
|------|---------|
| `setup_github_app.md` | Manual setup guide for Michael |
| `webhook_handler.py` | FastAPI webhook receiver (STUB) |
| `webhook_filter.yaml` | Event → channel routing config |
| `README.md` | This file |
