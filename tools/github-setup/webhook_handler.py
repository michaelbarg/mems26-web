"""
MEMS26 GitHub Webhook Handler (STUB)

Receives GitHub webhook events and forwards to appropriate Slack channels
based on webhook_filter.yaml configuration.

STUB — not deployed. Structure only.

Usage (when ready to deploy):
    uvicorn webhook_handler:app --host 0.0.0.0 --port 8001

Requires:
    pip install fastapi uvicorn httpx pyyaml
"""

import hashlib
import hmac
import os
from pathlib import Path

import httpx
import yaml
from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI(title="MEMS26 GitHub Webhook Handler")

# Load filter config
FILTER_CONFIG_PATH = Path(__file__).parent / "webhook_filter.yaml"
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")


def load_filter_config() -> dict:
    """Load webhook filter configuration."""
    with open(FILTER_CONFIG_PATH) as f:
        return yaml.safe_load(f)


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature (HMAC-SHA256)."""
    if not GITHUB_WEBHOOK_SECRET:
        return False
    expected = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def format_message(event: str, action: str, payload: dict) -> str | None:
    """Format GitHub event into Slack message. Returns None if should be silent."""
    if event == "pull_request":
        pr = payload.get("pull_request", {})
        title = pr.get("title", "")
        url = pr.get("html_url", "")
        user = pr.get("user", {}).get("login", "")
        branch = pr.get("head", {}).get("ref", "")

        if action == "opened":
            return f"🔀 PR opened by {user}: *{title}*\n{url}"
        elif action == "review_requested":
            reviewer = payload.get("requested_reviewer", {}).get("login", "")
            return f"👀 Review requested from {reviewer}: *{title}*\n{url}"
        elif action == "closed" and pr.get("merged"):
            return f"✅ PR merged: *{title}*\n{url}"

    elif event == "push":
        ref = payload.get("ref", "")
        commits = payload.get("commits", [])
        pusher = payload.get("pusher", {}).get("name", "")
        count = len(commits)

        if "refs/heads/main" in ref:
            return f"🚀 {pusher} pushed {count} commit(s) to main"

    elif event == "workflow_run":
        workflow = payload.get("workflow_run", {})
        conclusion = workflow.get("conclusion", "")
        name = workflow.get("name", "")

        if conclusion == "failure":
            url = workflow.get("html_url", "")
            return f"🚨 CI FAILED: {name}\n{url}"

    elif event == "issues":
        issue = payload.get("issue", {})
        title = issue.get("title", "")
        url = issue.get("html_url", "")

        if action == "opened":
            return f"📋 Issue opened: *{title}*\n{url}"

    return None


def get_target_channel(event: str, action: str, payload: dict, config: dict) -> str | None:
    """Determine which Slack channel to post to based on filter config."""
    rules = config.get("rules", [])

    for rule in rules:
        if rule["event"] != event:
            continue

        # Check action filter
        if "action" in rule and rule["action"] != action:
            continue

        # Check branch filter
        if "branch_pattern" in rule:
            ref = payload.get("ref", "")
            pr_base = payload.get("pull_request", {}).get("base", {}).get("ref", "")
            branch = ref.replace("refs/heads/", "") or pr_base
            pattern = rule["branch_pattern"]

            if pattern == "main" and branch != "main":
                continue
            if pattern == "feature/*" and not branch.startswith("feature/"):
                continue

        # Check if silent
        if rule.get("silent", False):
            return None

        return rule.get("channel")

    return None


async def post_to_slack(channel: str, message: str):
    """Post a message to a Slack channel."""
    if not SLACK_BOT_TOKEN:
        print(f"[STUB] Would post to #{channel}: {message}")
        return

    async with httpx.AsyncClient() as client:
        await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            json={"channel": channel, "text": message},
        )


@app.post("/webhooks/github")
async def handle_webhook(
    request: Request,
    x_github_event: str = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
):
    """Receive and process GitHub webhook events."""
    body = await request.body()

    # Verify signature
    if GITHUB_WEBHOOK_SECRET and x_hub_signature_256:
        if not verify_signature(body, x_hub_signature_256):
            raise HTTPException(status_code= 401, detail="Invalid signature")

    payload = await request.json()
    action = payload.get("action", "")

    # Load filter config
    config = load_filter_config()

    # Determine target channel
    channel = get_target_channel(x_github_event, action, payload, config)
    if channel is None:
        return {"status": "filtered", "event": x_github_event, "action": action}

    # Format message
    message = format_message(x_github_event, action, payload)
    if message is None:
        return {"status": "no_message", "event": x_github_event, "action": action}

    # Post to Slack
    await post_to_slack(channel, message)

    return {"status": "posted", "channel": channel, "event": x_github_event}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "mems26-github-webhook"}
