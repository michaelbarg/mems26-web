"""Canonical serialization and hashes for Replay Kernel outputs."""
from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable, Mapping, Tuple

from .types import ReplayBar, ReplayManifest


def _normalize(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        value = dataclasses.asdict(value)
    if isinstance(value, Mapping):
        return {
            str(key): _normalize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, float):
        return round(value, 4)
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        _normalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def manifest_hash(manifest: ReplayManifest) -> str:
    """Stable manifest identity; excludes run-instance metadata."""
    stable = dataclasses.asdict(manifest)
    stable.pop("run_id", None)
    stable.pop("created_at", None)
    return sha256_value(stable)


def bars_hash(bars: Iterable[ReplayBar]) -> str:
    return sha256_value([bar.identity_tuple() for bar in bars])


def flags_hash(flags: Mapping[str, str]) -> str:
    return sha256_value(sorted((str(key), str(value)) for key, value in flags.items()))


def canonical_result_hash(payload: Mapping[str, Any]) -> str:
    """Hash stable output, stripping only top-level run identity.

    Domain fields named `created_at` remain hash-significant. Inside the
    top-level manifest only its run-instance `run_id`/`created_at` are removed.
    """
    stable = dict(payload)
    for key in ("created_at", "run_id", "result_hash", "manifest_hash"):
        stable.pop(key, None)
    if "manifest" in stable:
        manifest = stable["manifest"]
        if dataclasses.is_dataclass(manifest):
            manifest = dataclasses.asdict(manifest)
        else:
            manifest = dict(manifest)
        manifest.pop("run_id", None)
        manifest.pop("created_at", None)
        stable["manifest"] = manifest
    return sha256_value(stable)


def git_identity(repo_root: Path) -> Tuple[str, str]:
    """Return (HEAD, dirty tree hash) without mutating git state."""
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()
    tracked = subprocess.check_output(
        ["git", "diff", "--binary", "--no-ext-diff"],
        cwd=repo_root,
    )
    staged = subprocess.check_output(
        ["git", "diff", "--cached", "--binary", "--no-ext-diff"],
        cwd=repo_root,
    )
    untracked_names = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=repo_root,
        text=True,
    ).splitlines()
    digest = hashlib.sha256()
    digest.update(tracked)
    digest.update(staged)
    for name in sorted(untracked_names):
        digest.update(name.encode("utf-8"))
        path = repo_root / name
        if path.is_file():
            digest.update(path.read_bytes())
    return head, digest.hexdigest()
