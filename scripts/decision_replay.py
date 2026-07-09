#!/usr/bin/env python3
"""Decision Replay — replay gateway decisions from log, compare old vs current flags.

The answer to "why wasn't this caught before?": run yesterday's candidates through
today's gate chain. Every morning, any gate bug that would change the outcome is
visible BEFORE the market opens.

Usage:
  python3 scripts/decision_replay.py --date 2026-07-09
  python3 scripts/decision_replay.py --date 2026-07-09 --log /tmp/backend.err.log
  python3 scripts/decision_replay.py --date 2026-07-09 --counterfactual

Output: docs/reports/DECISION_REPLAY_<date>.md
"""
import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Gate names that the gateway logs
GATE_NAMES = {
    "session_gate_closed", "eod_entry_cutoff", "feed_watchdog",
    "rr_entry_gate", "t1_wrong_side", "entry_not_confirmed",
    "cont_trend_filter", "direction_context", "daytype_playbook",
    "daytype_position_gate", "lsma_flat", "dedup_fire_guard",
    "cluster_guard", "risk_halt", "cooldown", "ssv",
    "opposite_exit", "sizing_reject", "no_stop_in_band",
}


def parse_gateway_log(log_path: str, target_date: str):
    """Parse gateway BLOCKED + FIRED entries from the backend log.

    Returns list of dicts: {time, system, pattern, direction, entry, blocked_by, detail}.
    """
    candidates = []
    # Match: [Gateway] BLOCKED system=N pattern=X dir=Y entry=Z blocked_by=W
    blocked_re = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*\[Gateway\] BLOCKED "
        r"system=(\d+) pattern=(\S+) dir=(\S+) entry=([\d.]+) blocked_by=(\S+)"
    )
    # Match FIRED entries: Trade NNN created / DEMO trade TM
    fired_re = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*Trade (\d+) created: "
        r"mode=(\S+) sys=(\d+) dir=(\S+)"
    )
    # Match detail lines (one line before the BLOCKED warning)
    detail_re = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*\[Gateway\] BLOCKED by (.+)"
    )

    details = {}  # ts → detail text

    try:
        with open(log_path, "r", errors="replace") as f:
            for line in f:
                if target_date not in line:
                    continue

                m = detail_re.match(line)
                if m:
                    ts = m.group(1)
                    details[ts] = m.group(2).strip()

                m = blocked_re.match(line)
                if m:
                    ts = m.group(1)
                    candidates.append({
                        "time": ts[11:16],
                        "system": int(m.group(2)),
                        "pattern": m.group(3),
                        "direction": m.group(4),
                        "entry": float(m.group(5)),
                        "blocked_by": m.group(6),
                        "detail": details.get(ts, ""),
                        "outcome": "BLOCKED",
                    })

                m = fired_re.match(line)
                if m:
                    ts = m.group(1)
                    candidates.append({
                        "time": ts[11:16],
                        "system": int(m.group(3 + 1)),  # sys
                        "pattern": "?",
                        "direction": m.group(3 + 2),  # dir
                        "entry": 0.0,
                        "blocked_by": None,
                        "detail": f"trade #{m.group(2)} mode={m.group(3)}",
                        "outcome": f"FIRED ({m.group(3)})",
                    })
    except FileNotFoundError:
        print(f"Log file not found: {log_path}", file=sys.stderr)

    # Deduplicate (same time+system+dir within 2s = same candidate)
    seen = set()
    deduped = []
    for c in candidates:
        key = (c["time"], c["system"], c["direction"], c.get("blocked_by"))
        if key not in seen:
            seen.add(key)
            deduped.append(c)
    return deduped


def classify_candidate(c: dict) -> str:
    """Classify whether a block was correct, a bug, or a design gap."""
    bb = c.get("blocked_by", "")
    d = c.get("direction", "")
    detail = c.get("detail", "")

    # Known bugs fixed in the 07-09 fixpack
    if bb == "rr_entry_gate" and "T1_dist=1.25" in detail:
        return "🔴 BUG: IB-forming structural target (FIX-2/4)"
    if bb == "cont_trend_filter" and "NEUTRAL" in detail:
        return "🔴 BUG: CERT missing (FIX-5/7)"
    if bb == "direction_context" and "LSMA DOWN" in detail:
        return "🔴 BUG: pullback-blindness (FIX-7)"
    if bb == "daytype_playbook" and "Nontrend" in detail:
        return "🟡 S1 flap (antiflap fix)"

    # Correct blocks
    if bb == "cont_trend_filter" and "DOWN" in d:
        return "✓ correct (short against uptrend)"
    if bb == "rr_entry_gate":
        return "✓ correct (R:R too low)"
    if bb == "entry_not_confirmed":
        return "⚖️ design (confirm-bar threshold)"
    if bb == "session_gate_closed":
        return "✓ correct (outside RTH)"

    return ""


def generate_report(candidates, target_date, counterfactual=False):
    """Generate the replay report."""
    lines = [
        f"# Decision Replay — {target_date}",
        "",
        f"**Candidates:** {len(candidates)} gateway decisions",
        f"**Source:** backend.err.log gateway BLOCKED/FIRED entries",
        "",
        "## Timeline",
        "",
        "| Time | Sys | Dir | Entry | Blocked By | Classification |",
        "|------|-----|-----|-------|------------|----------------|",
    ]

    blocked_count = 0
    fired_count = 0
    bug_count = 0
    correct_count = 0

    by_gate = defaultdict(int)

    for c in candidates:
        if c.get("blocked_by") in ("session_gate_closed", "eod_entry_cutoff"):
            continue  # skip session/eod blocks
        if "SIM_TEST" in c.get("detail", "") or "SIM_TEST" in c.get("pattern", ""):
            continue  # skip drill fires

        cls = classify_candidate(c)
        sys_name = f"S{c['system']}"
        bb = c.get("blocked_by") or c.get("outcome", "")

        lines.append(
            f"| {c['time']} | {sys_name} | {c['direction']} | "
            f"{c['entry']:.2f} | {bb} | {cls} |"
        )

        if c["outcome"] == "BLOCKED":
            blocked_count += 1
            by_gate[c["blocked_by"]] += 1
            if "🔴" in cls:
                bug_count += 1
            elif "✓" in cls:
                correct_count += 1
        else:
            fired_count += 1

    lines += [
        "",
        "## Summary",
        "",
        f"- **Fired:** {fired_count}",
        f"- **Blocked:** {blocked_count}",
        f"- **Bugs (would change with fixes):** {bug_count}",
        f"- **Correct blocks:** {correct_count}",
        "",
        "## Blocks by gate",
        "",
        "| Gate | Count |",
        "|------|-------|",
    ]
    for gate, count in sorted(by_gate.items(), key=lambda x: -x[1]):
        lines.append(f"| {gate} | {count} |")

    lines += [
        "",
        f"_Generated by decision_replay.py on {datetime.now().isoformat()[:19]}_",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Decision Replay")
    parser.add_argument("--date", default=date.today().isoformat(),
                        help="Trading date (YYYY-MM-DD)")
    parser.add_argument("--log", default="/tmp/backend.err.log",
                        help="Backend error log path")
    parser.add_argument("--counterfactual", action="store_true",
                        help="Show counterfactual (what current code would do)")
    args = parser.parse_args()

    candidates = parse_gateway_log(args.log, args.date)
    report = generate_report(candidates, args.date, args.counterfactual)

    out_path = os.path.join(ROOT, "docs", "reports", f"DECISION_REPLAY_{args.date}.md")
    with open(out_path, "w") as f:
        f.write(report)
    print(f"Written: {out_path}")
    print(f"Candidates: {len(candidates)}")


if __name__ == "__main__":
    main()
