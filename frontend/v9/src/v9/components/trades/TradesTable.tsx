'use client';
// TradesTable — Trade Review table (P-UI round, ADAPTED from the previous
// orphan implementation; skeleton kept: sticky header, expand row →
// TradeRowExpand which reuses MgmtTimeline + TradeChart, pattern chip
// click-to-filter, synthetic TEST badge).
//
// Columns per Michael's Trade-Review spec: time · id · pattern · mode ·
// direction · day-type · entry · stop (BE label) · exit · P&L (colored) ·
// exit_reason · T1-hit badge. Every column header is click-sortable
// (asc/desc, nulls last). Filtering stays in the shared tradeStore
// (mode / direction / pattern / date — default today, see TradeFilters).
//
// Field sources (backend/v9/api/v9/trades.py::_trade_list_row):
//   entry_ts, entry_price, stop, stop_note ("BE@entry" when t1_hit_ts set and
//   |stop-entry| < 0.5 — trades.py:81-87), exit_price, exit_reason, pnl_usd,
//   pnl_r, t1_hit/t2_hit/t3_hit, mode, direction, is_synthetic, stop_issue.
//   pattern_id / day_type come from extract_trade_display (trades.py:133 →
//   services/trade_context.py:647,658). The stamped SoT columns
//   v9_trades.pattern_id_at_entry / day_type_at_entry (db/models/trades.py:62-63,
//   docs/SOURCE_OF_TRUTH.md §Trades) are NOT in the API response yet — the
//   accessors below prefer them if the backend ever adds them, else fall back
//   to the display-derived fields (honest fallback, no synthesis).
import { Fragment, useState } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import type { Trade } from '../../types';
import { cellClass, contractHits, fmtPrice, pnlCell } from './tradeRowFormat';
import { tradeWhen } from '../../lib/tradeTime';
import { TradeRowExpand } from './TradeRowExpand';
import { patternKey } from './PatternPerformanceStrip';

const TD = `${cellClass()} px-2 py-1.5 align-top`;
const COLS = 13; // caret + 12 data columns

// ── field accessors ─────────────────────────────────────────────────────────

/** Pattern at entry: stamped SoT column if present, else display-derived. */
function patternAtEntry(t: Trade): string | null {
  const stamped = (t as unknown as Record<string, unknown>)['pattern_id_at_entry'];
  if (typeof stamped === 'string' && stamped) return stamped;
  return t.pattern_id ?? null;
}

/** Day-type at entry: stamped SoT column if present, else display-derived. */
function dayTypeAtEntry(t: Trade): string | null {
  const stamped = (t as unknown as Record<string, unknown>)['day_type_at_entry'];
  if (typeof stamped === 'string' && stamped) return stamped;
  return t.day_type ?? null;
}

/** Stop is at breakeven: backend stamps stop_note="BE@entry" when t1_hit_ts is
 *  set AND |stop-entry| < 0.5 (trades.py:81-87); direct check kept as fallback. */
function stopIsBE(t: Trade): boolean {
  if (t.stop_note === 'BE@entry') return true;
  return !!t.t1_hit && t.stop != null && t.entry_price != null && Math.abs(t.stop - t.entry_price) < 0.5;
}

// ── sorting ──────────────────────────────────────────────────────────────────

type SortKey =
  | 'time' | 'id' | 'pattern' | 'mode' | 'dir' | 'daytype'
  | 'entry' | 'stop' | 'exit' | 'pnl' | 'reason' | 't1';
type SortDir = 'asc' | 'desc';

const numVal = (v: number | null | undefined): number | null => (v != null && Number.isFinite(v) ? v : null);

function sortValue(t: Trade, key: SortKey): string | number | null {
  switch (key) {
    case 'time': return t.entry_ts ?? null; // ISO strings compare chronologically
    case 'id': return t.id;
    case 'pattern': return patternAtEntry(t);
    case 'mode': return t.mode ?? null;
    case 'dir': return t.direction ?? null;
    case 'daytype': return dayTypeAtEntry(t);
    case 'entry': return numVal(t.entry_price);
    case 'stop': return numVal(t.stop);
    case 'exit': return numVal(t.exit_price);
    case 'pnl': return numVal(t.pnl_usd);
    case 'reason': return t.exit_reason ?? null;
    case 't1': return t.t1_hit ? 1 : 0;
  }
}

function compareTrades(a: Trade, b: Trade, key: SortKey, dir: SortDir): number {
  const va = sortValue(a, key);
  const vb = sortValue(b, key);
  if (va == null && vb == null) return b.id - a.id;
  if (va == null) return 1; // nulls last regardless of direction
  if (vb == null) return -1;
  let cmp: number;
  if (typeof va === 'number' && typeof vb === 'number') cmp = va - vb;
  else cmp = String(va).localeCompare(String(vb));
  if (cmp === 0) cmp = a.id - b.id;
  return dir === 'asc' ? cmp : -cmp;
}

function Th({
  label, k, sort, onSort, align = 'left', title,
}: {
  label: string;
  k: SortKey;
  sort: { key: SortKey; dir: SortDir };
  onSort: (k: SortKey) => void;
  align?: 'left' | 'right';
  title?: string;
}) {
  const active = sort.key === k;
  return (
    <th
      className={`px-2 py-2 font-medium cursor-pointer select-none whitespace-nowrap ${align === 'right' ? 'text-right' : 'text-left'}`}
      style={{ color: active ? 'var(--sys1)' : undefined }}
      title={title ?? 'לחיצה = מיון לפי עמודה זו'}
      onClick={() => onSort(k)}
    >
      {label}
      <span style={{ marginInlineStart: 3, fontSize: 8, opacity: active ? 1 : 0.35 }}>
        {active ? (sort.dir === 'asc' ? '▲' : '▼') : '↕'}
      </span>
    </th>
  );
}

// ── table ────────────────────────────────────────────────────────────────────

export function TradesTable() {
  const { filteredTrades, expandedTradeId, toggleExpandedTradeId, filters, setFilters } = useTradeStore();
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDir }>({ key: 'time', dir: 'desc' });
  const activePattern = (filters.pattern ?? '').trim().toUpperCase();

  // Same per-render pattern as TradeCardList (`const trades = filteredTrades()`);
  // filteredTrades() returns a fresh array, so sorting a copy per render is the
  // codebase-consistent approach (≤500 rows — cheap).
  const trades = [...filteredTrades()].sort((a, b) => compareTrades(a, b, sort.key, sort.dir));

  const onSort = (k: SortKey) =>
    setSort((s) => (s.key === k ? { key: k, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key: k, dir: k === 'time' || k === 'pnl' || k === 'id' ? 'desc' : 'asc' }));

  return (
    <div className="overflow-x-auto rounded" style={{ border: '1px solid var(--border)' }}>
      <table className={`w-full min-w-[1180px] border-collapse ${cellClass()}`}>
        <thead>
          <tr
            className="sticky top-0 z-10 uppercase tracking-wide"
            style={{ background: 'var(--bg-secondary)', color: 'var(--text-secondary)', fontSize: '10px' }}
          >
            <th className="text-left px-2 py-2 font-medium w-6" />
            <Th label="זמן" k="time" sort={sort} onSort={onSort} />
            <Th label="#" k="id" sort={sort} onSort={onSort} />
            <Th label="תבנית" k="pattern" sort={sort} onSort={onSort} title="pattern_id_at_entry (חלופה: pattern_id מה-API)" />
            <Th label="מצב" k="mode" sort={sort} onSort={onSort} />
            <Th label="כיוון" k="dir" sort={sort} onSort={onSort} />
            <Th label="סוג-יום" k="daytype" sort={sort} onSort={onSort} title="day_type_at_entry (חלופה: day_type מה-API)" />
            <Th label="כניסה" k="entry" sort={sort} onSort={onSort} align="right" />
            <Th label="סטופ" k="stop" sort={sort} onSort={onSort} align="right" title="BE = הסטופ הוזז לנקודת הכניסה אחרי T1" />
            <Th label="יציאה" k="exit" sort={sort} onSort={onSort} align="right" />
            <Th label="P&L" k="pnl" sort={sort} onSort={onSort} align="right" />
            <Th label="סיבת יציאה" k="reason" sort={sort} onSort={onSort} />
            <Th label="T1" k="t1" sort={sort} onSort={onSort} title="T1 hit · tooltip מציג C1/C2/C3" />
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => {
            const open = expandedTradeId === t.id;
            const pnlColor =
              t.pnl_usd != null
                ? t.pnl_usd > 0
                  ? 'var(--green)'
                  : t.pnl_usd < 0
                    ? 'var(--red)'
                    : 'var(--text-secondary)'
                : 'var(--text-muted)';
            const p = pnlCell(t);
            const pattern = patternAtEntry(t);
            const patKey = patternKey(t);
            const dayType = dayTypeAtEntry(t);
            const be = stopIsBE(t);
            return (
              <Fragment key={t.id}>
                <tr
                  className="border-b cursor-pointer hover:bg-[var(--bg-secondary)]"
                  style={{
                    borderColor: 'var(--border)',
                    color: t.is_synthetic ? 'var(--text-muted)' : 'var(--text-primary)',
                    background: open
                      ? 'rgba(255,255,255,0.04)'
                      : t.is_synthetic
                        ? 'rgba(234,179,8,0.03)'
                        : t.stop_issue
                          ? 'rgba(234,179,8,0.06)'
                          : undefined,
                    opacity: t.is_synthetic ? 0.6 : 1,
                  }}
                  onClick={() => toggleExpandedTradeId(t.id)}
                >
                  <td className={`${TD} w-6 text-center`} style={{ color: 'var(--text-muted)' }}>
                    {open ? '▼' : '▶'}
                  </td>
                  <td className={TD} style={{ color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                    {(() => {
                      const w = tradeWhen(t.entry_ts);
                      if (!w) return '—';
                      return (
                        <>
                          <span className="block">{w.date} {w.etTime} <span style={{ color: 'var(--text-muted)' }}>ET</span></span>
                          <span className="block text-[10px]" style={{ color: 'var(--text-muted)' }}>{w.ilTime} IL</span>
                        </>
                      );
                    })()}
                  </td>
                  <td className={TD} style={{ color: 'var(--text-muted)' }}>
                    {t.id}
                    {t.is_synthetic && (
                      <span
                        style={{
                          display: 'inline-block',
                          marginInlineStart: 4,
                          padding: '0 3px',
                          fontSize: 8,
                          fontWeight: 700,
                          borderRadius: 2,
                          background: 'rgba(234,179,8,0.2)',
                          color: '#d97706',
                          border: '1px solid rgba(234,179,8,0.3)',
                          verticalAlign: 'middle',
                        }}
                      >
                        TEST
                      </span>
                    )}
                  </td>
                  <td className={TD}>
                    {patKey === '(none)' && !pattern ? (
                      <span style={{ color: 'var(--text-muted)' }}>—</span>
                    ) : (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setFilters({ pattern: activePattern === patKey ? null : patKey });
                        }}
                        className="px-1.5 py-0.5 rounded text-[10px] font-semibold hover:opacity-80"
                        style={{
                          background: activePattern === patKey ? 'rgba(59,130,246,0.18)' : 'rgba(255,255,255,0.06)',
                          color: activePattern === patKey ? 'var(--sys1)' : 'var(--text-primary)',
                          border: activePattern === patKey ? '1px solid var(--sys1)' : '1px solid transparent',
                        }}
                        title={
                          activePattern === patKey
                            ? `ניקוי סינון (כרגע: ${patKey})`
                            : `סינון לתבנית ${patKey} בלבד · ${t.trigger ?? ''}`.trim()
                        }
                      >
                        {pattern ?? patKey}
                      </button>
                    )}
                  </td>
                  <td className={TD}>
                    <span
                      style={{
                        fontSize: 9,
                        fontWeight: 600,
                        padding: '1px 5px',
                        borderRadius: 3,
                        color: t.mode === 'LIVE' ? '#fca5a5' : t.mode === 'SIM' ? '#06b6d4' : '#facc15',
                        border: `1px solid ${t.mode === 'LIVE' ? '#dc2626' : t.mode === 'SIM' ? '#06b6d4' : '#facc15'}44`,
                      }}
                    >
                      {t.mode === 'SIM' ? 'DEMO' : t.mode}
                    </span>
                  </td>
                  <td className={TD}>
                    <span style={{ color: t.direction === 'LONG' ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>
                      {t.direction === 'LONG' ? '▲' : '▼'} {t.direction}
                    </span>
                  </td>
                  <td className={TD} style={{ color: 'var(--text-secondary)' }}>
                    {dayType ?? '—'}
                  </td>
                  <td className={`${TD} text-right`}>{fmtPrice(t.entry_price)}</td>
                  <td className={`${TD} text-right`} title={t.stop_initial != null && t.stop != null && Math.abs(t.stop_initial - t.stop) >= 0.01 ? `סטופ התחלתי ${fmtPrice(t.stop_initial)} → ${fmtPrice(t.stop)}` : undefined}>
                    {be ? (
                      <span
                        style={{
                          fontSize: 9,
                          fontWeight: 700,
                          padding: '1px 5px',
                          borderRadius: 3,
                          color: '#eab308',
                          border: '1px solid rgba(234,179,8,0.45)',
                          background: 'rgba(234,179,8,0.10)',
                        }}
                        title={`BE — הסטופ בנקודת הכניסה (${fmtPrice(t.stop)})`}
                      >
                        BE
                      </span>
                    ) : (
                      fmtPrice(t.stop)
                    )}
                    {t.stop_issue === 'T1_NO_BE' && (
                      <span style={{ marginInlineStart: 3, color: '#eab308', fontSize: 8, fontWeight: 700 }} title="T1 נגע אך הסטופ לא הוזז ל-BE">
                        ⚠
                      </span>
                    )}
                  </td>
                  <td className={`${TD} text-right`}>{fmtPrice(t.exit_price)}</td>
                  <td className={`${TD} text-right`}>
                    <span className="font-semibold block" style={{ color: pnlColor }}>{p.value}</span>
                    <span
                      className="block text-[10px]"
                      style={{ color: t.pnl_mode === 'partial' ? '#eab308' : 'var(--text-muted)' }}
                    >
                      {p.sub}
                    </span>
                  </td>
                  <td className={TD} style={{ color: 'var(--text-secondary)', maxWidth: 120 }}>
                    <span className="block overflow-hidden text-ellipsis whitespace-nowrap" title={t.exit_reason ?? undefined}>
                      {t.exit_reason ?? (t.state && t.state !== 'CLOSED' ? t.state : '—')}
                    </span>
                  </td>
                  <td className={TD} title={contractHits(t)}>
                    {t.t1_hit ? (
                      <span
                        style={{
                          fontSize: 9,
                          fontWeight: 700,
                          padding: '1px 5px',
                          borderRadius: 3,
                          color: 'var(--green)',
                          border: '1px solid rgba(86,211,100,0.45)',
                          background: 'rgba(86,211,100,0.10)',
                        }}
                      >
                        T1✓
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>·</span>
                    )}
                  </td>
                </tr>
                {open && (
                  <tr className="border-b" style={{ borderColor: 'var(--border)' }}>
                    <td colSpan={COLS} className="p-0">
                      {/* Detail panel — TradeRowExpand reuses MgmtTimeline + TradeChart */}
                      <TradeRowExpand trade={t} />
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
          {trades.length === 0 && (
            <tr>
              <td colSpan={COLS} className={`${TD} text-center py-8`} style={{ color: 'var(--text-muted)' }}>
                אין עסקאות בטווח הסינון (ברירת-מחדל: היום). נקה את סינון התאריך למעלה כדי לראות היסטוריה.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
