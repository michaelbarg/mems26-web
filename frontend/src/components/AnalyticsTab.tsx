'use client';
import { useEffect, useState, useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
  LineChart, Line,
} from 'recharts';

const API_URL = 'https://mems26-web.onrender.com';
const G = '#22c55e', R = '#ef5350', Y = '#f59e0b', B = '#3b82f6';

// ── Types ────────────────────────────────────────────────────────────────

interface DailyReport {
  date: string;
  trade_count: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_pnl_pts: number;
  total_pnl_usd: number;
  avg_mae_pts: number;
  avg_mfe_pts: number;
  avg_risk_pts: number;
  avg_duration_min: number;
  killzone_breakdown: Record<string, { count: number; wins: number; pnl_pts: number }>;
  setup_type_breakdown: Record<string, { count: number; wins: number; pnl_pts: number }>;
  pillar_attribution: Record<string, { count: number; wins: number; wr: number }>;
  observations: string[];
  trades: any[];
}

interface WeeklyReport {
  week_start: string;
  week_end: string;
  trade_count: number;
  wins: number;
  win_rate: number;
  total_pnl_pts: number;
  total_pnl_usd: number;
  pillar_correlation: Record<string, { count: number; wins: number; wr: number }>;
  daily_breakdown: Record<string, { count: number; wins: number; pnl_pts: number }>;
  threshold_recommendations: string[];
  observations: string[];
}

interface PatternReport {
  trade_count: number;
  quality_matrix: { setup_type: string; killzone: string; count: number; wins: number; wr: number; avg_pnl_pts: number; avg_mae: number; avg_mfe: number }[];
  mae_mfe_dist: { mae: Record<string, number>; mfe: Record<string, number> };
  exit_efficiency: { avg_pct: number; distribution: number[] };
  exit_type_breakdown: Record<string, { count: number; avg_pnl: number; total_pnl: number }>;
  observations: string[];
}

// ── Helpers ──────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color: string }) {
  return (
    <div style={{ background: '#0a0e1a', border: '1px solid #1e2738', borderRadius: 6, padding: '8px 10px', textAlign: 'center', flex: 1, minWidth: 80 }}>
      <div style={{ fontSize: 10, color: '#4a5568', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 800, color, fontFamily: 'monospace' }}>{value}</div>
      {sub && <div style={{ fontSize: 10, color: '#4a5568', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 11, color: '#4a5568', letterSpacing: 1.5, fontWeight: 700, marginBottom: 6 }}>{title}</div>
      {children}
    </div>
  );
}

// ── Daily Sub-Tab ────────────────────────────────────────────────────────

function DailyView() {
  const [data, setData] = useState<DailyReport | null>(null);
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [loading, setLoading] = useState(false);

  const fetch_ = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/analytics/daily?date=${date}`);
      setData(await res.json());
    } catch {} finally { setLoading(false); }
  }, [date]);

  useEffect(() => { fetch_(); }, [fetch_]);

  if (loading) return <div style={{ padding: 16, textAlign: 'center', color: '#4a5568' }}>טוען...</div>;
  if (!data) return null;

  const kzData = Object.entries(data.killzone_breakdown).map(([k, v]) => ({ name: k, trades: v.count, wins: v.wins, pnl: v.pnl_pts }));
  const pillarData = Object.entries(data.pillar_attribution).map(([k, v]) => ({ name: `${k} pillars`, ...v }));
  const COLORS = [G, B, Y, R, '#a855f7', '#06b6d4'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {/* Date picker */}
      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
        <input type="date" value={date} onChange={e => setDate(e.target.value)}
          style={{ background: '#1e2738', border: '1px solid #2d3a4a', borderRadius: 4, padding: '4px 8px', color: '#e2e8f0', fontFamily: 'inherit', fontSize: 11 }} />
        <span style={{ fontSize: 11, color: '#4a5568' }}>{data.trade_count} עסקאות</span>
      </div>

      {/* KPIs */}
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
        <StatCard label="עסקאות" value={`${data.trade_count}`} color="#e2e8f0" />
        <StatCard label="WR" value={`${data.win_rate}%`} color={data.win_rate >= 50 ? G : R} />
        <StatCard label="P&L" value={`${data.total_pnl_pts >= 0 ? '+' : ''}${data.total_pnl_pts}pt`} color={data.total_pnl_pts >= 0 ? G : R} sub={`$${data.total_pnl_usd}`} />
        <StatCard label="MAE" value={`${data.avg_mae_pts}pt`} color={R} />
        <StatCard label="MFE" value={`${data.avg_mfe_pts}pt`} color={G} />
      </div>

      {/* Killzone chart */}
      {kzData.length > 0 && (
        <Section title="KILLZONE BREAKDOWN">
          <div style={{ height: 120 }}>
            <ResponsiveContainer>
              <BarChart data={kzData} margin={{ top: 4, right: 4, bottom: 4, left: 4 }}>
                <XAxis dataKey="name" tick={{ fill: '#4a5568', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis hide />
                <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #1e2738', borderRadius: 6, fontSize: 11 }} />
                <Bar dataKey="wins" fill={G} radius={[3, 3, 0, 0]} name="Wins" />
                <Bar dataKey="trades" fill="#1e2738" radius={[3, 3, 0, 0]} name="Total" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Section>
      )}

      {/* Pillar attribution */}
      {pillarData.length > 0 && (
        <Section title="PILLAR ATTRIBUTION">
          <div style={{ display: 'flex', gap: 4 }}>
            {pillarData.map((p, i) => (
              <div key={p.name} style={{ flex: 1, background: '#0a0e1a', border: '1px solid #1e2738', borderRadius: 4, padding: '6px 4px', textAlign: 'center' }}>
                <div style={{ fontSize: 10, color: '#4a5568' }}>{p.name}</div>
                <div style={{ fontSize: 14, fontWeight: 800, color: COLORS[i] || '#e2e8f0' }}>{p.wr}%</div>
                <div style={{ fontSize: 10, color: '#4a5568' }}>{p.count} trades</div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Observations */}
      {data.observations.length > 0 && (
        <Section title="OBSERVATIONS">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {data.observations.map((o, i) => (
              <div key={i} style={{ fontSize: 11, color: '#94a3b8', padding: '4px 8px', background: '#0a0e1a', borderRadius: 4, border: '1px solid #1e2738' }}>{o}</div>
            ))}
          </div>
        </Section>
      )}

      {/* Trade list */}
      {data.trades.length > 0 && (
        <Section title="TRADES">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {data.trades.map((t: any) => (
              <div key={t.id} style={{ display: 'flex', gap: 6, alignItems: 'center', padding: '4px 6px', background: '#0a0e1a', borderRadius: 3, fontSize: 10, fontFamily: 'monospace' }}>
                <span style={{ color: t.direction === 'LONG' ? G : R, fontWeight: 700, width: 40 }}>{t.direction === 'LONG' ? '▲ L' : '▼ S'}</span>
                <span style={{ color: '#94a3b8', flex: 1 }}>E:{t.entry_price?.toFixed(1)} S:{t.stop?.toFixed(1)}</span>
                <span style={{ color: (t.pnl_pts || 0) >= 0 ? G : R, fontWeight: 700 }}>{(t.pnl_pts || 0) >= 0 ? '+' : ''}{(t.pnl_pts || 0).toFixed(1)}pt</span>
                <span style={{ color: '#4a5568' }}>{t.close_reason || '—'}</span>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}

// ── Weekly Sub-Tab ───────────────────────────────────────────────────────

function WeeklyView() {
  const [data, setData] = useState<WeeklyReport | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/analytics/weekly`)
      .then(r => r.json()).then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: 16, textAlign: 'center', color: '#4a5568' }}>טוען...</div>;
  if (!data || data.trade_count === 0) return <div style={{ padding: 16, textAlign: 'center', color: '#4a5568' }}>אין נתונים השבוע</div>;

  const dailyData = Object.entries(data.daily_breakdown).map(([d, v]) => ({
    name: d.slice(5), // MM-DD
    trades: v.count,
    wins: v.wins,
    pnl: Math.round(v.pnl_pts * 10) / 10,
  })).sort((a, b) => a.name.localeCompare(b.name));

  const pillarData = Object.entries(data.pillar_correlation).map(([k, v]) => ({
    name: `${k}P`, count: v.count, wr: v.wr,
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ fontSize: 11, color: '#4a5568' }}>{data.week_start} — {data.week_end}</div>

      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
        <StatCard label="עסקאות" value={`${data.trade_count}`} color="#e2e8f0" />
        <StatCard label="WR" value={`${data.win_rate}%`} color={data.win_rate >= 50 ? G : R} />
        <StatCard label="P&L" value={`${data.total_pnl_pts >= 0 ? '+' : ''}${data.total_pnl_pts}pt`} color={data.total_pnl_pts >= 0 ? G : R} />
      </div>

      {/* Daily P&L chart */}
      {dailyData.length > 0 && (
        <Section title="DAILY P&L">
          <div style={{ height: 120 }}>
            <ResponsiveContainer>
              <BarChart data={dailyData} margin={{ top: 4, right: 4, bottom: 4, left: 4 }}>
                <XAxis dataKey="name" tick={{ fill: '#4a5568', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis hide />
                <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #1e2738', borderRadius: 6, fontSize: 11 }} />
                <Bar dataKey="pnl" fill={G} radius={[3, 3, 0, 0]} name="P&L (pts)">
                  {dailyData.map((d, i) => <Cell key={i} fill={d.pnl >= 0 ? G : R} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Section>
      )}

      {/* Pillar correlation */}
      {pillarData.length > 0 && (
        <Section title="PILLAR CORRELATION — WR%">
          <div style={{ height: 100 }}>
            <ResponsiveContainer>
              <BarChart data={pillarData} margin={{ top: 4, right: 4, bottom: 4, left: 4 }}>
                <XAxis dataKey="name" tick={{ fill: '#4a5568', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis hide domain={[0, 100]} />
                <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #1e2738', borderRadius: 6, fontSize: 11 }} />
                <Bar dataKey="wr" fill={B} radius={[3, 3, 0, 0]} name="Win Rate %" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Section>
      )}

      {/* Recommendations */}
      {data.threshold_recommendations.length > 0 && (
        <Section title="THRESHOLD RECOMMENDATIONS">
          {data.threshold_recommendations.map((r, i) => (
            <div key={i} style={{ fontSize: 11, color: Y, padding: '4px 8px', background: '#1a150a', borderRadius: 4, border: '1px solid #f59e0b33', marginBottom: 3 }}>{r}</div>
          ))}
        </Section>
      )}

      {data.observations.map((o, i) => (
        <div key={i} style={{ fontSize: 11, color: '#94a3b8', padding: '4px 8px', background: '#0a0e1a', borderRadius: 4 }}>{o}</div>
      ))}
    </div>
  );
}

// ── Patterns Sub-Tab ────────────────────────────────────────────────────

function PatternsView() {
  const [data, setData] = useState<PatternReport | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/analytics/patterns`)
      .then(r => r.json()).then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: 16, textAlign: 'center', color: '#4a5568' }}>טוען...</div>;
  if (!data || data.trade_count === 0) return <div style={{ padding: 16, textAlign: 'center', color: '#4a5568' }}>אין מספיק נתונים לניתוח</div>;

  const maeData = data.mae_mfe_dist?.mae ? Object.entries(data.mae_mfe_dist.mae).map(([k, v]) => ({ name: k, count: v })) : [];
  const mfeData = data.mae_mfe_dist?.mfe ? Object.entries(data.mae_mfe_dist.mfe).map(([k, v]) => ({ name: k, count: v })) : [];
  const exitData = data.exit_type_breakdown ? Object.entries(data.exit_type_breakdown).map(([k, v]) => ({ name: k, count: v.count, pnl: v.avg_pnl })) : [];
  const COLORS = [G, B, Y, R, '#a855f7', '#06b6d4'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', gap: 4 }}>
        <StatCard label="Total" value={`${data.trade_count}`} color="#e2e8f0" />
        <StatCard label="Exit Eff." value={`${data.exit_efficiency?.avg_pct || 0}%`} color={B} />
      </div>

      {/* Quality Matrix */}
      {data.quality_matrix.length > 0 && (
        <Section title="SETUP QUALITY MATRIX">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <div style={{ display: 'flex', gap: 4, fontSize: 9, color: '#4a5568', padding: '0 4px' }}>
              <span style={{ flex: 2 }}>Setup</span>
              <span style={{ flex: 1 }}>KZ</span>
              <span style={{ width: 28, textAlign: 'center' }}>N</span>
              <span style={{ width: 36, textAlign: 'center' }}>WR%</span>
              <span style={{ width: 40, textAlign: 'right' }}>P&L</span>
            </div>
            {data.quality_matrix.slice(0, 8).map((q, i) => (
              <div key={i} style={{ display: 'flex', gap: 4, fontSize: 10, padding: '3px 4px', background: '#0a0e1a', borderRadius: 3, alignItems: 'center', fontFamily: 'monospace' }}>
                <span style={{ flex: 2, color: '#94a3b8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{q.setup_type}</span>
                <span style={{ flex: 1, color: '#4a5568' }}>{q.killzone}</span>
                <span style={{ width: 28, textAlign: 'center', color: '#94a3b8' }}>{q.count}</span>
                <span style={{ width: 36, textAlign: 'center', color: q.wr >= 50 ? G : R, fontWeight: 700 }}>{q.wr}%</span>
                <span style={{ width: 40, textAlign: 'right', color: q.avg_pnl_pts >= 0 ? G : R }}>{q.avg_pnl_pts >= 0 ? '+' : ''}{q.avg_pnl_pts}</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* MAE/MFE distribution */}
      {(maeData.length > 0 || mfeData.length > 0) && (
        <Section title="MAE / MFE DISTRIBUTION (pts)">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
            <div>
              <div style={{ fontSize: 9, color: R, marginBottom: 2, textAlign: 'center' }}>MAE (worst drawdown)</div>
              <div style={{ height: 80 }}>
                <ResponsiveContainer>
                  <BarChart data={maeData} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                    <XAxis dataKey="name" tick={{ fill: '#4a5568', fontSize: 8 }} axisLine={false} tickLine={false} />
                    <Bar dataKey="count" fill={R} radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div>
              <div style={{ fontSize: 9, color: G, marginBottom: 2, textAlign: 'center' }}>MFE (best run)</div>
              <div style={{ height: 80 }}>
                <ResponsiveContainer>
                  <BarChart data={mfeData} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                    <XAxis dataKey="name" tick={{ fill: '#4a5568', fontSize: 8 }} axisLine={false} tickLine={false} />
                    <Bar dataKey="count" fill={G} radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </Section>
      )}

      {/* Exit type pie */}
      {exitData.length > 0 && (
        <Section title="EXIT TYPE BREAKDOWN">
          <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
            {exitData.map((e, i) => (
              <div key={e.name} style={{ background: '#0a0e1a', border: '1px solid #1e2738', borderRadius: 4, padding: '4px 8px', textAlign: 'center' }}>
                <div style={{ fontSize: 10, color: COLORS[i % COLORS.length], fontWeight: 700 }}>{e.name}</div>
                <div style={{ fontSize: 12, color: '#e2e8f0', fontWeight: 800 }}>{e.count}</div>
                <div style={{ fontSize: 9, color: e.pnl >= 0 ? G : R }}>{e.pnl >= 0 ? '+' : ''}{e.pnl}pt</div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Observations */}
      {data.observations.map((o, i) => (
        <div key={i} style={{ fontSize: 11, color: '#94a3b8', padding: '4px 8px', background: '#0a0e1a', borderRadius: 4, marginTop: 2 }}>{o}</div>
      ))}
    </div>
  );
}

// ── Scoring Sub-Tab (Framework Only) ────────────────────────────────────

function ScoringView() {
  return (
    <div style={{ padding: 16, textAlign: 'center' }}>
      <div style={{ fontSize: 14, color: '#f6c90e', fontWeight: 700, marginBottom: 8 }}>SCORING MODEL</div>
      <div style={{ fontSize: 12, color: '#4a5568', lineHeight: 1.8 }}>
        Framework ready — weights TBD after E3 provides data.<br />
        Minimum 18 trades needed for statistical significance.<br />
        <br />
        Features tracked per trade:<br />
        day_type · killzone · rel_vol · cvd_trend · vwap_dist<br />
        mtf_alignment · stacked_count · pillars_passed<br />
        sweep_wick_pts · post_news · manual_override<br />
        <br />
        Outcomes tracked:<br />
        WR · MAE · MFE · exit_efficiency · duration
      </div>
    </div>
  );
}

// ── Main AnalyticsTab Component ─────────────────────────────────────────

export default function AnalyticsTab() {
  const [sub, setSub] = useState<'daily' | 'weekly' | 'patterns' | 'scoring'>('daily');

  const subTabs = [
    { id: 'daily' as const, label: 'יומי', icon: '📋' },
    { id: 'weekly' as const, label: 'שבועי', icon: '📊' },
    { id: 'patterns' as const, label: 'תבניות', icon: '🧩' },
    { id: 'scoring' as const, label: 'ניקוד', icon: '🎯' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0, height: '100%' }}>
      {/* Sub-tab bar */}
      <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid #1e2738', flexShrink: 0, marginBottom: 8 }}>
        {subTabs.map(t => (
          <button key={t.id} onClick={() => setSub(t.id)}
            style={{ flex: 1, padding: '4px 2px', border: 'none', cursor: 'pointer', fontFamily: 'inherit',
              background: sub === t.id ? '#1e2738' : 'transparent',
              borderBottom: sub === t.id ? '2px solid #f6c90e' : '2px solid transparent',
              color: sub === t.id ? '#f6c90e' : '#4a5568', fontSize: 10, fontWeight: 700,
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0 }}>
            <span style={{ fontSize: 12 }}>{t.icon}</span>
            <span>{t.label}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {sub === 'daily' && <DailyView />}
        {sub === 'weekly' && <WeeklyView />}
        {sub === 'patterns' && <PatternsView />}
        {sub === 'scoring' && <ScoringView />}
      </div>

      {/* Open full journal */}
      <div style={{ padding: '6px 0', textAlign: 'center', borderTop: '1px solid #1e2738' }}>
        <a href="/journal" target="_blank" rel="noopener noreferrer"
          style={{ fontSize: 11, color: '#f6c90e', textDecoration: 'none', fontWeight: 700 }}>
          Open Full Journal
        </a>
      </div>
    </div>
  );
}
