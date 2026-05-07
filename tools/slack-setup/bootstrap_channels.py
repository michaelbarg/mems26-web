#!/usr/bin/env python3
"""Bootstrap 13 Slack channels for MEMS26-OPS workspace.

Decision: D-048 (MEMS26_FIRST.md V2 — Slack Workspace)

Usage:
    python bootstrap_channels.py              # full run
    python bootstrap_channels.py --dry-run    # show what would happen
    python bootstrap_channels.py --force      # skip workspace name check
    python bootstrap_channels.py --validate   # only validate existing channels
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "channels_config.yaml"
STATE_PATH = SCRIPT_DIR / "channels_state.json"
EXPECTED_WORKSPACE = "MEMS26-OPS"


def load_config() -> list[dict]:
    with open(CONFIG_PATH) as f:
        data = yaml.safe_load(f)
    return data["channels"]


def preflight(client: WebClient, force: bool) -> dict:
    """Verify token and workspace. Returns auth info."""
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token or not token.startswith("xoxb-"):
        print("ERROR: SLACK_BOT_TOKEN missing or invalid.")
        print("  Export it: export SLACK_BOT_TOKEN=xoxb-...")
        print("  Get it from: https://api.slack.com/apps → OAuth & Permissions")
        sys.exit(1)

    try:
        resp = client.auth_test()
    except SlackApiError as e:
        err = e.response.get("error", str(e))
        if err in ("not_authed", "invalid_auth"):
            print(f"ERROR: Token invalid ({err}).")
            print("  Re-export SLACK_BOT_TOKEN from Slack App OAuth page.")
        else:
            print(f"ERROR: auth.test failed: {err}")
        sys.exit(1)

    bot_name = resp["user"]
    team_name = resp["team"]
    print(f"Connected as bot '{bot_name}' to workspace '{team_name}'")

    if team_name != EXPECTED_WORKSPACE and not force:
        print(f"\nWARNING: Expected workspace '{EXPECTED_WORKSPACE}', got '{team_name}'.")
        print("  Re-run with --force to proceed anyway.")
        sys.exit(1)

    return {"bot_user": bot_name, "team": team_name}


def get_existing_channels(client: WebClient) -> dict[str, str]:
    """Return {name: id} for all public channels in workspace."""
    channels = {}
    cursor = None
    while True:
        resp = client.conversations_list(
            types="public_channel",
            limit=1000,
            cursor=cursor or "",
        )
        for ch in resp["channels"]:
            channels[ch["name"]] = ch["id"]
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    return channels


def create_channels(client: WebClient, config: list[dict], dry_run: bool) -> list[dict]:
    """Create channels from config. Returns state records."""
    existing = get_existing_channels(client)
    results = []

    for ch_conf in config:
        name = ch_conf["name"]
        topic = ch_conf["topic"]
        description = ch_conf["description"]

        if name in existing:
            ch_id = existing[name]
            print(f"[SKIP] #{name} exists (id={ch_id})")
            was_existing = True
        elif dry_run:
            ch_id = "DRY-RUN"
            print(f"[DRY-RUN] Would create #{name}")
            was_existing = False
        else:
            try:
                resp = client.conversations_create(name=name, is_private=ch_conf.get("is_private", False))
                ch_id = resp["channel"]["id"]
                print(f"[CREATE] #{name} (id={ch_id})")
                was_existing = False
            except SlackApiError as e:
                err = e.response.get("error", str(e))
                if err == "name_taken":
                    # Treat as existing — idempotent
                    existing = get_existing_channels(client)
                    ch_id = existing.get(name, "UNKNOWN")
                    print(f"[SKIP] #{name} name_taken, fetched id={ch_id}")
                    was_existing = True
                elif err == "missing_scope":
                    detail = e.response.get("needed", err)
                    print(f"ERROR: Bot missing scope '{detail}'.")
                    print("  Add via api.slack.com/apps → OAuth & Permissions → Re-install.")
                    save_state({"error": err, "partial": results})
                    sys.exit(1)
                elif err == "ratelimited":
                    retry_after = int(e.response.headers.get("Retry-After", 5))
                    print(f"[RATE-LIMITED] Sleeping {retry_after}s...")
                    time.sleep(retry_after)
                    try:
                        resp = client.conversations_create(name=name, is_private=ch_conf.get("is_private", False))
                        ch_id = resp["channel"]["id"]
                        print(f"[CREATE] #{name} (id={ch_id}) (retry)")
                        was_existing = False
                    except SlackApiError:
                        print(f"ERROR: Rate-limited twice on #{name}. Saving partial state.")
                        save_state({"error": "ratelimited_twice", "partial": results})
                        sys.exit(1)
                else:
                    print(f"ERROR: Unexpected error creating #{name}: {err}")
                    save_state({"error": err, "partial": results})
                    raise

        # Set topic and purpose (even for existing channels, to ensure they match config)
        if not dry_run and ch_id != "DRY-RUN":
            try:
                client.conversations_setTopic(channel=ch_id, topic=topic)
            except SlackApiError as e:
                err = e.response.get("error", str(e))
                if err == "ratelimited":
                    retry_after = int(e.response.headers.get("Retry-After", 5))
                    time.sleep(retry_after)
                    client.conversations_setTopic(channel=ch_id, topic=topic)
                elif err not in ("not_in_channel",):
                    print(f"  WARNING: Could not set topic for #{name}: {err}")

            try:
                client.conversations_setPurpose(channel=ch_id, purpose=description)
            except SlackApiError as e:
                err = e.response.get("error", str(e))
                if err == "ratelimited":
                    retry_after = int(e.response.headers.get("Retry-After", 5))
                    time.sleep(retry_after)
                    client.conversations_setPurpose(channel=ch_id, purpose=description)
                elif err not in ("not_in_channel",):
                    print(f"  WARNING: Could not set purpose for #{name}: {err}")

        results.append({
            "name": name,
            "id": ch_id,
            "topic": topic,
            "purpose": description,
            "was_existing": was_existing,
        })

        time.sleep(1)  # Rate limit safety

    return results


def validate_channels(client: WebClient, config: list[dict]) -> bool:
    """Validate all 13 channels exist with correct topic and purpose."""
    existing = get_existing_channels(client)
    all_ok = True

    # Slack converts unicode emoji to shortcodes in API responses,
    # so we normalize by stripping emoji for comparison purposes.
    import re
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251"
        "\U00002139\U00002328\U000023CF\U000023E9-\U000023F3\U000023F8-\U000023FA"
        "\U0000200D\U00002934\U00002935\U000025AA-\U000025FE\U00002600-\U000026FF"
        "\U00002700-\U000027BF\U0000FE0F\U0001F900-\U0001F9FF]+"
    )
    shortcode_pattern = re.compile(r":[a-z0-9_+-]+:")

    def normalize(text: str) -> str:
        """Strip emoji (unicode and shortcodes) for comparison."""
        text = emoji_pattern.sub("", text)
        text = shortcode_pattern.sub("", text)
        return text.strip()

    for ch_conf in config:
        name = ch_conf["name"]
        if name not in existing:
            print(f"❌ #{name} — NOT FOUND")
            all_ok = False
            continue

        ch_id = existing[name]
        try:
            info = client.conversations_info(channel=ch_id)["channel"]
        except SlackApiError as e:
            print(f"❌ #{name} — could not fetch info: {e.response.get('error')}")
            all_ok = False
            continue

        topic_actual = info.get("topic", {}).get("value", "")
        purpose_actual = info.get("purpose", {}).get("value", "")
        mismatches = []

        if normalize(topic_actual) != normalize(ch_conf["topic"]):
            mismatches.append(f"topic: got '{topic_actual}', expected '{ch_conf['topic']}'")
        if normalize(purpose_actual) != normalize(ch_conf["description"]):
            mismatches.append(f"purpose: got '{purpose_actual}', expected '{ch_conf['description']}'")

        if mismatches:
            print(f"❌ #{name} — {'; '.join(mismatches)}")
            all_ok = False
        else:
            print(f"✅ #{name} (id={ch_id})")

    if all_ok:
        print(f"\n✅ All {len(config)} channels validated")
    else:
        print(f"\n❌ Mismatch detected — see details above")

    return all_ok


def save_state(data: dict):
    with open(STATE_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"State saved to {STATE_PATH}")


def print_summary(results: list[dict]):
    print(f"\n{'Name':<20} {'ID':<14} {'Status'}")
    print("-" * 50)
    for r in results:
        status = "existed" if r["was_existing"] else "created"
        if r["id"] == "DRY-RUN":
            status = "dry-run"
        print(f"{r['name']:<20} {r['id']:<14} {status}")


def main():
    parser = argparse.ArgumentParser(description="Bootstrap MEMS26-OPS Slack channels")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen, no API writes")
    parser.add_argument("--force", action="store_true", help="Skip workspace name confirmation")
    parser.add_argument("--validate", action="store_true", help="Only validate existing channels")
    args = parser.parse_args()

    # Load .env from script directory if present
    env_path = SCRIPT_DIR / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    config = load_config()
    print(f"Loaded {len(config)} channels from config\n")

    client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN", ""))
    auth_info = preflight(client, args.force)

    if args.validate:
        ok = validate_channels(client, config)
        sys.exit(0 if ok else 1)

    results = create_channels(client, config, args.dry_run)
    print_summary(results)

    if not args.dry_run:
        # Validation pass
        print("\n--- Validation ---")
        validate_channels(client, config)

        # Save state
        state = {
            "workspace": auth_info["team"],
            "bot_user": auth_info["bot_user"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "channels": results,
        }
        save_state(state)


if __name__ == "__main__":
    main()
