'use client';
/**
 * AgentChatWidget — חלון-צ'אט צף עם הסוכן (Claude) בתוך הדשבורד (מייקל 07-12).
 *
 * ‏07-12 ערב (מייקל): הכפתור בצד ימין-למטה, והחלון גריר — תופסים את פס-הכותרת
 * וגוררים לכל מקום; המיקום נשמר (localStorage) בין רענונים.
 *
 * שיחה מקורקעת בהקשר-החי של המערכת (day_type, עסקאות, דגלים, התראות) דרך
 * ‏/api/v9/agent/chat; המפתח חי ב-.env בצד השרת בלבד.
 */
import { useEffect, useRef, useState } from 'react';

type Turn = { role: 'user' | 'assistant'; content: string };

const TOKEN = process.env.NEXT_PUBLIC_BRIDGE_TOKEN || '';
const POS_KEY = 'agent_chat_pos_v1';
const W = 380, H = 480;

function loadPos(): { x: number; y: number } | null {
  try {
    const raw = localStorage.getItem(POS_KEY);
    if (!raw) return null;
    const p = JSON.parse(raw);
    if (typeof p.x === 'number' && typeof p.y === 'number') return p;
  } catch {}
  return null;
}

export function AgentChatWidget() {
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const drag = useRef<{ dx: number; dy: number; active: boolean }>({ dx: 0, dy: 0, active: false });

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turns, open]);

  useEffect(() => {
    if (open && pos === null) {
      const saved = loadPos();
      // ברירת-מחדל: צד ימין, מעל הכפתור (בתוך המסך)
      setPos(saved ?? {
        x: Math.max(8, window.innerWidth - W - 20),
        y: Math.max(8, window.innerHeight - H - 80),
      });
    }
  }, [open, pos]);

  function onDragStart(e: React.PointerEvent) {
    if (!pos) return;
    drag.current = { dx: e.clientX - pos.x, dy: e.clientY - pos.y, active: true };
    const move = (ev: PointerEvent) => {
      if (!drag.current.active) return;
      const x = Math.min(Math.max(0, ev.clientX - drag.current.dx), window.innerWidth - 80);
      const y = Math.min(Math.max(0, ev.clientY - drag.current.dy), window.innerHeight - 40);
      setPos({ x, y });
    };
    const up = () => {
      drag.current.active = false;
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
      setPos((p) => {
        if (p) try { localStorage.setItem(POS_KEY, JSON.stringify(p)); } catch {}
        return p;
      });
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
  }

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
      {/* לחצן צף — צד ימין-למטה (מייקל 07-12) */}
      <button
        onClick={() => setOpen((o) => !o)}
        title="שיחה עם הסוכן"
        style={{
          position: 'fixed', bottom: 18, right: 20, zIndex: 60,
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

      {open && pos && (
        <div
          dir="rtl"
          style={{
            position: 'fixed', left: pos.x, top: pos.y, zIndex: 61,
            width: W, height: H, display: 'flex', flexDirection: 'column',
            background: 'var(--bg-secondary, #141821)',
            border: '1px solid var(--border, #333a48)', borderRadius: 12,
            boxShadow: '0 10px 32px rgba(0,0,0,.55)', overflow: 'hidden',
          }}
        >
          {/* פס-כותרת גריר */}
          <div
            onPointerDown={onDragStart}
            style={{ padding: '8px 12px', borderBottom: '1px solid var(--border, #333a48)',
                     display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                     cursor: 'grab', userSelect: 'none', touchAction: 'none' }}
          >
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary, #e5e7eb)' }}>
              ⠿ הסוכן · שיחה על מצב-המערכת החי
            </span>
            <button onClick={() => setOpen(false)} onPointerDown={(e) => e.stopPropagation()}
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
                ‏«אילו דגלים דלוקים על היעדים?»<br />
                <span style={{ opacity: 0.7 }}>(אפשר לגרור את החלון מהכותרת)</span>
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
