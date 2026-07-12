'use client';
/**
 * AgentChatWidget — חלון-צ'אט צף עם הסוכן (Claude) בתוך הדשבורד (מייקל 07-12).
 *
 * שיחה מקורקעת בהקשר-החי של המערכת (day_type, עסקאות פתוחות, דגלים, התראות) —
 * ה-backend  (/api/v9/agent/chat) אוסף את ההקשר ופונה ל-Anthropic API.
 * המפתח חי ב-.env בצד השרת בלבד. בלי מפתח — הודעה מסבירה (503).
 */
import { useEffect, useRef, useState } from 'react';

type Turn = { role: 'user' | 'assistant'; content: string };

const TOKEN = process.env.NEXT_PUBLIC_BRIDGE_TOKEN || '';

export function AgentChatWidget() {
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turns, open]);

  async function send() {
    const msg = input.trim();
    if (!msg || busy) return;
    setInput('');
    const history = turns.slice(-10);
    setTurns((t) => [...t, { role: 'user', content: msg }]);
    setBusy(true);
    try {
      const r = await fetch('http://localhost:8000/api/v9/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${TOKEN}` },
        body: JSON.stringify({ message: msg, history }),
      });
      const data = await r.json().catch(() => ({}));
      const reply = r.ok
        ? (data.reply ?? '(תשובה ריקה)')
        : `⚠ ${data.detail ?? `שגיאה ${r.status}`}`;
      setTurns((t) => [...t, { role: 'assistant', content: reply }]);
    } catch (e) {
      setTurns((t) => [...t, { role: 'assistant', content: `⚠ אין חיבור לבקאנד (${e})` }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {/* לחצן צף */}
      <button
        onClick={() => setOpen((o) => !o)}
        title="שיחה עם הסוכן"
        style={{
          position: 'fixed', bottom: 18, left: 74, zIndex: 60,
          width: 44, height: 44, borderRadius: 22, cursor: 'pointer',
          background: open ? 'var(--sys1, #6366f1)' : 'var(--bg-tertiary, #1f2430)',
          color: 'var(--text-primary, #e5e7eb)',
          border: '1px solid var(--border, #333a48)',
          fontSize: 20, lineHeight: '44px', textAlign: 'center',
          boxShadow: '0 4px 14px rgba(0,0,0,.45)',
        }}
      >
        💬
      </button>

      {open && (
        <div
          dir="rtl"
          style={{
            position: 'fixed', bottom: 72, left: 18, zIndex: 60,
            width: 380, height: 480, display: 'flex', flexDirection: 'column',
            background: 'var(--bg-secondary, #141821)',
            border: '1px solid var(--border, #333a48)', borderRadius: 12,
            boxShadow: '0 10px 32px rgba(0,0,0,.55)', overflow: 'hidden',
          }}
        >
          <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border, #333a48)',
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary, #e5e7eb)' }}>
              הסוכן · שיחה על מצב-המערכת החי
            </span>
            <button onClick={() => setOpen(false)}
                    style={{ background: 'none', border: 'none', color: 'var(--text-muted, #7c8497)',
                             cursor: 'pointer', fontSize: 14 }}>✕</button>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: 10, display: 'flex',
                        flexDirection: 'column', gap: 8 }}>
            {turns.length === 0 && (
              <div style={{ fontSize: 12, color: 'var(--text-muted, #7c8497)', lineHeight: 1.6 }}>
                שאל אותי על המערכת — למשל:<br />
                ‏«מה סוג-היום עכשיו ולמה?»<br />
                ‏«מה הסטופ של העסקה הפתוחה עושה?»<br />
                ‏«אילו דגלים דלוקים על היעדים?»
              </div>
            )}
            {turns.map((t, i) => (
              <div key={i} style={{
                alignSelf: t.role === 'user' ? 'flex-start' : 'flex-end',
                maxWidth: '88%', padding: '7px 10px', borderRadius: 10, fontSize: 12.5,
                whiteSpace: 'pre-wrap', lineHeight: 1.55,
                background: t.role === 'user' ? 'var(--sys1, #6366f1)' : 'var(--bg-tertiary, #1f2430)',
                color: 'var(--text-primary, #e5e7eb)',
                border: t.role === 'user' ? 'none' : '1px solid var(--border, #333a48)',
              }}>
                {t.content}
              </div>
            ))}
            {busy && <div style={{ fontSize: 12, color: 'var(--text-muted, #7c8497)' }}>חושב…</div>}
            <div ref={endRef} />
          </div>

          <div style={{ display: 'flex', gap: 6, padding: 8,
                        borderTop: '1px solid var(--border, #333a48)' }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && send()}
              placeholder="שאלה לסוכן…"
              style={{ flex: 1, padding: '8px 10px', borderRadius: 8, fontSize: 13,
                       background: 'var(--bg-primary, #0d1017)',
                       color: 'var(--text-primary, #e5e7eb)',
                       border: '1px solid var(--border, #333a48)', outline: 'none' }}
            />
            <button onClick={send} disabled={busy}
                    style={{ padding: '8px 14px', borderRadius: 8, fontSize: 13, cursor: 'pointer',
                             background: 'var(--sys1, #6366f1)', color: '#fff', border: 'none',
                             opacity: busy ? 0.5 : 1 }}>
              שלח
            </button>
          </div>
        </div>
      )}
    </>
  );
}
