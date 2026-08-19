#!/usr/bin/env python3
"""parity_report.py — EOD cross-machine parity check (cc-imac, 2026-08-19).

Produces a markdown report comparing this machine's state against what the
other machine will produce via the same script.  Each machine writes its own
file; divergence = finding to investigate, not to guess.

Usage:
    python3 scripts/parity_report.py              # stdout + file
    python3 scripts/parity_report.py --json        # also write JSON summary
    python3 scripts/parity_report.py --date 2026-08-19  # explicit date

Output:
    docs/reports/PARITY_<MACHINE_TAG>_<DATE>.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── env loading ─────────────────────────────────────────────────────────────
ENV_PATH = ROOT / ".env"
if ENV_PATH.exists():
    from scripts.flag_guard import parse_env
    for _k, _v in parse_env(str(ENV_PATH)).items():
        os.environ.setdefault(_k, _v)

MACHINE = os.getenv("MACHINE_TAG", "unknown")
EXPORT = Path(os.getenv("MEMS26_SIGNALS_DIR",
              os.path.expanduser("~/SierraChart_Data/v9_export")))
IL = ZoneInfo("Asia/Jerusalem")
ET = ZoneInfo("America/New_York")


def sha256(path: str | Path) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def run(cmd: str, timeout: int = 15) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"


def git_head() -> str:
    return run("git -C '{}' log -1 --format='%h %s'".format(ROOT))


# ── flag_guard hash ─────────────────────────────────────────────────────────
def flag_guard_result() -> tuple[str, int]:
    """Run flag_guard, return (last_line, count)."""
    out = run(f"cd '{ROOT}' && python3 scripts/flag_guard.py 2>&1")
    lines = out.strip().splitlines()
    last = lines[-1] if lines else "UNKNOWN"
    # extract count: "PASS — all 179 ruled flags match"
    import re
    m = re.search(r"all (\d+) ruled", last)
    count = int(m.group(1)) if m else 0
    return last, count


# ── DLL checksum ────────────────────────────────────────────────────────────
def dll_checksums() -> dict:
    mono = ROOT / "sc_study" / "MES_AI_DataExport_merged.cpp"
    deployed1 = Path.home() / "SierraChart" / "ACS_Source" / "MES_AI_DataExport.cpp"
    deployed2 = Path.home() / "SierraChart2" / "ACS_Source" / "MES_AI_DataExport.cpp"
    dll1 = Path.home() / "SierraChart" / "Data" / "MES_AI_DataExport_64.dll"
    dll2 = Path.home() / "SierraChart2" / "Data" / "MES_AI_DataExport_64.dll"
    return {
        "monolith_sha256": sha256(mono),
        "deployed_sc1_sha256": sha256(deployed1),
        "deployed_sc2_sha256": sha256(deployed2),
        "dll_sc1_sha256": sha256(dll1),
        "dll_sc2_sha256": sha256(dll2),
    }


# ── Postgres ────────────────────────────────────────────────────────────────
def find_psql() -> str | None:
    import glob
    candidates = glob.glob("/Applications/Postgres.app/Contents/Versions/*/bin/psql")
    if candidates:
        return sorted(candidates)[-1]
    for p in ["/opt/homebrew/bin/psql", "/usr/local/bin/psql"]:
        if os.path.exists(p):
            return p
    return None


def pg_query(sql: str) -> str:
    psql = find_psql()
    if not psql:
        return "PSQL_NOT_FOUND"
    db = os.getenv("DATABASE_URL", "postgresql://localhost/mems26")
    return run(f'"{psql}" "{db}" -tA -c "{sql}"')


def pg_migrations() -> list[str]:
    mig_dir = ROOT / "backend" / "v9" / "db" / "migrations" / "versions"
    if not mig_dir.exists():
        return []
    files = sorted(f.name for f in mig_dir.iterdir()
                   if f.suffix in (".sql", ".py") and not f.name.startswith("__"))
    return files


def pg_table_counts(trade_date: str) -> dict:
    tables = {
        "v9_bars_5min_woodies": f"SELECT count(*) FROM v9_bars_5min_woodies WHERE ts::date = '{trade_date}'",
        "v9_trades": f"SELECT count(*) FROM v9_trades WHERE (entry_ts AT TIME ZONE 'America/New_York')::date = '{trade_date}'",
        "v9_day_type_state": f"SELECT count(*) FROM v9_day_type_state WHERE created_at::date = '{trade_date}'",
        "v9_bars_total": "SELECT count(*) FROM v9_bars_5min_woodies",
        "v9_trades_total": "SELECT count(*) FROM v9_trades",
    }
    results = {}
    for name, sql in tables.items():
        val = pg_query(sql)
        try:
            results[name] = int(val)
        except (ValueError, TypeError):
            results[name] = val
    return results


# ── woodies bars ────────────────────────────────────────────────────────────
def woodies_summary(trade_date: str) -> dict:
    sql = (f"SELECT count(*), min(close), max(close), "
           f"(SELECT close FROM v9_bars_5min_woodies "
           f"WHERE ts::date = '{trade_date}' ORDER BY ts DESC LIMIT 1) "
           f"FROM v9_bars_5min_woodies WHERE ts::date = '{trade_date}'")
    raw = pg_query(sql)
    if not raw or raw.startswith("ERROR") or raw == "PSQL_NOT_FOUND":
        return {"raw": raw}
    parts = raw.split("|")
    if len(parts) >= 4:
        return {
            "bar_count": parts[0],
            "low_close": parts[1],
            "high_close": parts[2],
            "last_close": parts[3],
        }
    return {"raw": raw}


# ── day type ────────────────────────────────────────────────────────────────
def day_type_final(trade_date: str) -> str:
    sql = (f"SELECT day_type, confidence FROM v9_day_type_state "
           f"WHERE created_at::date = '{trade_date}' "
           f"ORDER BY created_at DESC LIMIT 1")
    return pg_query(sql)


# ── decision histogram ─────────────────────────────────────────────────────
def decision_histogram(trade_date: str) -> str:
    sql = (f"SELECT blocked_by, count(*) FROM "
           f"(SELECT payload->>'blocked_by' as blocked_by "
           f" FROM v9_gateway_decisions "
           f" WHERE created_at::date = '{trade_date}') sub "
           f"GROUP BY blocked_by ORDER BY count DESC LIMIT 15")
    raw = pg_query(sql)
    if raw.startswith("ERROR"):
        # fallback: try jsonl file
        jsonl = EXPORT / "gateway_decisions.jsonl"
        if jsonl.exists():
            from collections import Counter
            ctr: Counter = Counter()
            for line in jsonl.read_text().splitlines():
                try:
                    d = json.loads(line)
                    ts = d.get("ts", "")
                    if isinstance(ts, str) and trade_date in ts:
                        ctr[d.get("blocked_by", "none")] += 1
                    elif isinstance(ts, (int, float)):
                        dt = datetime.fromtimestamp(ts, tz=ET)
                        if dt.strftime("%Y-%m-%d") == trade_date:
                            ctr[d.get("blocked_by", "none")] += 1
                except Exception:
                    continue
            if ctr:
                return "\n".join(f"{k}: {v}" for k, v in ctr.most_common(15))
            return "no decisions found in jsonl"
        return raw
    return raw


# ── sierra state ────────────────────────────────────────────────────────────
def sierra_state() -> dict:
    sf = EXPORT / "sierra_state.json"
    if not sf.exists():
        return {"error": "sierra_state.json not found"}
    try:
        d = json.loads(sf.read_text())
        return {
            "is_sim": d.get("is_sim"),
            "position_qty": d.get("position_qty"),
            "working_orders": d.get("working_orders"),
            "armed": d.get("order_placement_armed"),
            "age_s": round(datetime.now().timestamp() - float(d.get("ts", 0)), 1),
        }
    except Exception as e:
        return {"error": str(e)}


# ── services ────────────────────────────────────────────────────────────────
def services_status() -> dict:
    health = run("curl -s -m4 -o /dev/null -w '%{http_code}' http://localhost:8000/health")
    bridge = run("pgrep -f json_bridge.py >/dev/null && echo running || echo stopped")
    promoter = run("pgrep -f v9_export_promoter >/dev/null && echo running || echo stopped")
    agents = run("launchctl list 2>/dev/null | grep -c mems26")
    return {
        "backend_http": health,
        "bridge": bridge,
        "export_promoter": promoter,
        "launchagents_count": agents,
    }


# ── main ────────────────────────────────────────────────────────────────────
def build_report(trade_date: str) -> tuple[str, dict]:
    now = datetime.now(IL)
    data: dict = {
        "machine": MACHINE,
        "date": trade_date,
        "generated": now.isoformat(),
        "git_head": git_head(),
    }

    # flag_guard
    fg_line, fg_count = flag_guard_result()
    data["flag_guard"] = {"result": fg_line, "count": fg_count}

    # DLL
    data["dll"] = dll_checksums()

    # services
    data["services"] = services_status()

    # sierra
    data["sierra_state"] = sierra_state()

    # PG
    data["pg_migrations"] = pg_migrations()
    data["pg_migration_count"] = len(data["pg_migrations"])
    data["pg_tables"] = pg_table_counts(trade_date)

    # woodies
    data["woodies"] = woodies_summary(trade_date)

    # day type
    data["day_type_final"] = day_type_final(trade_date)

    # decisions
    data["decision_histogram"] = decision_histogram(trade_date)

    # ── render markdown ─────────────────────────────────────────────────────
    lines = [
        f"# Parity Report — {MACHINE} — {trade_date}",
        f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"Git HEAD: `{data['git_head']}`",
        "",
        "## 1. Flag Guard",
        f"```",
        fg_line,
        f"```",
        f"Count: **{fg_count}** ruled flags",
        "",
        "## 2. DLL Checksums",
    ]
    for k, v in data["dll"].items():
        lines.append(f"- `{k}`: `{v or 'NOT_FOUND'}`")

    lines += [
        "",
        "## 3. Services",
    ]
    for k, v in data["services"].items():
        lines.append(f"- {k}: {v}")

    lines += [
        "",
        "## 4. Sierra State",
    ]
    for k, v in data["sierra_state"].items():
        lines.append(f"- {k}: {v}")

    lines += [
        "",
        "## 5. Postgres",
        f"Migration count: **{data['pg_migration_count']}**",
        f"Last 3 migrations: {', '.join(data['pg_migrations'][-3:]) if data['pg_migrations'] else 'none'}",
        "",
        "### Table counts (today):",
    ]
    for k, v in data["pg_tables"].items():
        lines.append(f"- {k}: {v}")

    lines += [
        "",
        "## 6. Woodies Bars",
    ]
    for k, v in data["woodies"].items():
        lines.append(f"- {k}: {v}")

    lines += [
        "",
        f"## 7. Day Type Final",
        f"```",
        data["day_type_final"],
        f"```",
        "",
        "## 8. Decision Histogram",
        f"```",
        data["decision_histogram"],
        f"```",
        "",
    ]

    return "\n".join(lines), data


def main():
    parser = argparse.ArgumentParser(description="Cross-machine parity report")
    parser.add_argument("--date", default=None, help="Trade date YYYY-MM-DD (default: today ET)")
    parser.add_argument("--json", action="store_true", help="Also write JSON")
    args = parser.parse_args()

    if args.date:
        trade_date = args.date
    else:
        # use ET date — if after midnight IL but before midnight ET, use yesterday ET
        now_et = datetime.now(ET)
        trade_date = now_et.strftime("%Y-%m-%d")

    md, data = build_report(trade_date)

    # write markdown
    out_dir = ROOT / "docs" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"PARITY_{MACHINE}_{trade_date}.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"Report: {md_path}")

    if args.json:
        json_path = EXPORT / "parity_report.json"
        json_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        print(f"JSON: {json_path}")

    # print to stdout
    print()
    print(md)


if __name__ == "__main__":
    main()
