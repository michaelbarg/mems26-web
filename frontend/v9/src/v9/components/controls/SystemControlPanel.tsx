'use client';
/**
 * P31 Phase 2 — System Control Panel.
 *
 * Cockpit-side surface for Michael's operator controls (2026-05-22):
 *
 *   "תוסיף כפתור הפעלה, כיבוי, ריסטרט, גאפ פיל, בדאשבורד -
 *    אני רוצה שאם עכשיו מדליקים כבר נקבל את כל ההיסטוריה
 *    אני רוצה לראות את כל הנתונים כבר בדאשבורד"
 *
 * The four buttons map to the four admin endpoints:
 *   * Start  → POST /api/v9/admin/services/{name}/start
 *   * Stop   → POST /api/v9/admin/services/{name}/stop
 *   * Restart → POST /api/v9/admin/services/{name}/restart
 *   * Gap-fill → POST /api/v9/admin/history/gap_fill
 *
 * The panel mounts as a fixed bottom-right floating button. Clicking opens
 * a collapsible side drawer with live status + the controls. Polling is
 * deliberately slow (15 s) — see `CLAUDE.md` Frontend Polling Floors.
 */

import { useEffect, useMemo, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const TOKEN = process.env.NEXT_PUBLIC_BRIDGE_TOKEN || 'michael-mems26-2026';

type Service = {
  name: string;
  description: string;
  running: boolean;
  class?: string;
  error?: string;
};

type DbTable = {
  table: string;
  ts_col: string;
  rows?: number;
  approx_rows?: number;
  max_ts?: string | null;
  error?: string;
};

type GapFillStreamResult = {
  ok?: boolean;
  rows_seen?: number;
  inserted?: number;
  skipped_existing?: number;
  age_s?: number;
  skipped?: string;
  error?: string;
};

type GapFillSummary = {
  reason?: string;
  started_at_utc?: string;
  elapsed_s?: number;
  streams?: Record<string, GapFillStreamResult>;
  never_run?: boolean;
};

type ArchiveState = {
  archive_dir: string;
  retention_days: number;
  files_per_archive: string[];
  dates_present: string[];
  total_archived_days: number;
};

async function adminFetch<T>(path: string, init?: RequestInit): Promise<T | null> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 30_000);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${TOKEN}`,
        ...init?.headers,
      },
      signal: ctrl.signal,
    });
    if (!res.ok) return null;
    return res.json() as Promise<T>;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

function relativeAge(ts: string | null | undefined): string {
  if (!ts) return '—';
  // Accept ISO (`...+00:00`) or naive (`YYYY-MM-DD HH:MM:SS[.ffffff]`).
  const norm = ts.includes('T') || ts.includes('+') ? ts : ts.replace(' ', 'T') + 'Z';
  const t = Date.parse(norm);
  if (!Number.isFinite(t)) return ts;
  const age_s = Math.max(0, (Date.now() - t) / 1000);
  if (age_s < 60) return `${age_s.toFixed(0)}s ago`;
  if (age_s < 3600) return `${(age_s / 60).toFixed(0)}m ago`;
  if (age_s < 86400) return `${(age_s / 3600).toFixed(1)}h ago`;
  return `${(age_s / 86400).toFixed(1)}d ago`;
}

export function SystemControlPanel() {
  const [open, setOpen] = useState(false);
  const [services, setServices] = useState<Service[]>([]);
  const [dbState, setDbState] = useState<DbTable[]>([]);
  const [archive, setArchive] = useState<ArchiveState | null>(null);
  const [lastGapFill, setLastGapFill] = useState<GapFillSummary | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    const [svc, db, arch, gf] = await Promise.all([
      adminFetch<{ services: Service[] }>(`/api/v9/admin/services/status`),
      adminFetch<{ tables: DbTable[] }>(`/api/v9/admin/history/db_state`),
      adminFetch<ArchiveState>(`/api/v9/admin/archive_state`),
      adminFetch<GapFillSummary>(`/api/v9/admin/history/last_gap_fill`),
    ]);
    if (svc?.services) setServices(svc.services);
    if (db?.tables) setDbState(db.tables);
    if (arch) setArchive(arch);
    if (gf && !gf.never_run) setLastGapFill(gf);
  };

  useEffect(() => {
    if (!open) return;
    refresh();
    // P30 Forensics polling floor: 15 s — diagnostic surface, not real-time.
    const id = setInterval(refresh, 15_000);
    return () => clearInterval(id);
  }, [open]);

  const handleService = async (name: string, action: 'start' | 'stop' | 'restart') => {
    setBusy(`${name}:${action}`);
    setError(null);
    const res = await adminFetch<{ ok: boolean; running: boolean }>(
      `/api/v9/admin/services/${name}/${action}`,
      { method: 'POST' },
    );
    if (!res) setError(`${action} ${name} failed`);
    await refresh();
    setBusy(null);
  };

  const handleGapFill = async () => {
    setBusy('gap_fill');
    setError(null);
    const res = await adminFetch<GapFillSummary>(`/api/v9/admin/history/gap_fill`, { method: 'POST' });
    if (!res) setError('gap-fill failed');
    else setLastGapFill(res);
    await refresh();
    setBusy(null);
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        title="System control panel — Start / Stop / Restart / Gap-fill"
        style={{
          position: 'fixed',
          left: 12, // 2026-07-08: was right:12 — collided with the DemoMonitor pill (both bottom-right)
          bottom: 12,
          zIndex: 100,
          background: '#1e1e1e',
          border: '1px solid #404040',
          color: '#e5e5e5',
          padding: '6px 10px',
          borderRadius: 6,
          fontSize: 11,
          cursor: 'pointer',
          fontFamily: 'system-ui, sans-serif',
        }}
      >
        ⚙ System
      </button>
    );
  }

  return (
    <div
      dir="rtl"
      style={{
        position: 'fixed',
        left: 12, // 2026-07-08: keep the expanded panel on the same (left) side as the button
        bottom: 12,
        zIndex: 100,
        width: 460,
        maxHeight: '80vh',
        overflowY: 'auto',
        background: '#161616',
        border: '1px solid #404040',
        borderRadius: 8,
        color: '#e5e5e5',
        fontSize: 11,
        fontFamily: 'system-ui, sans-serif',
        boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 12px',
          borderBottom: '1px solid #2a2a2a',
        }}
      >
        <span style={{ fontWeight: 600, fontSize: 12 }}>פאנל בקרה — מערכת</span>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            onClick={refresh}
            disabled={busy !== null}
            title="רענן"
            style={btnStyle}
          >
            ↻
          </button>
          <button onClick={() => setOpen(false)} title="סגור" style={btnStyle}>
            ✕
          </button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div style={{ padding: '6px 12px', background: '#3a1d1d', color: '#ff9999', fontSize: 10 }}>
          {error}
        </div>
      )}

      {/* Services */}
      <Section title="שירותים ברקע">
        <table style={tblStyle}>
          <thead>
            <tr style={trHeadStyle}>
              <th style={thStyle}>שירות</th>
              <th style={thStyle}>סטטוס</th>
              <th style={thStyle}>פעולות</th>
            </tr>
          </thead>
          <tbody>
            {services.map((s) => (
              <tr key={s.name} style={{ borderTop: '1px solid #2a2a2a' }}>
                <td style={tdStyle} title={s.description}>
                  <div style={{ fontFamily: 'monospace', fontSize: 10 }}>{s.name}</div>
                  <div style={{ fontSize: 9, color: '#888', maxWidth: 180 }}>{s.description}</div>
                </td>
                <td style={tdStyle}>
                  <span
                    style={{
                      display: 'inline-block',
                      width: 8,
                      height: 8,
                      borderRadius: 4,
                      background: s.running ? '#5cd478' : '#888',
                      marginInlineEnd: 4,
                    }}
                  />
                  {s.running ? 'רץ' : 'עוצר'}
                </td>
                <td style={tdStyle}>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    <button
                      onClick={() => handleService(s.name, 'start')}
                      disabled={busy !== null || s.running}
                      style={s.running ? btnStyleDisabled : btnStyleGreen}
                      title="הפעלה"
                    >
                      ▶ הפעלה
                    </button>
                    <button
                      onClick={() => handleService(s.name, 'stop')}
                      disabled={busy !== null || !s.running}
                      style={!s.running ? btnStyleDisabled : btnStyleAmber}
                      title="כיבוי"
                    >
                      ◼ כיבוי
                    </button>
                    <button
                      onClick={() => handleService(s.name, 'restart')}
                      disabled={busy !== null}
                      style={btnStyle}
                      title="ריסטרט (Stop → Start)"
                    >
                      ↻ ריסטרט
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {services.length === 0 && (
              <tr>
                <td colSpan={3} style={{ ...tdStyle, color: '#666' }}>
                  טוען…
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Section>

      {/* Gap-fill */}
      <Section title="היסטוריה (Gap-fill)">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <button
            onClick={handleGapFill}
            disabled={busy !== null}
            style={busy === 'gap_fill' ? btnStyleDisabled : btnStyleBlue}
            title="קרא נתונים מ-Sierra exports והשלם פערים ב-DB"
          >
            {busy === 'gap_fill' ? 'רץ…' : '⬇ Gap-fill עכשיו'}
          </button>
          <span style={{ fontSize: 10, color: '#888' }}>
            {lastGapFill?.elapsed_s !== undefined
              ? `אחרון: ${lastGapFill.elapsed_s.toFixed(2)}s (${lastGapFill.reason})`
              : 'מעולם לא הופעל'}
          </span>
        </div>
        {lastGapFill?.streams && (
          <table style={tblStyle}>
            <thead>
              <tr style={trHeadStyle}>
                <th style={thStyle}>זרם</th>
                <th style={thStyle}>נראו</th>
                <th style={thStyle}>הוכנסו</th>
                <th style={thStyle}>קיימים</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(lastGapFill.streams).map(([name, r]) => (
                <tr key={name} style={{ borderTop: '1px solid #2a2a2a' }}>
                  <td style={tdStyle}>
                    <span style={{ fontFamily: 'monospace', fontSize: 10 }}>{name}</span>
                  </td>
                  <td style={tdStyle}>{r.rows_seen ?? '—'}</td>
                  <td style={tdStyle}>
                    <span style={{ color: (r.inserted ?? 0) > 0 ? '#5cd478' : '#888' }}>
                      {r.inserted ?? 0}
                    </span>
                  </td>
                  <td style={tdStyle}>{r.skipped_existing ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      {/* DB state */}
      <Section title="מצב נתונים (DB)">
        <table style={tblStyle}>
          <thead>
            <tr style={trHeadStyle}>
              <th style={thStyle}>טבלה</th>
              <th style={thStyle}>שורות</th>
              <th style={thStyle}>עדכון אחרון</th>
            </tr>
          </thead>
          <tbody>
            {dbState.map((t) => (
              <tr key={t.table} style={{ borderTop: '1px solid #2a2a2a' }}>
                <td style={tdStyle}>
                  <span style={{ fontFamily: 'monospace', fontSize: 10 }}>{t.table}</span>
                </td>
                <td style={tdStyle}>{t.rows?.toLocaleString() ?? t.approx_rows?.toLocaleString() ?? '—'}</td>
                <td style={tdStyle} title={t.max_ts ?? ''}>{relativeAge(t.max_ts)}</td>
              </tr>
            ))}
            {dbState.length === 0 && (
              <tr>
                <td colSpan={3} style={{ ...tdStyle, color: '#666' }}>טוען…</td>
              </tr>
            )}
          </tbody>
        </table>
      </Section>

      {/* Archive state */}
      <Section title="ארכיון EOD">
        {archive ? (
          <div style={{ padding: '4px 12px', fontSize: 10, color: '#bbb' }}>
            <div>תיקייה: <span style={{ fontFamily: 'monospace' }}>{archive.archive_dir}</span></div>
            <div>שמירה: {archive.retention_days} ימים · ארכיב: {archive.total_archived_days} ימים</div>
            <div>קבצים לכל יום: {archive.files_per_archive.length}</div>
            <div style={{ marginTop: 4 }}>
              תאריכים בארכיב: {archive.dates_present.slice(0, 5).join(', ')}
              {archive.dates_present.length > 5 ? ' …' : ''}
            </div>
          </div>
        ) : (
          <div style={{ padding: '4px 12px', color: '#666' }}>טוען…</div>
        )}
      </Section>

      <div style={{ padding: '6px 12px', fontSize: 9, color: '#666', borderTop: '1px solid #2a2a2a' }}>
        פולל: כל 15 שניות · גרסה: P31 Phase 2 · 2026-05-22
      </div>
    </div>
  );
}

// ---------- shared styles ----------

const btnStyleBase: React.CSSProperties = {
  background: '#262626',
  border: '1px solid #404040',
  color: '#e5e5e5',
  fontSize: 10,
  padding: '2px 6px',
  borderRadius: 4,
  cursor: 'pointer',
  fontFamily: 'inherit',
};
const btnStyle = btnStyleBase;
const btnStyleGreen: React.CSSProperties = {
  ...btnStyleBase,
  background: '#1a3a24',
  borderColor: '#2c5d3c',
  color: '#aaffbb',
};
const btnStyleAmber: React.CSSProperties = {
  ...btnStyleBase,
  background: '#3a2d1a',
  borderColor: '#5d472c',
  color: '#ffd49a',
};
const btnStyleBlue: React.CSSProperties = {
  ...btnStyleBase,
  background: '#1a2a3a',
  borderColor: '#2c455d',
  color: '#9accff',
};
const btnStyleDisabled: React.CSSProperties = {
  ...btnStyleBase,
  background: '#1a1a1a',
  borderColor: '#262626',
  color: '#555',
  cursor: 'not-allowed',
};

const tblStyle: React.CSSProperties = { width: '100%', borderCollapse: 'collapse', fontSize: 10 };
const trHeadStyle: React.CSSProperties = { background: '#1e1e1e', color: '#bbb' };
const thStyle: React.CSSProperties = { padding: '4px 8px', textAlign: 'start', fontWeight: 600 };
const tdStyle: React.CSSProperties = { padding: '4px 8px', verticalAlign: 'top' };

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ padding: '8px 0', borderTop: '1px solid #2a2a2a' }}>
      <div style={{ padding: '0 12px 4px', fontSize: 10, color: '#888', fontWeight: 600 }}>
        {title}
      </div>
      {children}
    </div>
  );
}
