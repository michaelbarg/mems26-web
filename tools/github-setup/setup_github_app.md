# GitHub-Slack Integration Setup Guide

## Step 1: Install GitHub for Slack App

1. Go to Slack workspace settings → Apps
2. Search for "GitHub" (official GitHub app by GitHub, Inc.)
3. Click "Add to Slack"
4. Authorize with your GitHub account (michaelbarg)
5. Select the `michaelbarg/mems26-web` repository

## Step 2: Subscribe Channels to Events

Run these commands in each Slack channel:

### #cc-master
```
/github subscribe michaelbarg/mems26-web pulls
```

### #checkpoints
```
/github subscribe michaelbarg/mems26-web reviews
```

### #strategic
```
/github subscribe michaelbarg/mems26-web pulls merges
```
Then filter to main branch only:
```
/github subscribe michaelbarg/mems26-web pulls +label:"main"
```

### #alerts-critical
```
/github subscribe michaelbarg/mems26-web workflows:{name:"CI"}
```

### #methodology
```
/github subscribe michaelbarg/mems26-web issues
```

## Step 3: Configure Custom Webhook (Advanced)

For more granular control than the Slack GitHub app provides, set up a custom webhook:

1. Go to: https://github.com/michaelbarg/mems26-web/settings/hooks
2. Click "Add webhook"
3. **Payload URL**: `https://<your-render-backend>/webhooks/github` (deploy `webhook_handler.py` first)
4. **Content type**: `application/json`
5. **Secret**: Generate a webhook secret, store in backend `.env` as `GITHUB_WEBHOOK_SECRET`
6. **Events**: Select individual events:
   - Pull requests
   - Push
   - Workflow runs
   - Issues

## Step 4: Verify

1. Create a test PR on a feature branch
2. Verify notification appears in #cc-master
3. Request review → verify #checkpoints gets notification
4. Merge to main → verify #strategic gets notification

## Notes

- The GitHub Slack app handles most use cases without a custom webhook
- The custom webhook (`webhook_handler.py`) is for future advanced filtering (e.g., silent pushes to feature branches)
- Don't set up both for the same events — pick one per event type to avoid duplicate notifications
