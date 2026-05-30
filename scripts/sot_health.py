#!/usr/bin/env python3
"""SOT_HEALTH — Source of Truth Health Check.

Pre-LIVE / pre-market freshness check. Walks every MEMS26 system and verifies:

  1. Sierra Chart JSON file exists and is fresh
  2. DB table has recent rows
  3. API endpoint responds with expected fields
  4. The cross-source numbers agree (Sierra vs DB vs API)

Writes a live snapshot to ``docs/reference/SOT_HEALTH.md`` (header date is
overwritten each run; the per-system reference tables are static).

Usage:
    python3 scripts/sot_health.py            # update MD + print colored summary
    python3 scripts/sot_health.py --strict   # exit 1 if any check is STALE/MISSING
    python3 scripts/sot_health.py --json     # machine-readable JSON to stdout
    python3 scripts/sot_health.py --quiet    # MD only, no terminal output

Trigger words for the agent:
    "sot health" / "truth check" / "pre-market check" / "data freshness"
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


REPO = Path(__file__).resolve().parent.parent
DB_PATH = REPO / "data" / "mems26_local.db"
SIERRA_EXPORT = Path("/Users/michael/SierraChart_Data/v9_export")
API_BASE = os.environ.get("SOT_API_BASE", "http://localhost:8000")
MD_PATH = REPO / "docs" / "reference" / "SOT_HEALTH.md"

ET = ZoneInfo("America/New_York")
IL = ZoneInfo("Asia/Jerusalem")

# Freshness thresholds (seconds). RTH = market open (09:30–16:00 ET).
# Outside RTH we relax: a 5-min bar is allowed to be hours stale on weekends.
THRESH_RTH_FRESH = 60
THRESH_RTH_STALE = 300
THRESH_OFF_FRESH = 60 * 60 * 6     # 6h off-hours = still fresh
THRESH_OFF_STALE = 60 * 60 * 24 * 4  # 4d = weekend max


# ----------------------------------------------------------------------------
# Status enum
# ----------------------------------------------------------------------------

class Status:
    FRESH = "FRESH"
    STALE = "STALE"
    MISSING = "MISSING"
    ERROR = "ERROR"
    NA = "N/A"
    INFO = "INFO"

    EMOJI = {
        FRESH: "🟢",
        STALE: "🟡",
        MISSING: "🔴",
        ERROR: "❌",
        NA: "⚪",
        INFO: "ℹ️",
    }

    SEVERITY = {FRESH: 0, INFO: 0, NA: 0, STALE: 1, MISSING: 2, ERROR: 2}


def is_rth_now() -> bool:
    """Return True if current ET time is inside the regular trading session
    (09:30 → 16:00 ET, Mon–Fri). Used to relax thresholds when market is shut."""
    now_et = datetime.now(ET)
    if now_et.weekday() >= 5:
        return False
    minutes = now_et.hour * 60 + now_et.minute
    return 9 * 60 + 30 <= minutes < 16 * 60


def fresh_status(age_s: float | None) -> str:
    if age_s is None:
        return Status.MISSING
    rth = is_rth_now()
    fresh_t = THRESH_RTH_FRESH if rth else THRESH_OFF_FRESH
    stale_t = THRESH_RTH_STALE if rth else THRESH_OFF_STALE
    if age_s <= fresh_t:
        return Status.FRESH
    if age_s <= stale_t:
        return Status.STALE
    return Status.MISSING


# ----------------------------------------------------------------------------
# Probes
# ----------------------------------------------------------------------------

@dataclass
class Probe:
    label: str
    status: str
    age_s: float | None = None
    detail: str = ""

    def line(self) -> str:
        e = Status.EMOJI[self.status]
        age = f"{int(self.age_s)}s ago" if self.age_s is not None and self.age_s < 3600 \
            else f"{int(self.age_s/60)}m ago" if self.age_s is not None and self.age_s < 86400 \
            else f"{int(self.age_s/3600)}h ago" if self.age_s is not None \
            else "—"
        return f"{e} {self.status:<7} {age:<10} {self.label}{(' · ' + self.detail) if self.detail else ''}"


def probe_sierra_file(name: str, optional: bool = False) -> Probe:
    p = SIERRA_EXPORT / name
    label = f"Sierra: {name}" + (" (optional)" if optional else "")
    if not p.exists():
        st = Status.INFO if optional else Status.MISSING
        return Probe(label, st, None, "file not found")
    age = time.time() - p.stat().st_mtime
    if optional:
        # Diag dumps update infrequently — never gate health on them
        return Probe(label, Status.INFO, age, f"{p.stat().st_size:,}B (informational)")
    return Probe(label, fresh_status(age), age, f"{p.stat().st_size:,}B")


def _parse_ts_to_epoch(ts_raw: Any) -> float | None:
    """Best-effort ts → epoch seconds. Accepts:
      • numeric epoch seconds (e.g. 1780035000)
      • numeric epoch milliseconds (e.g. 1780035000000)  → /1000
      • ISO-8601 with or without TZ
      • ``YYYY-MM-DD HH:MM:SS[.ffffff]``
    """
    if ts_raw is None:
        return None
    if isinstance(ts_raw, (int, float)):
        v = float(ts_raw)
        return v / 1000.0 if v > 1e12 else v  # ms → s
    s = str(ts_raw).strip()
    if not s:
        return None
    try:
        v = float(s)
        return v / 1000.0 if v > 1e12 else v
    except ValueError:
        pass
    # Normalise: strip trailing 'Z' / collapse '+00:00' → '+0000' so %z fires.
    norm = s.replace("Z", "+0000")
    if norm.endswith("+00:00"):
        norm = norm[:-6] + "+0000"
    elif len(norm) >= 5 and norm[-3] == ":" and norm[-6] in "+-":
        norm = norm[:-3] + norm[-2:]
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            dt = datetime.strptime(norm[:32], fmt[:32])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except (ValueError, TypeError):
            continue
    # Last-ditch: try ISO-format directly (Python 3.11+ supports +HH:MM)
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        return None


def probe_db_table(table: str, ts_col: str = "ts", where: str = "") -> Probe:
    label = f"DB: {table}.{ts_col}"
    if not DB_PATH.exists():
        return Probe(label, Status.MISSING, None, "DB file not found")
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=5)
        cur = conn.execute(
            f"SELECT {ts_col} FROM {table} {('WHERE ' + where) if where else ''} "
            f"ORDER BY rowid DESC LIMIT 1"
        )
        row = cur.fetchone()
        conn.close()
    except sqlite3.Error as e:
        return Probe(label, Status.ERROR, None, str(e)[:60])
    if not row or row[0] is None:
        return Probe(label, Status.MISSING, None, "no rows")
    epoch = _parse_ts_to_epoch(row[0])
    if epoch is None:
        return Probe(label, Status.ERROR, None, f"unparseable ts: {row[0]!r}")
    age = time.time() - epoch
    if age < -300:
        # Future timestamp > 5 min ahead = TZ regression or DLL bug
        return Probe(label, Status.ERROR, age,
                     f"FUTURE ts ({-int(age)}s ahead) — TZ/clock regression?")
    return Probe(label, fresh_status(age), age, f"last={str(row[0])[:19]}")


def probe_api(endpoint: str, expect_keys: list[str] | None = None) -> tuple[Probe, dict | None]:
    url = f"{API_BASE}{endpoint}"
    label = f"API: {endpoint}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "sot_health/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            body = resp.read().decode()
    except urllib.error.HTTPError as e:
        return Probe(label, Status.ERROR, None, f"HTTP {e.code}"), None
    except (urllib.error.URLError, TimeoutError, ConnectionRefusedError) as e:
        return Probe(label, Status.MISSING, None, f"unreachable ({e})"), None

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return Probe(label, Status.ERROR, None, "non-JSON response"), None

    if expect_keys:
        missing = [k for k in expect_keys if k not in (data if isinstance(data, dict) else {})]
        if missing:
            return Probe(label, Status.STALE, None, f"missing keys: {missing}"), data
    return Probe(label, Status.FRESH, None, "200 OK"), data


# ----------------------------------------------------------------------------
# System definitions — what each system gets from Sierra and what it computes
# ----------------------------------------------------------------------------

# DB tables — (table_name, ts_column).  We pick the column that best
# represents "row was last touched" for each table.  See PRAGMA table_info
# for the schema; map verified 2026-05-29.
DBTable = tuple[str, str]


@dataclass
class SystemSpec:
    sid: str
    title: str
    sierra_files: list[str]
    computed: list[str]
    db_tables: list[DBTable]
    api_endpoints: list[str]
    description: str = ""
    sierra_optional: tuple[str, ...] = ()  # files that may legitimately be stale
    probes: list[Probe] = field(default_factory=list)

    def overall(self) -> str:
        sev = max((Status.SEVERITY.get(p.status, 0) for p in self.probes), default=0)
        return {0: Status.FRESH, 1: Status.STALE, 2: Status.MISSING}.get(sev, Status.FRESH)


SYSTEMS: list[SystemSpec] = [
    SystemSpec(
        sid="S0_BARS",
        title="Bars / Price / Flow",
        description=(
            "Pure pass-through. Sierra DLL writes JSON → bridge POSTs to API → "
            "DB row. **No backend computation.** If the row is stale, the bridge "
            "or DLL is the issue, not the system."
        ),
        sierra_files=[
            "5min.json", "cumulative_delta.json", "volume_profile.json",
            "footprint.json", "tick_reversal_12.json", "tick_reversal_15.json",
            "imbalance_flags.json", "live_price.json",
        ],
        computed=[],
        db_tables=[
            ("v9_bars_5min", "ts"),
            ("v9_bars_cumulative_delta", "ts"),
            ("v9_bars_volume_profile", "ts"),
            ("v9_bars_footprint", "ts"),
            ("v9_bars_tick_reversal", "ts"),
            ("v9_bars_imbalance", "ts"),
        ],
        api_endpoints=["/api/v9/chart/bars5min", "/api/v9/health", "/api/v9/footprint/current"],
    ),
    SystemSpec(
        sid="S5_TPO",
        title="TPO / POC / VAH / VAL / IB",
        description=(
            "Sierra TPO Studies (ID 1=yesterday, ID 3=today, ID 6=IB). "
            "Two consumers: `/tpo/current` reads **tpo.json directly** (sub-30s "
            "freshness for chart). `/key_levels` reads **DB** (`v9_tpo_sessions`, "
            "`v9_day_type_history`). **IB synthesis from bars is FORBIDDEN** "
            "(2026-05-28 evening revocation): if Sierra `ib.found=false`, the "
            "API returns `ib_source='missing'`."
        ),
        sierra_files=["tpo.json"],
        computed=[
            "S5 IB-from-Sierra normalization (no fallback synthesis)",
            "session-aware POC/VAH/VAL persistence to v9_tpo_history (B1 snapshotter)",
        ],
        db_tables=[
            # v9_tpo_sessions removed (P32-J): last write 2026-04-29 (30 days dead).
            # Replaced by v9_tpo_history (B1 snapshotter).
            ("v9_tpo_history", "ts"),
            ("v9_tpo_bars", "ts"),
        ],
        api_endpoints=["/api/v9/tpo/current", "/api/v9/key_levels"],
    ),
    SystemSpec(
        sid="S1_DAY_TYPE",
        title="Day Type State Machine",
        description=(
            "Authoritative IB after 10:30 ET lock. Stages A1→A4. Computes "
            "`day_type`, `opening_type`, `ib_width_class`, fade-zones. "
            "Pre-RTH: row is DEVELOPING/NULL by spec. **TZ rule:** Sierra "
            "Inputs Start=09:30 / End=10:29 are interpreted as ET (not UTC, "
            "not Chicago)."
        ),
        sierra_files=["5min.json"],
        computed=[
            "IB high/low/width over 09:30–10:30 ET (S1 authoritative)",
            "Globex / RTH range from 5min bars",
            "Day type classification (TND_UP, TND_DN, NEU_E, NEU_C, RNG, NT)",
            "Opening type (OD/ORR/OTD/OAOR)",
        ],
        db_tables=[
            ("v9_day_type_history", "last_updated_at"),
            ("v9_day_type_state", "ts"),
        ],
        api_endpoints=["/api/v9/day_type/v9/current", "/api/v9/key_levels"],
    ),
    SystemSpec(
        sid="S2_FIVE_MIN",
        title="Five-Min Patterns (FHB / Reactive / Initiative)",
        description=(
            "Pattern detection from 5min bars + day-type context. "
            "**Volume key alias** added 2026-05-28 (bridge `vol` → detector `v`). "
            "FHB only fires within first hour of RTH. Reactive/Initiative/Quiet "
            "patterns gated on day_type auth-table."
        ),
        sierra_files=["5min.json"],
        computed=[
            "FHB (First Hour Break)",
            "Reactive Long / Short (volume + delta confluence)",
            "Initiative Long / Short",
            "Quiet lookback patterns",
            "Confluence stack (S2 + day_type + tpo levels)",
        ],
        db_tables=[
            ("v9_five_min_setups", "ts"),
            ("v9_five_min_state", "last_processed_ts"),
        ],
        api_endpoints=["/api/v9/build/pattern-status"],
    ),
    SystemSpec(
        sid="S4_WOODIES",
        title="Woodies CCI Patterns + W-10 TimeStop",
        description=(
            "Sierra Woodies Studies (Input 18). Patterns: ZLR, TLB, TT, GB100, "
            "VEGAS, GHOST, FAMIR, HTLB, HFE. **W-10 TimeStop** (Registry #11) "
            "is the SOLE TIME_STOP authority — 90 min flat-out, fixed "
            "2026-05-28 evening (Bug A: bar-count per closed bar; Fix #5: "
            "exit_price set before close_trade)."
        ),
        sierra_files=["woodies_5min.json", "woodies_30min.json", "woodies_diag.json"],
        sierra_optional=("woodies_diag.json",),  # diag dump, not per-bar
        computed=[
            "Pattern detectors (9 patterns × directions)",
            "W-10 TimeStop enforcement (90 min / 18 bars)",
            "Trail / Exit discipline (D-092)",
            "ZLR / HFE / LSMA-above-price flags from DLL",
        ],
        db_tables=[
            ("v9_bars_5min_woodies", "ts"),
            ("v9_bars_30min_woodies", "ts"),
            ("v9_woodies_signals", "ts"),
            ("v9_woodies_patterns", "ts"),
        ],
        api_endpoints=["/api/v9/woodies/current"],
    ),
    SystemSpec(
        sid="TRADE_MANAGER",
        title="Trade Manager / Bar-Level Detector",
        description=(
            "Owns trade lifecycle: open, monitor, exit. **Layer 4 TIME_STOP "
            "removed 2026-05-28 evening** — W-10 is now the sole TIME_STOP "
            "authority. Layer 4 still owns stop-hit / target-hit detection."
        ),
        sierra_files=[],
        computed=[
            "Stop / target hit detection (per bar)",
            "Trade close → close_trade(reason)",
            "P&L compute on close",
        ],
        db_tables=[
            ("v9_trades", "entry_ts"),
            # TODO(P-future): wire v9_trade_management_log + v9_audit_events
            # writers (audit report 05, 2026-05-29: zero rows, zero writers).
        ],
        api_endpoints=["/api/v9/trades/active"],
    ),
    SystemSpec(
        sid="KILLZONE",
        title="Killzone / Chop Score",
        description=(
            "Time-of-day kill switch (NY open / lunch / power hour). Chop "
            "score from 5min bar volatility. Gates pattern firing per "
            "Constitution V3."
        ),
        sierra_files=["5min.json"],
        computed=[
            "Killzone classification (currently active / off)",
            "Chop score (0-100) from ATR / range",
        ],
        db_tables=[
            ("v9_killzone_log", "ts"),
            ("v9_chop_score", "ts"),
        ],
        api_endpoints=[],
    ),
]


# ----------------------------------------------------------------------------
# Cross-source value-agreement checks (Sierra vs DB vs API)
# ----------------------------------------------------------------------------

def _read_json_file(p: Path) -> dict | None:
    try:
        with open(p) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def cross_check_ib() -> Probe:
    """Compare Sierra `tpo.json::ib` ↔ DB `v9_tpo_sessions::ib_*` ↔ API
    `/key_levels::today.ib_*`. They should agree (or all be missing
    consistently)."""
    label = "Cross-check: IB consistency (Sierra ↔ DB ↔ API)"
    sierra = _read_json_file(SIERRA_EXPORT / "tpo.json") or {}
    s_ib = sierra.get("ib") or {}
    s_high = s_ib.get("high") if s_ib.get("found") else None

    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=5)
        row = conn.execute(
            "SELECT ib_high FROM v9_tpo_sessions "
            "WHERE trading_date=date('now') AND session_type='CASH'"
        ).fetchone()
        conn.close()
        d_high = row[0] if row else None
    except sqlite3.Error as e:
        return Probe(label, Status.ERROR, None, f"DB: {e}")

    a_probe, a_data = probe_api("/api/v9/key_levels", expect_keys=["today"])
    a_high = (a_data or {}).get("today", {}).get("ib_high") if a_data else None

    vals = {"sierra": s_high, "db": d_high, "api": a_high}
    nums = {k: v for k, v in vals.items() if isinstance(v, (int, float))}
    if not nums:
        return Probe(label, Status.INFO, None, "all sources missing IB (pre-10:30 ET or DLL silent)")
    spread = max(nums.values()) - min(nums.values())
    if spread > 0.01:
        return Probe(label, Status.MISSING, None,
                     f"DIVERGENT — sierra={s_high} db={d_high} api={a_high}")
    return Probe(label, Status.FRESH, None,
                 f"agree @ {next(iter(nums.values()))} ({list(nums)})")


def cross_check_day_type() -> Probe:
    label = "Cross-check: day_type API vs DB"
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=5)
        row = conn.execute(
            "SELECT day_type FROM v9_day_type_history WHERE date=date('now')"
        ).fetchone()
        conn.close()
        db_dt = row[0] if row else None
    except sqlite3.Error as e:
        return Probe(label, Status.ERROR, None, str(e))

    api_probe, api_data = probe_api("/api/v9/day_type/v9/current")
    api_dt = (api_data or {}).get("day_type") if api_data else None
    if db_dt is None and api_dt is None:
        return Probe(label, Status.INFO, None, "both pre-classification (likely pre-10:30 ET)")
    if db_dt != api_dt:
        return Probe(label, Status.STALE, None, f"DB={db_dt} API={api_dt}")
    return Probe(label, Status.FRESH, None, f"agree: {db_dt}")


def cross_check_bridge_tz() -> Probe:
    """Verify the bridge interprets Sierra timestamps as ET, not Chicago.
    A 1-hour drift in the freshest 5min row = TZ regression."""
    label = "Cross-check: bridge TZ (no 1h Chicago drift)"
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=5)
        row = conn.execute(
            "SELECT ts FROM v9_bars_5min ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        conn.close()
    except sqlite3.Error as e:
        return Probe(label, Status.ERROR, None, str(e))
    if not row or row[0] is None:
        return Probe(label, Status.MISSING, None, "no bars")
    epoch = _parse_ts_to_epoch(row[0])
    if epoch is None:
        return Probe(label, Status.ERROR, None, "unparseable ts")
    age = time.time() - epoch
    if age < -1800:
        return Probe(label, Status.MISSING, None,
                     f"FUTURE timestamp ({-int(age)}s ahead) — TZ regression?")
    return Probe(label, Status.FRESH, age, "ET-anchored (no future drift)")


CROSS_CHECKS = [cross_check_ib, cross_check_day_type, cross_check_bridge_tz]


# ----------------------------------------------------------------------------
# Probe assembly
# ----------------------------------------------------------------------------

def run_all() -> tuple[list[SystemSpec], list[Probe]]:
    for sys_spec in SYSTEMS:
        for sf in sys_spec.sierra_files:
            sys_spec.probes.append(
                probe_sierra_file(sf, optional=(sf in sys_spec.sierra_optional))
            )
        for tbl, col in sys_spec.db_tables:
            sys_spec.probes.append(probe_db_table(tbl, col))
        for ep in sys_spec.api_endpoints:
            p, _ = probe_api(ep)
            sys_spec.probes.append(p)

    cross = [fn() for fn in CROSS_CHECKS]
    return SYSTEMS, cross


# ----------------------------------------------------------------------------
# Markdown writer
# ----------------------------------------------------------------------------

MD_HEADER = """# SOT_HEALTH — Source of Truth Health Check

> **Purpose:** Pre-LIVE / pre-market data freshness audit. For every MEMS26
> system, lists what it receives from Sierra Chart, what it computes
> internally, where it persists, and the live freshness of each source.
>
> **Refresh:** `python3 scripts/sot_health.py` (rewrites the live block below
> in place; the per-system reference is static).
>
> **Strict mode for launchd / pre-market:**
> `python3 scripts/sot_health.py --strict` exits 1 on any STALE/MISSING.

<!-- LIVE_BLOCK_START -->
"""

MD_FOOTER_BEFORE_REF = """<!-- LIVE_BLOCK_END -->

---

## Reference — Per-system inventory

> The tables below describe the **stable** wiring of each system. They do not
> change between runs. The live block above is the only thing the script
> mutates.
"""


def render_md(systems: list[SystemSpec], cross: list[Probe], started: float) -> str:
    now_il = datetime.now(IL).strftime("%Y-%m-%d %H:%M:%S IL")
    now_et = datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S ET")
    rth = "RTH" if is_rth_now() else "OFF-HOURS"
    duration_ms = int((time.time() - started) * 1000)

    sev = 0
    for s in systems:
        sev = max(sev, Status.SEVERITY.get(s.overall(), 0))
    for p in cross:
        sev = max(sev, Status.SEVERITY.get(p.status, 0))
    overall = {0: Status.FRESH, 1: Status.STALE, 2: Status.MISSING}.get(sev, Status.FRESH)
    overall_emoji = Status.EMOJI[overall]

    lines = [MD_HEADER]
    lines.append(f"**Last run:** {now_il}  ·  {now_et}  ·  market: **{rth}**  ·  duration: {duration_ms}ms")
    lines.append("")
    lines.append(f"**Overall: {overall_emoji} {overall}**")
    lines.append("")

    lines.append("## Live status — per system")
    lines.append("")
    lines.append("| System | Sierra inputs | Computed | DB tables | API | Status |")
    lines.append("|--------|---------------|----------|-----------|-----|--------|")
    for s in systems:
        sf = ", ".join(f"`{f}`" for f in s.sierra_files) or "—"
        comp = "<br>".join(f"• {c}" for c in s.computed) or "—"
        dbs = "<br>".join(f"`{t}.{c}`" for t, c in s.db_tables) or "—"
        apis = "<br>".join(f"`{a}`" for a in s.api_endpoints) or "—"
        emoji = Status.EMOJI[s.overall()]
        lines.append(
            f"| **{s.sid}** — {s.title} | {sf} | {comp} | {dbs} | {apis} | "
            f"{emoji} {s.overall()} |"
        )
    lines.append("")

    lines.append("## Cross-source consistency (Sierra ↔ DB ↔ API)")
    lines.append("")
    lines.append("| Check | Result | Detail |")
    lines.append("|-------|--------|--------|")
    for p in cross:
        emoji = Status.EMOJI[p.status]
        lines.append(f"| {p.label} | {emoji} {p.status} | {p.detail or '—'} |")
    lines.append("")

    lines.append("## Freshness probes — per system breakdown")
    lines.append("")
    for s in systems:
        emoji = Status.EMOJI[s.overall()]
        lines.append(f"### {emoji} {s.sid} — {s.title}")
        lines.append("")
        lines.append(f"_{s.description}_")
        lines.append("")
        lines.append("| Source | Status | Age | Detail |")
        lines.append("|--------|--------|-----|--------|")
        for p in s.probes:
            e = Status.EMOJI[p.status]
            age = (
                f"{int(p.age_s)}s" if p.age_s is not None and p.age_s < 3600
                else f"{int(p.age_s/60)}m" if p.age_s is not None and p.age_s < 86400
                else f"{int(p.age_s/3600)}h" if p.age_s is not None
                else "—"
            )
            lines.append(f"| {p.label} | {e} {p.status} | {age} | {p.detail or '—'} |")
        lines.append("")

    lines.append(MD_FOOTER_BEFORE_REF)
    lines.append("")
    lines.append("### Sierra Chart Study Inputs")
    lines.append("")
    lines.append("| Input | Name | Default | Purpose |")
    lines.append("|-------|------|---------|---------|")
    lines.append("| 4 | V9 Export Directory | `~/SierraChart_Data/v9_export/` | All JSON files |")
    lines.append("| 13 | TPO Yesterday Study ID | 1 | Prev day POC/VAH/VAL |")
    lines.append("| 14 | TPO Today Study ID | 3 | Today POC/VAH/VAL |")
    lines.append("| 15 | Initial Balance Study ID | 6 | IB high (subgraph 6) / IB low (subgraph 8) |")
    lines.append("| 16 | Projected H/L Study ID | 0 | proj_hi / proj_lo for Woodies |")
    lines.append("| 17 | TPO Chart Number | 0 | Chart hosting TPO+IB |")
    lines.append("| 18 | Woodies Chart Number | 0 | Chart hosting Woodies studies |")
    lines.append("")

    lines.append("### What each system receives vs computes")
    lines.append("")
    for s in systems:
        lines.append(f"#### {s.sid} — {s.title}")
        lines.append("")
        lines.append(f"_{s.description}_")
        lines.append("")
        lines.append(f"- **Sierra inputs:** {', '.join('`' + f + '`' for f in s.sierra_files) or '_none — pure compute_'}")
        lines.append("- **Backend computes:**")
        if s.computed:
            for c in s.computed:
                lines.append(f"  - {c}")
        else:
            lines.append("  - _pass-through — no backend computation_")
        lines.append(f"- **DB tables (writes):** {', '.join('`' + t + '.' + c + '`' for t, c in s.db_tables) or '—'}")
        lines.append(f"- **API endpoints:** {', '.join('`' + a + '`' for a in s.api_endpoints) or '—'}")
        lines.append("")

    lines.append("### Freshness threshold rules")
    lines.append("")
    lines.append("| Window | Fresh ≤ | Stale ≤ | Missing > |")
    lines.append("|--------|---------|---------|-----------|")
    lines.append(f"| RTH (09:30–16:00 ET, Mon–Fri) | {THRESH_RTH_FRESH}s | {THRESH_RTH_STALE}s | {THRESH_RTH_STALE}s |")
    lines.append(f"| Off-hours / weekend | {THRESH_OFF_FRESH//60}m | {THRESH_OFF_STALE//3600}h | {THRESH_OFF_STALE//3600}h |")
    lines.append("")

    lines.append("### Source-of-Truth discipline (CLAUDE.md)")
    lines.append("")
    lines.append("- **Rule 1 — Honest failure > synthetic value.** When Sierra is silent, "
                 "propagate `None` / `\"missing\"`. Never synthesize from another source "
                 "and tag it with the canonical source's `found` flag.")
    lines.append("- **Rule 2 — Verify before you trust.** Run the equivalent DB/bar-math "
                 "query before believing any UI screenshot or assertion.")
    lines.append("- **Rule 3 — `min`/`max` aggregators are amplifiers.** Audit every "
                 "downstream `min`/`max` for a synthesis fix.")
    lines.append("- **Rule 4 — TZ ambiguity is forbidden.** Every `HH:MM:SS` spec value "
                 "must carry its TZ in the value, comment, or boundary conversion.")
    lines.append("- **Rule 5 — Verification quote, not assertion.** \"Should work\" "
                 "claims require pasted command + raw output.")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_md(content: str) -> None:
    MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    MD_PATH.write_text(content)


# ----------------------------------------------------------------------------
# Terminal printer
# ----------------------------------------------------------------------------

def print_terminal(systems: list[SystemSpec], cross: list[Probe]) -> None:
    bar = "=" * 78
    print(bar)
    print("  SOT_HEALTH — Source of Truth Health Check")
    print(f"  {datetime.now(IL).strftime('%Y-%m-%d %H:%M:%S IL')}  · "
          f"{datetime.now(ET).strftime('%H:%M:%S ET')}  · "
          f"market={'RTH' if is_rth_now() else 'OFF-HOURS'}")
    print(bar)

    for s in systems:
        emoji = Status.EMOJI[s.overall()]
        print(f"\n{emoji} {s.sid:<14}  {s.title}")
        for p in s.probes:
            print(f"   {p.line()}")

    print(f"\n{'-' * 78}")
    print("  CROSS-SOURCE CONSISTENCY")
    print(f"{'-' * 78}")
    for p in cross:
        print(f"  {p.line()}")
    print(bar)


# ----------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--strict", action="store_true",
                    help="Exit 1 if any STALE/MISSING/ERROR.")
    ap.add_argument("--json", action="store_true",
                    help="Emit JSON to stdout, no terminal table.")
    ap.add_argument("--quiet", action="store_true",
                    help="No terminal output (just rewrite the MD).")
    ap.add_argument("--no-md", action="store_true",
                    help="Skip the markdown rewrite.")
    args = ap.parse_args()

    started = time.time()
    systems, cross = run_all()

    sev = max(
        max((Status.SEVERITY.get(p.status, 0) for s in systems for p in s.probes), default=0),
        max((Status.SEVERITY.get(p.status, 0) for p in cross), default=0),
    )

    if not args.no_md:
        md = render_md(systems, cross, started)
        write_md(md)

    if args.json:
        out = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "rth": is_rth_now(),
            "systems": [
                {
                    "sid": s.sid,
                    "title": s.title,
                    "status": s.overall(),
                    "probes": [
                        {"label": p.label, "status": p.status,
                         "age_s": p.age_s, "detail": p.detail}
                        for p in s.probes
                    ],
                }
                for s in systems
            ],
            "cross_checks": [
                {"label": p.label, "status": p.status, "detail": p.detail}
                for p in cross
            ],
        }
        print(json.dumps(out, indent=2))
    elif not args.quiet:
        print_terminal(systems, cross)
        if not args.no_md:
            print(f"\n[i] Markdown updated: {MD_PATH.relative_to(REPO)}")

    if args.strict and sev > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
