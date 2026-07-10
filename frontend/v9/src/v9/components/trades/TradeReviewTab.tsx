'use client';
// TradeReviewTab — collapsible/resizable trade list (left) + the proven live
// marker tool in an iframe (right). Clicking a trade posts a message to the
// marker (/marker.html) which selects it.
//
// UI round 2 (2026-07-02) — the LIST was rebuilt (Michael's fix #1); the marker
// workspace (iframe) is untouched:
// - Real column headers (sticky): שעה · # · תבנית · כיוון · סוג-יום · P&L · תוצאה
// - Comfortable rows (~30px), day-type chip colored via lib/dayType (canonical
//   palette), direction badge, RTL panel with dir="ltr" wraps on numbers/latin.
// - Labeled filter chips: הכל / ✓ רווח / ✗ הפסד / = BE / 🏷 מסומנות / DEMO
//   (+ counts), plus a pattern dropdown filter.
// - Keyboard ↑/↓ moves the selection (and the marker iframe follows).
// Marks are read from localStorage (PRE-EXISTING bridge shared with the iframe)
// + the DB (/api/v9/trade_reviews) and re-polled so marks made in the iframe
// show up here within ~1.5s — mechanism unchanged.
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import { fetchTrades } from '../../lib/api';
import { fmtTimeET } from '../../lib/tradeTime';
import { dayTypeColor, dayTypeAbbrev } from '../../lib/dayType';
import { systemColor } from '../../design/system_colors';
import type { Trade } from '../../types';

type Filter = 'all' | 'win' | 'loss' | 'be' | 'marked' | 'demo';
interface MarkEntry { no_entry?: boolean; note?: string; [k: string]: unknown; }
type MarksMap = Record<string, MarkEntry>;

const FILTERS: Array<{ id: Filter; label: string; color?: string; title: string }> = [
  { id: 'all',    label: 'הכל',        title: 'כל העסקאות' },
  { id: 'win',    label: '✓ רווח',     color: '#56d364', title: 'עסקאות ברווח' },
  { id: 'loss',   label: '✗ הפסד',     color: '#f85149', title: 'עסקאות בהפסד' },
  { id: 'be',     label: '= BE',       color: '#d29922', title: 'ברייק-איבן / סקראץ׳' },
  { id: 'marked', label: '🏷 מסומנות', color: '#e3b341', title: 'עסקאות שסימנת (כולל 🚫 לא-נכנס)' },
  { id: 'demo',   label: 'DEMO',       color: '#06b6d4', title: 'עסקאות DEMO בלבד (mode=demo)' },
];

const outcome = (t: Trade) => {
  const p = t.pnl_usd, o = (t.outcome || '').toUpperCase();
  if (o === 'WIN' || (o === '' && p != null && p > 0)) return { i: '✓', c: '#56d364', cls: 'win' };
  if (o === 'LOSS' || (o === '' && p != null && p < 0)) return { i: '✗', c: '#f85149', cls: 'loss' };
  if (p == null && !t.exit_ts) return { i: '•', c: '#8b949e', cls: 'open' };
  return { i: '=', c: '#d29922', cls: 'be' };
};
const money = (v: number | null | undefined) => (v == null ? '—' : (v >= 0 ? '+$' : '-$') + Math.abs(v).toFixed(0));
const hasMark = (m?: MarkEntry) => { if (!m) return false; if (m.no_entry) return true; if (typeof m.note === 'string' && m.note.trim()) return true; return Object.values(m).some((v) => typeof v === 'number'); };
/** Pattern label — same fallback chain as PatternPerformanceStrip (pattern_id → classification → trigger). */
const patternOf = (t: Trade): string | null => t.pattern_id ?? t.classification ?? t.trigger ?? null;
/** Day-type: prefer the entry-stamped SoT column when the API row carries it; fall back to the
 *  display-derived day_type the API returns today (same caveat as round-1 TradesTable). */
const dayTypeOf = (t: Trade): string | null =>
  (t as { day_type_at_entry?: string | null }).day_type_at_entry ?? t.day_type ?? null;

// Shared grid — header and rows must stay in sync. RTL panel: first column renders rightmost.
const GRID = '40px 40px minmax(0,1fr) 42px 46px 54px 20px 18px';

export function TradeReviewTab() {
  const trades = useTradeStore((s) => s.trades);
  const setTrades = useTradeStore((s) => s.setTrades);
  const [filter, setFilter] = useState<Filter>('all');
  const [patternFilter, setPatternFilter] = useState<string>('');
  const [selId, setSelId] = useState<number | null>(null);
  const [marks, setMarks] = useState<MarksMap>({});
  const [panelW, setPanelW] = useState<number>(400);
  const [collapsed, setCollapsed] = useState<boolean>(false);
  const [iframeV] = useState<number>(() => Date.now()); // cache-bust the static marker.html per mount
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const rowRefs = useRef<Map<number, HTMLButtonElement>>(new Map());
  const dragRef = useRef<{ on: boolean; x0: number; w0: number }>({ on: false, x0: 0, w0: 400 });

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
    const mv = (e: MouseEvent) => { if (!dragRef.current.on) return; setPanelW(Math.max(260, Math.min(640, dragRef.current.w0 + (e.clientX - dragRef.current.x0)))); };
    const up = () => { dragRef.current.on = false; };
    window.addEventListener('mousemove', mv); window.addEventListener('mouseup', up);
    return () => { window.removeEventListener('mousemove', mv); window.removeEventListener('mouseup', up); };
  }, []);

  const patterns = useMemo(() => {
    const set = new Set<string>();
    for (const t of trades) { const p = patternOf(t); if (p) set.add(p); }
    return [...set].sort();
  }, [trades]);

  const matchesChip = (t: Trade, f: Filter): boolean => {
    const oc = outcome(t), m = marks[String(t.id)];
    if (f === 'loss') return oc.cls === 'loss';
    if (f === 'win') return oc.cls === 'win';
    if (f === 'be') return oc.cls === 'be';
    if (f === 'marked') return hasMark(m);
    if (f === 'demo') return t.mode === 'SIM'; // mapTradeRow: backend "demo" → SIM (lib/api.ts:153-161)
    return true;
  };

  const rows = useMemo(() => [...trades].sort((a, b) => b.id - a.id).filter((t) => {
    if (!matchesChip(t, filter)) return false;
    if (patternFilter && patternOf(t) !== patternFilter) return false;
    return true;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [trades, filter, patternFilter, marks]);

  const counts = useMemo(() => {
    const c: Record<Filter, number> = { all: trades.length, win: 0, loss: 0, be: 0, marked: 0, demo: 0 };
    for (const t of trades) {
      const oc = outcome(t);
      if (oc.cls === 'win') c.win++;
      else if (oc.cls === 'loss') c.loss++;
      else if (oc.cls === 'be') c.be++;
      if (hasMark(marks[String(t.id)])) c.marked++;
      if (t.mode === 'SIM') c.demo++;
    }
    return c;
  }, [trades, marks]);

  const select = (id: number) => {
    setSelId(id);
    iframeRef.current?.contentWindow?.postMessage({ type: 'mems26-select-trade', id }, '*');
    requestAnimationFrame(() => rowRefs.current.get(id)?.scrollIntoView({ block: 'nearest' }));
  };

  // Keyboard ↑/↓ between trades (skipped while typing in inputs/textareas/selects).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
      const el = e.target as HTMLElement | null;
      if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable)) return;
      if (!rows.length || collapsed) return;
      e.preventDefault();
      const idx = rows.findIndex((r) => r.id === selId);
      const next = idx === -1
        ? rows[0]
        : rows[Math.max(0, Math.min(rows.length - 1, idx + (e.key === 'ArrowDown' ? 1 : -1)))];
      if (next && next.id !== selId) select(next.id);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, selId, collapsed]);

  const markedTotal = counts.marked;

  const HeadCell = ({ label, title, style }: { label: string; title: string; style?: React.CSSProperties }) => (
    <span title={title} style={{ fontSize: 10, color: 'var(--text-secondary)', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', ...style }}>{label}</span>
  );

  return (
    <div style={{ display: 'flex', height: '100%', background: 'var(--bg-primary)' }}>
      {!collapsed && (
        <div dir="rtl" style={{ width: panelW, flexShrink: 0, display: 'flex', flexDirection: 'column', minWidth: 0, borderInlineEnd: '1px solid var(--border)' }}>
          {/* Filter chips (labeled + counts) */}
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center', padding: '6px 8px', borderBottom: '1px solid var(--border)', background: 'var(--bg-secondary)' }}>
            {FILTERS.map((f) => (
              <button key={f.id} onClick={() => setFilter(f.id)} title={f.title}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 4, padding: '3px 9px', borderRadius: 6, cursor: 'pointer', fontSize: 11.5,
                  border: `1px solid ${filter === f.id ? (f.color ?? 'var(--text-secondary)') : 'var(--border)'}`,
                  background: filter === f.id ? 'rgba(255,255,255,0.07)' : 'transparent',
                  color: f.color ?? 'var(--text-primary)', fontWeight: filter === f.id ? 700 : 400,
                }}>
                {f.label}
                <span dir="ltr" style={{ fontSize: 9.5, color: 'var(--text-secondary)', fontFamily: 'var(--mono)' }}>{counts[f.id]}</span>
              </button>
            ))}
            <span style={{ marginInlineStart: 'auto', fontSize: 11, color: '#e3b341', fontFamily: 'var(--mono)' }} title="עסקאות שסימנת">✎ <span dir="ltr">{markedTotal}</span></span>
          </div>
          {/* Pattern dropdown + hint */}
          <div style={{ display: 'flex', gap: 6, alignItems: 'center', padding: '5px 8px', borderBottom: '1px solid var(--border)', background: 'var(--bg-secondary)' }}>
            <label style={{ fontSize: 10.5, color: 'var(--text-secondary)', flexShrink: 0 }}>תבנית:</label>
            <select value={patternFilter} onChange={(e) => setPatternFilter(e.target.value)}
              style={{ flex: 1, minWidth: 0, background: 'var(--bg-primary)', color: 'var(--text-primary)', border: '1px solid var(--border)', borderRadius: 5, padding: '2px 6px', fontSize: 11, fontFamily: 'var(--mono)' }}>
              <option value="">כל התבניות ({patterns.length})</option>
              {patterns.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
            {patternFilter && (
              <button onClick={() => setPatternFilter('')} title="נקה סינון תבנית"
                style={{ border: '1px solid var(--border)', background: 'transparent', color: 'var(--text-secondary)', borderRadius: 5, fontSize: 11, padding: '1px 7px', cursor: 'pointer' }}>✕</button>
            )}
            <span style={{ fontSize: 9.5, color: 'var(--text-secondary)', flexShrink: 0 }} title="ניווט במקלדת">↑↓ ניווט</span>
          </div>
          {/* List + sticky column headers */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            <div style={{
              display: 'grid', gridTemplateColumns: GRID, gap: 4, alignItems: 'center',
              padding: '5px 8px 5px 6px', position: 'sticky', top: 0, zIndex: 2,
              background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border)',
            }}>
              <HeadCell label="שעה" title="שעת כניסה (ET)" />
              <HeadCell label="#" title="מזהה עסקה" />
              <HeadCell label="תבנית" title="pattern_id → classification → trigger" />
              <HeadCell label="כיוון" title="LONG / SHORT" />
              <HeadCell label="סוג-יום" title="סוג-היום בכניסה (day_type_at_entry אם קיים, אחרת day_type)" />
              <HeadCell label="P&L$" title="רווח/הפסד בדולרים" style={{ textAlign: 'left' }} />
              <HeadCell label="✓" title="תוצאה: ✓ רווח · ✗ הפסד · = BE · • פתוחה" style={{ textAlign: 'center' }} />
              <span title="סימון שלך: ✎ מסומנת · 🚫 לא-נכנס" style={{ fontSize: 10, color: 'var(--text-secondary)' }}>✎</span>
            </div>
            {rows.map((t) => {
              const oc = outcome(t), m = marks[String(t.id)], isSel = t.id === selId;
              const dt = dayTypeOf(t);
              const dtc = dayTypeColor(dt);
              const dtKnown = !!dt && dt.toUpperCase() !== 'UNKNOWN';
              const dirLong = t.direction === 'LONG';
              // מייקל 07-10: תג-מערכת (S2/S4) בכל שורה — firing_system מגיע כ-t.system מ-/api/v9/trades.
              const sys = Number(t.system) || null;
              return (
                <button
                  key={t.id}
                  ref={(el) => { if (el) rowRefs.current.set(t.id, el); else rowRefs.current.delete(t.id); }}
                  onClick={() => select(t.id)}
                  style={{
                    display: 'grid', gridTemplateColumns: GRID, gap: 4, alignItems: 'center',
                    width: '100%', textAlign: 'start', padding: '7px 8px 7px 6px', cursor: 'pointer', border: 'none',
                    borderInlineStart: `3px solid ${oc.c}`, borderBottom: '1px solid var(--border)',
                    background: isSel ? 'rgba(88,166,255,0.16)' : 'transparent',
                    color: 'var(--text-primary)', fontFamily: 'var(--mono)', fontSize: 11.5,
                  }}
                >
                  <span dir="ltr" style={{ color: 'var(--text-secondary)' }} title="שעת כניסה ET">
                    {t.entry_ts ? fmtTimeET(t.entry_ts) : '—'}
                  </span>
                  <span dir="ltr" style={{ color: 'var(--text-secondary)' }}>#{t.id}</span>
                  <span dir="ltr" style={{ display: 'flex', alignItems: 'center', gap: 3, minWidth: 0 }}>
                    {sys ? (
                      <span title={`מערכת ${sys}`} style={{
                        flexShrink: 0, fontSize: 8, fontWeight: 700, padding: '0 3px', borderRadius: 3,
                        color: systemColor(sys), background: `${systemColor(sys)}22`, border: `1px solid ${systemColor(sys)}66`,
                        fontFamily: 'ui-monospace',
                      }}>S{sys}</span>
                    ) : null}
                    <span style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', minWidth: 0 }} title={patternOf(t) ?? ''}>
                      {patternOf(t) ?? '?'}
                    </span>
                  </span>
                  <span dir="ltr" style={{
                    fontSize: 9.5, fontWeight: 700, textAlign: 'center', borderRadius: 4, padding: '1px 0',
                    color: dirLong ? '#56d364' : '#f85149',
                    background: dirLong ? 'rgba(86,211,100,0.10)' : 'rgba(248,81,73,0.10)',
                    border: `1px solid ${dirLong ? 'rgba(86,211,100,0.35)' : 'rgba(248,81,73,0.35)'}`,
                  }} title={t.direction}>
                    {dirLong ? '▲ L' : '▼ S'}
                  </span>
                  {dtKnown ? (
                    <span dir="ltr" style={{
                      fontSize: 9.5, fontWeight: 700, textAlign: 'center', borderRadius: 4, padding: '1px 0',
                      color: dtc, background: `${dtc}1a`, border: `1px solid ${dtc}55`,
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }} title={`סוג-יום: ${dt}`}>
                      {dayTypeAbbrev(dt)}
                    </span>
                  ) : (
                    <span dir="rtl" style={{
                      fontSize: 8.5, fontWeight: 600, textAlign: 'center', borderRadius: 4, padding: '1px 0',
                      color: 'var(--text-secondary)', background: 'rgba(110,118,129,0.10)', border: '1px solid rgba(110,118,129,0.35)',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }} title="סיווג בהתהוות (day_type בעת-הירי = UNKNOWN)">
                      בהת׳
                    </span>
                  )}
                  <span dir="ltr" style={{ textAlign: 'right', color: oc.cls === 'be' || t.pnl_usd == null ? 'var(--text-secondary)' : oc.c }}>
                    {money(t.pnl_usd)}
                  </span>
                  <span style={{ color: oc.c, fontWeight: 700, textAlign: 'center' }} title={oc.cls}>{oc.i}</span>
                  {m?.no_entry ? <span title="סימנת: לא-נכנס">🚫</span> : hasMark(m) ? <span title="מסומנת">✎</span> : <span />}
                </button>
              );
            })}
            {rows.length === 0 && <div style={{ padding: 12, color: 'var(--text-secondary)', fontSize: 12 }}>אין עסקאות שמתאימות לסינון.</div>}
          </div>
        </div>
      )}
      {!collapsed && <div onMouseDown={(e) => { dragRef.current = { on: true, x0: e.clientX, w0: panelW }; e.preventDefault(); }} title="גרור לשינוי רוחב" style={{ width: 5, cursor: 'ew-resize', background: 'var(--border)', flexShrink: 0 }} />}
      <button onClick={() => setCollapsed((c) => !c)} title={collapsed ? 'הצג רשימה' : 'הסתר רשימה'} style={{ width: 18, flexShrink: 0, border: 'none', borderInlineEnd: '1px solid var(--border)', background: 'var(--bg-secondary)', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: 11 }}>{collapsed ? '▸' : '◂'}</button>
      <iframe ref={iframeRef} src={`/marker.html?v=${iframeV}`} title="Trade Marker (live)" style={{ flex: 1, minWidth: 0, border: 'none', background: '#0d1117' }} />
    </div>
  );
}
