'use client';
// TradeReviewTab — collapsible/resizable trade list (left) + the proven live
// marker tool in an iframe (right). Clicking a trade posts a message to the
// marker (/marker.html) which selects it. The list shows ✓/✗ + P&L and a ✎ /🚫
// flag on trades you've marked (so you can see all your marks at a glance), with
// All / Loss / Win / No-entry / Marked filters. Marks are read from localStorage
// (shared with the iframe) + the DB (/api/v9/trade_reviews) and re-polled so marks
// made in the iframe show up here within ~1.5s.
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import { fetchTrades } from '../../lib/api';
import type { Trade } from '../../types';

type Filter = 'all' | 'loss' | 'win' | 'noentry' | 'marked';
interface MarkEntry { no_entry?: boolean; note?: string; [k: string]: unknown; }
type MarksMap = Record<string, MarkEntry>;

const FILTERS: Array<{ id: Filter; label: string; color?: string }> = [
  { id: 'all', label: 'All' }, { id: 'loss', label: '✗', color: '#f85149' }, { id: 'win', label: '✓', color: '#56d364' },
  { id: 'noentry', label: '🚫', color: '#f85149' }, { id: 'marked', label: '✎', color: '#e3b341' },
];
const outcome = (t: Trade) => {
  const p = t.pnl_usd, o = (t.outcome || '').toUpperCase();
  if (o === 'WIN' || (o === '' && p != null && p > 0)) return { i: '✓', c: '#56d364', cls: 'win' };
  if (o === 'LOSS' || (o === '' && p != null && p < 0)) return { i: '✗', c: '#f85149', cls: 'loss' };
  if (p == null && !t.exit_ts) return { i: '•', c: '#8b949e', cls: 'open' };
  return { i: '=', c: '#8b949e', cls: 'be' };
};
const money = (v: number | null | undefined) => (v == null ? '—' : (v >= 0 ? '+$' : '-$') + Math.abs(v).toFixed(0));
const hasMark = (m?: MarkEntry) => { if (!m) return false; if (m.no_entry) return true; if (typeof m.note === 'string' && m.note.trim()) return true; return Object.values(m).some((v) => typeof v === 'number'); };

export function TradeReviewTab() {
  const trades = useTradeStore((s) => s.trades);
  const setTrades = useTradeStore((s) => s.setTrades);
  const [filter, setFilter] = useState<Filter>('all');
  const [selId, setSelId] = useState<number | null>(null);
  const [marks, setMarks] = useState<MarksMap>({});
  const [panelW, setPanelW] = useState<number>(320);
  const [collapsed, setCollapsed] = useState<boolean>(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const dragRef = useRef<{ on: boolean; x0: number; w0: number }>({ on: false, x0: 0, w0: 320 });

  useEffect(() => { fetchTrades().then(setTrades).catch(() => {}); }, [setTrades]);

  // hydrate marks: localStorage (shared with iframe) merged with the DB
  useEffect(() => {
    let dead = false;
    (async () => {
      let local: MarksMap = {};
      try { const raw = localStorage.getItem('mems26_marks'); local = raw ? JSON.parse(raw) : {}; } catch { /* ignore */ }
      try {
        const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const tok = process.env.NEXT_PUBLIC_BRIDGE_TOKEN || 'michael-mems26-2026';
        const r = await fetch(`${base}/api/v9/trade_reviews`, { headers: { Authorization: `Bearer ${tok}` } });
        if (r.ok && !dead) { const d = await r.json() as { reviews?: Record<string, MarkEntry> }; const merged = { ...local }; for (const [id, rev] of Object.entries(d.reviews || {})) merged[id] = { ...(merged[id] || {}), ...rev }; try { localStorage.setItem('mems26_marks', JSON.stringify(merged)); } catch { /* ignore */ } setMarks(merged); return; }
      } catch { /* DB best-effort */ }
      if (!dead) setMarks(local);
    })();
    return () => { dead = true; };
  }, []);

  // reflect marks made inside the iframe (localStorage) into the list
  useEffect(() => {
    const t = setInterval(() => { try { const raw = localStorage.getItem('mems26_marks'); if (raw) setMarks(JSON.parse(raw)); } catch { /* ignore */ } }, 1500);
    return () => clearInterval(t);
  }, []);

  // panel resize
  useEffect(() => {
    const mv = (e: MouseEvent) => { if (!dragRef.current.on) return; setPanelW(Math.max(180, Math.min(580, dragRef.current.w0 + (e.clientX - dragRef.current.x0)))); };
    const up = () => { dragRef.current.on = false; };
    window.addEventListener('mousemove', mv); window.addEventListener('mouseup', up);
    return () => { window.removeEventListener('mousemove', mv); window.removeEventListener('mouseup', up); };
  }, []);

  const rows = useMemo(() => [...trades].sort((a, b) => b.id - a.id).filter((t) => {
    const oc = outcome(t), m = marks[String(t.id)];
    if (filter === 'loss') return oc.cls === 'loss';
    if (filter === 'win') return oc.cls === 'win';
    if (filter === 'noentry') return !!m?.no_entry;
    if (filter === 'marked') return hasMark(m);
    return true;
  }), [trades, filter, marks]);
  const markedTotal = useMemo(() => Object.keys(marks).filter((id) => hasMark(marks[id])).length, [marks]);

  const select = (id: number) => { setSelId(id); iframeRef.current?.contentWindow?.postMessage({ type: 'mems26-select-trade', id }, '*'); };

  return (
    <div style={{ display: 'flex', height: '100%', background: 'var(--bg-primary)' }}>
      {!collapsed && (
        <div style={{ width: panelW, flexShrink: 0, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center', padding: '6px 8px', borderBottom: '1px solid var(--border)', background: 'var(--bg-secondary)' }}>
            {FILTERS.map((f) => (
              <button key={f.id} onClick={() => setFilter(f.id)} title={f.id} style={{ padding: '2px 9px', borderRadius: 6, cursor: 'pointer', fontSize: 12, border: `1px solid ${filter === f.id ? (f.color ?? 'var(--text-secondary)') : 'var(--border)'}`, background: filter === f.id ? 'rgba(255,255,255,0.06)' : 'transparent', color: f.color ?? 'var(--text-primary)', fontWeight: filter === f.id ? 700 : 400 }}>{f.label}</button>
            ))}
            <span style={{ marginInlineStart: 'auto', fontSize: 11, color: '#e3b341', fontFamily: 'var(--mono)' }} title="trades you have marked">✎ {markedTotal}</span>
          </div>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {rows.map((t) => {
              const oc = outcome(t), m = marks[String(t.id)], isSel = t.id === selId;
              return (
                <button key={t.id} onClick={() => select(t.id)} style={{ display: 'flex', alignItems: 'center', gap: 6, width: '100%', textAlign: 'start', padding: '5px 8px', cursor: 'pointer', border: 'none', borderInlineStart: `3px solid ${oc.c}`, borderBottom: '1px solid var(--border)', background: isSel ? 'rgba(88,166,255,0.16)' : 'transparent', color: 'var(--text-primary)', fontFamily: 'var(--mono)', fontSize: 11 }}>
                  <span style={{ color: oc.c, fontWeight: 700, width: 12 }}>{oc.i}</span>
                  <span style={{ width: 30, color: 'var(--text-secondary)' }}>#{t.id}</span>
                  <span style={{ flex: 1, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.pattern_id ?? '?'}</span>
                  <span style={{ width: 38, color: t.direction === 'LONG' ? '#56d364' : '#f85149' }}>{t.direction}</span>
                  <span style={{ width: 46, textAlign: 'end', color: oc.c }}>{money(t.pnl_usd)}</span>
                  {m?.no_entry ? <span title="no-entry">🚫</span> : hasMark(m) ? <span title="marked">✎</span> : <span style={{ width: 12 }} />}
                </button>
              );
            })}
            {rows.length === 0 && <div style={{ padding: 12, color: 'var(--text-secondary)', fontSize: 12 }}>No trades match this filter.</div>}
          </div>
        </div>
      )}
      {!collapsed && <div onMouseDown={(e) => { dragRef.current = { on: true, x0: e.clientX, w0: panelW }; e.preventDefault(); }} title="drag to resize" style={{ width: 5, cursor: 'ew-resize', background: 'var(--border)', flexShrink: 0 }} />}
      <button onClick={() => setCollapsed((c) => !c)} title={collapsed ? 'show list' : 'hide list'} style={{ width: 18, flexShrink: 0, border: 'none', borderInlineEnd: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: 11 }}>{collapsed ? '▸' : '◂'}</button>
      <iframe ref={iframeRef} src="/marker.html" title="Trade Marker (live)" style={{ flex: 1, minWidth: 0, border: 'none', background: '#0d1117' }} />
    </div>
  );
}
