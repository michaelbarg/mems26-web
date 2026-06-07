"""Minimal .env loader — load KEY=VALUE pairs into the process environment.

Why this exists (2026-06-07): the backend reads feature flags from
`os.environ` at import time (`backend/v9/shared/atr.py`, `backend/main.py`).
Those env vars were only ever set by `scripts/start_all.sh` doing `source .env`.
When the backend came up by *any other path* — the `com.mems26.backend`
LaunchAgent auto-restart, or a manual `uvicorn` — `.env` was never sourced, so
the SHADOW calibration flags silently fell back to their `default=False`. That
is the "flags didn't fire in SHADOW on 2026-06-06" incident.

`main.py` calls `load_dotenv_file()` BEFORE importing any `backend.v9` module,
so the flags are consistent regardless of how the process was launched.

No third-party dependency (python-dotenv not guaranteed installed). Pure stdlib.
Already-present env vars are NOT overridden by default — an explicit export
(start_all.sh, the LaunchAgent, a shell) always wins over the file.
"""

from __future__ import annotations

import os
from typing import Dict, Optional, MutableMapping


def load_dotenv_file(
    path: str,
    environ: Optional[MutableMapping[str, str]] = None,
    *,
    override: bool = False,
) -> Dict[str, str]:
    """Parse a .env file and apply KEY=VALUE pairs to `environ`.

    - Blank lines and `#` comments are ignored.
    - Surrounding single/double quotes on the value are stripped.
    - A missing file is a no-op (returns {}).
    - Keys already present in `environ` are skipped unless `override=True`,
      so an explicit environment export always takes precedence over the file.

    Returns the dict of keys actually applied (useful for logging/tests).
    """
    if environ is None:
        environ = os.environ
    applied: Dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if not key:
                    continue
                if override or key not in environ:
                    environ[key] = val
                    applied[key] = val
    except FileNotFoundError:
        return applied
    return applied
