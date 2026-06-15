'use client';
// Trade Review — live W/L selectable list (dashboard tab).
// Added 2026-06-15: surfaces every trade with a clear success/fail marker and a
// selectable list, per Michael's request. Pulls live trades from tradeStore
// (self-loads via fetchTrades so the tab works without the chart view mounted).
// Bridges to the standalone marker tool's saved marks (localStorage 'mems26_marks')
// for the No-entry / Marked filters. Chart-marking (placing levels) stays in the
// standalone tool until the /api/v9/chart/replay aggregator lands (Phase B).
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import { fetchTrades, fetchTradeById, type TradeDetailResponse } from '../../lib/api';
import type { Trade } from '../../types';
import { TradeMarkChart } from './TradeMarkChart';

type Filter = 'all' | 'loss' | 'win' | 'noentry' | 'marked';

interface MarkEntry { no_entry?: boolean; note?: string; [k: string]: unknown; }
type MarksMap = Record<string, MarkEntry>;

interface Outcome { cls: 'win' | 'loss' | 'be' | 'open'; icon: string; color: string; }

function outcomeOf(t: Trade): Outcome {
  const p = t.pnl_usd;
  const o = (t.outcome || '').toUpperCase();
  if (o === 'WIN' || (o === '' && p != null && p > 0)) return { cls: 'win', icon: '✓', color: '#56d364' };
  if (o === 'LOSS' || (o === '' && p != null && p < 0)) return { cls: 'loss', icon: '✗', color: '#f85149' };
  if (p == null && !t.exit_ts) return { cls: 'open', icon: '•', color: '#8b949e' };
  return { cls: 'be', icon: '=', color: '#8b949e' };
}

const money = (v: number | null | undefined): string =>
  v == null ? '—' : (v >= 0 ? '+$' : '-$') + Math.abs(v).toFixed(0);
const num = (v: number | null | undefined): string => (v == null ? '—' : String(v));

function whenLabel(ts: string | null): string {
  if (!ts) return '—';
  const d = new Date(ts);
  if (isNaN(d.getTime())) return ts.slice(5, 16);
  // ET (America/New_York), DST-safe
  return new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(d);
}

function hasAnyMark(m?: MarkEntry): boolean {
  if (!m) return false;
  if (m.no_entry) return true;
  if (typeof m.note === 'string' && m.note.trim()) return true;
  return Object.values(m).some((v) => typeof v === 'number');
}

const FILTERS: Array<{ id: Filter; label: string; color?: string }> = [
  { id: 'all', label: 'All' },
  { id: 'loss', label: '✗ Losses', color: '#f85149' },
  { id: 'win', label: '✓ Wins', color: '#56d364' },
  { id: 'noentry', label: '🚫 No-entry', color: '#f85149' },
  { id: 'marked', label: '✎ Marked', color: '#e3b341' },
];

export function TradeReviewPanel() {
  const trades = useTradeStore((s) => s.trades);
  const setTrades = useTradeStore((s) => s.setTrades);
  const [filter, setFilter] = useState<Filter>('all');
  const [selId, setSelId] = useState<number | null>(null);
  const [marks, setMarks] = useState<MarksMap>({});
  const [showHelp, setShowHelp] = useState<boolean>(false);

  // Self-load trades (the tab can be opened without the chart view mounted).
  useEffect(() => {
    fetchTrades().then(setTrades).catch((e) => console.error('TradeReview: load failed', e));
  }, [setTrades]);

  // Bridge to the marker tool's saved marks (client-only, SSR-safe). Reloaded
  // whenever the chart writes a new mark so the list filters/indicators update.
  const reloadMarks = useCallback(async () => {
    let local: MarksMap = {};
    try { const raw = localStorage.getItem('mems26_marks'); local = raw ? (JSON.parse(raw) as MarksMap) : {}; } catch { /* ignore */ }
    // Hydrate from the DB so marks submitted from ANY browser/origin show up here
    // (fixes the localhost / 127.0.0.1 / file:// split). DB review wins on conflict.
    try {
      const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const tok = process.env.NEXT_PUBLIC_BRIDGE_TOKEN || 'michael-mems26-2026';
      const res = await fetch(`${base}/api/v9/trade_reviews`, { headers: { Authorization: `Bearer ${tok}` } });
      if (res.ok) {
        const d = (await res.json()) as { reviews?: Record<string, MarkEntry> };
        const merged: MarksMap = { ...local };
        for (const [id, rev] of Object.entries(d.reviews || {})) merged[id] = { ...(merged[id] || {}), ...rev };
        try { localStorage.setItem('mems26_marks', JSON.stringify(merged)); } catch { /* ignore */ }
        setMarks(merged); return;
      }
    } catch { /* DB hydrate is best-effort */ }
    setMarks(local);
  }, []);
  useEffect(() => { void reloadMarks(); }, [reloadMarks]);

  const rows = useMemo(() => {
    return [...trades].sort((a, b) => b.id - a.id).filter((t) => {
      const oc = outcomeOf(t);
      const m = marks[String(t.id)];
      if (filter === 'loss') return oc.cls === 'loss';
      if (filter === 'win') return oc.cls === 'win';
      if (filter === 'noentry') return !!m?.no_entry;
      if (filter === 'marked') return hasAnyMark(m);
      return true;
    });
  }, [trades, filter, marks]);

  const summary = useMemo(() => {
    let w = 0, l = 0, net = 0;
    for (const t of rows) {
      const oc = outcomeOf(t);
      if (oc.cls === 'win') w++;
      else if (oc.cls === 'loss') l++;
      if (t.pnl_usd != null) net += t.pnl_usd;
    }
    return { w, l, net, n: rows.length };
  }, [rows]);

  const sel = rows.find((t) => t.id === selId) ?? null;
  const visIds = rows.map((t) => t.id);
  const nav = (d: number) => { if (!visIds.length) return; const i = visIds.indexOf(selId ?? -1); const ni = i < 0 ? 0 : Math.min(Math.max(i + d, 0), visIds.length - 1); setSelId(visIds[ni]); };
  const markedN = rows.filter((t) => hasAnyMark(marks[String(t.id)])).length;

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--bg-primary)', color: 'var(--text-primary)', fontSize: 13 }}>
      {/* collapsible help / legend header */}
      <div onClick={() => setShowHelp((h) => !h)} style={{ cursor: 'pointer', padding: '4px 12px', fontSize: 11, color: '#58a6ff', borderBottom: '1px solid var(--border)', background: 'var(--bg-secondary)' }}>{showHelp ? '▾' : '▸'} How to use · legend</div>
      {showHelp && (
        <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border)', background: 'var(--bg-secondary)', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
          <b style={{ color: 'var(--text-primary)' }}>How:</b> pick a trade → pick a level (Entry / Stop-1..3 / T1..3) → click the price panel to place what <i>you</i> would have done · 🚫 = wouldn&apos;t enter · ✎ note becomes a rule · <b style={{ color: '#1f6feb' }}>⤴ Submit</b> saves to the DB (calibration input). Scroll or drag the price/time axis to zoom; drag the bottom handle to resize.
          <br /><b style={{ color: 'var(--text-primary)' }}>Lines:</b> <span style={{ color: '#d2a8ff' }}>POC</span> · <span style={{ color: '#a5d6ff' }}>VAH/VAL</span> · <span style={{ color: '#ffa657' }}>IB</span> · <span style={{ color: '#ff7bf2' }}>PP</span>/<span style={{ color: '#ff6b6b' }}>R1-3</span>/<span style={{ color: '#3fb950' }}>S1-3</span> · <span style={{ color: '#7ee787' }}>PDH</span>/<span style={{ color: '#ffa198' }}>PDL</span> · <span style={{ color: '#8b949e' }}>dashed</span> = system actuals · solid <b>✎</b> = your marks · CVD histogram (green↑/red↓) · Woodies CCI colored by trend (blue/red/yellow/gray).
        </div>
      )}
      {/* Filter + summary bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', padding: '8px 12px', borderBottom: '1px solid var(--border)', background: 'var(--bg-secondary)' }}>
        <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>Filter:</span>
        {FILTERS.map((f) => {
          const active = filter === f.id;
          return (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              style={{
                padding: '3px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 12,
                border: `1px solid ${active ? (f.color ?? 'var(--text-secondary)') : 'var(--border)'}`,
                background: active ? 'rgba(255,255,255,0.06)' : 'transparent',
                color: f.color ?? 'var(--text-primary)',
                fontWeight: active ? 700 : 400,
              }}
            >{f.label}</button>
          );
        })}
        <span style={{ display: 'flex', gap: 3, alignItems: 'center', marginInlineStart: 6 }}>
          <button onClick={() => nav(-1)} title="previous trade (up)" style={{ padding: '2px 9px', borderRadius: 6, cursor: 'pointer', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text-primary)', fontSize: 12 }}>◀</button>
          <button onClick={() => nav(1)} title="next trade (down)" style={{ padding: '2px 9px', borderRadius: 6, cursor: 'pointer', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text-primary)', fontSize: 12 }}>▶</button>
        </span>
        <span style={{ marginInlineStart: 'auto', fontFamily: 'var(--mono)', fontSize: 12 }}>
          <span style={{ color: '#e3b341' }}>✎ {markedN}/{summary.n}</span>
          {'   '}<span style={{ color: 'var(--text-secondary)' }}>{summary.n} trades</span>
          {'  '}<span style={{ color: '#56d364' }}>{summary.w}W</span>
          {' / '}<span style={{ color: '#f85149' }}>{summary.l}L</span>
          {'  net '}<span style={{ color: summary.net >= 0 ? '#56d364' : '#f85149', fontWeight: 700 }}>{money(summary.net)}</span>
        </span>
      </div>

      {/* Two-column: selectable list + detail */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex' }}>
        {/* List */}
        <div style={{ width: 420, flexShrink: 0, overflowY: 'auto', borderInlineEnd: '1px solid var(--border)' }}>
          {rows.length === 0 && (
            <div style={{ padding: 16, color: 'var(--text-secondary)' }}>No trades match this filter.</div>
          )}
          {rows.map((t) => {
            const oc = outcomeOf(t);
            const m = marks[String(t.id)];
            const isSel = t.id === selId;
            return (
              <button
                key={t.id}
                onClick={() => setSelId(t.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8, width: '100%', textAlign: 'start',
                  padding: '6px 12px', cursor: 'pointer', border: 'none',
                  borderInlineStart: `3px solid ${oc.color}`,
                  borderBottom: '1px solid var(--border)',
                  background: isSel ? 'rgba(88,166,255,0.12)' : 'transparent',
                  color: 'var(--text-primary)', fontFamily: 'var(--mono)', fontSize: 12,
                }}
              >
                <span style={{ color: oc.color, fontWeight: 700, width: 14 }}>{oc.icon}</span>
                <span style={{ width: 38, color: 'var(--text-secondary)' }}>#{t.id}</span>
                <span style={{ flex: 1, fontWeight: 600 }}>{t.pattern_id ?? '?'}</span>
                <span style={{ width: 44, color: t.direction === 'LONG' ? '#56d364' : '#f85149' }}>{t.direction}</span>
                <span style={{ width: 84, color: 'var(--text-secondary)' }}>{whenLabel(t.entry_ts)}</span>
                <span style={{ width: 56, textAlign: 'end', color: oc.color }}>{money(t.pnl_usd)}</span>
                {m?.no_entry && <span title="marked: would not enter">🚫</span>}
                {!m?.no_entry && hasAnyMark(m) && <span title="has marks">✎</span>}
              </button>
            );
          })}
        </div>

        {/* Detail */}
        <div style={{ flex: 1, minWidth: 0, overflowY: 'auto', padding: 16 }}>
          {!sel ? (
            <div style={{ color: 'var(--text-secondary)' }}>Select a trade to chart it and mark what you would have done.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <TradeMarkChart trade={sel} onChange={reloadMarks} />
              <DetailView t={sel} mark={marks[String(sel.id)]} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ k, v, color }: { k: string; v: string; color?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid var(--border)' }}>
      <span style={{ color: 'var(--text-secondary)' }}>{k}</span>
      <span style={{ fontFamily: 'var(--mono)', color: color ?? 'var(--text-primary)' }}>{v}</span>
    </div>
  );
}

function DetailView({ t, mark }: { t: Trade; mark?: MarkEntry }) {
  const oc = outcomeOf(t);
  return (
    <div style={{ maxWidth: 480 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
        <span style={{ background: oc.color, color: '#0d1117', padding: '2px 10px', borderRadius: 6, fontWeight: 700, fontSize: 12 }}>
          {oc.cls.toUpperCase()} {money(t.pnl_usd)}
        </span>
        <span style={{ fontWeight: 700 }}>#{t.id} · {t.pattern_id ?? '?'} · {t.direction}</span>
      </div>
      <Row k="Result" v={`${t.outcome ?? oc.cls} · ${t.exit_reason ?? '—'}`} color={oc.color} />
      <Row k="P&L ($ / R)" v={`${money(t.pnl_usd)} / ${t.pnl_r == null ? '—' : t.pnl_r.toFixed(2) + 'R'}`} color={oc.color} />
      <Row k="Entry" v={`${num(t.entry_price)}  @ ${whenLabel(t.entry_ts)}`} />
      <Row k="Stop (init)" v={`${num(t.stop)}${t.stop_initial != null && t.stop_initial !== t.stop ? `  (init ${num(t.stop_initial)})` : ''}`} color="#f85149" />
      <Row k="T1 / T2 / T3" v={`${num(t.t1)} / ${num(t.t2)} / ${num(t.t3)}`} />
      <Row k="Exit" v={`${num(t.exit_price)}  @ ${whenLabel(t.exit_ts)}`} />
      <Row k="MFE / MAE (pts)" v={`${num(t.mfe_pts)} / ${num(t.mae_pts)}`} />
      <Row k="Day type / Mode" v={`${t.day_type ?? '—'} / ${t.mode}`} />
      {mark && (mark.no_entry || (mark.note && mark.note.trim())) && (
        <div style={{ marginTop: 12, padding: 10, borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg-secondary)' }}>
          <div style={{ color: '#e3b341', fontWeight: 700, marginBottom: 4 }}>
            {mark.no_entry ? '🚫 Marked: would not enter' : '✎ Marked'}
          </div>
          {mark.note && <div style={{ color: 'var(--text-primary)' }}>{mark.note}</div>}
        </div>
      )}
      <SystemRationale tradeId={t.id} />
    </div>
  );
}

// "Why the system fired" — fire headline + each observer system's view (what it
// saw + agree/disagree), from /api/v9/trades/{id} insight.
function SystemRationale({ tradeId }: { tradeId: number }) {
  const [data, setData] = useState<TradeDetailResponse | null>(null);
  const [open, setOpen] = useState(true);
  useEffect(() => { let dead = false; fetchTradeById(tradeId).then((d) => { if (!dead) setData(d); }).catch(() => {}); return () => { dead = true; }; }, [tradeId]);
  const ins = data?.insight; const fire = ins?.fire as Record<string, unknown> | undefined; const rec = ins?.recognition ?? [];
  if (!fire) return null;
  const s = (k: string) => (fire[k] == null ? '—' : String(fire[k]));
  return (
    <div style={{ marginTop: 12, border: '1px solid var(--border)', borderRadius: 6, background: 'var(--bg-secondary)' }}>
      <div onClick={() => setOpen((o) => !o)} style={{ cursor: 'pointer', padding: '6px 10px', fontWeight: 700, color: '#58a6ff' }}>{open ? '▾' : '▸'} Why the system fired — {s('headline')}</div>
      {open && (
        <div style={{ padding: '0 10px 10px' }}>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>trigger {s('trigger')} · day {s('day_type')} · confidence {s('confidence')}{fire.blocked_by ? ' · blocked: ' + s('blocked_by') : ''}</div>
          {rec.map((o) => (
            <div key={o.id} style={{ display: 'flex', gap: 8, padding: '3px 0', borderTop: '1px solid var(--border)', fontSize: 12 }}>
              <span style={{ width: 14, color: o.agree === true ? '#56d364' : o.agree === false ? '#f85149' : '#6e7681' }}>{o.agree === true ? '✓' : o.agree === false ? '✗' : '·'}</span>
              <span style={{ width: 116, color: o.is_firing ? '#e3b341' : 'var(--text-primary)', fontWeight: o.is_firing ? 700 : 400 }}>{o.name}</span>
              <span style={{ flex: 1, color: 'var(--text-secondary)', fontFamily: 'var(--mono)' }}>{(o.lines || []).join(' · ')}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
