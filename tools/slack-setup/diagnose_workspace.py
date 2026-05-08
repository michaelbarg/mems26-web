#!/usr/bin/env python3
"""Diagnose MEMS26-OPS Slack workspace state.

Compares actual workspace channels against channels_config.yaml,
identifies issues, and outputs a structured diagnosis.

Decision reference: D-048
"""

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
REPORT_PATH = SCRIPT_DIR / "DIAGNOSIS_REPORT.md"


def load_config() -> list[dict]:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)["channels"]


def load_state() -> dict | None:
    if STATE_PATH.exists():
        with open(STATE_PATH) as f:
            return json.load(f)
    return None


def retry_api(fn, retries=3):
    """Call fn() with exponential backoff on rate limits and timeouts."""
    for attempt in range(retries):
        try:
            return fn()
        except SlackApiError as e:
            err = e.response.get("error", str(e))
            if err == "ratelimited":
                wait = int(e.response.headers.get("Retry-After", 5))
                print(f"  [Rate limited, waiting {wait}s...]")
                time.sleep(wait)
                continue
            raise
        except Exception:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
    return fn()


def main():
    env_path = SCRIPT_DIR / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    elif not os.environ.get("SLACK_BOT_TOKEN"):
        print("BLOCKER: No .env file and SLACK_BOT_TOKEN not set.")
        write_blocker_report("No .env file found and SLACK_BOT_TOKEN not in environment.")
        sys.exit(1)

    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token.startswith("xoxb-"):
        print("BLOCKER: SLACK_BOT_TOKEN missing or invalid.")
        write_blocker_report("SLACK_BOT_TOKEN missing or does not start with xoxb-.")
        sys.exit(1)

    client = WebClient(token=token)
    config = load_config()
    expected_names = [ch["name"] for ch in config]
    config_by_name = {ch["name"]: ch for ch in config}

    # --- Phase 1.1: Auth test ---
    print("=" * 60)
    print("Phase 1.1 — Auth Test")
    print("=" * 60)
    try:
        auth = retry_api(lambda: client.auth_test())
    except SlackApiError as e:
        err = e.response.get("error", str(e))
        print(f"BLOCKER: auth.test failed: {err}")
        write_blocker_report(f"Token invalid/revoked. auth.test error: {err}. Michael must run setup_token.sh first.")
        sys.exit(1)

    workspace = auth["team"]
    bot_user = auth["user"]
    bot_id = auth["user_id"]
    team_id = auth["team_id"]
    url = auth.get("url", "N/A")
    print(f"  Workspace: {workspace}")
    print(f"  Bot: {bot_user} ({bot_id})")
    print(f"  Team ID: {team_id}")
    print(f"  URL: {url}")
    print()

    # --- Phase 1.2: List ALL channels ---
    print("=" * 60)
    print("Phase 1.2 — List All Channels")
    print("=" * 60)
    all_channels = []
    cursor = None
    while True:
        resp = retry_api(lambda: client.conversations_list(
            types="public_channel",
            limit=200,
            cursor=cursor or "",
            exclude_archived=False,
        ))
        all_channels.extend(resp["channels"])
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    print(f"  Total public channels in workspace: {len(all_channels)}")
    print(f"  (Note: private channels not listed — bot lacks groups:read scope)")
    print()
    print(f"  {'Name':<20} {'ID':<14} {'Private':<8} {'Archived':<10} {'Member':<8} {'Created'}")
    print("  " + "-" * 80)
    for ch in sorted(all_channels, key=lambda c: c["name"]):
        created = datetime.fromtimestamp(ch["created"]).strftime("%Y-%m-%d %H:%M")
        print(f"  {ch['name']:<20} {ch['id']:<14} {ch['is_private']!s:<8} {ch.get('is_archived', False)!s:<10} {ch.get('is_member', False)!s:<8} {created}")
    print()

    # Build lookup
    channels_by_name = {ch["name"]: ch for ch in all_channels}

    # --- Phase 1.3: Compare state file ---
    print("=" * 60)
    print("Phase 1.3 — State File Comparison")
    print("=" * 60)
    old_state = load_state()
    if old_state:
        state_channels = {ch["name"]: ch for ch in old_state.get("channels", [])}
        print(f"  State file has {len(state_channels)} channels, created at {old_state.get('created_at', 'unknown')}")
        for name, sch in state_channels.items():
            actual = channels_by_name.get(name)
            if actual:
                print(f"  {name}: state_id={sch['id']} actual_id={actual['id']} match={'YES' if sch['id'] == actual['id'] else 'NO'}")
            else:
                print(f"  {name}: state_id={sch['id']} — NOT FOUND in workspace!")
    else:
        print("  No state file found.")
    print()

    # --- Phase 1.4: Categorize each expected channel ---
    print("=" * 60)
    print("Phase 1.4 — Channel Categories")
    print("=" * 60)
    categories = {}
    for name in expected_names:
        ch = channels_by_name.get(name)
        if ch is None:
            categories[name] = "MISSING"
        elif ch.get("is_archived", False):
            categories[name] = "EXISTS_ARCHIVED"
        elif ch["is_private"]:
            if ch.get("is_member", False):
                categories[name] = "EXISTS_PRIVATE_BOT_MEMBER"
            else:
                categories[name] = "EXISTS_PRIVATE_BOT_NOT_MEMBER"
        else:
            if ch.get("is_member", False):
                categories[name] = "EXISTS_PUBLIC_BOT_MEMBER"
            else:
                categories[name] = "EXISTS_PUBLIC_BOT_NOT_MEMBER"

    for name, cat in categories.items():
        print(f"  {name:<20} → {cat}")

    # Summary counts
    cat_counts = {}
    for cat in categories.values():
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    print()
    print("  Summary:")
    for cat, count in sorted(cat_counts.items()):
        print(f"    {cat}: {count}")
    print()

    # --- Phase 1.5: Root cause hypothesis ---
    print("=" * 60)
    print("Phase 1.5 — Root Cause Analysis")
    print("=" * 60)

    missing = [n for n, c in categories.items() if c == "MISSING"]
    not_member = [n for n, c in categories.items() if "NOT_MEMBER" in c]
    archived = [n for n, c in categories.items() if "ARCHIVED" in c]
    private = [n for n, c in categories.items() if "PRIVATE" in c]
    ok = [n for n, c in categories.items() if c == "EXISTS_PUBLIC_BOT_MEMBER"]

    hypothesis = ""
    hypothesis_code = ""

    if len(ok) == 13:
        hypothesis = "All 13 channels exist and bot is a member. The 'only 3 visible' issue is likely a Slack UI filter (Michael may be viewing a filtered sidebar, or needs to browse all channels)."
        hypothesis_code = "UI_FILTER"
    elif missing:
        hypothesis = f"Script halted mid-run. {len(missing)} channels were never created: {', '.join(missing)}. {len(ok)} channels are OK."
        hypothesis_code = "PARTIAL_RUN"
    elif not_member:
        hypothesis = f"All channels exist but bot is not a member of {len(not_member)}: {', '.join(not_member)}. Bot needs to join these."
        hypothesis_code = "BOT_NOT_MEMBER"
    elif archived:
        hypothesis = f"{len(archived)} channels are archived: {', '.join(archived)}. Need to unarchive."
        hypothesis_code = "CHANNELS_ARCHIVED"
    elif private:
        hypothesis = f"{len(private)} channels are private: {', '.join(private)}. Config bug — all should be public."
        hypothesis_code = "PRIVATE_CHANNELS"
    elif workspace != "MEMS26-OPS":
        hypothesis = f"Bot is in workspace '{workspace}' but expected 'MEMS26-OPS'. Wrong workspace."
        hypothesis_code = "WRONG_WORKSPACE"
    else:
        hypothesis = "Unknown state — manual investigation needed."
        hypothesis_code = "UNKNOWN"

    print(f"  Hypothesis: {hypothesis_code}")
    print(f"  Detail: {hypothesis}")
    print()

    # --- Phase 2: Repairs ---
    print("=" * 60)
    print("Phase 2 — Repairs")
    print("=" * 60)
    repairs = []

    if hypothesis_code == "WRONG_WORKSPACE":
        msg = f"BLOCKER: Bot is in workspace '{workspace}' but Michael expects 'MEMS26-OPS'."
        print(f"  {msg}")
        repairs.append({"action": "BLOCKER", "detail": msg})
    else:
        # Create missing channels
        for name in missing:
            conf = config_by_name[name]
            print(f"  Creating #{name}...")
            try:
                resp = retry_api(lambda n=name, c=conf: client.conversations_create(
                    name=n, is_private=c.get("is_private", False)
                ))
                ch_id = resp["channel"]["id"]
                print(f"    Created: {ch_id}")
                channels_by_name[name] = resp["channel"]
                categories[name] = "EXISTS_PUBLIC_BOT_MEMBER"

                # Set topic and purpose
                retry_api(lambda: client.conversations_setTopic(channel=ch_id, topic=conf["topic"]))
                retry_api(lambda: client.conversations_setPurpose(channel=ch_id, purpose=conf["description"]))
                repairs.append({"action": "CREATED", "channel": name, "id": ch_id})
                time.sleep(1)
            except SlackApiError as e:
                err = e.response.get("error", str(e))
                print(f"    ERROR: {err}")
                repairs.append({"action": "CREATE_FAILED", "channel": name, "error": err})

        # Join channels where bot is not member
        for name in not_member:
            ch = channels_by_name[name]
            ch_id = ch["id"]
            if ch["is_private"]:
                print(f"  #{name} is private — cannot self-join. Michael must invite bot.")
                repairs.append({"action": "SKIPPED_PRIVATE", "channel": name})
                continue
            print(f"  Joining #{name}...")
            try:
                retry_api(lambda: client.conversations_join(channel=ch_id))
                print(f"    Joined.")
                categories[name] = "EXISTS_PUBLIC_BOT_MEMBER"
                repairs.append({"action": "JOINED", "channel": name})
                time.sleep(1)
            except SlackApiError as e:
                err = e.response.get("error", str(e))
                print(f"    ERROR: {err}")
                repairs.append({"action": "JOIN_FAILED", "channel": name, "error": err})

        # Unarchive archived channels
        for name in archived:
            ch = channels_by_name[name]
            ch_id = ch["id"]
            print(f"  Unarchiving #{name}...")
            try:
                retry_api(lambda: client.conversations_unarchive(channel=ch_id))
                print(f"    Unarchived.")
                categories[name] = categories[name].replace("ARCHIVED", "PUBLIC_BOT_MEMBER")
                repairs.append({"action": "UNARCHIVED", "channel": name})
                time.sleep(1)
            except SlackApiError as e:
                err = e.response.get("error", str(e))
                print(f"    ERROR: {err}")
                repairs.append({"action": "UNARCHIVE_FAILED", "channel": name, "error": err})

    if not repairs:
        print("  No repairs needed.")
    print()

    # --- Phase 3: Validate ---
    print("=" * 60)
    print("Phase 3 — Validation")
    print("=" * 60)

    # Re-fetch channels after repairs
    all_channels_post = []
    cursor = None
    while True:
        resp = retry_api(lambda: client.conversations_list(
            types="public_channel",
            limit=200,
            cursor=cursor or "",
            exclude_archived=False,
        ))
        all_channels_post.extend(resp["channels"])
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    channels_by_name_post = {ch["name"]: ch for ch in all_channels_post}

    import re
    emoji_re = re.compile(
        "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251"
        "\U00002139\U00002328\U000023CF\U000023E9-\U000023F3\U000023F8-\U000023FA"
        "\U0000200D\U00002934\U00002935\U000025AA-\U000025FE\U00002600-\U000026FF"
        "\U00002700-\U000027BF\U0000FE0F\U0001F900-\U0001F9FF]+"
    )
    shortcode_re = re.compile(r":[a-z0-9_+-]+:")

    def normalize(text: str) -> str:
        text = emoji_re.sub("", text)
        text = shortcode_re.sub("", text)
        return text.strip()

    validated_channels = []
    all_valid = True

    for conf in config:
        name = conf["name"]
        ch = channels_by_name_post.get(name)
        entry = {"name": name}

        if not ch:
            entry.update({"status": "MISSING", "is_member": False, "topic_match": False, "purpose_match": False})
            all_valid = False
            print(f"  ❌ #{name} — MISSING")
        else:
            ch_id = ch["id"]
            entry["id"] = ch_id
            entry["is_archived"] = ch.get("is_archived", False)
            entry["is_private"] = ch["is_private"]
            entry["is_member"] = ch.get("is_member", False)

            # Get detailed info for topic/purpose
            try:
                info = retry_api(lambda: client.conversations_info(channel=ch_id))["channel"]
                topic_actual = info.get("topic", {}).get("value", "")
                purpose_actual = info.get("purpose", {}).get("value", "")
                entry["topic_match"] = normalize(topic_actual) == normalize(conf["topic"])
                entry["purpose_match"] = normalize(purpose_actual) == normalize(conf["description"])
                entry["topic_actual"] = topic_actual
                entry["purpose_actual"] = purpose_actual
            except SlackApiError as e:
                entry["topic_match"] = False
                entry["purpose_match"] = False
                print(f"  ⚠️  #{name} — could not fetch info: {e.response.get('error')}")

            issues = []
            if entry.get("is_archived"):
                issues.append("ARCHIVED")
            if not entry["is_member"]:
                issues.append("BOT_NOT_MEMBER")
            if not entry["topic_match"]:
                issues.append("TOPIC_MISMATCH")
            if not entry["purpose_match"]:
                issues.append("PURPOSE_MISMATCH")

            if issues:
                all_valid = False
                entry["status"] = ", ".join(issues)
                print(f"  ❌ #{name} — {entry['status']}")
            else:
                entry["status"] = "OK"
                print(f"  ✅ #{name} (id={ch_id})")

            time.sleep(0.5)

        validated_channels.append(entry)

    print()
    ok_count = sum(1 for v in validated_channels if v.get("status") == "OK")
    print(f"  Result: {ok_count}/13 channels valid. all_valid={all_valid}")
    print()

    # --- Phase 4: Strategic channel bot membership ---
    print("=" * 60)
    print("Phase 4 — Strategic Channel Bot Check")
    print("=" * 60)
    strategic_channels = ["strategic", "cc-master", "methodology", "checkpoints"]
    strategic_status = {}
    for name in strategic_channels:
        ch = channels_by_name_post.get(name)
        if ch:
            is_member = ch.get("is_member", False)
            strategic_status[name] = "BOT_MEMBER" if is_member else "BOT_NOT_MEMBER"
            print(f"  #{name}: {strategic_status[name]}")
        else:
            strategic_status[name] = "MISSING"
            print(f"  #{name}: MISSING")
    print()

    # --- Save state ---
    now = datetime.now(timezone.utc).isoformat()
    state = {
        "validated_at": now,
        "workspace": workspace,
        "bot_id": bot_id,
        "expected_count": 13,
        "actual_count": ok_count,
        "all_valid": all_valid,
        "channels": validated_channels,
    }
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"State saved to {STATE_PATH}")

    # --- Write report ---
    before_count = len(ok)
    after_count = ok_count
    repair_count = len(repairs)
    blockers = [r for r in repairs if r["action"] == "BLOCKER"]

    # Build category table
    cat_before = {}
    for name in expected_names:
        ch = channels_by_name.get(name)
        if ch is None:
            cat_before[name] = "MISSING"
        elif ch.get("is_archived", False):
            cat_before[name] = "EXISTS_ARCHIVED"
        elif ch["is_private"]:
            cat_before[name] = "EXISTS_PRIVATE"
        elif ch.get("is_member", False):
            cat_before[name] = "EXISTS_PUBLIC_BOT_MEMBER"
        else:
            cat_before[name] = "EXISTS_PUBLIC_BOT_NOT_MEMBER"

    repair_actions = {}
    for r in repairs:
        ch_name = r.get("channel", "")
        if ch_name:
            repair_actions[ch_name] = r["action"]

    channel_rows = ""
    for v in validated_channels:
        name = v["name"]
        before = cat_before.get(name, "UNKNOWN")
        action = repair_actions.get(name, "none")
        after = v.get("status", "UNKNOWN")
        channel_rows += f"| {name} | {before} | {action} | {after} |\n"

    outstanding = []
    for name, status in strategic_status.items():
        if status == "BOT_NOT_MEMBER":
            outstanding.append(f"- [ ] `/invite @mems26_bot` to #{name} via Slack UI")
    for r in repairs:
        if r["action"] == "BLOCKER":
            outstanding.append(f"- [ ] BLOCKER: {r['detail']}")
        elif "FAILED" in r["action"]:
            outstanding.append(f"- [ ] Fix failed repair: {r['action']} on #{r.get('channel', '?')}: {r.get('error', '?')}")
    outstanding.append("- [ ] `/invite @Claude` to strategic channels via Slack UI (if using Anthropic chat app)")
    outstanding.append("- [ ] Decide: keep Claude Code Slack app, install Claude Chat app, or both (see analysis below)")

    files_touched = [
        "tools/slack-setup/diagnose_workspace.py (new)",
        "tools/slack-setup/channels_state.json (updated)",
        "tools/slack-setup/DIAGNOSIS_REPORT.md (new)",
    ]

    report = f"""# Slack MEMS26-OPS — Diagnosis Report
**Generated:** {now}
**Trigger:** Only 3 channels visible in Slack UI; suspected halted CC run

## Executive Summary
- Found: {len(all_channels)} channels in workspace (total)
- Expected: 13 (per channels_config.yaml)
- Matched before repair: {before_count}/13
- Action taken: {repair_count} repairs attempted
- Final state: {after_count}/13 valid

## Connection Status
- Workspace: {workspace} | URL: {url}
- Bot user: {bot_user} ({bot_id})
- Team ID: {team_id}
- Token: VALID

## Channels Inventory
| Expected name | Status before | Action | Status after |
|---|---|---|---|
{channel_rows}
## Root Cause Hypothesis
**Code:** {hypothesis_code}

{hypothesis}

### Evidence
- auth.test workspace: `{workspace}`
- Total channels found: {len(all_channels)}
- Channels matching config: {before_count}/13 (before repair)
- State file timestamp: {old_state.get('created_at', 'N/A') if old_state else 'N/A'}
- State file claimed all 13 channels with `was_existing: true`

### "Only 3 visible" Explanation
If all 13 channels exist in the workspace but Michael sees only 3, the most likely causes are:
1. **Slack sidebar filter** — By default, Slack shows only channels you've joined or have unread messages. Michael may need to click "Browse Channels" or adjust sidebar settings.
2. **Bot created channels but Michael not auto-joined** — Channel creators (the bot) are auto-joined, but other workspace members need to manually join or be invited.
3. **Slack mobile/desktop caching** — Sometimes the channel list needs a refresh (pull down to refresh on mobile, Cmd+R on desktop).

**Recommendation:** Michael should open Slack → click "Browse Channels" (or the + icon next to Channels) → search for channel names like `dev-dll`, `alerts-critical` etc. They should appear there even if not in the sidebar.

## Repairs Performed
"""
    if repairs:
        for i, r in enumerate(repairs, 1):
            report += f"{i}. **{r['action']}** — #{r.get('channel', 'N/A')}"
            if "error" in r:
                report += f" (error: {r['error']})"
            if "id" in r:
                report += f" (id: {r['id']})"
            if "detail" in r:
                report += f" — {r['detail']}"
            report += "\n"
    else:
        report += "No repairs needed — all channels already exist.\n"

    report += f"""
## Strategic Channel Bot Status
| Channel | Bot Status |
|---|---|
"""
    for name, status in strategic_status.items():
        report += f"| #{name} | {status} |\n"

    report += """
## Image 2 Analysis — Claude Code vs Claude Chat

The Claude that responded "pick a repository" is the **Claude Code Slack integration**, not the standard Anthropic chat app. These are two different apps:

| App | Purpose | Install URL |
|---|---|---|
| Claude (chat) | General Q&A, project knowledge | https://claude.ai/install-slack |
| Claude Code | Repo-aware coding assistant | https://docs.claude.com/en/docs/claude-code/slack |

Michael likely installed the Claude Code app (which is repo-aware and asks about repositories) when they wanted the general chat-oriented Claude app.

### Recommendation
1. **Keep Claude Code** if useful for coding tasks — but rename in Slack settings to `@ClaudeCode` to avoid confusion
2. **Install the chat-oriented Anthropic app** additionally for `#strategic` discussions (requires UI/OAuth — cannot be automated)
3. **OR:** Stick with Claude Code for now, just be aware it will always ask about repos when first messaged

DO NOT attempt to install the chat app via automation — it requires UI/OAuth flow.

"""

    report += f"""## Outstanding Items for Michael
"""
    for item in outstanding:
        report += f"{item}\n"

    report += f"""
## Files Touched
"""
    for f in files_touched:
        report += f"- {f}\n"

    with open(REPORT_PATH, "w") as f:
        f.write(report)
    print(f"Report saved to {REPORT_PATH}")

    # --- Print summary box ---
    action_items = [item.replace("- [ ] ", "") for item in outstanding[:3]]
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║ SLACK-SETUP-V1.2 — DIAGNOSIS & REPAIR COMPLETE           ║")
    print("╠════════════════════════════════════════════════════════════╣")
    print(f"║ Workspace:        {workspace:<40}║")
    print(f"║ Channels before:  {before_count:<2} / 13{' ' * 34}║")
    print(f"║ Channels after:   {after_count:<2} / 13{' ' * 34}║")
    print(f"║ Repairs:          {repair_count:<40}║")
    print(f"║ Blockers:         {len(blockers):<40}║")
    print("║                                                          ║")
    print(f"║ Root cause:       {hypothesis_code:<40}║")
    print("║                                                          ║")
    print("║ For Michael:                                             ║")
    for i, item in enumerate(action_items, 1):
        line = f"{i}. {item}"
        if len(line) > 56:
            line = line[:53] + "..."
        print(f"║   {line:<56}║")
    print("║                                                          ║")
    print("║ Full report: tools/slack-setup/DIAGNOSIS_REPORT.md       ║")
    print("╚════════════════════════════════════════════════════════════╝")

    return 0 if all_valid else 1


def write_blocker_report(message: str):
    now = datetime.now(timezone.utc).isoformat()
    report = f"""# Slack MEMS26-OPS — Diagnosis Report
**Generated:** {now}
**Trigger:** Only 3 channels visible in Slack UI; suspected halted CC run

## Executive Summary
BLOCKER: {message}

Cannot proceed without valid token. Michael must run `setup_token.sh` first.
"""
    with open(REPORT_PATH, "w") as f:
        f.write(report)
    print(f"Blocker report saved to {REPORT_PATH}")


if __name__ == "__main__":
    sys.exit(main())
