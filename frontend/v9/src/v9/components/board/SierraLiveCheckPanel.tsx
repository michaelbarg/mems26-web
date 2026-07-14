'use client';
/**
 * SierraLiveCheckPanel — T1 (מייקל 07-14): בדיקת-אמת read-only שהמערכת *יודעת*
 * מה קורה בסיירה: (1) חיה + סים/חימוש · (2) עסקה-פתוחה מזוהה · (3) סגירות-היום
 * על מימושים + P&L. קורא /api/v9/agent/sierra_live_check כל 5ש'. אין פקודות.
 */
import { useCallback, useEffect, useState } from 'react';

type Check = { ok: boolean; detail?: string; [k: string]: unknown };
type Res = { checks: Record<string, Check>; verdict: string; ts: string };

const LABEL: Record<string, string> = {
  sierra_alive: 'סיירה חיה',
  open_trade_detect: 'זיהוי עסקה-פתוחה',
  closures_on_fills: 'סגירות-היום על מימושים',
};

export function SierraLiveCheckPanel() {
  const [r, setR] = useState<Res | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v9/agent/sierra_live_check', { cache: 'no-store' });
      if (res.ok) setR(await res.json());
    } catch { /* backend down — hide */ }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);

  if (!r) return null;
  const allOk = Object.values(r.checks).every((c) => c.ok);

  return (
    <div dir="rtl" style={{
      background: 'var(--bg-panel, #0d1117)',
      border: `1px solid ${allOk ? 'var(--green, #238636)' : 'var(--orange, #d29922)'}`,
      borderRadius: 8, padding: 14, color: 'var(--text-secondary, #c9d1d9)',
    }}>
      <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text, #e6edf3)' }}>
        🔎 בדיקת-אמת: המערכת מזהה את סיירה
        <span style={{ fontSize: 12, fontWeight: 400, marginRight: 8,
                       color: allOk ? 'var(--green, #3fb950)' : 'var(--orange, #d29922)' }}>
          {r.verdict}
        </span>
      </div>

      <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {Object.entries(r.checks).map(([key, c]) => (
          <div key={key} style={{
            display: 'flex', gap: 8, alignItems: 'baseline', padding: '6px 8px',
            borderRadius: 6, background: 'rgba(255,255,255,0.02)',
            borderRight: `3px solid ${c.ok ? 'var(--green, #238636)' : 'var(--red, #f85149)'}`,
          }}>
            <span style={{ fontSize: 13 }}>{c.ok ? '✅' : '🔴'}</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text, #e6edf3)' }}>
                {LABEL[key] || key}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted, #8b949e)' }}>{c.detail}</div>
              {key === 'sierra_alive' && (
                <div style={{ fontSize: 11, color: 'var(--text-muted, #8b949e)', marginTop: 2 }}>
                  age {String(c.age_s)}s · is_sim={String(c.is_sim)} · armed={String(c.armed)}
                </div>
              )}
              {key === 'open_trade_detect' && (
                <div style={{ fontSize: 11, color: 'var(--text-muted, #8b949e)', marginTop: 2 }}>
                  סיירה qty={String(c.sierra_qty)} · working={String(c.working_orders)} · TM={String(c.tm_open_trades)} עסקאות
                </div>
              )}
              {key === 'closures_on_fills' && (
                <div style={{ fontSize: 11, color: 'var(--text-muted, #8b949e)', marginTop: 2 }}>
                  ‏P&L היום ${String(c.day_pnl)} · {String(c.day_n)} עסקאות · {String(c.day_wins)} מנצחות
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      <div style={{ fontSize: 10, color: 'var(--text-muted, #8b949e)', marginTop: 6 }}>
        read-only · אין פקודות-מסחר · מתעדכן כל 5ש'
      </div>
    </div>
  );
}
