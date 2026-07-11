import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

// §6 (PROMPT_SYSTEMS_TRADE_UX_2026-07-10) — serve the session-watch liveness beacon
// docs/reports/AGENT_HEARTBEAT.json to the TopBar. Frontend-only: a small Next route
// that reads the repo file server-side. Honest-missing → { exists:false } (the dot then
// renders gray "not checked" — truth, not fabrication).
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

// process.cwd() is the dir `next dev` runs from (frontend/v9). Try a few parents so it
// resolves whether launched from frontend/v9 or the repo root.
const CANDIDATES = [
  path.join(process.cwd(), '..', '..', 'docs', 'reports', 'AGENT_HEARTBEAT.json'),
  path.join(process.cwd(), '..', 'docs', 'reports', 'AGENT_HEARTBEAT.json'),
  path.join(process.cwd(), 'docs', 'reports', 'AGENT_HEARTBEAT.json'),
];

export async function GET() {
  for (const p of CANDIDATES) {
    try {
      const raw = await fs.readFile(p, 'utf8');
      const data = JSON.parse(raw);
      return NextResponse.json(
        { exists: true, ...data },
        { headers: { 'Cache-Control': 'no-store' } },
      );
    } catch {
      /* try next candidate */
    }
  }
  return NextResponse.json({ exists: false }, { headers: { 'Cache-Control': 'no-store' } });
}
