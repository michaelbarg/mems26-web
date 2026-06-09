# Two-Mac Setup over Tailscale — Production (Mac #2) + Dev (this Mac)

**Created:** 2026-06-04 · **Owner:** Michael

## Goal & roles

| Machine | Role | Runs |
|---------|------|------|
| **Mac #2** | **Production / source of truth** | Sierra Chart + `MES_AI_DataExport` DLL → exports → bridge → backend `127.0.0.1:8000` → Postgres `localhost/mems26` → frontend `:3000`. All services bound to **localhost**. |
| **This Mac** | **Development** | Editing, tests, builds. Pulls live data + dashboard from Mac #2 over Tailscale. **Does not** run the live stack or a second DB. |

## Core principle — nothing about the stack changes

This setup adds **zero** changes to service bindings or the bridge. Specifically it
preserves every guardrail in `CLAUDE.md`:

- The **bridge still pushes only to `http://localhost:8000`** inside Mac #2. Tailscale is
  never in that path. `CLOUD_URL` stays `http://localhost:8000`.
- The **backend stays bound to `127.0.0.1:8000`** (as in `scripts/start_all.sh`). No
  rebind to `0.0.0.0` or a tailnet IP — that would expose the single-worker uvicorn.
- The dev Mac reaches the services through **SSH port-forwarding over Tailscale** — a
  private, encrypted tunnel. No port is ever opened to the network.

> Why tunnels and not Tailscale Serve / rebinding: keeping services on `localhost`
> means the only way in is an authenticated SSH session over the tailnet. This is the
> *smallest correct change* and keeps the localhost-only discipline intact.

---

## Step 1 — Install Tailscale on both Macs

On **each** Mac:

```bash
brew install --cask tailscale     # or download the app from tailscale.com
```

Open the app and sign in **both Macs to the same Tailscale account** (same tailnet).

In the Tailscale admin console (login.tailscale.com), enable **MagicDNS** so each
machine has a stable name. Give Mac #2 a clear hostname (e.g. `mac2`).

Verify from the dev Mac:

```bash
tailscale status            # both machines listed, state "active"
tailscale ping mac2         # direct connection succeeds
```

## Step 2 — Enable SSH into Mac #2

Easiest is **Tailscale SSH** (auth via tailnet ACLs, no separate keys). On **Mac #2**:

```bash
sudo tailscale up --ssh
```

(Or, classic SSH: System Settings → General → Sharing → **Remote Login = ON**, limited
to your user, then use an SSH key.)

Verify from the dev Mac:

```bash
ssh michael@mac2 'hostname && sw_vers -productVersion'
```

## Step 3 — Sync code via the existing GitHub remote

The repo already has a remote: `github-mems26:michaelbarg/mems26-web.git` (an SSH host
alias). Use GitHub as the sync point between the two Macs — no Tailscale needed for git.

On **Mac #2**, make sure `~/.ssh/config` has the same `github-mems26` alias + key, then
clone to the **identical path** (paths are hard-coded in `scripts/start_all.sh`):

```bash
git clone github-mems26:michaelbarg/mems26-web.git /Users/michael/Downloads/mems26_web_git
cd /Users/michael/Downloads/mems26_web_git
git checkout stabilize/mems26-local-truth-2026-05-16   # current working branch
```

Daily workflow:

- Edit on **dev Mac** → `git commit` → `git push`.
- On **Mac #2** → `git pull` → restart the affected service if needed.

> One DB, one stack. Only Mac #2 runs the services and Postgres. Never point a second
> running stack at the same `mems26` database.

## Step 4 — Bring up the stack on Mac #2

Per `CLAUDE.md` § Service Bring-Up, first check nothing is already listening:

```bash
lsof -iTCP:3000 -sTCP:LISTEN; lsof -iTCP:8000 -sTCP:LISTEN
```

Then start (bridge + backend `:8000` + frontend `:3000`):

```bash
cd /Users/michael/Downloads/mems26_web_git
bash scripts/start_all.sh
```

Reminders from the guardrails:
- `DATABASE_URL=postgresql://localhost/mems26` (local Postgres, never cloud PG).
- Sierra Study **Input 4** export dir = `/Users/michael/SierraChart_Data/v9_export/`.
- Bridge LaunchAgent uses conditional `KeepAlive` + `V9_DISABLE_WATCHDOG=1` — do not change.

## Step 5 — Access from the dev Mac (SSH tunnels)

One command forwards all three ports. Run it on the **dev Mac** and leave it open:

```bash
ssh -N \
  -L 3000:localhost:3000 \
  -L 8000:localhost:8000 \
  -L 5432:localhost:5432 \
  michael@mac2
```

Now, on the **dev Mac**:

- **Dashboard:** http://localhost:3000  (frontend on Mac #2)
- **API / docs:** http://localhost:8000/docs  (backend on Mac #2)
- **Postgres:** `psql -h localhost -p 5432 mems26`

Why it "just works": the dashboard's browser calls `localhost:8000`, which is *also*
tunneled to Mac #2's backend — so the page, its API calls, and the WebSocket feed all
resolve through the tunnel with no code change.

**Caveat (single-worker backend):** dev viewing is occasional and fine. Do **not** leave a
second always-on dashboard polling Mac #2 — the polling floors in `CLAUDE.md` are tuned
for one viewer.

Optional convenience: wrap the tunnel in `autossh` or a dev-side LaunchAgent so it
reconnects. Keep it **manual-start** if you'd rather not imply the dev Mac is "live".

## Step 6 — Verify

```bash
# 1. Tailnet up
tailscale status                       # both nodes active

# 2. Health on Mac #2 directly
ssh michael@mac2 'curl -s -m2 localhost:8000/health'

# 3. With the tunnel open, same health from the dev Mac
curl -s -m2 localhost:8000/health      # must match (2)

# 4. Dashboard renders on dev
open http://localhost:3000

# 5. DB reachable + recency sane (adjust table name)
psql -h localhost -p 5432 mems26 -c "select max(ts) from bars;"
```

If `ssh michael@mac2 'tail -f /tmp/bridge.err.log'` ever shows
`API push FAILED to https://...`, **stop the bridge and investigate** — that means a
`CLOUD_URL` drift, per the Bridge Local-Only Rule.

---

## What this does NOT change (anti-regression checklist)

- ❌ No rebind of backend off `127.0.0.1`.
- ❌ No change to `CLOUD_URL` / bridge push target.
- ❌ No change to LaunchAgent `KeepAlive` / watchdog settings.
- ❌ No increase to frontend polling intervals.
- ✅ Dev access is read-only-by-network: an authenticated SSH tunnel, nothing exposed.
