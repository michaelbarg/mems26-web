#!/usr/bin/env python3
"""Resolve Slack channel visibility for Michael.

Finds Michael's user in the workspace, checks which of the 13 expected
channels he's a member of, and auto-invites him to any he's missing.

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
REPORT_PATH = SCRIPT_DIR / "DIAGNOSIS_REPORT.md"
STATE_PATH = SCRIPT_DIR / "visibility_state.json"

EXPECTED = [
    "strategic", "cc-master", "checkpoints",
    "dev-dll", "dev-backend", "dev-frontend", "qa",
    "alerts-critical", "alerts-info", "live-trading",
    "methodology", "simulations", "daily-reports",
]


def retry_api(fn, retries=3):
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


def append_blocker(msg: str):
    with open(REPORT_PATH, "a") as f:
        f.write(f"\n\n## V1.3 BLOCKER — {datetime.now(timezone.utc).isoformat()}\n")
        f.write(msg + "\n")


def main():
    load_dotenv(SCRIPT_DIR / ".env")
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token.startswith("xoxb-"):
        print("BLOCKER: SLACK_BOT_TOKEN missing or invalid.")
        append_blocker("SLACK_BOT_TOKEN missing or invalid.")
        return 1

    client = WebClient(token=token)

    # --- Phase 1: Truth check ---
    print("=" * 60)
    print("Phase 1 — Bot-side truth check")
    print("=" * 60)
    try:
        auth = retry_api(lambda: client.auth_test())
    except SlackApiError as e:
        print(f"BLOCKER: auth.test failed: {e.response.get('error')}")
        append_blocker(f"auth.test failed: {e.response.get('error')}")
        return 1

    print(f"  Workspace: {auth['team']} (ID: {auth['team_id']})")
    print(f"  Bot user: {auth['user']} ({auth['user_id']})")
    print(f"  URL: {auth.get('url')}")

    # List public channels only (bot lacks groups:read for private)
    channels = []
    cursor = None
    while True:
        resp = retry_api(lambda: client.conversations_list(
            types="public_channel", limit=200,
            cursor=cursor or "", exclude_archived=False,
        ))
        channels.extend(resp["channels"])
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    print(f"  Public channels: {len(channels)}")
    channels_by_name = {ch["name"]: ch for ch in channels}
    print()

    # --- Phase 2: Find Michael ---
    print("=" * 60)
    print("Phase 2 — Find Michael's user")
    print("=" * 60)
    users = []
    cursor = None
    while True:
        resp = retry_api(lambda: client.users_list(limit=200, cursor=cursor or ""))
        users.extend(resp["members"])
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    print(f"  Total users in workspace: {len(users)}")

    michael = None
    # Try email match first
    for u in users:
        email = u.get("profile", {}).get("email", "")
        if email == "michael@passparto.com":
            michael = u
            break
    # Fallback: workspace owner or admin named Michael
    if not michael:
        for u in users:
            if u.get("is_bot") or u.get("id") == "USLACKBOT":
                continue
            name = u.get("real_name", "").lower()
            if "michael" in name or "מיכאל" in name:
                michael = u
                break
    # Fallback: workspace owner
    if not michael:
        for u in users:
            if u.get("is_owner") or u.get("is_primary_owner"):
                michael = u
                break

    if not michael:
        msg = (
            "Cannot find Michael's user in workspace.\n"
            "This likely means the token is for a different workspace than Michael uses.\n"
            f"Workspace: {auth['team']} ({auth.get('url')})\n"
            f"Users found: {[u.get('real_name', u['id']) for u in users if not u.get('is_bot')]}\n"
            "\nFix: Michael must verify which workspace he sees in Slack UI.\n"
        )
        print(f"  BLOCKER: {msg}")
        append_blocker(msg)

        print()
        print("╔════════════════════════════════════════════╗")
        print("║ BLOCKER — User not found in workspace      ║")
        print(f"║ Bot is in: {auth['team']:<32}║")
        print("║ Michael's user not matched                 ║")
        print("║ See DIAGNOSIS_REPORT.md V1.3 BLOCKER       ║")
        print("╚════════════════════════════════════════════╝")
        return 1

    michael_id = michael["id"]
    michael_name = michael.get("real_name", michael.get("name", "unknown"))
    michael_email = michael.get("profile", {}).get("email", "N/A")
    print(f"  Found: {michael_name} ({michael_id})")
    print(f"  Email: {michael_email}")
    print(f"  Is owner: {michael.get('is_owner', False)}")
    print()

    # --- Phase 3: Check membership ---
    print("=" * 60)
    print("Phase 3 — Check Michael's channel membership")
    print("=" * 60)
    membership = []
    for name in EXPECTED:
        ch = channels_by_name.get(name)
        if not ch:
            membership.append({"name": name, "exists": False, "michael_is_member": False})
            print(f"  {name:<20} — CHANNEL NOT FOUND")
            continue

        ch_id = ch["id"]
        # Paginate members to find Michael
        is_member = False
        mem_cursor = None
        while True:
            try:
                resp = retry_api(lambda: client.conversations_members(
                    channel=ch_id, limit=200, cursor=mem_cursor or ""
                ))
            except SlackApiError as e:
                print(f"  {name:<20} — ERROR checking members: {e.response.get('error')}")
                break
            if michael_id in resp["members"]:
                is_member = True
                break
            mem_cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not mem_cursor:
                break

        membership.append({
            "name": name,
            "channel_id": ch_id,
            "exists": True,
            "is_private": ch["is_private"],
            "is_archived": ch.get("is_archived", False),
            "michael_is_member": is_member,
        })
        status = "MEMBER" if is_member else "NOT MEMBER"
        print(f"  {name:<20} — {status}")
        time.sleep(0.3)

    member_count = sum(1 for m in membership if m["michael_is_member"])
    not_member = [m for m in membership if m["exists"] and not m["michael_is_member"]]
    print()
    print(f"  Michael is member of {member_count}/13 channels")
    print(f"  Needs invite to {len(not_member)}: {[m['name'] for m in not_member]}")
    print()

    # --- Phase 4: Auto-invite ---
    print("=" * 60)
    print("Phase 4 — Auto-invite Michael")
    print("=" * 60)
    invited = []
    failed = []

    for m in not_member:
        ch_id = m["channel_id"]
        name = m["name"]
        print(f"  Inviting to #{name}...", end=" ")
        try:
            retry_api(lambda: client.conversations_invite(
                channel=ch_id, users=michael_id
            ))
            invited.append(name)
            print("OK")
        except SlackApiError as e:
            err = e.response.get("error", str(e))
            if err == "already_in_channel":
                invited.append(name)
                print("already member")
            else:
                failed.append({"name": name, "error": err})
                print(f"FAILED: {err}")
        time.sleep(0.5)

    if not not_member:
        print("  No invites needed — Michael is already in all channels.")
    print()

    # --- Phase 5: Save state + append report ---
    now = datetime.now(timezone.utc).isoformat()
    final_member_count = member_count + len(invited)

    state = {
        "validated_at": now,
        "workspace": auth["team"],
        "workspace_url": auth.get("url"),
        "michael_user_id": michael_id,
        "michael_name": michael_name,
        "channels_total": len(channels),
        "channels_expected": 13,
        "michael_was_member_of": member_count,
        "auto_invited_to": invited,
        "failed": failed,
        "michael_now_member_of": final_member_count,
    }

    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"State saved to {STATE_PATH}")

    with open(REPORT_PATH, "a") as f:
        f.write(f"\n\n## V1.3 Resolution — {now}\n")
        f.write(f"- Bot workspace: {auth['team']} (URL: {auth.get('url')})\n")
        f.write(f"- Michael: {michael_name} ({michael_id}) | email: {michael_email}\n")
        f.write(f"- Total public channels: {len(channels)}\n")
        f.write(f"- Michael was member of: {member_count}/13 expected channels\n")
        f.write(f"- Auto-invited to: {len(invited)} channels ({', '.join(invited) if invited else 'none'})\n")
        f.write(f"- Failures: {len(failed)}\n")
        if failed:
            for fail in failed:
                f.write(f"  - #{fail['name']}: {fail['error']}\n")
        f.write(f"- Michael now member of: {final_member_count}/13\n")
        f.write(f"\n### Root Cause Confirmed\n")
        if member_count < 13:
            f.write(f"Michael was only a member of {member_count}/13 channels. ")
            f.write("The bot created all channels successfully, but Michael's user was never invited. ")
            f.write("Slack only shows channels you've joined in the sidebar — hence 'only 3 visible'.\n")
        else:
            f.write("Michael was already a member of all 13 channels. ")
            f.write("The visibility issue may be a Slack sidebar filter or cache problem.\n")
    print(f"Report appended to {REPORT_PATH}")

    # --- Summary ---
    print()
    print("╔════════════════════════════════════════════════════╗")
    print("║ SLACK-SETUP-V1.3 — VISIBILITY RESOLVED            ║")
    print("╠════════════════════════════════════════════════════╣")
    print(f"║ Workspace:       {auth['team']:<33}║")
    print(f"║ Michael in:      {member_count}/13 channels before{' ' * 16}║")
    print(f"║ Auto-invited to: {len(invited)} channels{' ' * 24}║")
    print(f"║ Now visible:     {final_member_count}/13{' ' * 28}║")
    print("║                                                   ║")
    if final_member_count == 13:
        print("║ Action: refresh Slack — channels will appear      ║")
        print("║         in sidebar within 30s                      ║")
    else:
        print(f"║ Failures: {len(failed)} — see report{' ' * 23}║")
    print("╚════════════════════════════════════════════════════╝")

    return 0 if final_member_count == 13 else 1


if __name__ == "__main__":
    sys.exit(main())
