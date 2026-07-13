'use client';
/**
 * NewsDropdown — הודעות-החשובות של היום בהאדר (מייקל 07-13: "דרופ-דאון בהאדר
 * של המערכת של הודעות חשובות של אותו היום").
 *
 * צ'יפ קומפקטי בסרגל-העליון: 📰 + ספירת-אירועי-היום (אדומים מודגשים). לחיצה
 * פותחת רשימת-היום: 🔴 עם חלון-החסימה (רק אדום חוסם — פסיקת 07-13), 🟠🟡
 * לתצוגה. כשחסימה פעילה עכשיו — הצ'יפ מאדים. לא נוגע בפריסת-הטבלה הראשית.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

type Ev = { date: string; time_il: string; name: string; severity: string;
            blocks: boolean; block_il: string; past: boolean };
type Cal = { enabled: boolean; active_now: { event: string } | null; events: Ev[] };

const ICON: Record<string, string> = { red: '🔴', orange: '🟠', yellow: '🟡' };

function todayET(): string {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
}

export function NewsDropdown() {
  const [cal, setCal] = useState<Cal | null>(null);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    try {
      const r = await fetch('http://localhost:8000/api/v9/agent/news_calendar', { cache: 'no-store' });
      if (r.ok) setCal(await r.json());
    } catch { /* backend down — chip hides */ }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 60000);
    return () => clearInterval(id);
  }, [load]);

  // סגירה בלחיצה-בחוץ
  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);

  if (!cal) return null;
  const today = todayET();
  const evs = cal.events.filter((e) => e.date === today);
  const reds = evs.filter((e) => e.severity === 'red');
  const upcoming = evs.filter((e) => !e.past);
  const active = cal.active_now;

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen((o) => !o)}
        title="הודעות חשובות היום (יומן-TradingView)"
        className="text-xs px-2 py-0.5 rounded hover:bg-[var(--bg-tertiary)]"
        style={{
          whiteSpace: 'nowrap', cursor: 'pointer', border: 'none', fontWeight: 600,
          background: active ? 'var(--red, #f85149)' : 'transparent',
          color: active ? '#fff' : reds.some((e) => !e.past) ? 'var(--red, #f85149)' : 'var(--text-secondary)',
        }}
      >
        📰 {active ? 'חסימה!' : `היום ${upcoming.length ? upcoming.length : '—'}`}
        {reds.length > 0 && !active && (
          <span style={{ marginRight: 4, fontSize: 10 }}>({reds.length}🔴)</span>
        )}
      </button>

      {open && (
        <div dir="rtl" style={{
          position: 'absolute', top: '110%', right: 0, zIndex: 70, width: 340,
          maxHeight: 420, overflowY: 'auto',
          background: 'var(--bg-secondary, #141821)',
          border: '1px solid var(--border, #333a48)', borderRadius: 10,
          boxShadow: '0 10px 32px rgba(0,0,0,.55)', padding: 10,
        }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary, #e6edf3)', marginBottom: 6 }}>
            📰 הודעות היום · רק 🔴 חוסם (-10/+5 דק')
            {active && (
              <div style={{ color: 'var(--red, #f85149)', marginTop: 4 }}>
                🛑 עכשיו בחסימה: {active.event}
              </div>
            )}
          </div>
          {evs.length === 0 && (
            <div style={{ fontSize: 12, color: 'var(--text-muted, #7c8497)' }}>אין אירועים מדורגים היום.</div>
          )}
          {evs.map((e, i) => (
            <div key={i} style={{
              display: 'flex', gap: 8, alignItems: 'baseline', padding: '4px 2px',
              borderTop: i ? '1px solid var(--border, #21262d)' : 'none',
              opacity: e.past ? 0.45 : 1,
              color: e.severity === 'red' ? 'var(--text-primary, #e6edf3)' : 'var(--text-muted, #8b949e)',
              fontSize: 12,
            }}>
              <span style={{ fontFamily: 'ui-monospace, monospace', minWidth: 38 }}>{e.time_il}</span>
              <span style={{ flex: 1 }}>{ICON[e.severity]} {e.name}</span>
              {e.blocks && (
                <span style={{ fontSize: 10, color: 'var(--red, #f85149)', whiteSpace: 'nowrap' }}>
                  ⛔ {e.block_il}
                </span>
              )}
            </div>
          ))}
          <a href="/board" target="_blank" rel="noopener noreferrer"
             style={{ display: 'block', marginTop: 8, fontSize: 11, color: 'var(--accent, #58a6ff)', textDecoration: 'none' }}>
            ← כל השבוע בלוח
          </a>
        </div>
      )}
    </div>
  );
}
