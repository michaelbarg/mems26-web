'use client';
/**
 * DailyPnlPanel — P&L by day from Sierra's trade activity journal
 * (Michael 2026-07-28: "טבלה של רווח והפסד לפי ימים ולהבין איפה נפלנו ומה טעינו").
 *
 * Source: GET /api/v9/account/daily_pnl → trade_activity_events.jsonl (Sierra
 * truth — includes Michael's manual trades, which v9_trades deliberately
 * omits). Poll: 60s (history changes rarely).
 */
import { useEffect, useState } from 'react';
import { COLORS } from '../../design/tokens';
import { getApiBase } from '../../lib/api';

const API_BASE = getApiBase();

interface Row {
  day: string; pnl: number; closes: number; wins: number; losses: number;
  biggest_win: number; biggest_loss: number; cumulative: number;
  system_pnl: number | null; system_trades: number | null;
}

function money(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return '—';
  return `${v < 0 ? '-' : ''}$${Math.abs(v).toFixed(2)}`;
}
const pnlColor = (v: number | null | undefined) =>
  v == null ? COLORS.textTertiary : v > 0 ? '#16a34a' : v < 0 ? '#dc2626' : COLORS.textTertiary;

export function DailyPnlPanel() {
  const [rows, setRows] = useState<Row[]>([]);
  const [note, setNote] = useState<string>('');
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const r = await fetch(`${API_BASE}/api/v9/account/daily_pnl?days=30`);
        const d = await r.json();
        if (!alive) return;
        if (!d.ok) { setErr(d.error || 'error'); return; }
        setRows(d.rows || []);
        setNote(d.note || '');
        setErr(null);
      } catch (e) { if (alive) setErr(String(e)); }
    };
    load();
    const id = setInterval(load, 60000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  const th: React.CSSProperties = {
    fontSize: 8, color: COLORS.textDim, textAlign: 'right',
    padding: '3px 8px', borderBottom: `1px solid ${COLORS.borderFaint}`,
    whiteSpace: 'nowrap',
  };
  const td: React.CSSProperties = {
    fontSize: 10, fontFamily: 'ui-monospace', textAlign: 'right',
    padding: '3px 8px', borderBottom: `1px solid ${COLORS.borderFaint}`,
    whiteSpace: 'nowrap',
  };

  return (
    <div style={{ border: `1px solid ${COLORS.borderFaint}`, borderRadius: 6, padding: 8 }}>
      <div style={{ fontSize: 10, fontWeight: 700, marginBottom: 6 }}>
        רווח/הפסד לפי ימים
        <span style={{ fontSize: 8, fontWeight: 400, color: COLORS.textDim, marginInlineStart: 8 }}>
          מקור: יומן הפעילות של סיירה (כולל עסקאות ידניות)
        </span>
      </div>
      {err && <div style={{ fontSize: 9, color: '#eab308' }}>שגיאה: {err}</div>}
      <div style={{ maxHeight: 320, overflowY: 'auto' }}>
        <table style={{ borderCollapse: 'collapse', width: '100%', direction: 'rtl' }}>
          <thead>
            <tr>
              <th style={th}>יום</th>
              <th style={th}>P&L</th>
              <th style={th}>סגירות</th>
              <th style={th}>W/L</th>
              <th style={th}>הפסד גדול</th>
              <th style={th}>רווח גדול</th>
              <th style={th} title="מהספרים שלנו — עסקאות מערכת בלבד">מהמערכת</th>
              <th style={th}>מצטבר</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.day} style={{ background: r.pnl < -500 ? 'rgba(220,38,38,0.08)' : undefined }}>
                <td style={td}>{r.day}</td>
                <td style={{ ...td, color: pnlColor(r.pnl), fontWeight: 700 }}>{money(r.pnl)}</td>
                <td style={td}>{r.closes}</td>
                <td style={td}>
                  <span style={{ color: '#16a34a' }}>{r.wins}</span>/
                  <span style={{ color: '#dc2626' }}>{r.losses}</span>
                </td>
                <td style={{ ...td, color: pnlColor(r.biggest_loss) }}>{money(r.biggest_loss)}</td>
                <td style={{ ...td, color: pnlColor(r.biggest_win) }}>{money(r.biggest_win)}</td>
                <td style={{ ...td, color: pnlColor(r.system_pnl) }}>
                  {r.system_pnl == null ? '—' : `${money(r.system_pnl)} (${r.system_trades})`}
                </td>
                <td style={{ ...td, color: pnlColor(r.cumulative) }}>{money(r.cumulative)}</td>
              </tr>
            ))}
            {rows.length === 0 && !err && (
              <tr><td style={td} colSpan={8}>אין נתונים</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {note && <div style={{ fontSize: 7, color: COLORS.textDim, marginTop: 4 }}>{note}</div>}
    </div>
  );
}
