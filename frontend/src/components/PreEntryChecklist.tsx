'use client';
import { useEffect, useState, useCallback, useRef } from 'react';

const API_URL = 'https://mems26-web.onrender.com';

export interface ChecklistSetup {
  id: string;
  dir: 'long' | 'short';
  entry: number;
  stop: number;
  t1: number;
  t2: number;
  t3: number;
  riskPts: number;
  levelName: string;
  sweepWick: number;
  hasAbsorption: boolean;
  hasExhaustion: boolean;
}

interface Condition {
  id: string;
  label: string;
  detail: string;
  status: 'pass' | 'fail' | 'wait';
}

interface Props {
  setup: ChecklistSetup | null;
  live: any;
  patterns: any[];
  wsCircuitBreaker: { allowed: boolean; reason: string } | null;
  onExecute: (params: {
    direction: 'LONG' | 'SHORT';
    entry_price: number;
    stop: number;
    t1: number; t2: number; t3: number;
    setup_type: string;
  }) => Promise<void>;
  onCancel: () => void;
}

function inKillzone(): { active: boolean; name: string } {
  const etStr = new Date().toLocaleString('en-US', { timeZone: 'America/New_York' });
  const et = new Date(etStr);
  const mins = et.getHours() * 60 + et.getMinutes();
  if (mins >= 120 && mins < 300) return { active: true, name: 'London 02:00-05:00' };
  if (mins >= 570 && mins < 660) return { active: true, name: 'NY Open 09:30-11:00' };
  if (mins >= 810 && mins < 960) return { active: true, name: 'NY Close 13:30-16:00' };
  return { active: false, name: '' };
}

const COL = { pass: '#22c55e', fail: '#ef4444', wait: '#f59e0b' } as const;
const statusIcon = (s: Condition['status']) =>
  s === 'pass' ? '✅' : s === 'fail' ? '❌' : '⏳';

export default function PreEntryChecklist({ setup, live, patterns, wsCircuitBreaker, onExecute, onCancel }: Props) {
  const safePatterns = Array.isArray(patterns) ? patterns : [];
  const [conditions, setConditions] = useState<Condition[]>([]);
  const [healthScore, setHealthScore] = useState<number | null>(null);
  const [cbState, setCbState] = useState<{ allowed: boolean; reason: string } | null>(null);
  const [executing, setExecuting] = useState(false);
  const [lastError, setLastError] = useState('');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchRemote = useCallback(async () => {
    try {
      const [hRes, cbRes] = await Promise.all([
        fetch(`${API_URL}/trade/health`, { method: 'POST', body: '{}', headers: {'content-type':'application/json'} }),
        fetch(`${API_URL}/trade/circuit-breaker`, { cache: 'no-store' }),
      ]);
      if (hRes.ok) { const hd = await hRes.json(); setHealthScore(hd.health_score ?? null); }
      if (cbRes.ok) { const cbd = await cbRes.json(); setCbState({ allowed: cbd.allowed, reason: cbd.reason || '' }); }
    } catch {}
  }, []);

  const effectiveCB = wsCircuitBreaker ?? cbState;

  const evaluate = useCallback(() => {
    if (!setup) return;
    const day = (live as any)?.day || {};
    const fp  = (live as any)?.footprint_bools || {};
    const vol = (live as any)?.volume_context  || {};
    const cvd = live?.cvd || {};
    const kz  = inKillzone();

    const dtype = day.type || '';
    const NO_TRADE = ['ROTATIONAL', 'NON_TREND', 'NEUTRAL'];
    const c0s = dtype ? (NO_TRADE.includes(dtype) ? 'fail' : 'pass') : 'wait';

    const c1s: Condition['status'] = kz.active ? 'pass' : 'wait';

    const hasVolExt = setup.hasAbsorption || setup.hasExhaustion || fp.absorption_detected || fp.exhaustion_detected;
    const relVolOk  = (vol.rel_vol || 1) < 1.0;
    const cvdDiv    = setup.dir === 'long' ? (cvd.change_5bar ?? cvd.d5 ?? 0) > 0 : (cvd.change_5bar ?? cvd.d5 ?? 0) < 0;
    const deltaOpp  = setup.dir === 'long' ? (live?.bar?.delta ?? 0) < 0 : (live?.bar?.delta ?? 0) > 0;
    const volScore  = [hasVolExt, relVolOk || cvdDiv, deltaOpp].filter(Boolean).length;
    const c3s: Condition['status'] = volScore >= 2 ? 'pass' : volScore === 1 ? 'wait' : 'fail';

    const stackedOk = (fp.stacked_imbalance_count ?? 0) >= 2;
    const hasMSS    = safePatterns.some((p: any) => p.pattern === 'mss' || p.pattern === 'liquidity_sweep');
    const c4s: Condition['status'] = stackedOk || hasMSS ? 'pass' : 'wait';

    const hasFVG = safePatterns.some((p: any) => p.pattern === 'fvg' || p.pattern === 'fair_value_gap');
    const fvgPat = safePatterns.find((p: any) => p.pattern === 'fvg' || p.pattern === 'fair_value_gap');
    const c5s: Condition['status'] = hasFVG ? 'pass' : 'wait';

    const c6s: Condition['status'] = healthScore === null ? 'wait' : healthScore >= 70 ? 'pass' : healthScore >= 50 ? 'wait' : 'fail';

    const c7s: Condition['status'] = !effectiveCB ? 'wait' : effectiveCB.allowed ? 'pass' : 'fail';

    const c8s: Condition['status'] = fp.absorption_at_fvg ? 'pass' : 'wait';
    const c9s: Condition['status'] = fp.delta_confirmed_5m ? 'pass' : 'wait';

    setConditions([
      { id: 'daytype',  label: 'Day Type',           detail: dtype || 'ממתין', status: c0s },
      { id: 'killzone', label: 'Killzone',            detail: kz.active ? kz.name : 'מחוץ ל-Killzone', status: c1s },
      { id: 'sweep',    label: 'Sweep / Rejection',  detail: `${setup.dir.toUpperCase()} @ ${setup.levelName} | ${setup.sweepWick.toFixed(2)}pt`, status: 'pass' },
      { id: 'volext',   label: 'Volume Exhaustion',  detail: `${volScore}/3 | abs:${fp.absorption_detected?'✓':'·'} exh:${fp.exhaustion_detected?'✓':'·'}`, status: c3s },
      { id: 'mss',      label: 'MSS + Stacked ≥ 2×', detail: `Stacked: ${fp.stacked_imbalance_count ?? 0}× ${fp.stacked_imbalance_dir ?? ''}`, status: c4s },
      { id: 'fvg',      label: 'FVG תקף',            detail: hasFVG ? `FVG @ ${fvgPat?.entry?.toFixed(2) ?? '?'}` : 'מחפש...', status: c5s },
      { id: 'health',   label: 'Health Score ≥ 70',  detail: healthScore !== null ? `${healthScore}/100` : 'טוען...', status: c6s },
      { id: 'circuit',  label: 'Circuit Breaker',    detail: effectiveCB ? (effectiveCB.allowed ? 'מאושר' : effectiveCB.reason) : 'בודק...', status: c7s },
      { id: 'absfvg',   label: 'Absorption at FVG',  detail: fp.absorption_at_fvg ? 'ספיגה ב-FVG' : 'ממתין...', status: c8s },
      { id: 'delta5m',  label: 'Delta 5m confirmed',  detail: fp.delta_confirmed_5m ? 'דלתא מאשרת' : 'ממתין...', status: c9s },
    ]);
  }, [setup, live, patterns, healthScore, effectiveCB]);

  useEffect(() => {
    if (!setup) return;
    fetchRemote();
    evaluate();
    intervalRef.current = setInterval(evaluate, 2000);
    const hi = setInterval(fetchRemote, 10000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); clearInterval(hi); };
  }, [setup]);

  useEffect(() => { evaluate(); }, [live, patterns, effectiveCB, healthScore]);

  if (!setup) return null;

  const passCount = conditions.filter(c => c.status === 'pass').length;
  const allPass   = conditions.length === 10 && passCount === 10;

  const handleExecute = async () => {
    if (!allPass || executing) return;
    setExecuting(true); setLastError('');
    try {
      await onExecute({ direction: setup.dir === 'long' ? 'LONG' : 'SHORT',
        entry_price: setup.entry, stop: setup.stop,
        t1: setup.t1, t2: setup.t2, t3: setup.t3, setup_type: 'LIQUIDITY_SWEEP' });
    } catch (e: any) { setLastError(e?.message || 'שגיאה'); }
    finally { setExecuting(false); }
  };

  return (
    <div style={{ position:'fixed', bottom:24, right:24, zIndex:9999,
      background:'#0f172a', border:`1px solid ${allPass ? '#22c55e' : '#1e293b'}`,
      borderRadius:12, padding:'14px 16px', width:320,
      boxShadow: allPass ? '0 0 24px rgba(34,197,94,0.3)' : '0 4px 24px rgba(0,0,0,0.6)',
      fontFamily:'monospace', transition:'border-color 0.3s, box-shadow 0.3s' }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:10 }}>
        <div>
          <span style={{ fontSize:11, fontWeight:800, color:'#94a3b8', letterSpacing:1 }}>PRE-ENTRY CHECKLIST</span>
          <span style={{ marginLeft:8, fontSize:10, fontWeight:700,
            color: passCount===10 ? '#22c55e' : passCount>=5 ? '#f59e0b' : '#ef4444' }}>{passCount}/10</span>
        </div>
        <div style={{ display:'flex', gap:6, alignItems:'center' }}>
          <span style={{ fontSize:10, padding:'2px 6px', borderRadius:4,
            background: setup.dir==='long' ? '#14532d' : '#450a0a',
            color: setup.dir==='long' ? '#22c55e' : '#ef4444', fontWeight:700 }}>
            {setup.dir==='long' ? '▲ LONG' : '▼ SHORT'}
          </span>
          <button onClick={onCancel} style={{ background:'none', border:'none', color:'#475569', fontSize:14, cursor:'pointer' }}>✕</button>
        </div>
      </div>
      <div style={{ fontSize:10, color:'#64748b', marginBottom:10, direction:'ltr' }}>
        E:{setup.entry.toFixed(2)} SL:{setup.stop.toFixed(2)} T1:{setup.t1.toFixed(2)} R:{setup.riskPts.toFixed(2)}pt
      </div>
      <div style={{ display:'flex', flexDirection:'column', gap:5 }}>
        {conditions.map(c => (
          <div key={c.id} style={{ display:'flex', alignItems:'center', gap:8, padding:'5px 8px', borderRadius:6,
            background: c.status==='pass' ? 'rgba(34,197,94,0.08)' : c.status==='fail' ? 'rgba(239,68,68,0.08)' : 'rgba(245,158,11,0.05)' }}>
            <span style={{ fontSize:13, width:18, textAlign:'center', flexShrink:0 }}>{statusIcon(c.status)}</span>
            <div style={{ flex:1, minWidth:0 }}>
              <div style={{ fontSize:10, fontWeight:700, color:COL[c.status] }}>{c.label}</div>
              <div style={{ fontSize:9, color:'#64748b', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{c.detail}</div>
            </div>
          </div>
        ))}
      </div>
      {/* ── Info: New High/Low + Returned to Range (not a gate condition) ── */}
      {(() => {
        const of = (live as any)?.order_flow || {};
        const nh = !!of.new_high;
        const nl = !!of.new_low;
        const rtr = !!of.returned_to_range;
        const hasNewHL = nh || nl;
        const label = hasNewHL && rtr ? 'Strong Sweep' : hasNewHL ? 'Sweep Active' : '';
        const labelCol = hasNewHL && rtr ? '#22c55e' : hasNewHL ? '#f59e0b' : '#475569';
        return (
          <div style={{ marginTop:8, padding:'6px 8px', borderRadius:6, background:'rgba(100,116,139,0.06)', borderTop:'1px solid #1e293b' }}>
            <div style={{ fontSize:9, fontWeight:700, color:'#64748b', marginBottom:4, letterSpacing:0.5 }}>INFO</div>
            <div style={{ display:'flex', gap:12, fontSize:10, color:'#94a3b8' }}>
              <span>New High/Low: {nh ? <span style={{color:'#22c55e'}}>✅ High</span> : nl ? <span style={{color:'#22c55e'}}>✅ Low</span> : <span style={{color:'#475569'}}>❌</span>}</span>
              <span>Returned: {rtr ? <span style={{color:'#22c55e'}}>✅</span> : <span style={{color:'#475569'}}>❌</span>}</span>
            </div>
            {label && <div style={{ fontSize:10, fontWeight:800, color:labelCol, marginTop:3 }}>{label}</div>}
          </div>
        );
      })()}
      <div style={{ height:3, background:'#1e293b', borderRadius:2, margin:'10px 0 8px' }}>
        <div style={{ height:'100%', borderRadius:2, width:`${(passCount/10)*100}%`,
          background: allPass ? '#22c55e' : passCount>=5 ? '#f59e0b' : '#ef4444',
          transition:'width 0.4s, background 0.4s' }} />
      </div>
      {lastError && <div style={{ fontSize:10, color:'#ef4444', marginBottom:6, textAlign:'center' }}>⚠ {lastError}</div>}
      <button onClick={handleExecute} disabled={!allPass || executing} style={{
        width:'100%', padding:'10px 0', border:'none', borderRadius:8,
        fontSize:13, fontWeight:900, cursor: allPass ? 'pointer' : 'not-allowed',
        background: allPass ? (executing ? '#15803d' : '#22c55e') : '#1e293b',
        color: allPass ? '#0a0e1a' : '#334155',
        boxShadow: allPass ? '0 0 16px rgba(34,197,94,0.4)' : 'none',
        transition:'all 0.3s' }}>
        {executing ? '⏳ שולח...' : allPass ? '🚀 EXECUTE — 3 חוזים' : `⏳ ממתין ${10-passCount} תנאים`}
      </button>
    </div>
  );
}
