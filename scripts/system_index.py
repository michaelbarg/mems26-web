#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""system_index.py — the whole MEMS26 system in one read-only index (T-533, Michael 05.10 "סוכן שיבצע אינדקס על הכל").

Writes docs/index/SYSTEM_INDEX.md + docs/index/system_index.json. Never writes anything else; never touches the DB
except SELECTs through psql. Sections: git/tree/flags · producers (30d) · gates (30d) · tree leaves · DB tables ·
LaunchAgents · scripts · tickets (open, by status, with next step) · reports · harness runs · "measurable now".
usage: python3 scripts/system_index.py [--days 30] [--quiet]
"""
import collections, datetime, glob, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
DB = "mems26"
DAYS = 30
QUIET = "--quiet" in sys.argv
if "--days" in sys.argv:
    DAYS = int(sys.argv[sys.argv.index("--days") + 1])
NOW = datetime.datetime.now()
IDX = {"generated_at": NOW.strftime("%Y-%m-%d %H:%M:%S"), "days": DAYS, "sections": {}}


def sh(cmd, timeout=60):
    try:
        return subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception as e:  # noqa
        return "ERR %s" % e


def q(sql):
    """psql -Atc; rows as lists of strings (pipe-separated)."""
    out = sh('%s -d %s -Atc "%s"' % (PSQL, DB, sql.replace('"', '\\"')), timeout=90)
    if out.startswith("ERR") or out.startswith("psql:"):
        return []
    return [r.split("|") for r in out.splitlines() if r]


def load_env():
    env = {}
    try:
        for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env


ENV = load_env()
for k, v in ENV.items():
    os.environ.setdefault(k, v)
sys.path.insert(0, ROOT)

# ── 1. git / tree / flags ───────────────────────────────────────────────────────────────────────
sec = {}
sec["head"] = sh("git log -1 --format='%h %ad %s' --date=format:'%Y-%m-%d %H:%M'")[:160]
sec["branch"] = sh("git branch --show-current")
sec["dirty_files"] = len([l for l in sh("git status --short").splitlines() if l.strip()])
try:
    import yaml  # noqa
    tree_doc = yaml.safe_load(open(os.path.join(ROOT, "config", "decision_tree_v3.yaml"), encoding="utf-8"))
    sec["tree_version"] = str(tree_doc.get("version"))
except Exception as e:  # noqa
    tree_doc, sec["tree_version"] = None, "ERR %s" % e
try:
    ruled = yaml.safe_load(open(os.path.join(ROOT, "config", "RULED_FLAGS.yaml"), encoding="utf-8")).get("ruled", {}) or {}
except Exception:
    ruled = {}
flags = []
for name, spec in sorted(ruled.items()):
    exp = str((spec or {}).get("expected", ""))
    act = ENV.get(name, "")
    ok = (exp == act) or (exp == "unset_or_0" and act in ("", "0"))
    flags.append({"flag": name, "expected": exp, "actual": act, "ok": ok, "ruled_by": (spec or {}).get("ruled_by", ""),
                  "date": str((spec or {}).get("date", "")), "measured": bool((spec or {}).get("measured"))})
sec["ruled_flags"] = len(flags)
sec["flags_mismatch"] = [f["flag"] for f in flags if not f["ok"]]
sec["flags_on"] = sorted(f["flag"] for f in flags if f["actual"] not in ("", "0", "false", "off"))
sec["flags_shadow"] = sorted(f["flag"] for f in flags if f["actual"] == "shadow")
sec["flags_measured"] = sum(1 for f in flags if f["measured"])
IDX["sections"]["git_tree_flags"] = sec
IDX["flags"] = flags

# ── 2. producers (DECISION rows, last N days) ─────────────────────────────────────────────────────
rows = q("select classification, system, count(*), sum(case when blocked_by is null then 1 else 0 end) "
         "from v9_decision_vectors where kind='DECISION' and ts >= now() - interval '%d days' "
         "group by 1,2 order by 3 desc" % DAYS)
live_fires = {r[0]: int(r[1]) for r in q(
    "select pattern_id_at_entry, count(*) from v9_trades where mode='live' and coalesce(entry_ts,created_at) >= now() - interval '%d days' "
    "group by 1" % DAYS) if len(r) == 2}
live_pnl = {r[0]: float(r[1] or 0) for r in q(
    "select pattern_id_at_entry, sum(coalesce(pnl_sierra, pnl_usd, 0)) from v9_trades where mode='live' and state='CLOSED' "
    "and coalesce(entry_ts,created_at) >= now() - interval '%d days' group by 1" % DAYS) if len(r) == 2}
top_block = collections.defaultdict(list)
for r in q("select classification, coalesce(blocked_by,'(passed)'), count(*) from v9_decision_vectors where kind='DECISION' "
           "and ts >= now() - interval '%d days' group by 1,2 order by 1, 3 desc" % DAYS):
    if len(r) == 3 and len(top_block[r[0]]) < 3:
        top_block[r[0]].append("%s %s" % (r[1], r[2]))
try:
    from backend.v9.services.next_fire import live_capability  # noqa
except Exception:
    live_capability = lambda p: (None, "n/a")  # noqa
producers = []
for r in rows:
    if len(r) != 4:
        continue
    cls, system_, n, passed = r[0], r[1], int(r[2]), int(r[3])
    cap, switch = live_capability(cls)
    producers.append({"pattern": cls, "system": system_, "decisions": n, "passed_tree_gates": passed,
                      "live_fires": live_fires.get(cls, 0), "live_pnl": round(live_pnl.get(cls, 0.0), 2),
                      "live_capable": cap, "switch": switch, "top": top_block.get(cls, [])})
IDX["producers"] = producers

# ── 3. gates (blocked_by, last N days) ───────────────────────────────────────────────────────────
gates = [{"blocked_by": r[0], "n": int(r[1])} for r in q(
    "select coalesce(blocked_by,'(passed)'), count(*) from v9_decision_vectors where kind='DECISION' and ts >= now() - interval '%d days' "
    "group by 1 order by 2 desc" % DAYS) if len(r) == 2]
IDX["gates"] = gates

# ── 4. tree leaves ──────────────────────────────────────────────────────────────────────────────
leaves_info = {"take": 0, "skip": 0, "shadow": 0, "ruled": [], "n": 0}
try:
    from backend.v9.services import decision_tree as dt3  # noqa
    tree = dt3.load_tree()
    for lf in dt3.leaves(tree):
        leaves_info["n"] += 1
        k = str(lf.get("leaf", "")).lower()
        if k in leaves_info:
            leaves_info[k] += 1
        if lf.get("ruling"):
            m = lf.get("measured") or {}
            leaves_info["ruled"].append({"id": lf.get("id") or lf.get("path"), "sessions": m.get("sessions"), "usd": m.get("usd"),
                                         "usd_net": m.get("usd_net"), "date": m.get("date")})
except Exception as e:  # noqa
    leaves_info["error"] = str(e)[:200]
IDX["tree"] = leaves_info

# ── 5. DB tables ────────────────────────────────────────────────────────────────────────────────
tables = []
for t, tscol in (("v9_trades", "coalesce(entry_ts,created_at)"), ("v9_decision_vectors", "ts"), ("v9_bars_5min_woodies", "ts"),
                 ("v9_bars_5min", "ts"), ("v9_day_type_state", None), ("v9_exit_decisions", None), ("v9_trade_management_log", None),
                 ("v9_woodies_signals", None), ("v9_footprint_journal", "ts"), ("v9_bars_cumulative_delta", "ts"), ("broker_truth", None)):
    cnt = q("select count(*) from %s" % t)
    if not cnt:
        tables.append({"table": t, "rows": None, "max_ts": "missing"})
        continue
    mx = q("select to_char(max(%s) at time zone 'Asia/Jerusalem','YYYY-MM-DD HH24:MI') from %s" % (tscol, t)) if tscol else []
    tables.append({"table": t, "rows": int(cnt[0][0]), "max_ts_il": (mx[0][0] if mx and mx[0] else "")})
IDX["db_tables"] = tables

# ── 6. LaunchAgents ─────────────────────────────────────────────────────────────────────────────
agents = []
for line in sh("launchctl list | grep mems26").splitlines():
    p = line.split()
    if len(p) >= 3:
        agents.append({"label": p[2], "pid": p[0], "rc": p[1]})
IDX["launch_agents"] = agents

# ── 7. scripts ─────────────────────────────────────────────────────────────────────────────────
scripts = []
for f in sorted(glob.glob(os.path.join(ROOT, "scripts", "*.py")) + glob.glob(os.path.join(ROOT, "scripts", "*.sh"))):
    doc = ""
    try:
        for line in open(f, encoding="utf-8", errors="replace").read().splitlines()[:12]:
            s = line.strip().lstrip("#").strip().strip('"""').strip("'''").strip()
            if s and not s.startswith("!") and not s.startswith("-*-") and "coding" not in s and "usr/bin" not in s:
                doc = s[:140]
                break
    except Exception:
        pass
    scripts.append({"file": os.path.relpath(f, ROOT), "doc": doc})
IDX["scripts"] = scripts

# ── 8. tickets (TASK_LOG rows) ─────────────────────────────────────────────────────────────────
tickets = []
try:
    tl = open(os.path.join(ROOT, "docs", "plans", "TASK_LOG.md"), encoding="utf-8").read()
    for m in re.finditer(r"^\| (T-\d+) \| (\S+) \*\*(.+?)\*\*(.*)$", tl, flags=re.M):
        tid, status, title, rest = m.group(1), m.group(2), m.group(3), m.group(4)
        nxt = ""
        mm = re.search(r"\*\*הצעד הבא[^*]*\*\*:?(.*)", rest)
        if mm:
            nxt = mm.group(1).strip().strip("|").strip()[:260]
        tickets.append({"id": tid, "status": status, "title": title[:200], "next": nxt,
                        "measurable": bool(re.search(r"למדוד|מדיד|הרנס|ריפליי|וריאנט|מדידה", nxt or ""))})
except Exception as e:  # noqa
    tickets.append({"id": "ERR", "status": "", "title": str(e)[:100], "next": "", "measurable": False})
OPEN = ("🔴", "🟠", "🟡", "🔵")
open_t = [t for t in tickets if t["status"] in OPEN]
IDX["tickets"] = {"total": len(tickets), "open": len(open_t),
                  "by_status": dict(collections.Counter(t["status"] for t in tickets)),
                  "open_rows": open_t}
order = {"🔴": 0, "🟠": 1, "🟡": 2, "🔵": 3}
measurable = sorted([t for t in open_t if t["measurable"]], key=lambda t: (order.get(t["status"], 9), -int(t["id"][2:])))
IDX["measurable_now"] = measurable[:40]

# ── 9. reports / harness ───────────────────────────────────────────────────────────────────────
reps = sorted(glob.glob(os.path.join(ROOT, "docs", "reports", "*.md")), key=os.path.getmtime, reverse=True)[:12]
IDX["reports"] = [{"file": os.path.relpath(f, ROOT), "mtime": datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y-%m-%d %H:%M")} for f in reps]
runs = []
for d in sorted(glob.glob(os.path.join(ROOT, "harness_out", "t*")), key=os.path.getmtime, reverse=True)[:10]:
    outs = sorted(glob.glob(os.path.join(d, "*.out")), key=os.path.getmtime, reverse=True)
    last = ""
    if outs:
        try:
            last = open(outs[0], encoding="utf-8", errors="replace").read().strip().splitlines()[-1][:160]
        except Exception:
            pass
    runs.append({"dir": os.path.relpath(d, ROOT), "last": last})
IDX["harness_runs"] = runs

# ── write ──────────────────────────────────────────────────────────────────────────────────────
os.makedirs(os.path.join(ROOT, "docs", "index"), exist_ok=True)
with open(os.path.join(ROOT, "docs", "index", "system_index.json"), "w", encoding="utf-8") as fh:
    json.dump(IDX, fh, ensure_ascii=False, indent=1, default=str)

g = IDX["sections"]["git_tree_flags"]
md = []
md.append("# MEMS26 · אינדקס-המערכת (נוצר אוטומטית — `scripts/system_index.py`)\n")
md.append("**נוצר:** %s · **HEAD:** `%s` · **ענף:** `%s` · **קבצים לא-מקומטים:** %s · **עץ:** %s · **דגלים פסוקים:** %s (ON %s · shadow %s · עם measured %s · אי-התאמה %s)\n"
          % (IDX["generated_at"], g["head"], g["branch"], g["dirty_files"], g["tree_version"], g["ruled_flags"], len(g["flags_on"]),
             len(g["flags_shadow"]), g["flags_measured"], g["flags_mismatch"] or "0"))
md.append("## 1 · מדיד-עכשיו (פריטים פתוחים עם צעד-מדידה, לפי חומרה) — %d\n" % len(IDX["measurable_now"]))
md.append("| # | סטטוס | כותרת | הצעד הבא |\n|---|---|---|---|")
for t in IDX["measurable_now"]:
    md.append("| %s | %s | %s | %s |" % (t["id"], t["status"], t["title"][:110].replace("|", "/"), (t["next"] or "")[:200].replace("|", "/")))
md.append("\n## 2 · מפיקים (DECISION ב-%d הימים האחרונים)\n" % DAYS)
md.append("| תבנית | מערכת | החלטות | עברו-עץ+שערים | ירי-לייב | P&L לייב | live-capable | מפסק | 3 התוצאות הנפוצות |\n|---|---|---|---|---|---|---|---|---|")
for p in producers:
    md.append("| %s | %s | %s | %s | %s | %s | %s | `%s` | %s |" % (p["pattern"], p["system"], p["decisions"], p["passed_tree_gates"], p["live_fires"],
                                                                 p["live_pnl"], p["live_capable"], p["switch"], " · ".join(p["top"])))
md.append("\n## 3 · שערים (blocked_by, %d יום)\n" % DAYS)
md.append("| שער | n |\n|---|---|")
for gt in gates:
    md.append("| `%s` | %s |" % (gt["blocked_by"], gt["n"]))
md.append("\n## 4 · העץ (%s)\n" % g["tree_version"])
md.append("עלים: %s · TAKE %s · SKIP %s · SHADOW %s · עלים עם פסיקה+מדידה: %s\n" % (leaves_info["n"], leaves_info["take"], leaves_info["skip"], leaves_info["shadow"], len(leaves_info["ruled"])))
md.append("| עלה | סשנים | $ | $ נטו | תאריך |\n|---|---|---|---|---|")
for r in leaves_info["ruled"]:
    md.append("| `%s` | %s | %s | %s | %s |" % (str(r["id"])[:90], r["sessions"], r["usd"], r["usd_net"], r["date"]))
md.append("\n## 5 · דגלים פסוקים (RULED_FLAGS ↔ .env)\n")
md.append("| דגל | צפוי | בפועל | ✓ | פסק | תאריך | measured |\n|---|---|---|---|---|---|---|")
for f in flags:
    md.append("| `%s` | %s | %s | %s | %s | %s | %s |" % (f["flag"], f["expected"][:40], f["actual"][:40], "✓" if f["ok"] else "✗", f["ruled_by"], f["date"], "✓" if f["measured"] else ""))
md.append("\n## 6 · טבלאות-DB\n")
md.append("| טבלה | שורות | max ts (IL) |\n|---|---|---|")
for t in tables:
    md.append("| `%s` | %s | %s |" % (t["table"], t["rows"], t.get("max_ts_il", t.get("max_ts", ""))))
md.append("\n## 7 · LaunchAgents\n")
md.append("| label | pid | rc |\n|---|---|---|")
for a in agents:
    md.append("| `%s` | %s | %s |" % (a["label"], a["pid"], a["rc"]))
md.append("\n## 8 · תיקטים — %d סה״כ · %d פתוחים · %s\n" % (IDX["tickets"]["total"], IDX["tickets"]["open"], IDX["tickets"]["by_status"]))
md.append("| # | סטטוס | כותרת | הצעד הבא |\n|---|---|---|---|")
for t in sorted(open_t, key=lambda t: (order.get(t["status"], 9), -int(t["id"][2:]))):
    md.append("| %s | %s | %s | %s |" % (t["id"], t["status"], t["title"][:110].replace("|", "/"), (t["next"] or "")[:160].replace("|", "/")))
md.append("\n## 9 · סקריפטים (%d)\n" % len(scripts))
md.append("| קובץ | מה |\n|---|---|")
for s in scripts:
    md.append("| `%s` | %s |" % (s["file"], s["doc"].replace("|", "/")))
md.append("\n## 10 · דוחות אחרונים\n")
for r in IDX["reports"]:
    md.append("- `%s` (%s)" % (r["file"], r["mtime"]))
md.append("\n## 11 · ריצות-הרנס אחרונות\n")
for r in runs:
    md.append("- `%s` — %s" % (r["dir"], r["last"].replace("|", "/")))
with open(os.path.join(ROOT, "docs", "index", "SYSTEM_INDEX.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(md) + "\n")
if not QUIET:
    print("index written: producers %d · gates %d · leaves %d · tables %d · agents %d · scripts %d · tickets %d (open %d, measurable %d)"
          % (len(producers), len(gates), leaves_info["n"], len(tables), len(agents), len(scripts), IDX["tickets"]["total"], IDX["tickets"]["open"], len(measurable)))
