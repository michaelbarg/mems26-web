#!/usr/bin/env python3
"""
Upload MEMS26 docs/ mirror to Google Drive per docs/drive/DRIVE_SYNC_MANIFEST.yaml.

Auth (first time):  python3 scripts/drive_sync_upload.py --auth
Dry run:            python3 scripts/drive_sync_upload.py --dry-run
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "docs/drive/DRIVE_SYNC_MANIFEST.yaml"
STATE_PATH = REPO_ROOT / "docs/drive/.sync_state.json"
LOG_PATH = REPO_ROOT / "docs/drive/.sync_log.jsonl"
TOKEN_PATH = Path.home() / ".config/mems26/drive_token.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

DOC_MIMES = {".md", ".markdown", ".txt"}
GOOGLE_DOC = "application/vnd.google-apps.document"


def load_dotenv() -> None:
    env_file = REPO_ROOT / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip("'\"")
        os.environ.setdefault(key, val)


def parse_manifest(path: Path) -> tuple[list[str], list[tuple[str, str]]]:
    """Return (include_globs, routing [(prefix, folder_key)])."""
    text = path.read_text(encoding="utf-8")
    includes: list[str] = []
    routing: list[tuple[str, str]] = []
    section = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("include:"):
            section = "include"
            continue
        if line.startswith("routing:"):
            section = "routing"
            continue
        if line.startswith("exclude:") or line.startswith("folders:"):
            section = None
            continue
        if section == "include" and line.startswith("- "):
            includes.append(line[2:].strip())
        if section == "routing" and "prefix:" in line:
            m = re.search(r'prefix:\s*(\S+)', line)
            if m:
                routing.append((m.group(1), ""))
        if section == "routing" and "folder:" in line and routing:
            m = re.search(r'folder:\s*(\S+)', line)
            if m:
                p, _ = routing[-1]
                routing[-1] = (p, m.group(1))
    return includes, routing


def load_folder_map(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    folders: dict[str, str] = {}
    in_folders = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("folders:"):
            in_folders = True
            continue
        if in_folders and line.startswith("include:"):
            break
        if in_folders and ":" in line and not line.startswith("#"):
            key, _, val = line.partition(":")
            folders[key.strip()] = val.strip()
    return folders


def expand_includes(patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for pat in patterns:
        if "*" in pat:
            files.extend(REPO_ROOT.glob(pat))
        else:
            p = REPO_ROOT / pat
            if p.is_file():
                files.append(p)
    out: list[Path] = []
    seen: set[str] = set()
    for p in sorted(files):
        if not p.is_file():
            continue
        rel = p.relative_to(REPO_ROOT).as_posix()
        if rel in seen:
            continue
        seen.add(rel)
        out.append(p)
    return out


def route_folder(rel_posix: str, routing: list[tuple[str, str]], folder_names: dict[str, str]) -> str:
    best = ("", "docs_root")
    for prefix, key in routing:
        if rel_posix.startswith(prefix) and len(prefix) > len(best[0]):
            best = (prefix, key)
    return folder_names.get(best[1], "docs")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_state() -> dict:
    if STATE_PATH.is_file():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"files": {}, "drive_folders": {}}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def append_log(entry: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def get_drive_service():
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    sa_path = os.environ.get("MEMS26_DRIVE_SA_JSON")
    if sa_path and Path(sa_path).is_file():
        creds = service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    creds = None
    client_secrets = os.environ.get(
        "MEMS26_DRIVE_OAUTH_CLIENT",
        str(Path.home() / ".config/mems26/drive_client_secret.json"),
    )
    if TOKEN_PATH.is_file():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not Path(client_secrets).is_file():
            raise SystemExit(
                f"Missing Drive auth. Run --auth with client secret at {client_secrets}\n"
                "Or set MEMS26_DRIVE_SA_JSON. See docs/drive/README.md"
            )
        flow = InstalledAppFlow.from_client_secrets_file(client_secrets, SCOPES)
        creds = flow.run_local_server(port=0)
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        TOKEN_PATH.chmod(0o600)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def ensure_folder(service, parent_id: str, name: str, cache: dict) -> str:
    key = f"{parent_id}/{name}"
    if key in cache:
        return cache[key]
    q = (
        f"'{parent_id}' in parents and name = '{name.replace(chr(39), '')}' "
        f"and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )
    res = service.files().list(q=q, fields="files(id)", pageSize=1).execute()
    files = res.get("files", [])
    if files:
        fid = files[0]["id"]
    else:
        meta = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        fid = service.files().create(body=meta, fields="id").execute()["id"]
    cache[key] = fid
    return fid


def upload_or_update(service, local: Path, parent_id: str, drive_id: str | None, dry_run: bool) -> str | None:
    from googleapiclient.http import MediaFileUpload

    suffix = local.suffix.lower()
    name = local.name
    if suffix in DOC_MIMES:
        metadata = {"name": name, "parents": [parent_id], "mimeType": GOOGLE_DOC}
        media = MediaFileUpload(str(local), mimetype="text/plain", resumable=True)
    else:
        metadata = {"name": name, "parents": [parent_id]}
        media = MediaFileUpload(str(local), resumable=True)

    if dry_run:
        return "dry-run"

    if drive_id:
        if suffix in DOC_MIMES:
            service.files().update(
                fileId=drive_id,
                media_body=media,
                fields="id",
            ).execute()
        else:
            service.files().update(fileId=drive_id, media_body=media, fields="id").execute()
        return drive_id

    created = (
        service.files()
        .create(body=metadata, media_body=media, fields="id")
        .execute()
    )
    return created["id"]


def write_report(results: list[dict], verdict: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    report = REPO_ROOT / f"docs/reports/P30_DRIVE_SYNC_{ts}.md"
    uploaded = sum(1 for r in results if r["action"] == "UPLOADED")
    skipped = sum(1 for r in results if r["action"] == "SKIPPED")
    failed = sum(1 for r in results if r["action"] == "FAILED")
    lines = [
        f"# P30 Drive Sync — {datetime.now(timezone.utc).isoformat()}",
        "",
        f"**Verdict:** {verdict}",
        f"**Uploaded:** {uploaded} · **Skipped:** {skipped} · **Failed:** {failed}",
        "",
        "| Path | Action | Drive ID |",
        "|------|--------|----------|",
    ]
    for r in results:
        did = (r.get("drive_id") or "")[:12]
        lines.append(f"| `{r['path']}` | {r['action']} | {did} |")
    if failed:
        lines.extend(["", "## Failures", ""])
        for r in results:
            if r["action"] == "FAILED":
                lines.append(f"- `{r['path']}`: {r.get('error', '?')}")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def run_auth() -> None:
    TOKEN_PATH.unlink(missing_ok=True)
    get_drive_service()
    print(f"Token saved: {TOKEN_PATH}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync docs/ to Google Drive")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--all", action="store_true", help="Ignore SHA cache")
    parser.add_argument("--auth", action="store_true")
    args = parser.parse_args()

    if args.auth:
        run_auth()
        return 0

    load_dotenv()
    root_id = os.environ.get("MEMS26_DRIVE_MIRROR_FOLDER_ID", "").strip()
    if not root_id:
        if args.dry_run:
            root_id = "DRY_RUN_ROOT"
        else:
            print(
                "Set MEMS26_DRIVE_MIRROR_FOLDER_ID in .env (see docs/drive/README.md)",
                file=sys.stderr,
            )
            return 2

    includes, routing = parse_manifest(MANIFEST)
    folder_names = load_folder_map(MANIFEST)
    paths = expand_includes(includes)
    state = load_state()
    results: list[dict] = []

    service = None
    folder_cache: dict[str, str] = dict(state.get("drive_folders", {}))
    if not args.dry_run:
        service = get_drive_service()

    for local in paths:
        rel = local.relative_to(REPO_ROOT).as_posix()
        sha = file_sha256(local)
        prev = state.get("files", {}).get(rel, {})
        if not args.all and prev.get("sha256") == sha and prev.get("drive_id"):
            results.append({"path": rel, "action": "SKIPPED", "drive_id": prev["drive_id"]})
            continue

        sub = route_folder(rel, routing, folder_names)
        action = "UPLOADED"
        drive_id = None
        err = None
        try:
            if args.dry_run:
                drive_id = "dry-run"
            else:
                assert service is not None
                parent = root_id
                for part in folder_names.get(sub, sub).split("/"):
                    parent = ensure_folder(service, parent, part, folder_cache)
                drive_id = upload_or_update(
                    service, local, parent, prev.get("drive_id"), dry_run=False
                )
            state.setdefault("files", {})[rel] = {
                "sha256": sha,
                "drive_id": drive_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:  # noqa: BLE001 — report per file
            action = "FAILED"
            err = str(exc)
            results.append({"path": rel, "action": action, "error": err})

        if err is None:
            results.append({"path": rel, "action": action, "drive_id": drive_id})
            append_log(
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "path": rel,
                    "action": action,
                    "drive_id": drive_id,
                }
            )

    state["drive_folders"] = folder_cache
    if not args.dry_run:
        save_state(state)

    failed = any(r["action"] == "FAILED" for r in results)
    verdict = "FAIL" if failed else ("PASS" if not args.dry_run else "DRY-RUN")
    report = write_report(results, verdict)
    print(f"Sync complete: {verdict} — {len(paths)} files — report {report}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
