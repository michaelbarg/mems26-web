#!/usr/bin/env python3
"""
gen_flag_index.py — generate docs/FLAG_INDEX.md, the canonical index of every
MEMS26 behavior / trading flag.

WHY THIS EXISTS
    The flag state used to live scattered across .env + code + CLAUDE.md +
    SOURCE_OF_TRUTH.md, and SoT went stale (it listed 4 flags as OFF that were
    actually ON). This generator makes the index UN-stale-able: every mechanical
    column (file:line, code default, current .env value, ON/OFF, inert) is read
    LIVE from the code and the .env at generation time. The only hand-authored
    part is the meaning of each flag, which lives in docs/FLAG_REGISTRY.yaml.

WHAT IT DOES
    1. Scans backend/ + bridge/ for flag reads:
         os.getenv("X"[, default]) / environ.get("X"[, default]) / flag("X"[, default])
       capturing the flag name, every file:line, and the code default.
    2. Reads .env for the current value of each flag.
    3. Merges with docs/FLAG_REGISTRY.yaml (category / what / why / status / ...).
    4. Computes ON / OFF / ON-but-inert and detects drift:
         - a behavior flag found in code but absent from the registry (UNDOCUMENTED)
         - a registry flag not found in code (DEAD?, unless status: not_built)
    5. Writes docs/FLAG_INDEX.md.

USAGE
    python3 scripts/gen_flag_index.py            # write docs/FLAG_INDEX.md
    python3 scripts/gen_flag_index.py --check     # exit 1 if there is undocumented drift
                                                  # (CI / pre-commit friendly)

FUTURE AGENTS: add new behavior flags to docs/FLAG_REGISTRY.yaml, then rerun this.
Never hand-edit docs/FLAG_INDEX.md.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("ERROR: PyYAML is required (pip install pyyaml).\n")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "docs" / "FLAG_REGISTRY.yaml"
ENV_PATH = ROOT / ".env"
OUT_PATH = ROOT / "docs" / "FLAG_INDEX.md"
SCAN_DIRS = ["backend", "bridge"]

TRUTHY = {"1", "true", "yes", "on"}

# Env vars that are infra / secrets / ops / data-pipeline — intentionally OUT of
# scope for the behavior-flag index. Add new infra vars here so they don't show
# up as "undocumented" drift.
INFRA_EXCLUDE = {
    "NAME", "EXPORT",  # regex false-positives
    "UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN", "BRIDGE_TOKEN",
    "DATABASE_URL", "CLOUD_URL", "REDIS_URL", "SOT_API_BASE", "CORS_ORIGINS",
    "SLACK_WEBHOOK_URL", "SLACK_UAT_WEBHOOK",
    "V9_EXPORT_DIR", "V9_TPO_EXPORT_PATH", "V9_CUMDELTA_EXPORT_PATH",
    "V9_CUMDELTA_MAX_AGE_S", "V9_ARCHIVE_DIR", "V9_ARCHIVE_RETENTION_DAYS",
    "V9_HISTORY_MAX_AGE_H", "V9_HISTORY_BATCH_SIZE", "V9_SKIP_HISTORY",
    "V9_DO_WARMUP", "V9_POLL_INTERVAL", "V9_STREAMS", "V9_STATUS_REDIS_TIMEOUT_S",
    "V9_STATUS_ENDPOINT_BUDGET_S", "V9_STATUS_BRIDGE_BUDGET_S", "V9_CVD_PERIOD_S",
    "V9_CVD_HOST_BAR_S", "V9_CVD_HISTORY_LIMIT", "V9_TPO_MAX_AGE_S",
    "V9_WOODIES_5MIN_MAX_AGE_S", "V9_WOODIES_RTH_ONLY", "V9_DISABLE_WATCHDOG",
    "V9_DISABLE_CHICAGO_TS_FIX", "V9_DISABLE_TPO_SNAPSHOTTER",
    "V9_DISABLE_HISTORY_LOADER", "V9_DISABLE_EOD_SCHEDULER", "SC_HISTORY_DAYS",
    "MAX_STALE_HOURS", "STALE_PRICE_BAND", "MEMS26_MODE", "MEMS26_CLOCK_MODE",
    "MEMS26_SIGNALS_DIR", "MEMS26_DRIVE_SA_JSON", "MEMS26_DRIVE_MIRROR_FOLDER_ID",
    "AUDIT_POLL_MS", "AUDIT_BATCH_SIZE",
}

# Order categories appear in the document.
CATEGORY_ORDER = [
    ("s1", "S1 — Day-type / classification"),
    ("s2", "S2 — 5-min (Reactive / Initiative)"),
    ("s3", "S3 — Footprint (suppressed pre-LIVE)"),
    ("s4", "S4 — Woodies (ZLR / HFE / TLB / …)"),
    ("cascade_gate", "Cascade alignment gates (gateway)"),
    ("targets", "Targets"),
    ("sizing", "Stops / sizing"),
    ("risk", "Risk breakers"),
    ("param", "Numeric parameters"),
    ("misc", "Misc"),
]

ENV_RE = re.compile(
    r'(?:\b\w+\.)?(?:getenv|environ\.get)\(\s*["\']([A-Z][A-Z0-9_]+)["\']\s*(?:,\s*([^)\n]*?))?\)'
)
FLAG_RE = re.compile(
    r'\b_?flag\(\s*["\']([A-Z][A-Z0-9_]+)["\']\s*(?:,\s*([^)\n]*?))?\)'
)


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def scan_code() -> dict:
    """name -> {locations: [(relpath, lineno)], default_display, default_truthy, style}"""
    found: dict[str, dict] = {}

    def record(name, default_raw, style, relpath, lineno):
        entry = found.setdefault(
            name,
            {"locations": [], "default_display": None, "default_truthy": None, "style": style},
        )
        entry["locations"].append((relpath, lineno))
        if entry["default_display"] is None:
            if style == "flag":
                if default_raw is None:
                    entry["default_display"] = "False (flag() default)"
                    entry["default_truthy"] = False
                else:
                    tok = default_raw.strip()
                    entry["default_display"] = tok
                    entry["default_truthy"] = tok.lower() == "true"
            else:  # env
                if default_raw is None:
                    entry["default_display"] = "(no default)"
                    entry["default_truthy"] = False
                else:
                    raw = default_raw.strip()
                    if raw and raw[0] in "\"'":          # string literal default
                        tok = raw.strip("\"'")
                        entry["default_display"] = f'"{tok}"' if tok != "" else '"" (empty → OFF)'
                        entry["default_truthy"] = tok.lower() in TRUTHY
                    elif re.fullmatch(r"-?\d+(?:\.\d+)?", raw):  # numeric literal default
                        entry["default_display"] = raw
                        entry["default_truthy"] = False
                    else:                                 # identifier / expression (a constant)
                        entry["default_display"] = f"{raw} (constant)"
                        entry["default_truthy"] = False

    for d in SCAN_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            parts = set(path.parts)
            if "__pycache__" in parts or "tests" in parts or "test" in parts:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                for m in ENV_RE.finditer(line):
                    record(m.group(1), m.group(2), "env", _rel(path), i)
                for m in FLAG_RE.finditer(line):
                    record(m.group(1), m.group(2), "flag", _rel(path), i)
    return found


def parse_env(path: Path) -> dict:
    """name -> raw value string (only un-commented assignments)."""
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        k = k.strip()
        if re.fullmatch(r"[A-Z][A-Z0-9_]+", k):
            env[k] = v.strip()
    return env


def is_truthy(val: str) -> bool:
    return val.strip().strip("\"'").lower() in TRUTHY


def esc(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if undocumented behavior flags exist (no write)")
    args = ap.parse_args()

    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    reg_flags = registry.get("flags", {}) or {}
    code = scan_code()
    env = parse_env(ENV_PATH)

    # Drift: behavior flags in code but not registered (excluding infra).
    undocumented = sorted(
        n for n in code
        if n not in reg_flags and n not in INFRA_EXCLUDE
    )
    # Registry flags with no code reference (dead?) unless intentionally not built.
    not_in_code = sorted(
        n for n, meta in reg_flags.items()
        if n not in code and (meta or {}).get("status") != "not_built"
    )

    if args.check:
        if undocumented:
            sys.stderr.write(
                "UNDOCUMENTED behavior flags (add to docs/FLAG_REGISTRY.yaml):\n  "
                + "\n  ".join(undocumented) + "\n")
            return 1
        print("flag index: no undocumented drift.")
        return 0

    rows_by_cat: dict[str, list] = {}
    counts = {"on": 0, "off": 0, "inert": 0, "standing_off": 0, "param": 0,
              "rejected": 0, "awaiting": 0, "not_built": 0, "total": 0}

    for name, meta in reg_flags.items():
        meta = meta or {}
        c = code.get(name, {})
        env_val = env.get(name)
        status = meta.get("status")

        # state
        if status == "not_built":
            state = "⚪ not built"
            counts["not_built"] += 1
        elif meta.get("category") == "param":
            state = "🔢 param"
            counts["param"] += 1
        else:
            if env_val is not None:
                on = is_truthy(env_val)
            else:
                on = bool(c.get("default_truthy"))
            inert = False
            iw = meta.get("inert_when")
            if on and iw:
                deps = re.findall(r"([A-Z][A-Z0-9_]+)=1", iw)
                inert = bool(deps) and all(
                    env.get(dep) is not None and is_truthy(env.get(dep)) for dep in deps
                )
            if on and inert:
                state = "🟡 ON·inert"
                counts["inert"] += 1
                counts["on"] += 1
            elif on:
                state = "✅ ON"
                counts["on"] += 1
            else:
                state = "🔴 OFF"
                counts["off"] += 1
                if meta.get("standing_decision"):
                    counts["standing_off"] += 1
        if status == "rejected":
            counts["rejected"] += 1
        elif status == "awaiting_backtest":
            counts["awaiting"] += 1
        counts["total"] += 1

        # current value display
        if env_val is not None:
            cur = f"`{env_val}` (.env)"
        elif name in code:
            cur = "unset → " + (c.get("default_display") or "OFF")
        else:
            cur = "—"

        # notes
        notes = []
        if meta.get("inert_when"):
            notes.append(f"inert: {meta['inert_when']}")
        if meta.get("standing_decision"):
            notes.append("STANDING-OFF — Michael sign-off to enable")
        if status == "rejected":
            notes.append("REJECTED by backtest — do not enable")
        elif status == "awaiting_backtest":
            notes.append("awaiting backtest before enable")
        elif status == "not_built":
            notes.append("not wired in code")
        elif status == "deferred":
            notes.append("deferred")
        if meta.get("ref"):
            notes.append(meta["ref"])

        # locations
        locs = c.get("locations", [])
        loc_str = "—"
        if locs:
            shown = [f"`{p}:{ln}`" for p, ln in locs[:3]]
            if len(locs) > 3:
                shown.append(f"(+{len(locs) - 3})")
            loc_str = "<br>".join(shown)

        label = name
        if meta.get("group"):
            label = f"{name}<br><sub>{esc(meta['group'])}</sub>"

        rows_by_cat.setdefault(meta.get("category", "misc"), []).append({
            "label": label,
            "state": state,
            "current": cur,
            "default": c.get("default_display") or "—",
            "what": esc(meta.get("what", "")),
            "why": esc(meta.get("why", "")),
            "loc": loc_str,
            "notes": esc("; ".join(notes)),
        })

    # ---- emit ----
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    env_mtime = (
        _dt.datetime.fromtimestamp(ENV_PATH.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        if ENV_PATH.exists() else "n/a"
    )
    out = []
    out.append("# MEMS26 — Flag Index (canonical)")
    out.append("")
    out.append("> **AUTO-GENERATED — do not hand-edit.** Run `python3 scripts/gen_flag_index.py`.")
    out.append("> Meaning of each flag is hand-authored in `docs/FLAG_REGISTRY.yaml`; every other")
    out.append("> column is read live from the code + `.env` at generation time, so this file")
    out.append("> cannot go stale the way `SOURCE_OF_TRUTH.md` did.")
    out.append("")
    out.append(f"_Generated {now} · `.env` last modified {env_mtime} · "
               f"scan dirs: {', '.join(SCAN_DIRS)}_")
    out.append("")
    out.append("**Legend:** ✅ ON · 🔴 OFF · 🟡 ON·inert (set ON but superseded at runtime) · "
               "🔢 numeric param · ⚪ not built.")
    out.append("")
    out.append(
        "**Summary:** "
        f"{counts['total']} documented · {counts['on']} ON "
        f"(of which {counts['inert']} inert) · {counts['off']} OFF "
        f"({counts['standing_off']} standing-OFF) · "
        f"{counts['param']} numeric params · "
        f"{counts['awaiting']} awaiting backtest · {counts['rejected']} rejected · "
        f"{counts['not_built']} not built."
    )
    out.append("")
    if undocumented:
        out.append(f"> ⚠ **{len(undocumented)} UNDOCUMENTED behavior flag(s)** found in code but "
                   f"missing from the registry — add them to `docs/FLAG_REGISTRY.yaml`: "
                   + ", ".join(f"`{n}`" for n in undocumented))
        out.append("")
    if not_in_code:
        out.append(f"> ⚠ **{len(not_in_code)} registry flag(s) not referenced in code** "
                   f"(dead or renamed?): " + ", ".join(f"`{n}`" for n in not_in_code))
        out.append("")

    for cat_key, cat_title in CATEGORY_ORDER:
        rows = rows_by_cat.get(cat_key)
        if not rows:
            continue
        rows.sort(key=lambda r: r["label"])
        out.append(f"## {cat_title}")
        out.append("")
        out.append("| Flag | State | Current | Code default | What it does | Why / state | Where (file:line) | Notes |")
        out.append("|------|-------|---------|--------------|--------------|-------------|-------------------|-------|")
        for r in rows:
            out.append(
                f"| {r['label']} | {r['state']} | {r['current']} | {r['default']} | "
                f"{r['what']} | {r['why']} | {r['loc']} | {r['notes']} |"
            )
        out.append("")

    out.append("---")
    out.append("")
    out.append("### How to maintain (future agents)")
    out.append("")
    out.append("1. **Add / change a behavior flag in code** → add or edit its entry in "
               "`docs/FLAG_REGISTRY.yaml` (category / what / why / status).")
    out.append("2. Run `python3 scripts/gen_flag_index.py` and commit both files.")
    out.append("3. `python3 scripts/gen_flag_index.py --check` fails (exit 1) if any behavior "
               "flag in code is undocumented — wire it into CI / pre-commit to keep this honest.")
    out.append("4. Enabling a **standing-OFF**, **rejected**, or **awaiting-backtest** flag is a "
               "trading-risk-surface change → Michael sign-off (CLAUDE.md §Standing Decisions).")
    out.append("")

    OUT_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {_rel(OUT_PATH)} — {counts['total']} flags "
          f"({counts['on']} ON / {counts['off']} OFF / {counts['not_built']} not built); "
          f"{len(undocumented)} undocumented, {len(not_in_code)} not-in-code.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
