'use client';
import { useEffect, useState } from 'react';
import { useTradeStore } from '../../stores/tradeStore';
import { fetchTradeById } from '../../lib/api';
import { SYSTEM_COLORS, SYSTEM_NAMES, SYSTEM_BORDER_STYLE } from '../../types';
import type { SystemId, Trade, TradeMode } from '../../types';
import { contractHits, excursionLine, pnlCell, tradePathLine } from './tradeRowFormat';
import { fmtTimeETIL } from '../../lib/tradeTime';

interface MgmtLogRow {
  ts: string;
  action: string;
  value?: Record<string, unknown> | null;
}

interface TradeFireInsight {
  headline?: string;
  firing_system?: number;
  firing_name?: string;
  direction?: string;
  trigger?: string;
  pattern_id?: string;
  classification?: string;
  confidence?: number | null;
  day_type?: string;
  blocked_by?: string | null;
}

interface SystemRecognition {
  id: number;
  name: string;
  role: string;
  is_firing: boolean;
  agree: boolean | null;
  lines: string[];
}

interface LifecycleEvent {
  event: string;
  label: string;
  detail?: string | null;
}

interface TradeInsight {
  fire?: TradeFireInsight;
  recognition?: SystemRecognition[];
  lifecycle?: LifecycleEvent[];
}

function agreeLabel(agree: boolean | null | undefined): { text: string; color: string } {
  if (agree === true) return { text: 'agrees', color: 'var(--green)' };
  if (agree === false) return { text: 'against', color: 'var(--red)' };
  return { text: 'neutral', color: 'var(--text-muted)' };
}

export function TradeDetailsModal() {
  const { trades, selectedTradeId, setSelectedTradeId } = useTradeStore();
  const trade = trades.find((t) => t.id === selectedTradeId);
  const [detail, setDetail] = useState<Trade | null>(null);
  const [insight, setInsight] = useState<TradeInsight | null>(null);
  const [logs, setLogs] = useState<MgmtLogRow[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedTradeId == null) {
      setDetail(null);
      setInsight(null);
      setLogs([]);
      return;
    }
    setLoading(true);
    fetchTradeById(selectedTradeId)
      .then((res) => {
        if (res?.trade) setDetail(res.trade as unknown as Trade);
        setInsight((res?.insight as unknown as TradeInsight) ?? null);
        setLogs(Array.isArray(res?.management_log) ? (res.management_log as unknown as MgmtLogRow[]) : []);
      })
      .catch(() => {
        setDetail(null);
        setInsight(null);
        setLogs([]);
      })
      .finally(() => setLoading(false));
  }, [selectedTradeId]);

  if (!trade) return null;

  const t = detail ?? trade;
  const fire = insight?.fire;
  const color = SYSTEM_COLORS[(t.system as SystemId) || 1];
  const borderStyle = SYSTEM_BORDER_STYLE[(t.mode as TradeMode) || 'SHADOW'];

  return (
    <>
      <div className="fixed inset-0 z-40" style={{ background: 'rgba(0,0,0,0.6)' }} onClick={() => setSelectedTradeId(null)} />
      <div
        className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-[640px] max-h-[92vh] overflow-y-auto rounded-lg"
        style={{ background: 'var(--bg-secondary)', border: `2px ${borderStyle} ${color}` }}
      >
        <div className="flex items-center justify-between p-4 border-b sticky top-0 z-10" style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ background: color }} />
            <span className="font-medium text-sm" style={{ color }}>
              Trade #{t.id}
            </span>
            {t.pnl_usd != null && (() => {
              const p = pnlCell(t);
              const pc =
                t.pnl_usd > 0 ? 'var(--green)' : t.pnl_usd < 0 ? 'var(--red)' : 'var(--text-secondary)';
              return (
                <span className="ml-3 font-mono text-sm font-bold" style={{ color: pc }}>
                  {p.value}
                  <span
                    className="ml-1 text-[10px] font-normal"
                    style={{ color: t.pnl_mode === 'partial' ? '#eab308' : 'var(--text-muted)' }}
                  >
                    ({p.sub})
                  </span>
                </span>
              );
            })()}
          </div>
          <button type="button" onClick={() => setSelectedTradeId(null)} className="text-lg hover:opacity-70" style={{ color: 'var(--text-secondary)' }}>
            &times;
          </button>
        </div>

        <div className="p-4 space-y-4 text-xs font-mono">
          {loading && <p style={{ color: 'var(--text-muted)' }}>Loading trade insight…</p>}

          {/* What fired */}
          <section>
            <h3 className="text-[10px] uppercase tracking-wide mb-2" style={{ color: 'var(--text-muted)' }}>
              What fired (ירי)
            </h3>
            <div className="p-3 rounded text-sm leading-relaxed" style={{ background: 'var(--bg-primary)', color }}>
              {fire?.headline ?? `S${t.system} ${SYSTEM_NAMES[(t.system as SystemId) || 1]} · ${t.direction}`}
            </div>
            <div className="grid grid-cols-2 gap-2 mt-2">
              <Mini label="Trigger" value={fire?.trigger ?? t.trigger ?? '—'} />
              <Mini label="Pattern" value={fire?.pattern_id ?? t.pattern_id ?? '—'} />
              <Mini label="Class" value={fire?.classification ?? t.classification ?? '—'} />
              <Mini
                label="Confidence"
                value={fire?.confidence != null ? `${(Number(fire.confidence) * (fire.confidence <= 1 ? 100 : 1)).toFixed(0)}%` : '—'}
              />
              <Mini label="Day type" value={fire?.day_type ?? t.day_type ?? '—'} />
              <Mini label="Blocked" value={fire?.blocked_by ?? '—'} />
            </div>
          </section>

          {/* What each system recognized */}
          <section>
            <h3 className="text-[10px] uppercase tracking-wide mb-2" style={{ color: 'var(--text-muted)' }}>
              Recognition at entry (מה כל מערכת זיהתה)
            </h3>
            <div className="space-y-2">
              {(insight?.recognition ?? []).map((sys) => {
                const ag = agreeLabel(sys.agree);
                const sc = SYSTEM_COLORS[sys.id as SystemId] || 'var(--text-secondary)';
                return (
                  <div
                    key={sys.id}
                    className="p-2 rounded border"
                    style={{
                      borderColor: sys.is_firing ? sc : 'var(--border)',
                      background: sys.is_firing ? `${sc}14` : 'var(--bg-primary)',
                    }}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold" style={{ color: sc }}>
                        S{sys.id} {sys.name}
                        {sys.is_firing ? ' · FIRE' : ''}
                      </span>
                      <span className="text-[10px] px-1 rounded" style={{ color: ag.color, background: 'rgba(255,255,255,0.05)' }}>
                        {ag.text}
                      </span>
                      <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{sys.role}</span>
                    </div>
                    <ul className="list-disc pl-4 space-y-0.5" style={{ color: 'var(--text-secondary)' }}>
                      {sys.lines.map((line, i) => (
                        <li key={i}>{line}</li>
                      ))}
                    </ul>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Lifecycle */}
          {(insight?.lifecycle?.length ?? 0) > 0 && (
            <section>
              <h3 className="text-[10px] uppercase tracking-wide mb-2" style={{ color: 'var(--text-muted)' }}>
                Timeline (מה קרה אחר כך)
              </h3>
              <ul className="space-y-1">
                {insight!.lifecycle!.map((ev, i) => (
                  <li key={i} className="flex gap-2" style={{ color: 'var(--text-secondary)' }}>
                    <span style={{ color: 'var(--text-muted)' }}>{i + 1}.</span>
                    <span>
                      <b style={{ color: 'var(--text-primary)' }}>{ev.label}</b>
                      {ev.detail ? ` — ${ev.detail}` : ''}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {t.contracts_pnl && t.contracts_pnl.length > 0 && (
            <section>
              <h3 className="text-[10px] uppercase tracking-wide mb-2" style={{ color: 'var(--text-muted)' }}>
                P&L per contract (C1/C2/C3)
              </h3>
              <div className="grid grid-cols-3 gap-2">
                {t.contracts_pnl.map((c) => (
                  <div key={c.id} className="p-2 rounded text-center" style={{ background: 'var(--bg-primary)' }}>
                    <div style={{ color: 'var(--text-muted)' }}>{c.id}</div>
                    <div
                      className="font-semibold"
                      style={{ color: c.pnl_usd > 0 ? 'var(--green)' : c.pnl_usd < 0 ? 'var(--red)' : 'var(--text-secondary)' }}
                    >
                      ${c.pnl_usd.toFixed(2)}
                    </div>
                    <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                      {c.status}{c.pnl_r != null ? ` ${c.pnl_r}R` : ''}
                    </div>
                  </div>
                ))}
              </div>
              {t.pnl_mode === 'partial' && (
                <p className="mt-1" style={{ color: '#eab308' }}>
                  Partial — sum is realized hits only; C3 open not included until close.
                </p>
              )}
            </section>
          )}

          {excursionLine(t) && (
            <section>
              <h3 className="text-[10px] uppercase tracking-wide mb-2" style={{ color: 'var(--text-muted)' }}>
                Price range (5m bars)
              </h3>
              <div className="p-2 rounded text-xs" style={{ background: 'var(--bg-primary)', color: 'var(--text-secondary)' }}>
                {excursionLine(t)}
              </div>
              <div className="grid grid-cols-2 gap-2 mt-2">
                <Mini label="High" value={t.price_high != null ? String(t.price_high) : '\u2014'} />
                <Mini label="Low" value={t.price_low != null ? String(t.price_low) : '\u2014'} />
                <Mini label="MFE" value={t.mfe_pts != null ? `${t.mfe_pts.toFixed(2)} pt` : '\u2014'} />
                <Mini label="MAE" value={t.mae_pts != null ? `${t.mae_pts.toFixed(2)} pt` : '\u2014'} />
                <Mini
                  label="Closest to T1"
                  value={
                    t.t1_reached || t.t1_closest_pts === 0
                      ? '0 (hit)'
                      : t.t1_closest_pts != null
                        ? `${t.t1_closest_pts.toFixed(2)} pt`
                        : '\u2014'
                  }
                />
                <Mini
                  label="At MFE peak → T1"
                  value={t.t1_at_mfe_pts != null ? `${t.t1_at_mfe_pts.toFixed(2)} pt` : '\u2014'}
                />
              </div>
              {(t.bars_count ?? 0) > 0 && (
                <p className="mt-1 text-[10px]" style={{ color: 'var(--text-muted)' }}>
                  {t.bars_count} five-minute bars in trade window (not tick precision).
                </p>
              )}
            </section>
          )}

          {/* Execution path */}
          <section>
            <h3 className="text-[10px] uppercase tracking-wide mb-2" style={{ color: 'var(--text-muted)' }}>
              Execution
            </h3>
            <div className="p-2 rounded text-xs" style={{ background: 'var(--bg-primary)' }}>
              {tradePathLine(t)}
            </div>
            <p className="mt-1" style={{ color: 'var(--text-muted)' }}>{contractHits(t)}</p>
            {t.stop_issue === 'T1_NO_BE' && (
              <p className="mt-1" style={{ color: '#eab308' }}>⚠ T1 hit without breakeven stop (historical)</p>
            )}
          </section>

          <section>
            <h3 className="text-[10px] uppercase mb-1" style={{ color: 'var(--text-muted)' }}>
              Trade Timeline {logs.length === 0 && <span style={{ color: 'var(--text-muted)' }}>(awaiting RTH data)</span>}
            </h3>
            <div className="space-y-1 max-h-48 overflow-y-auto" style={{ fontSize: 11, borderLeft: '2px solid var(--border)', paddingLeft: 8 }}>
              {/* Entry */}
              <div style={{ color: 'var(--text-secondary)' }}>
                <span style={{ color: '#56d364', fontWeight: 600 }}>ENTRY</span>{' '}
                <span style={{ color: 'var(--text-muted)' }}>{t.entry_ts ? fmtTimeETIL(t.entry_ts) : ''}</span>{' '}
                @ {t.entry_price?.toFixed(2)}
              </div>
              {/* Management log entries */}
              {logs.map((l, i) => {
                const val = typeof l.value === 'object' && l.value ? l.value as Record<string, unknown> : {};
                const actionColors: Record<string, string> = {
                  STOP_MOVE: '#d97706', SMART_BE: '#3b82f6', T1_HIT: '#56d364',
                  T2_HIT: '#56d364', T3_HIT: '#56d364', STOP_HIT: '#f85149',
                };
                const color = actionColors[l.action] || 'var(--text-secondary)';
                const detail = l.action === 'STOP_MOVE' || l.action === 'SMART_BE'
                  ? ` ${Number(val.from ?? 0).toFixed(2)} → ${Number(val.to ?? 0).toFixed(2)}${val.reason ? ` (${val.reason})` : ''}`
                  : '';
                return (
                  <div key={i} style={{ color: 'var(--text-secondary)' }}>
                    <span style={{ color, fontWeight: 600 }}>{l.action}</span>{' '}
                    <span style={{ color: 'var(--text-muted)' }}>{l.ts ? fmtTimeETIL(l.ts) : ''}</span>
                    {detail && <span>{detail}</span>}
                  </div>
                );
              })}
              {/* Exit */}
              {t.exit_ts && (
                <div style={{ color: 'var(--text-secondary)' }}>
                  <span style={{ color: '#f85149', fontWeight: 600 }}>EXIT</span>{' '}
                  <span style={{ color: 'var(--text-muted)' }}>{fmtTimeETIL(t.exit_ts)}</span>{' '}
                  @ {t.exit_price?.toFixed(2)} ({t.exit_reason})
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-[10px] block" style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span className="text-xs" style={{ color: 'var(--text-primary)' }}>{value}</span>
    </div>
  );
}
