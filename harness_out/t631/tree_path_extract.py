#!/usr/bin/env python3
"""tree_path_extract.py — T-631 (22.10): per-day tree paths for Michael's "מסלול העץ" review.

Read-only. For each session date: the demo decisions + shadow rows (v9_decision_vectors), the demo trades
(v9_trades, mode=demo) with their management log, the day-type timeline, the TPO references, and the harness
replays (gateway_decisions + trades) for the given tags; plus the live tree (config/decision_tree_v3.3.4.0.yaml)
compacted to {q, b} nodes / {leaf, id, n, usd} leaves. Output: one JSON object per line (section records).
Usage: python3 harness_out/t631/tree_path_extract.py OUT.jsonl DATE... [--tags mnxs,mnxofs] [--tree config/....yaml]
"""
import json, os, subprocess, sys

PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
DB = os.environ.get("TP_DB", "mems26")


def q(sql, db=DB):
    out = subprocess.run([PSQL, "-d", db, "-Atc", sql], capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise SystemExit("psql failed: %s" % out.stderr.strip()[:400])
    s = out.stdout.strip()
    return json.loads(s) if s else None


VEC_KEYS = ("zone", "phase", "day_type", "day_type_conf", "dir_hint", "extension", "extension_pts", "vol_ratio",
            "atr_causal", "opening_type", "bars_since_high", "bars_since_low", "ib_width", "prior_zone", "entry_kind")


def decisions(d):
    rows = q("""select json_agg(json_build_object('t', to_char(ts at time zone 'Asia/Jerusalem','HH24:MI:SS'),
        'kind', kind, 'sys', system, 'cls', classification, 'dir', direction, 'entry', entry, 'phase', phase,
        'blocked', blocked_by, 'reason', left(reason, 320), 'vec', vector) order by ts)
        from v9_decision_vectors where kind in ('DECISION','TREE_SHADOW')
        and ts >= '%s 16:25+03' and ts < '%s 23:05+03'""" % (d, d)) or []
    for r in rows:
        v = r.get("vec") or {}
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except Exception:
                v = {}
        r["vec"] = {k: v.get(k) for k in VEC_KEYS if v.get(k) not in (None, "", "null")}
    return rows


def trades(d):
    rows = q("""select json_agg(json_build_object('id', id, 'mode', mode, 'sys', firing_system, 'dir', direction,
        'entry_t', to_char(entry_ts at time zone 'Asia/Jerusalem','HH24:MI:SS'), 'entry', entry_price, 'stop', stop,
        't1', t1, 't2', t2, 't3', t3, 'exit_t', to_char(exit_ts at time zone 'Asia/Jerusalem','HH24:MI:SS'),
        'exit', exit_price, 'exit_reason', exit_reason, 'pnl', pnl_usd, 'pnl_sierra', pnl_sierra, 'outcome', outcome,
        'contracts', quality->>'contracts', 'cls', coalesce(quality->>'classification', pattern_id_at_entry),
        'dt', day_type_at_entry, 'state', state, 't1_hit', to_char(t1_hit_ts at time zone 'Asia/Jerusalem','HH24:MI:SS'),
        'stop_hit', to_char(stop_hit_ts at time zone 'Asia/Jerusalem','HH24:MI:SS')) order by entry_ts)
        from v9_trades where mode='demo' and entry_ts >= '%s 16:00+03' and entry_ts < '%s 23:30+03'""" % (d, d)) or []
    ids = [r["id"] for r in rows]
    log = []
    if ids:
        log = q("""select json_agg(row_to_json(l) order by l.id) from v9_trade_management_log l
                   where l.trade_id in (%s)""" % ",".join(str(i) for i in ids)) or []
        keep = ("id", "trade_id", "ts", "created_at", "action", "old_stop", "new_stop", "price", "reason", "note",
                "detail", "from_stop", "to_stop", "stop_before", "stop_after", "contracts", "leg")
        log = [{k: r[k] for k in r if k in keep} for r in log]
    return rows, log


def day_type_timeline(d):
    rows = q("""select json_agg(row_to_json(s) order by s.ts) from v9_day_type_state s
                where s.ts >= timestamp '%s 13:25' and s.ts < timestamp '%s 20:05'""" % (d, d)) or []
    out, last = [], None
    for r in rows:
        key = tuple(sorted((k, str(v)) for k, v in r.items() if k not in ("id", "ts", "created_at", "updated_at")))
        if key != last:
            out.append({k: r[k] for k in r if k in ("ts", "day_type", "confidence", "opening_type", "direction",
                                                     "extension", "ib_high", "ib_low", "stage", "day_type_conf",
                                                     "ext", "ib_locked", "label", "conf", "opening", "dir")})
            last = key
    return out


def tpo(d, prev):
    rows = q("""select json_agg(row_to_json(t)) from v9_tpo_sessions t where t.trading_date in ('%s','%s')""" % (prev, d)) or []
    keep = ("trading_date", "poc_price", "vah_price", "val_price", "ib_high", "ib_low", "ib_width", "ib_class",
            "range_high", "range_low", "session_type", "profile_shape", "letter_count", "total_volume")
    return [{k: r[k] for k in r if k in keep} for r in rows]


def bars(d):
    return q("""select json_agg(json_build_object('t', to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), 'o', open,
        'h', high, 'l', low, 'c', close, 'v', volume, 'cd', cumulative_delta) order by ts) from v9_bars_5min
        where ts >= '%s 16:30+03' and ts < '%s 23:00+03'""" % (d, d)) or []


def harness(tag, d):
    p = os.path.join("harness_out", "t628", "days", "%s_%s.json" % (tag, d))
    if not os.path.exists(p):
        return None
    j = json.load(open(p))
    gd = []
    for e in j.get("gateway_decisions", []):
        t3 = e.get("tree_v3") or {}
        vec = t3.get("vec") or {}
        gd.append({"ts": e.get("ts"), "sys": e.get("system"), "pattern": e.get("pattern"), "dir": e.get("direction"),
                   "entry": e.get("entry"), "blocked": e.get("blocked_by"), "reason": (e.get("reason") or "")[:240],
                   "outcome": e.get("outcome"), "trade_id": e.get("trade_id"),
                   "leaf": t3.get("leaf"), "id": t3.get("id"), "path": t3.get("path"),
                   "vec": {k: vec.get(k) for k in ("opening_type", "phase", "day_type", "structure", "kind", "rel_bias",
                                                    "zone", "prior_zone", "value_migration", "edge", "test", "volume",
                                                    "delta", "hour", "turn", "turn_rel")},
                   "skip_gates": e.get("skip_gates"), "ibr": e.get("ibr")})
    tr = []
    for t in j.get("trades", []):
        tr.append({k: t.get(k) for k in ("trade_id", "classification", "direction", "entry", "stop_initial", "contracts",
                                         "fired_il", "fill_price", "legs", "pnl_usd", "outcome", "exit_il",
                                         "day_type_at_entry", "t1_target", "t1_pts", "mfe_pts", "mae_pts", "tightened")})
    s1, last = [], None
    for r in j.get("s1", []):
        key = (r.get("machine_opening"), r.get("published"), r.get("live_label"), r.get("ot_locked"), r.get("ib_locked"))
        if key != last:
            s1.append(r)
            last = key
    return {"tag": tag, "date": d, "daily_pnl": j.get("daily_pnl_harness"), "flags": j.get("flags"),
            "f5_trail": j.get("f5_trail"), "decisions": gd, "trades": tr, "s1": s1}


def compact_tree(node):
    if not isinstance(node, dict):
        return node
    if "leaf" in node or "action" in node:
        m = node.get("measured") or {}
        return {"leaf": node.get("leaf") or node.get("action"), "id": node.get("id"),
                "n": m.get("n"), "usd": m.get("usd"), "win": m.get("win"), "note": (node.get("note") or node.get("why") or "")[:120]}
    split = node.get("split")
    br = node.get("branches") or {}
    if split is None and not br:
        return {k: compact_tree(v) for k, v in node.items()}
    return {"q": split, "id": node.get("id"), "b": {str(k): compact_tree(v) for k, v in br.items()}}


def main():
    skip = {i + 1 for i, a in enumerate(sys.argv) if a in ("--tags", "--tree")}
    args = [a for i, a in enumerate(sys.argv) if i > 0 and i not in skip and not a.startswith("--")]
    out, dates = args[0], args[1:]
    tags = "mnxs"
    tree_path = "config/decision_tree_v3.3.4.0.yaml"
    for i, a in enumerate(sys.argv):
        if a == "--tags":
            tags = sys.argv[i + 1]
        if a == "--tree":
            tree_path = sys.argv[i + 1]
    tags = tags.split(",")
    with open(out, "w") as f:
        try:
            import yaml
            y = yaml.safe_load(open(tree_path))
            root = y.get("root", y)
            f.write(json.dumps({"section": "tree", "path": tree_path, "version": y.get("version"), "tree": compact_tree(root)},
                               ensure_ascii=False, separators=(",", ":")) + "\n")
        except Exception as e:
            f.write(json.dumps({"section": "tree", "error": str(e)[:300]}) + "\n")
        for d in dates:
            pd = q("select to_json(max((ts at time zone 'America/New_York')::date)::text) from v9_bars_5min where (ts at time zone 'America/New_York')::date < '%s'" % d)
            tr, log = trades(d)
            rec = {"section": "day", "date": d, "prev": pd, "tpo": tpo(d, pd), "bars": bars(d),
                   "day_type": day_type_timeline(d), "decisions": decisions(d), "trades": tr, "tm_log": log}
            f.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":"), default=str) + "\n")
            for tag in tags:
                h = harness(tag, d)
                if h:
                    f.write(json.dumps(dict(section="harness", **h), ensure_ascii=False, separators=(",", ":"), default=str) + "\n")
    sz = os.path.getsize(out)
    print("wrote", out, sz, "bytes;", sum(1 for _ in open(out)), "lines")


if __name__ == "__main__":
    main()
