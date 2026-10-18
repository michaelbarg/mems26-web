#!/usr/bin/env python3
"""phone_reply.py — append an agent reply to the durable phone thread.

Usage: python3 scripts/phone_reply.py <sender> "<text>"
Writes docs/handoff/PHONE_THREAD.jsonl (the source of truth the relay pushes
to Render every cycle) and POSTs /reply for instant display — then VERIFIES
the delivery on Render (T-260, BRIEF §3.5) and says what it saw.
Display-only; never touches trading.

{NOW} token (added 08.09, cowork): any occurrence of {NOW} in <text> is replaced
at SEND time with the local wall clock (HH:MM). Agents compose the message body
before the send call and had been estimating "נמדד HH:MM" forward by a few
minutes — it happened three times in two days (07.09 15:50, 07.09 19:15,
08.09 11:09). Writing "נמדד {NOW}" makes the stamp a measurement instead of a
guess. No behaviour change when the token is absent.

Delivery verification (added 19.10, fix-agent, T-260 / BRIEF §3.5 — the phone
channel lost agent messages silently on two independent paths and this script
printed "ok" on both):
  (1) Render's /reply rejects text > 2000 chars with 400 — the 04.09 21:17 night
      report (2402 chars) was swallowed by `except Exception: pass` and reported
      as sent. Now: a text over 2000 chars is REFUSED before anything is written
      or sent (nothing to resend twice); the length is measured in Python chars.
  (2) Render's /reply store is RAM on a free-tier service that cold-starts (and
      is wiped by every deploy); the page can be dark while the relay window is
      closed (05.10 13:07). Now: after the POST the script reads GET /chat and
      looks for its own line (sender + text); the last stdout line is
        ok render=verified reply=200 ntfy=<..> len=<n>          (exit 0)
        UNVERIFIED render=<why> reply=<..> ntfy=<..> len=<n>     (exit 2)
      UNVERIFIED is a measurement, not a failure to act on by resending: the
      line IS in PHONE_THREAD.jsonl and the relay re-pushes it inside
      RELAY_WINDOW_IL — a second send is a T-369 violation. Re-check GET /chat.
  With no MOBILE_ACCESS_KEY in .env there is no Render path at all (tests):
        ok render=no-key ntfy=<..> len=<n>                       (exit 0)
"""
import json, os, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "docs", "handoff", "PHONE_THREAD.jsonl")
RENDER = "https://mems26-mobile.onrender.com"
MAX_CHARS = 2000            # render_mobile_relay/app.py post_reply: len(text) > 2000 ⇒ HTTP 400
_urlopen = urllib.request.urlopen   # one seam for the regression tests (no network in tests)


def _read_env(root):
    """MOBILE_ACCESS_KEY / NTFY_TOPIC / PHONE_REPLY_NTFY from <root>/.env (missing file ⇒ empty)."""
    key, ntfy_topic, ntfy_on = "", "", "1"
    try:
        for line in open(os.path.join(root, ".env"), encoding="utf-8"):
            if line.startswith("MOBILE_ACCESS_KEY="):
                key = line.split("=", 1)[1].strip()
            elif line.startswith("NTFY_TOPIC="):
                ntfy_topic = line.split("=", 1)[1].strip()
            elif line.startswith("PHONE_REPLY_NTFY="):
                ntfy_on = line.split("=", 1)[1].strip()
    except Exception:
        pass
    return key, ntfy_topic, ntfy_on


def _post(url, data, headers, timeout):
    """POST and return a short status token: '200' | 'http=400' | 'timeout' | 'err=<Exc>' — never raises."""
    try:
        req = urllib.request.Request(url, data=data, method="POST", headers=headers)
        with _urlopen(req, timeout=timeout) as r:
            r.read()
            return str(getattr(r, "status", None) or getattr(r, "code", None) or 200)
    except urllib.error.HTTPError as e:
        return f"http={e.code}"
    except Exception as e:
        return "timeout" if "timed out" in str(e).lower() else f"err={type(e).__name__}"


def verify_on_render(key, sender, text, timeout=12, retry_sleep=3):
    """GET /chat and look for THIS line (sender + text). Returns (found, reason).
    One retry after `retry_sleep` s when the GET itself failed (cold start) — not when it answered without us."""
    url = f"{RENDER}/chat?key={key}"
    last = ""
    for attempt in (1, 2):
        try:
            with _urlopen(urllib.request.Request(url), timeout=timeout) as r:
                items = (json.loads(r.read().decode("utf-8")) or {}).get("items") or []
        except urllib.error.HTTPError as e:
            return False, f"chat http={e.code}"
        except Exception as e:
            last = "chat timeout" if "timed out" in str(e).lower() else f"chat err={type(e).__name__}"
            if attempt == 1 and retry_sleep:
                time.sleep(retry_sleep)
            continue
        for i in items:
            if (i.get("sender") or "") == sender[:20] and (i.get("text") or "").strip() == text:
                return True, f"items={len(items)}"
        return False, f"not-in-chat items={len(items)}"
    return False, last or "chat unreachable"


def main():
    # Switch guard (added 15.09, cowork). `text = argv[-1]` means ANY single
    # argument becomes the message body — so `phone_reply.py --help` SENDS the
    # word "--help" to Michael's phone instead of printing usage. That happened
    # three times: 03.09 09:15, 04.09 15:44, 15.09 15:09 (all three are in
    # PHONE_THREAD.jsonl / the Render feed; Render has no delete endpoint, and a
    # correction message is itself a phone-rule violation). A bare switch token
    # is never a real message, so refuse it and print the docstring instead.
    argv = sys.argv[1:]
    if not argv or argv[-1].strip() in ("-h", "--help", "help", "-?", "/?"):
        sys.exit(__doc__)
    sender = argv[0] if len(argv) > 1 else "cowork"
    # Sender guard (added 21.09, cowork-dev). The sender is POSITIONAL, but the
    # sibling script `channel_post.py` takes `--frm <who>` — and the habit
    # carries over: `phone_reply.py --frm cowork-dev "<text>"` parses as
    # sender="--frm" with "cowork-dev" silently DROPPED as a middle argument.
    # It reached Michael's phone that way on 21.09 16:17:01Z: body correct, but
    # the thread shows "--frm" as the author. Render has no delete endpoint and
    # a correction message is itself a phone-rule violation (T-369 flooding),
    # so the only fix is to never let it send. Refuse and print the usage.
    if sender.startswith("-"):
        sys.exit(f"refusing to send with sender={sender!r} — the sender is "
                 f"POSITIONAL, not a flag (that is channel_post.py).\n"
                 f"Did you mean:  phone_reply.py {argv[1] if len(argv) > 2 else 'cowork-dev'} \"<text>\"\n"
                 f"{__doc__}")
    text = argv[-1].strip()
    if not text:
        sys.exit("empty text")
    if text.startswith("-") and not text[1:].strip().startswith(" ") and len(text.split()) == 1:
        sys.exit(f"refusing to send bare switch token {text!r} as a message body\n{__doc__}")
    # Stamp the clock at send time, not at compose time (see module docstring).
    text = text.replace("{NOW}", time.strftime("%H:%M", time.localtime()))
    # T-260 (1): the 2000-char ceiling is Render's hard 400 — refuse BEFORE the thread line is written, so the
    # agent shortens and sends once (a line already in the thread + a resend = the same report twice, T-369).
    if len(text) > MAX_CHARS:
        sys.exit(f"refusing: text is {len(text)} chars > {MAX_CHARS} — Render /reply rejects it with 400 "
                 f"(T-260); nothing was written or sent — shorten and send once")
    item = {"sender": sender, "text": text,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "status": ""}
    with open(P, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    key, ntfy_topic, ntfy_on = _read_env(ROOT)
    # 16.09 (Michael: the phone page is not comfortable to read): mirror the
    # same message as a push notification on the ntfy topic the backend already
    # uses for trade events, so a report reaches the phone without opening the
    # page. Best-effort, display-only; PHONE_REPLY_NTFY=0 in .env disables it.
    ntfy = "off"
    if ntfy_topic and ntfy_on != "0":
        ntfy = _post(f"https://ntfy.sh/{ntfy_topic}", text.encode("utf-8"),
                     {"Title": ("MEMS26 - " + sender).encode("ascii", "ignore").decode(),
                      "Content-Type": "text/plain; charset=utf-8"}, timeout=5)
    if not key:
        print(f"ok render=no-key ntfy={ntfy} len={len(text)}")
        return
    # timeout 10 → 30 (T-260 (ג): a free-tier cold start was measured at 22.9 s — the 08:30 message lands outside
    # RELAY_WINDOW_IL, i.e. on a cold instance). Worst case of the whole send: 30 + 12 + 3 + 12 = 57 s < the 60 s
    # tool limit the agents run under.
    reply = _post(f"{RENDER}/reply?key={key}", json.dumps({"sender": sender, "text": text}).encode(),
                  {"Content-Type": "application/json"}, timeout=30)
    # T-260 (2): the delivery is what Render SHOWS, not what the POST returned — read it back.
    found, why = verify_on_render(key, sender, text)
    if found:
        print(f"ok render=verified reply={reply} ntfy={ntfy} len={len(text)}")
        return
    print(f"UNVERIFIED render={why} reply={reply} ntfy={ntfy} len={len(text)} — the line IS in "
          f"PHONE_THREAD.jsonl (the relay re-pushes it inside RELAY_WINDOW_IL); do NOT resend (T-369) — "
          f"re-check: GET {RENDER}/chat?key=…")
    sys.exit(2)


if __name__ == "__main__":
    main()
