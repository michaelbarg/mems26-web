'use client';
import { useEffect, useState } from 'react';

// §6 (PROMPT_SYSTEMS_TRADE_UX_2026-07-10) — "האם הסוכן חי" dot in the TopBar.
// Reads docs/reports/AGENT_HEARTBEAT.json via the /api/agent-heartbeat route (frontend
// Next route, same origin). Green/yellow/red per the supervisor verdict; a beacon older
// than 40min during trading hours (or a missing file) degrades to gray "הסוכן לא נבדק" —
// honest, never a fabricated green. Polls at the TopBar 15s floor (CLAUDE.md).

interface Heartbeat {
  exists?: boolean;
  ts?: string;
  verdict?: string; // 🟢 | 🟡 | 🔴
  note?: string;
  checks?: Record<string, string>;
  source?: string;
}

const VERDICT_COLOR: Record<string, string> = { '🟢': '#16a34a', '🟡': '#eab308', '🔴': '#dc2626' };
const GRAY = '#525252';
const STALE_MIN = 40;

function minutesAgo(ts?: string): number | null {
  if (!ts) return null;
  const t = new Date(ts).getTime();
  if (!Number.isFinite(t)) return null;
  return Math.floor((Date.now() - t) / 60000);
}

// RTH-ish window: Mon–Fri 09:30–16:00 America/New_York (DST-safe via Intl).
function inTradingHours(now = new Date()): boolean {
  const et = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
  const day = et.getDay();
  if (day === 0 || day === 6) return false;
  const mins = et.getHours() * 60 + et.getMinutes();
  return mins >= 9 * 60 + 30 && mins <= 16 * 60;
}

function agoHe(mins: number | null): string {
  if (mins == null) return '';
  if (mins < 1) return 'הרגע';
  if (mins < 60) return `לפני ${mins} דק'`;
  return `לפני ${Math.floor(mins / 60)}ש' ${mins % 60}ד'`;
}

export function AgentHeartbeatDot() {
  const [hb, setHb] = useState<Heartbeat | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let alive = true;
    const f = () =>
      fetch('/api/agent-heartbeat', { cache: 'no-store' })
        .then((r) => r.json())
        .then((d) => { if (alive) { setHb(d); setLoaded(true); } })
        .catch(() => { if (alive) setLoaded(true); });
    f();
    const id = setInterval(f, 15000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  if (!loaded) return null;

  const mins = minutesAgo(hb?.ts);
  const missing = !hb?.exists || mins == null;
  const stale = mins != null && mins > STALE_MIN && inTradingHours();
  const gray = missing || stale;
  const color = gray ? GRAY : (VERDICT_COLOR[hb?.verdict ?? ''] ?? GRAY);
  const ago = agoHe(mins);

  const title = gray
    ? (missing
        ? 'הסוכן לא נבדק — אין דופק (session-watch עוד לא רץ)'
        : `הסוכן לא נבדק — דופק ישן (${ago})`)
    : [
        `סוכן ${hb?.verdict ?? ''} ${hb?.note || 'ללא הערה'}`.trim(),
        ago,
        hb?.source ? `(${hb.source})` : '',
      ].filter(Boolean).join(' · ');

  return (
    <span
      title={title}
      data-testid="agent-heartbeat-dot"
      style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}
    >
      <span
        style={{
          width: 7, height: 7, borderRadius: '50%', display: 'inline-block',
          background: color, boxShadow: gray ? 'none' : `0 0 4px ${color}`,
        }}
      />
      <span style={{ fontSize: 8, color: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace' }}>סוכן</span>
    </span>
  );
}
