'use client';
/**
 * NewsCalendarPanel — לוח-החדשות של חלון-ה-NO_TRADE (מייקל 07-13: "איפה הוא מופיע?").
 * מציג את האירועים-האדומים של השבוע (מקור: יומן-TradingView, גיבוי FF) עם שעות-IL,
 * חלון-החסימה של כל אירוע, הדגשת אירועים שנופלים בתוך RTH, ומצב-חסימה חי עכשיו.
 */
import { useCallback, useEffect, useState } from 'react';

type Ev = { date: string; day: string; time_et: string; time_il: string; name: string;
            block_il: string; in_rth: boolean; past: boolean };
type Cal = { enabled: boolean; window: string; active_now: { event: string } | null; events: Ev[] };

const DAY_HE: Record<string, string> = {
  Sunday: 'ראשון', Monday: 'שני', Tuesday: 'שלישי', Wednesday: 'רביעי',
  Thursday: 'חמישי', Friday: 'שישי', Saturday: 'שבת',
};

export function NewsCalendarPanel() {
  const [cal, setCal] = useState<Cal | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await fetch('http://localhost:8000/api/v9/agent/news_calendar', { cache: 'no-store' });
      if (r.ok) setCal(await r.json());
    } catch { /* backend down — hide */ }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 60000);
    return () => clearInterval(id);
  }, [load]);

  if (!cal) return null;
  const upcoming = cal.events.filter((e) => !e.past);

  return (
    <div dir="rtl" style={{
      background: 'var(--bg-panel, #0d1117)',
      border: `1px solid ${cal.active_now ? 'var(--red, #f85149)' : 'var(--border, #30363d)'}`,
      borderRadius: 8, padding: 14, color: 'var(--text-secondary, #c9d1d9)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: 8 }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text, #e6edf3)' }}>
          📰 חלון-חדשות NO_TRADE
          <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--text-muted, #8b949e)', marginRight: 8 }}>
            מקור: יומן-TradingView (אדום/ארה"ב) · חלון {cal.window} · {cal.enabled ? '🟢 דלוק' : '⚪ כבוי'}
          </span>
        </div>
        {cal.active_now && (
          <span style={{ fontSize: 12, fontWeight: 700, color: '#fff', background: 'var(--red, #f85149)',
                         padding: '2px 10px', borderRadius: 6 }}>
            🛑 עכשיו בחסימה: {cal.active_now.event}
          </span>
        )}
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 10, fontSize: 12.5 }}>
        <thead>
          <tr style={{ color: 'var(--text-muted, #8b949e)', textAlign: 'right' }}>
            <th style={{ padding: '2px 6px' }}>יום</th>
            <th style={{ padding: '2px 6px' }}>אירוע</th>
            <th style={{ padding: '2px 6px' }}>שעה (IL)</th>
            <th style={{ padding: '2px 6px' }}>חלון-חסימה (IL)</th>
            <th style={{ padding: '2px 6px' }}></th>
          </tr>
        </thead>
        <tbody>
          {upcoming.map((e, i) => (
            <tr key={i} style={{
              borderTop: '1px solid var(--border, #21262d)',
              color: e.in_rth ? 'var(--text, #e6edf3)' : 'var(--text-muted, #8b949e)',
            }}>
              <td style={{ padding: '4px 6px', whiteSpace: 'nowrap' }}>{DAY_HE[e.day] || e.day} {e.date.slice(5)}</td>
              <td style={{ padding: '4px 6px' }}>🔴 {e.name}</td>
              <td style={{ padding: '4px 6px', fontFamily: 'ui-monospace, monospace' }}>{e.time_il}</td>
              <td style={{ padding: '4px 6px', fontFamily: 'ui-monospace, monospace' }}>{e.block_il}</td>
              <td style={{ padding: '4px 6px', fontSize: 11 }}>
                {e.in_rth ? <span style={{ color: 'var(--orange, #d29922)', fontWeight: 600 }}>⚠ בתוך המסחר</span>
                          : 'לפני-פתיחה'}
              </td>
            </tr>
          ))}
          {upcoming.length === 0 && (
            <tr><td colSpan={5} style={{ padding: 8, color: 'var(--text-muted, #8b949e)' }}>
              אין אירועים-אדומים קרובים בלוח.
            </td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
