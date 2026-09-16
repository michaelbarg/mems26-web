#!/usr/bin/env python3
"""T-392: Tree diff — compare real gate decisions vs draft tree v2.

Run after 23:05 (post-RTH) to avoid interference:

    python3 scripts/tree_diff.py --sessions 2026-09-15 2026-09-11

Reads v9_decision_vectors rows (kind=DECISION and kind=TREE_SHADOW) for the
given sessions and prints a per-setup comparison:

    SETUP  <ts>  real=<blocked_by|FIRED>  tree=<decision>  row=<rule_id>  MATCH|DIFF

Skeleton — full replay_admits integration deferred (requires replay which
can't run during RTH).
"""
from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="T-392 tree diff report")
    parser.add_argument(
        "--sessions", nargs="+", required=True,
        help="Session dates to compare (YYYY-MM-DD)")
    args = parser.parse_args()

    print(f"[tree_diff] sessions: {args.sessions}")
    print()

    # ── Phase 1: read DECISION + TREE_SHADOW rows from DB ────────────────
    try:
        from backend.v9.db.read import read_all
    except ImportError:
        print("[tree_diff] ERROR: cannot import backend.v9.db.read — "
              "run from the repo root with PYTHONPATH=.", file=sys.stderr)
        sys.exit(1)

    for session_date in args.sessions:
        print(f"--- session {session_date} ---")
        rows = read_all(
            """SELECT ts, kind, classification, direction, blocked_by, reason
               FROM v9_decision_vectors
               WHERE kind IN ('DECISION', 'TREE_SHADOW')
                 AND ts::date = :dt
               ORDER BY ts""",
            {"dt": session_date},
        )
        if not rows:
            print("  (no decision vectors for this date)")
            continue

        # Pair DECISION + TREE_SHADOW rows by timestamp proximity
        decisions = [r for r in rows if r["kind"] == "DECISION"]
        shadows = [r for r in rows if r["kind"] == "TREE_SHADOW"]
        print(f"  decisions={len(decisions)}  tree_shadows={len(shadows)}")

        for d in decisions:
            real = d["blocked_by"] or "FIRED"
            # Find closest shadow row
            matched_shadow = None
            for s in shadows:
                if (s["classification"] == d["classification"]
                        and s["direction"] == d["direction"]):
                    matched_shadow = s
                    break
            if matched_shadow:
                tree = matched_shadow["blocked_by"] or "stand_down"
                reason = matched_shadow["reason"] or ""
                tag = "MATCH" if real == tree else "DIFF"
                print(f"  {d['ts']}  {d['classification']}  {d['direction']}  "
                      f"real={real}  tree={tree}  {reason}  {tag}")
                shadows.remove(matched_shadow)
            else:
                print(f"  {d['ts']}  {d['classification']}  {d['direction']}  "
                      f"real={real}  tree=???  (no shadow row)")

        print()

    # ── Phase 2 (TODO): replay_admits integration ────────────────────────
    # Full implementation requires running historical setups through both
    # the real gate and the tree evaluator.  Deferred — needs replay
    # infrastructure which can't run during RTH.
    print("[tree_diff] stub complete — full replay integration deferred")


if __name__ == "__main__":
    main()
