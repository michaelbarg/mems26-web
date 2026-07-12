#!/usr/bin/env python3
"""gen_task_board — writes the static fallback frontend/v9/public/task_board.json
from docs/plans/DEV_BACKLOG.md (same parser as the live endpoint).

The /board panel prefers the LIVE endpoint /api/v9/agent/backlog_board; this
static file is only the backend-down fallback. Run after any DEV_BACKLOG edit
(part of the roadmap-autoupdate rule).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from backend.v9.services.backlog_board import build_board  # noqa: E402

OUT = REPO / "frontend/v9/public/task_board.json"


def main() -> int:
    board = build_board()
    OUT.write_text(json.dumps(board, ensure_ascii=False, indent=1), encoding="utf-8")
    n = len(board["tasks"])
    lanes = {}
    for t in board["tasks"]:
        lanes[t["status"]] = lanes.get(t["status"], 0) + 1
    print(f"[gen_task_board] wrote {OUT.name}: {n} tasks {lanes} (updated {board['meta']['updated']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
