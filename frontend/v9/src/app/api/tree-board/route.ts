import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

// T-521 (מייקל 01.10: "תוסיף את עץ-ההחלטות במבנה התלת-מימדי של הקנבס גם לפרונט-אנד") —
// serves the nightly measured board of DECISION_TREE_V3 (scripts/tree_measure.py →
// render_mobile_relay/static/docs/data/tree_v3.json: the nested tree with n/win/Σ$ on every
// node + the leaf list) to the desktop star-field. Frontend-only Next route that reads the
// repo file server-side (same pattern as api/agent-heartbeat) — no backend restart needed.
// Honest-missing → 404 {error} (the field then says "אין לוח" instead of drawing nothing).
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const REL = ['render_mobile_relay', 'static', 'docs', 'data', 'tree_v3.json'];
// process.cwd() is the dir `next dev` runs from (frontend/v9). Try a few parents so it
// resolves whether launched from frontend/v9 or the repo root.
const CANDIDATES = [
  path.join(process.cwd(), '..', '..', ...REL),
  path.join(process.cwd(), '..', ...REL),
  path.join(process.cwd(), ...REL),
];

export async function GET() {
  for (const p of CANDIDATES) {
    try {
      const [raw, st] = await Promise.all([fs.readFile(p, 'utf8'), fs.stat(p)]);
      const data = JSON.parse(raw);
      return NextResponse.json(
        { ...data, file_mtime: st.mtime.toISOString() },
        { headers: { 'Cache-Control': 'no-store' } },
      );
    } catch {
      /* try next candidate */
    }
  }
  return NextResponse.json(
    { error: 'tree_v3.json not found — run scripts/tree_measure.py' },
    { status: 404, headers: { 'Cache-Control': 'no-store' } },
  );
}
