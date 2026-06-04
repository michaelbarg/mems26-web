#!/usr/bin/env python3
"""Generate a living index of the MEMS26 codebase.

Writes `_INDEX.md` in every scanned code directory + a root `SYSTEM_INDEX.md`.
Each file gets: one-line purpose (from docstring/leading comment) + usage flag
(inbound internal-import count) + LOC + last-modified date (git).

Re-run anytime to refresh. Read-only on code — only writes index files.

Usage:  python3 scripts/gen_index.py
"""
import os, re, ast, json, subprocess
from pathlib import Path
from collections import defaultdict
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = ["backend", "frontend/v9/src", "bridge", "scripts", "sc_study"]
EXCLUDE = {"node_modules", "__pycache__", ".next", ".git", ".pytest_cache",
           "dist", "build", ".venv"}
CODE_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".cpp", ".h", ".sh"}
INDEX_NAME = "_INDEX.md"

def is_excluded(p: Path) -> bool:
    return any(part in EXCLUDE for part in p.parts)


# ── Purpose extraction ───────────────────────────────────────────────

def py_purpose(text):
    try:
        mod = ast.parse(text)
        d = ast.get_docstring(mod)
        if d:
            return d.strip().splitlines()[0][:120]
    except Exception:
        pass
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#") and not s.startswith("#!"):
            return s.lstrip("# ").strip()[:120]
        if s and not s.startswith(("import", "from", "#")):
            break
    return ""

def cstyle_purpose(text):
    m = re.search(r"/\*+(.*?)\*/", text, re.S)
    if m:
        for ln in m.group(1).splitlines():
            ln = ln.strip().lstrip("*").strip()
            if ln:
                return ln[:120]
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("//"):
            return s.lstrip("/ ").strip()[:120]
        if s and not s.startswith(("import", "export", "//", "/*", "'use")):
            break
    return ""

def purpose_for(path, text):
    if path.suffix == ".py":
        return py_purpose(text)
    if path.suffix in {".ts", ".tsx", ".js", ".jsx", ".cpp", ".h"}:
        return cstyle_purpose(text)
    if path.suffix == ".sh":
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("#") and not s.startswith("#!"):
                return s.lstrip("# ").strip()[:120]
    return ""


# ── Collect files ────────────────────────────────────────────────────

files = []
for sd in SCAN_DIRS:
    base = ROOT / sd
    if not base.exists():
        continue
    for p in sorted(base.rglob("*")):
        if (p.is_file() and p.suffix in CODE_EXT
                and not is_excluded(p)
                and p.name != INDEX_NAME):
            files.append(p)

text_cache = {}
def read(p):
    if p not in text_cache:
        try:
            text_cache[p] = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text_cache[p] = ""
    return text_cache[p]


# ── LOC ──────────────────────────────────────────────────────────────

def loc(p):
    return read(p).count("\n")


# ── Git last-modified ────────────────────────────────────────────────

_git_dates = {}
def git_date(p):
    if p not in _git_dates:
        try:
            r = subprocess.run(
                ["git", "log", "-1", "--format=%cs", "--", str(p)],
                capture_output=True, text=True, cwd=ROOT, timeout=5,
            )
            _git_dates[p] = r.stdout.strip() or "—"
        except Exception:
            _git_dates[p] = "—"
    return _git_dates[p]


# ── Python import graph ──────────────────────────────────────────────

py_files = [p for p in files if p.suffix == ".py"]

def py_module(p):
    rel = p.relative_to(ROOT).with_suffix("")
    return ".".join(rel.parts)

mod_to_path = {py_module(p): p for p in py_files}
inbound = defaultdict(set)

for p in py_files:
    txt = read(p)
    # Standard imports: import x.y / from x.y import z
    for m in re.finditer(
        r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))", txt, re.M
    ):
        target = m.group(1) or m.group(2)
        for known in mod_to_path:
            if target == known or target.startswith(known + "."):
                if mod_to_path[known] != p:
                    inbound[mod_to_path[known]].add(p)
    # from x.y import z where z is a submodule
    for m in re.finditer(
        r"^\s*from\s+([\w\.]+)\s+import\s+([\w, ]+)", txt, re.M
    ):
        pkg = m.group(1)
        for name in re.split(r"[,\s]+", m.group(2).strip()):
            name = name.strip()
            if not name:
                continue
            cand = f"{pkg}.{name}"
            if cand in mod_to_path and mod_to_path[cand] != p:
                inbound[mod_to_path[cand]].add(p)
    # Relative imports: from . import x, y / from .pkg import x
    for m in re.finditer(r"^\s*from\s+(\.[\w\.]*)\s+import\s+([\w, ]+)", txt, re.M):
        rel_pkg = m.group(1)  # e.g. "." or ".sub"
        # Resolve relative to importer's package
        pkg_parts = list(p.relative_to(ROOT).parent.parts)
        if rel_pkg == ".":
            base_mod = ".".join(pkg_parts)
        else:
            # ".sub" → package + ".sub" (strip leading dot)
            rest = rel_pkg[1:]  # e.g. "row_helpers" or ".sub.pkg"
            base_mod = ".".join(pkg_parts) + "." + rest.lstrip(".")
        for name in re.split(r"[,\s]+", m.group(2).strip()):
            name = name.strip()
            if not name:
                continue
            # Try both: base_mod.name (submodule) and base_mod (the module itself is the target)
            cand = f"{base_mod}.{name}"
            # Also try base_mod directly (from .module import function)
            if base_mod in mod_to_path and mod_to_path[base_mod] != p:
                inbound[mod_to_path[base_mod]].add(p)
            if cand in mod_to_path and mod_to_path[cand] != p:
                inbound[mod_to_path[cand]].add(p)
    # Dynamic imports: importlib.import_module("x.y")
    for m in re.finditer(r'importlib\.import_module\(["\']([^"\']+)', txt):
        target = m.group(1)
        for known in mod_to_path:
            if target == known or target.startswith(known + "."):
                if mod_to_path[known] != p:
                    inbound[mod_to_path[known]].add(p)
    # String references to module names (registry/plugin patterns)
    for m in re.finditer(r'["\'](' + r'backend\.[\w.]+' + r')["\']', txt):
        target = m.group(1)
        if target in mod_to_path and mod_to_path[target] != p:
            inbound[mod_to_path[target]].add(p)


# ── TS/TSX import graph ──────────────────────────────────────────────

ts_files = [p for p in files if p.suffix in {".ts", ".tsx", ".js", ".jsx"}]
ts_inbound = defaultdict(set)

def resolve_ts(importer, spec):
    if spec.startswith("."):
        base = (importer.parent / spec).resolve()
    elif spec.startswith("@/"):
        base = (ROOT / "frontend/v9/src" / spec[2:]).resolve()
    else:
        return None
    for ext in ["", ".ts", ".tsx", ".js", ".jsx"]:
        c = Path(str(base) + ext)
        if c.exists() and c.is_file():
            return c
    for idx in ["index.ts", "index.tsx", "index.js"]:
        c = base / idx
        if c.exists():
            return c
    return None

for p in ts_files:
    txt = read(p)
    for m in re.finditer(
        r"""(?:import|export)[^'"]*from\s*['"]([^'"]+)['"]""", txt
    ):
        tgt = resolve_ts(p, m.group(1))
        if tgt and tgt != p:
            ts_inbound[tgt].add(p)

inbound.update(ts_inbound)


# ── Entrypoint / framework detection ─────────────────────────────────

# Next.js framework entrypoints (page.tsx, layout.tsx, route.ts, etc.)
NEXTJS_ENTRY = re.compile(
    r"(^|/)(?:page|layout|loading|error|not-found|route|template|default)"
    r"\.(ts|tsx|js|jsx)$"
)
# Python entrypoints, tests, scripts
PY_ENTRY = re.compile(
    r"(^|/)(?:main|__init__|conftest|setup)\.(py)$"
    r"|/tests?/|test_|\.test\.|\.spec\."
    r"|scripts/|sc_study/"
)
# Bridge streams loaded dynamically by json_bridge.py via __init__.py
BRIDGE_STREAM = re.compile(r"bridge/v9_streams/\w+_stream\.py$")
# DB migration files
MIGRATION = re.compile(r"/migrations/versions/")

def usage_flag(p):
    n = len(inbound.get(p, ()))
    rel = str(p.relative_to(ROOT))
    if p.suffix not in {".py", ".ts", ".tsx", ".js", ".jsx"}:
        return "—"
    if n > 0:
        return f"✅ {n}"
    # Framework / dynamic entrypoints
    if NEXTJS_ENTRY.search(rel):
        return "▶ nextjs-entry"
    if PY_ENTRY.search(rel):
        return "▶ entry/test"
    if BRIDGE_STREAM.search(rel):
        return "▶ bridge-stream"
    if MIGRATION.search(rel):
        return "▶ migration"
    # app/ directory pages
    if "/app/" in rel and p.suffix in {".ts", ".tsx"}:
        return "▶ app-route"
    return "⚠️ orphan?"


# ── Write per-dir _INDEX.md ──────────────────────────────────────────

by_dir = defaultdict(list)
for p in files:
    by_dir[p.parent].append(p)

stamp = date.today().isoformat()
orphans = []
dirs_written = 0

for d, fs in sorted(by_dir.items()):
    rel_d = d.relative_to(ROOT)
    subdirs = sorted({
        c.name for c in d.iterdir()
        if c.is_dir() and not is_excluded(c)
        and any(True for _ in c.rglob("*") if _.suffix in CODE_EXT)
    }) if d.exists() else []

    lines = [
        f"# Index · `{rel_d}`", "",
        f"*Auto-generated by `scripts/gen_index.py` · {stamp}. Do not edit manually.*",
        "",
    ]
    if subdirs:
        lines.append("## Subdirectories")
        for s in subdirs:
            lines.append(f"- `{s}/` → `{s}/_INDEX.md`")
        lines.append("")
    lines.append("## Files")
    lines.append("| File | Usage | LOC | Modified | Description |")
    lines.append("|---|---|---|---|---|")
    for p in sorted(fs):
        flag = usage_flag(p)
        if flag == "⚠️ orphan?":
            orphans.append(p.relative_to(ROOT))
        desc = purpose_for(p, read(p)).replace("|", "\\|")
        lines.append(
            f"| `{p.name}` | {flag} | {loc(p)} | {git_date(p)} | {desc} |"
        )
    (d / INDEX_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")
    dirs_written += 1


# ── Root SYSTEM_INDEX.md ─────────────────────────────────────────────

total = len(files)
root_lines = [
    "# MEMS26 · System Index", "",
    f"*Auto-generated by `python3 scripts/gen_index.py` · {stamp}.*  ",
    f"Legend: ✅N = N internal importers · ▶ entry/test/stream · ⚠️ orphan? = 0 importers (suspect, verify before deleting).",
    "",
    f"**Scope:** {SCAN_DIRS} · {total} files · {dirs_written} directories · "
    f"each has `_INDEX.md`.",
    "",
    "## Top-level tree",
]
for sd in SCAN_DIRS:
    base = ROOT / sd
    if not base.exists():
        continue
    cnt = sum(1 for p in files if str(p).startswith(str(base)))
    root_lines.append(f"- `{sd}/` — {cnt} files → `{sd}/_INDEX.md`")

root_lines += [
    "", f"## Suspected orphans ({len(orphans)})",
    "*May include false positives (dynamic imports, framework routes, registries). "
    "Verify before deleting.*",
    "",
]
for o in sorted(orphans)[:200]:
    root_lines.append(f"- `{o}`")
if len(orphans) > 200:
    root_lines.append(f"- … and {len(orphans) - 200} more")

(ROOT / "SYSTEM_INDEX.md").write_text("\n".join(root_lines) + "\n", encoding="utf-8")

print(json.dumps({
    "files": total,
    "dirs_indexed": dirs_written,
    "orphans": len(orphans),
}, ensure_ascii=False))
