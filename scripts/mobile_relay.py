#!/usr/bin/env python3
"""MEMS26 mobile relay — pushes snapshot + polls emergency commands from Render.

07-21 (Michael): mobile link via Render, display-only, trading stays local.
08-04 (Michael): emergency commands (FLATTEN/PAUSE/RESUME) via pull-based relay.

Loop every ~5s:
  1. GET local /api/v9/mobile/data → POST Render /api/v9/mobile/snapshot (display)
  2. GET Render /cmd/pending → if command: execute locally → POST Render /cmd/ack

Run by LaunchAgent com.mems26.mobile_relay. Log: /tmp/mobile_relay.log.
"""
import json
import os
import sys
import time
import urllib.request

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
LOCAL = "http://localhost:8000/api/v9/mobile"
INTERVAL_OK = 5
INTERVAL_BAD = 30


def _env() -> dict:
    out = {}
    try:
        for line in open(ENV_PATH, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.split(" #")[0].strip()
    except Exception as e:
        print(f"[relay] .env read failed: {e}", flush=True)
    return out


def _push_snapshot(access_key, push_key, render):
    """Push local snapshot to Render."""
    with urllib.request.urlopen(f"{LOCAL}/data?key={access_key}", timeout=4) as r:
        data = r.read()
    req = urllib.request.Request(
        f"{render}/api/v9/mobile/snapshot", data=data, method="POST",
        headers={"Content-Type": "application/json", "X-Push-Key": push_key})
    with urllib.request.urlopen(req, timeout=15) as r:
        json.loads(r.read().decode())


def _push_chat_thread(push_key, render):
    """Push the durable phone chat thread (Michael 26.08: 'אני לא רואה את
    ההודעות שלכם — כל הרעיון שיהיה דו-סטרי'). Render memory is wiped on every
    deploy, so the Mac re-pushes the thread from the durable JSONL each cycle."""
    try:
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "docs", "handoff", "PHONE_THREAD.jsonl")
        if not os.path.isfile(p):
            return
        items = []
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        items.append(json.loads(line))
                    except Exception:
                        pass
        payload = json.dumps({"items": items[-30:]}).encode()
        req = urllib.request.Request(
            f"{render}/chat_push", data=payload, method="POST",
            headers={"Content-Type": "application/json", "X-Push-Key": push_key})
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()
    except Exception:
        pass  # display-only; never break the snapshot loop


def _poll_instructions(access_key, render):
    """Pull Michael's phone instructions into the durable thread + inbox.

    26.08 (Michael): "שלחתי הרבה הודעות ולא קיבלתי תשובות - רנדר לסדר מיידית".
    Root cause: scripts/inbox_relay.py was built but NEVER launched (no
    LaunchAgent) — instructions sat on Render unanswered. Folded here so ONE
    daemon owns the whole phone pipe. Flow: pending → append to
    PHONE_THREAD.jsonl (durable; _push_chat_thread echoes it back so Michael
    sees his message with 'התקבל ✓') + MICHAEL_INBOX.md (agents read) → mark
    done on Render. Dedup by instruction id stored in the thread lines.
    Instructions are tracking text, never auto-executed (bridge-local rule)."""
    try:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        p_thread = os.path.join(root, "docs", "handoff", "PHONE_THREAD.jsonl")
        p_inbox = os.path.join(root, "docs", "handoff", "MICHAEL_INBOX.md")
        with urllib.request.urlopen(
                f"{render}/instruction/pending?key={access_key}", timeout=8) as r:
            items = json.loads(r.read().decode()).get("items", [])
        if not items:
            return
        seen = set()
        if os.path.isfile(p_thread):
            for line in open(p_thread, encoding="utf-8"):
                try:
                    seen.add(json.loads(line).get("id"))
                except Exception:
                    pass
        for it in items:
            iid = it.get("id")
            if iid and iid not in seen:
                with open(p_thread, "a", encoding="utf-8") as f:
                    f.write(json.dumps(
                        {"sender": "מייקל", "text": it.get("text", ""),
                         "ts": it.get("ts", ""), "id": iid,
                         "status": "התקבל ✓"}, ensure_ascii=False) + "\n")
                with open(p_inbox, "a", encoding="utf-8") as f:
                    f.write(f"### [{it.get('ts', '')}] מייקל (מהפלאפון) · "
                            f"ID {iid}\n{it.get('text', '')}\n\n")
                # 26.08 (Michael): "ברגע שליחת הודעה - קלוד קוד חייב להגיב
                # שקיבל" + 27.08: "שיח רציף שאני לא מול המחשב". Instant
                # receipt WITH live status (answers "מה מצבנו" classes at
                # zero latency); a real agent adds substance within ≤30min
                # via the scheduled responder run.
                import datetime as _dt
                _ack_ts = _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                _st = ""
                try:
                    _ak = _env().get("MOBILE_ACCESS_KEY", "")
                    with urllib.request.urlopen(
                            f"{LOCAL}/data?key={_ak}", timeout=4) as _r:
                        _d = json.loads(_r.read().decode())
                    _s = _d.get("sierra", {}) or {}
                    _mode = "לייב" if _s.get("is_sim") == 0 else "סים"
                    _armed = "חמוש" if _s.get("order_placement_armed") == 1 else "לא-חמוש"
                    _st = (f" · מצב-חי: {_mode}+{_armed} · פוזיציה {_s.get('position_qty', '?')}"
                           f" · P&L-יום {_s.get('daily_pnl', '?')}"
                           f" · מחיר {_s.get('last_price', '?')}")
                except Exception:
                    _st = " · (מצב-חי לא זמין כרגע)"
                with open(p_thread, "a", encoding="utf-8") as f:
                    f.write(json.dumps(
                        {"sender": "cc", "text": "✓ התקבל" + _st +
                         " · סוכן יענה בהרחבה (עד ~30 דק')", "ts": _ack_ts,
                         "id": f"{iid}-ack", "status": ""},
                        ensure_ascii=False) + "\n")
                print(f"[relay] instruction {iid} → thread+inbox+ack", flush=True)
            body = json.dumps({"id": iid, "status": "done"}).encode()
            req = urllib.request.Request(
                f"{render}/instruction/status?key={access_key}", data=body,
                headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=8)
    except Exception as e:
        print(f"[relay] instr poll: {str(e)[:80]}", flush=True)


def _poll_commands(access_key, render):
    """Poll Render for pending emergency commands and execute locally."""
    try:
        with urllib.request.urlopen(
            f"{render}/cmd/pending?key={access_key}", timeout=5
        ) as r:
            resp = json.loads(r.read().decode())
        cmd = resp.get("cmd")
        if cmd is None:
            return
        action = cmd.get("action", "").upper()
        cmd_id = cmd.get("id")
        print(f"[relay] COMMAND RECEIVED: {action} (id={cmd_id})", flush=True)

        # Execute locally
        ok = _execute_local(action, access_key)

        # ACK to Render (clears queue)
        ack_data = json.dumps({"id": cmd_id}).encode()
        ack_req = urllib.request.Request(
            f"{render}/cmd/ack?key={access_key}",
            data=ack_data, method="POST",
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(ack_req, timeout=5) as r:
            json.loads(r.read().decode())
        print(f"[relay] COMMAND ACK sent (ok={ok})", flush=True)

    except Exception as e:
        # Command polling failures are non-fatal
        if "HTTP Error 401" not in str(e):
            print(f"[relay] cmd poll: {str(e)[:80]}", flush=True)


def _execute_local(action, access_key):
    """Execute command on the local trading machine."""
    try:
        if action == "FLATTEN":
            data = json.dumps({"confirm": "FLATTEN"}).encode()
            req = urllib.request.Request(
                f"{LOCAL}/flatten?key={access_key}",
                data=data, method="POST",
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as r:
                resp = json.loads(r.read().decode())
            print(f"[relay] FLATTEN result: {resp}", flush=True)
            return resp.get("ok", False)

        elif action == "PAUSE":
            data = json.dumps({"confirm": "PAUSE"}).encode()
            req = urllib.request.Request(
                f"{LOCAL}/pause?key={access_key}",
                data=data, method="POST",
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as r:
                resp = json.loads(r.read().decode())
            print(f"[relay] PAUSE result: {resp}", flush=True)
            return resp.get("ok", False)

        elif action == "RESUME":
            data = json.dumps({"confirm": "RESUME"}).encode()
            req = urllib.request.Request(
                f"{LOCAL}/resume?key={access_key}",
                data=data, method="POST",
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as r:
                resp = json.loads(r.read().decode())
            print(f"[relay] RESUME result: {resp}", flush=True)
            return resp.get("ok", False)

        elif action.startswith("GATE_OFF:") or action.startswith("GATE_ON:"):
            # 2026-08-19 (Michael): phone gate-override. Backend enforces the
            # whitelist; session-scoped (restart reverts).
            gate = action.split(":", 1)[1].lower()
            data = json.dumps({"gate": gate,
                               "restore": action.startswith("GATE_ON:")}).encode()
            req = urllib.request.Request(
                f"{LOCAL}/gate_override?key={access_key}",
                data=data, method="POST",
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as r:
                resp = json.loads(r.read().decode())
            print(f"[relay] {action} result: {resp}", flush=True)
            return resp.get("ok", False)

        else:
            print(f"[relay] unknown action: {action}", flush=True)
            return False

    except Exception as e:
        print(f"[relay] local exec failed: {str(e)[:80]}", flush=True)
        return False


def _in_active_window(env: dict) -> bool:
    """Free-tier hours budget (Michael 13.08: "רנדר בחינם, לא בחבילה שעולה כסף").

    Render free tier = 750 instance-hours/month for the WHOLE workspace; a
    service stays awake as long as traffic arrives, and our 5s pushes are
    exactly such traffic. Two machines pushing 24/7 ≈ 1,460h → mid-month
    suspension (the mems26-web class of death). Gating the pusher to the
    trading window keeps both phone services free AND alive:
      RELAY_WINDOW_IL="11:30-23:59" (default when set) ≈ 12.5h/day
      RELAY_DAYS_IL="Sun,Mon,Tue,Wed,Thu,Fri" (Sat = market closed)
      ⇒ ~325h/month per service, ~650h for two < 750 ✓
    Unset RELAY_WINDOW_IL → 24/7 (backward-compatible). Outside the window
    the loop idles (no push, no cmd-poll) — the Render service spins down,
    the page still opens (cold start ~50s) showing the last snapshot.
    """
    win = (env.get("RELAY_WINDOW_IL", "") or "").strip()
    if not win:
        return True
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Asia/Jerusalem"))
        days = (env.get("RELAY_DAYS_IL", "Sun,Mon,Tue,Wed,Thu,Fri") or "").strip()
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        if day_names[now.weekday()] not in [d.strip() for d in days.split(",")]:
            return False
        lo, hi = win.split("-")
        lo_h, lo_m = (int(x) for x in lo.split(":"))
        hi_h, hi_m = (int(x) for x in hi.split(":"))
        cur = now.hour * 60 + now.minute
        return (lo_h * 60 + lo_m) <= cur <= (hi_h * 60 + hi_m)
    except Exception as e:
        print(f"[relay] window parse error ({e}) — failing OPEN (24/7)", flush=True)
        return True


def _push_idle_notice(push_key: str, render: str, env: dict) -> None:
    """Tell the page it is idle BY DESIGN and when live data resumes."""
    win = (env.get("RELAY_WINDOW_IL", "") or "").strip()
    tag = (env.get("MACHINE_TAG", "") or "").strip()
    body = json.dumps({
        "relay_idle": True,
        "relay_window_il": win,
        "relay_days_il": (env.get("RELAY_DAYS_IL", "") or "").strip(),
        "relay_note": (f"הממסר במנוחה מתוכננת (חסכון בתוכנית-החינם). "
                       f"נתונים חיים בחלון {win} (שעון ישראל)."),
        "machine": tag or None,
    }).encode()
    req = urllib.request.Request(
        f"{render}/api/v9/mobile/snapshot", data=body, method="POST",
        headers={"Content-Type": "application/json", "X-Push-Key": push_key})
    with urllib.request.urlopen(req, timeout=15) as r:
        r.read()
    print(f"[relay] idle notice pushed (window={win})", flush=True)


def main() -> None:
    env = _env()
    access_key = env.get("MOBILE_ACCESS_KEY", "")
    push_key = env.get("MOBILE_PUSH_KEY", "")
    render = (env.get("RENDER_MOBILE_URL", "") or "").rstrip("/")
    if not (access_key and push_key and render):
        print("[relay] missing MOBILE_ACCESS_KEY/MOBILE_PUSH_KEY/RENDER_MOBILE_URL — exit", flush=True)
        sys.exit(1)
    print(f"[relay] start → {render} (interval {INTERVAL_OK}s, cmd relay enabled, "
          f"window={env.get('RELAY_WINDOW_IL') or '24/7'})", flush=True)
    fails = 0
    idle_logged = False
    while True:
        if not _in_active_window(env):
            if not idle_logged:
                print("[relay] outside active window — idling (free-tier hours budget)", flush=True)
                idle_logged = True
            # 14.08 (Michael: "אם רנדר לא עובד מסיבות חכמות אני רוצה שזה יופיע
            # באפליקציה עם הסבר מתי זה יעבוד"): push ONE heartbeat per idle
            # cycle carrying the window, so the page can say "idle by design,
            # data resumes at HH:MM" instead of a bare "stale" scare. One push
            # every 10 min costs nothing against the free-tier budget.
            try:
                if int(time.time()) % 600 < 60:
                    _push_idle_notice(push_key, render, env)
            except Exception:
                pass
            time.sleep(60)
            continue
        idle_logged = False
        try:
            _push_snapshot(access_key, push_key, render)
            _poll_instructions(access_key, render)
            _push_chat_thread(push_key, render)
            if fails:
                print(f"[relay] recovered after {fails} fails", flush=True)
            fails = 0
        except Exception as e:
            fails += 1
            if fails in (1, 5) or fails % 60 == 0:
                print(f"[relay] fail #{fails}: {str(e)[:90]}", flush=True)

        # Poll commands from Render (even if snapshot push failed)
        _poll_commands(access_key, render)

        time.sleep(INTERVAL_BAD if fails >= 5 else INTERVAL_OK)


if __name__ == "__main__":
    main()
