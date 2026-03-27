'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import LightweightChart from './LightweightChart';

const API_URL = 'https://mems26-web.onrender.com';

// ── Types ─────────────────────────────────────────────────────────────────────
interface Bar { o:number; h:number; l:number; c:number; vol:number; buy:number; sell:number; delta:number; }
interface Signal { direction:'LONG'|'SHORT'|'NO_TRADE'; score:number; confidence:string; entry:number; stop:number; target1:number; target2:number; target3:number; risk_pts:number; rationale:string; tl_color:string; setup?:string; win_rate?:number; t1_win_rate?:number; t2_win_rate?:number; t3_win_rate?:number; wait_reason?:string; }
interface MarketData {
  ts:number; price:number; bar:Bar;
  mtf:{ m3:Bar; m15:Bar; m30:Bar; m60:Bar };
  cvd:{ total:number; d20:number; d5:number; trend:string; buy_vol:number; sell_vol:number; delta:number };
  vwap:{ value:number; distance:number; above:boolean; pullback:boolean };
  session:{ phase:string; min:number; sh:number; sl:number; ibh:number; ibl:number; ib_locked:boolean };
  profile:{ poc:number; vah:number; val:number; tpo_poc:number; in_va:boolean; above_poc:boolean };
  woodi:{ pp:number; r1:number; r2:number; s1:number; s2:number; above_pp:boolean };
  levels:{ prev_high:number; prev_low:number; prev_close:number; daily_open:number; overnight_high:number; overnight_low:number };
  order_flow:{ absorption_bull:boolean; liq_sweep:boolean; liq_sweep_long:boolean; liq_sweep_short:boolean; imbalance_bull:number; imbalance_bear:number };
  reversal:{ ib_high:number; ib_low:number; rev15_type:string; rev15_price:number };
  signal?:Signal;
}
interface Candle { ts:number; o:number; h:number; l:number; c:number; buy:number; sell:number; delta:number; }

// ── Helpers ───────────────────────────────────────────────────────────────────
const G = '#22c55e', Y = '#f59e0b', R = '#ef5350';
const scoreCol = (s:number) => s >= 7 ? G : s >= 5 ? Y : R;

// ── Real-time Setup Scanner ───────────────────────────────────────────────────
function calcSetups(live: MarketData | null) {
  if (!live) return null;
  const cvd  = live.cvd        || {} as any;
  const vwap = live.vwap       || {} as any;
  const prof = live.profile    || {} as any;
  const of2  = live.order_flow || {} as any;
  const sess = live.session    || {} as any;
  const bar  = live.bar        || {} as any;
  const mtf  = live.mtf        || {} as any;
  const wcci = (live as any).woodies_cci     || {};
  const day  = (live as any).day             || {};
  const cp   = (live as any).candle_patterns || {};

  const liqLong   = [
    { label:'LiqSweep', ok:!!of2.liq_sweep_long },
    { label:'Delta +',  ok:(bar.delta||0)>0 },
    { label:'CVD Bull', ok:cvd.trend==='BULLISH' },
    { label:'Vol Buy',  ok:(cvd.buy_vol||0)>(cvd.sell_vol||0) },
    { label:'Engulf ↑', ok:!!cp.bull_engulf },
  ];
  const liqShort  = [
    { label:'Sweep ↓',  ok:!!of2.liq_sweep_short },
    { label:'Delta −',  ok:(bar.delta||0)<0 },
    { label:'CVD Bear', ok:cvd.trend==='BEARISH' },
    { label:'Vol Sell', ok:(cvd.sell_vol||0)>(cvd.buy_vol||0) },
    { label:'Engulf ↓', ok:!!cp.bear_engulf },
  ];
  const vwapLong  = [
    { label:'מעל VWAP', ok:!!vwap.above },
    { label:'Pullback', ok:!!vwap.pullback },
    { label:'CVD Bull', ok:cvd.trend==='BULLISH' },
    { label:'Hook Up',  ok:!!wcci.hook_up||!!wcci.zlr_bull },
    { label:'Hammer',   ok:cp.bar0==='HAMMER'||cp.bar0==='BULL_STRONG' },
  ];
  const vwapShort = [
    { label:'מתחת VWAP',ok:!vwap.above },
    { label:'Dist < 2', ok:(vwap.distance||0)<2&&!vwap.above },
    { label:'CVD Bear', ok:cvd.trend==='BEARISH' },
    { label:'Hook Dn',  ok:!!wcci.hook_down||!!wcci.zlr_bear },
    { label:'Star',     ok:cp.bar0==='SHOOTING_STAR'||cp.bar0==='BEAR_STRONG' },
  ];
  const ibLong    = [
    { label:'IB Lock',  ok:!!sess.ib_locked },
    { label:'Break Up', ok:!!day.ib_breakout_up },
    { label:'Absorb',   ok:!!of2.absorption_bull },
    { label:'CCI14>0',  ok:(wcci.cci14||0)>0 },
    { label:'15m Bull', ok:(mtf?.m15?.delta||0)>0 },
  ];
  const ibShort   = [
    { label:'IB Lock',  ok:!!sess.ib_locked },
    { label:'Break Dn', ok:!!day.ib_breakout_down },
    { label:'CVD Bear', ok:cvd.trend==='BEARISH' },
    { label:'CCI14<0',  ok:(wcci.cci14||0)<0 },
    { label:'15m Bear', ok:(mtf?.m15?.delta||0)<0 },
  ];
  const turboLong = [
    { label:'Turbo ↑',  ok:!!wcci.turbo_bull },
    { label:'BLUE',     ok:wcci.hist_color==='BLUE' },
    { label:'מעל VWAP', ok:!!vwap.above },
    { label:'מעל POC',  ok:!!prof.above_poc },
    { label:'CVD d5+',  ok:(cvd.d5||0)>0 },
  ];
  const turboShort= [
    { label:'Turbo ↓',  ok:!!wcci.turbo_bear },
    { label:'D.RED',    ok:wcci.hist_color==='DARK_RED' },
    { label:'מתחת VWAP',ok:!vwap.above },
    { label:'מתחת POC', ok:!prof.above_poc },
    { label:'CVD d5−',  ok:(cvd.d5||0)<0 },
  ];

  const pct = (c:{ok:boolean}[]) => Math.round(c.filter(x=>x.ok).length/c.length*100);
  const wr  = (base:number, s:number) => Math.round(base*(s/100)*0.55 + base*0.45);

  return [
    { name:'Liq Sweep',    col:'#22c55e', base:72, long:{checks:liqLong,   score:pct(liqLong)},   short:{checks:liqShort,  score:pct(liqShort)} },
    { name:'VWAP Pullback',col:'#f6c90e', base:66, long:{checks:vwapLong,  score:pct(vwapLong)},  short:{checks:vwapShort, score:pct(vwapShort)} },
    { name:'IB Breakout',  col:'#60a5fa', base:62, long:{checks:ibLong,    score:pct(ibLong)},    short:{checks:ibShort,   score:pct(ibShort)} },
    { name:'CCI Turbo',    col:'#a78bfa', base:64, long:{checks:turboLong, score:pct(turboLong)}, short:{checks:turboShort,score:pct(turboShort)} },
  ].map(s=>({...s, long:{...s.long,wr:wr(s.base,s.long.score)}, short:{...s.short,wr:wr(s.base,s.short.score)}}));
}

function SetupScanner({ live }:{ live:MarketData|null }) {
  const setups = calcSetups(live);
  if (!setups) return null;
  return (
    <div style={{ background:'#111827', border:'1px solid #1e2738', borderRadius:8, padding:12 }}>
      <div style={{ fontSize:9, color:'#4a5568', letterSpacing:2, marginBottom:8 }}>סורק סטאפים — זמן אמת</div>
      <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
        {setups.map(s => {
          const best    = s.long.score >= s.short.score ? 'long' : 'short';
          const bScore  = best==='long' ? s.long.score : s.short.score;
          const bWR     = best==='long' ? s.long.wr    : s.short.wr;
          const bChecks = best==='long' ? s.long.checks: s.short.checks;
          const active  = bScore >= 60;
          return (
            <div key={s.name} style={{ border:`1px solid ${active?s.col+'55':'#1e2738'}`, borderRadius:6, padding:'7px 9px', background:active?s.col+'08':'transparent' }}>
              <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:4 }}>
                <div style={{ width:7, height:7, borderRadius:'50%', background:s.col, opacity:active?1:0.3, boxShadow:active?`0 0 5px ${s.col}`:'none' }} />
                <span style={{ fontSize:11, fontWeight:500, color:'#e2e8f0', flex:1 }}>{s.name}</span>
                <span style={{ fontSize:10, color:best==='long'?G:R, fontWeight:700 }}>{best==='long'?'▲ L':'▼ S'}</span>
                <span style={{ fontSize:14, fontWeight:800, color:active?s.col:'#4a5568', fontFamily:'monospace', minWidth:34, textAlign:'right' }}>{bWR}%</span>
              </div>
              <div style={{ height:3, background:'#1e2738', borderRadius:2, marginBottom:5, overflow:'hidden' }}>
                <div style={{ width:`${bScore}%`, height:'100%', background:s.col, borderRadius:2, opacity:active?1:0.4 }} />
              </div>
              <div style={{ display:'flex', flexWrap:'wrap', gap:'2px 6px' }}>
                {bChecks.map(c=>(
                  <span key={c.label} style={{ fontSize:9, color:c.ok?s.col:'#2d3a4a', display:'flex', alignItems:'center', gap:2 }}>
                    <span style={{ width:4, height:4, borderRadius:'50%', background:c.ok?s.col:'#2d3a4a', display:'inline-block', flexShrink:0 }} />
                    {c.label}
                  </span>
                ))}
              </div>
              <div style={{ display:'flex', marginTop:4, fontSize:9 }}>
                <span style={{ color:G, flex:1 }}>L {s.long.score}% <span style={{ color:'#2d3a4a' }}>({s.long.wr}% WR)</span></span>
                <span style={{ color:R, textAlign:'right' }}>S {s.short.score}% <span style={{ color:'#2d3a4a' }}>({s.short.wr}% WR)</span></span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Live LONG/SHORT probability ───────────────────────────────────────────────
function calcProbability(live: MarketData | null): { long: number; short: number } {
  if (!live) return { long: 50, short: 50 };

  const cvd    = live.cvd    || {} as any;
  const vwap   = live.vwap   || {} as any;
  const prof   = live.profile|| {} as any;
  const woodi  = live.woodi  || {} as any;
  const of2    = live.order_flow || {} as any;
  const bar    = live.bar    || {} as any;
  const sess   = live.session|| {} as any;

  let longScore  = 0;
  let shortScore = 0;

  // CVD Trend (משקל גבוה)
  if (cvd.trend === 'BULLISH')  longScore  += 20;
  if (cvd.trend === 'BEARISH')  shortScore += 20;
  if ((cvd.d20 || 0) > 200)    longScore  += 10;
  if ((cvd.d20 || 0) < -200)   shortScore += 10;
  if ((cvd.d5  || 0) > 50)     longScore  += 8;
  if ((cvd.d5  || 0) < -50)    shortScore += 8;
  if ((bar.delta || 0) > 100)   longScore  += 6;
  if ((bar.delta || 0) < -100)  shortScore += 6;

  // VWAP
  if (vwap.above)             longScore  += 12;
  else                        shortScore += 12;
  if (vwap.pullback)          longScore  += 8;

  // Profile
  if (prof.above_poc)         longScore  += 8;
  else                        shortScore += 8;
  if (prof.in_va) { longScore += 3; shortScore += 3; }

  // Woodi PP
  if (woodi.above_pp)         longScore  += 6;
  else                        shortScore += 6;

  // Order Flow
  if (of2.absorption_bull)    longScore  += 10;
  if (of2.liq_sweep || of2.liq_sweep_long) longScore += 8;
  if (of2.liq_sweep_short)    shortScore += 8;
  if ((of2.imbalance_bull||0) > 0) longScore  += 5;
  if ((of2.imbalance_bear||0) > 0) shortScore += 5;

  // Session
  if (sess.phase === 'RTH' || sess.phase === 'AM_SESSION') {
    longScore += 2; shortScore += 2;
  }

  const total = longScore + shortScore || 1;
  const longPct  = Math.round((longScore  / total) * 100);
  const shortPct = 100 - longPct;
  return { long: longPct, short: shortPct };
}

// ── Traffic Light — רמזור קלאסי אנכי ─────────────────────────────────────────
function TrafficLight({ score, live }: { score: number; live: MarketData | null }) {
  const isGreen  = score >= 7;
  const isYellow = score >= 5 && score < 7;
  const isRed    = score < 5;
  const { long, short } = calcProbability(live);
  const bias = long > short ? 'LONG' : short > long ? 'SHORT' : 'NEUTRAL';
  const biasCol = bias === 'LONG' ? G : bias === 'SHORT' ? R : Y;

  const light = (on: boolean, color: string) => ({
    width: 28, height: 28, borderRadius: '50%',
    background: on ? color : '#1a1a2e',
    border: `2px solid ${on ? color : '#2d3a4a'}`,
    boxShadow: on ? `0 0 14px ${color}, 0 0 4px ${color}` : 'none',
    transition: 'all .4s',
  });

  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:6, flexShrink:0 }}>
      {/* Traffic light housing */}
      <div style={{ background:'#111827', border:'2px solid #2d3a4a', borderRadius:14, padding:'10px 8px', display:'flex', flexDirection:'column', gap:8, alignItems:'center', width:48 }}>
        <div style={light(isRed,    R)} />
        <div style={light(isYellow, Y)} />
        <div style={light(isGreen,  G)} />
      </div>

      {/* LONG/SHORT probability */}
      <div style={{ width:48, background:'#111827', border:'1px solid #1e2738', borderRadius:8, padding:'6px 4px', display:'flex', flexDirection:'column', gap:4 }}>
        <div style={{ textAlign:'center', fontSize:8, color:'#4a5568', marginBottom:2 }}>סיכוי</div>
        {/* LONG bar */}
        <div>
          <div style={{ display:'flex', justifyContent:'space-between', fontSize:8, marginBottom:1 }}>
            <span style={{ color:G, fontWeight:700 }}>L</span>
            <span style={{ color:G, fontFamily:'monospace', fontWeight:700 }}>{long}%</span>
          </div>
          <div style={{ height:4, background:'#1e2738', borderRadius:2, overflow:'hidden' }}>
            <div style={{ width:`${long}%`, height:'100%', background:G, borderRadius:2, transition:'width .5s' }} />
          </div>
        </div>
        {/* SHORT bar */}
        <div>
          <div style={{ display:'flex', justifyContent:'space-between', fontSize:8, marginBottom:1 }}>
            <span style={{ color:R, fontWeight:700 }}>S</span>
            <span style={{ color:R, fontFamily:'monospace', fontWeight:700 }}>{short}%</span>
          </div>
          <div style={{ height:4, background:'#1e2738', borderRadius:2, overflow:'hidden' }}>
            <div style={{ width:`${short}%`, height:'100%', background:R, borderRadius:2, transition:'width .5s' }} />
          </div>
        </div>
        {/* Bias label */}
        <div style={{ textAlign:'center', fontSize:9, fontWeight:700, color:biasCol, marginTop:2 }}>{bias}</div>
      </div>
    </div>
  );
}

// ── Mini Traffic Light — 3 נקודות קטנות לאינדיקטור ───────────────────────────
function MiniLight({ col }: { col: string }) {
  const isG = col === G;
  const isY = col === Y;
  const isR = col === R;
  const dot = (on: boolean, color: string) => ({
    width: 8, height: 8, borderRadius: '50%',
    background: on ? color : '#1e2738',
    boxShadow: on ? `0 0 5px ${color}` : 'none',
    transition: 'all .3s',
    flexShrink: 0 as const,
  });
  return (
    <div style={{ display:'flex', gap:3, alignItems:'center', flexShrink:0 }}>
      <div style={dot(isR, R)} />
      <div style={dot(isY, Y)} />
      <div style={dot(isG, G)} />
    </div>
  );
}

// ── Zone A: Top Bar ───────────────────────────────────────────────────────────
function TopBar({ live, connected, onAskAI, aiLoading }:{ live:MarketData|null; connected:boolean; onAskAI:()=>void; aiLoading:boolean }) {
  const [time, setTime] = useState('');
  useEffect(() => {
    const t = setInterval(() => {
      setTime(new Date().toLocaleTimeString('en-US', { hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false, timeZone:'America/New_York' }));
    }, 1000);
    return () => clearInterval(t);
  }, []);

  const price = live?.price ?? 0;
  const phase = live?.session?.phase ?? '—';
  const phaseCol = phase === 'RTH' ? G : phase === 'OVERNIGHT' ? Y : '#60a5fa';

  return (
    <div style={{ display:'flex', alignItems:'center', gap:16, padding:'10px 16px', background:'#111827', borderRadius:8, border:'1px solid #1e2738' }}>
      <span style={{ fontSize:16, fontWeight:800, letterSpacing:2, color:'#f0f6fc' }}>MES<span style={{ color:'#f6c90e' }}>26</span></span>
      <span style={{ fontSize:28, fontWeight:800, fontFamily:'monospace', color:'#f0f6fc' }}>{price ? price.toFixed(2) : '—'}</span>
      <span style={{ fontSize:11, padding:'3px 10px', borderRadius:12, fontWeight:700, background:phaseCol+'22', color:phaseCol, border:`1px solid ${phaseCol}44` }}>{phase}</span>

      {/* כפתור AI on-demand */}
      <button onClick={onAskAI} disabled={aiLoading} style={{
        display:'flex', alignItems:'center', gap:6,
        padding:'6px 14px', borderRadius:8, fontSize:12, fontWeight:700,
        background: aiLoading ? '#1e2738' : '#7f77dd22',
        color: aiLoading ? '#4a5568' : '#7f77dd',
        border:`1px solid ${aiLoading ? '#2d3a4a' : '#7f77dd44'}`,
        cursor: aiLoading ? 'not-allowed' : 'pointer',
        fontFamily:'inherit', transition:'all .2s',
      }}>
        {aiLoading ? (
          <>
            <span style={{ display:'inline-block', width:10, height:10, borderRadius:'50%', border:'2px solid #4a5568', borderTopColor:'#7f77dd', animation:'spin 0.8s linear infinite' }} />
            מנתח...
          </>
        ) : (
          <>⚡ שאל AI עכשיו</>
        )}
      </button>

      <div style={{ marginLeft:'auto', display:'flex', alignItems:'center', gap:16 }}>
        <span style={{ fontSize:18, fontWeight:700, fontFamily:'monospace', color:'#f0f6fc' }}>{time}</span>
        <span style={{ fontSize:11, color:'#4a5568' }}>EST</span>
        <div style={{ display:'flex', alignItems:'center', gap:6 }}>
          <div style={{ width:8, height:8, borderRadius:'50%', background:connected?G:R, boxShadow:connected?`0 0 6px ${G}`:'none' }} className={connected?'live-blink':''} />
          <span style={{ fontSize:11, fontWeight:700, color:connected?G:R }}>{connected?'LIVE':'OFFLINE'}</span>
        </div>
      </div>
    </div>
  );
}

// ── Zone B: Main Score + Signal Panel ────────────────────────────────────────
function MainScore({ live, onAccept, onReject, accepted }:{ live:MarketData|null; onAccept:()=>void; onReject:()=>void; accepted:boolean }) {
  const sig   = live?.signal;
  const score = sig?.score ?? 0;
  const col   = scoreCol(score);
  const dir   = sig?.direction ?? 'NO_TRADE';
  const isActive = dir !== 'NO_TRADE' && score >= 5;
  const isGreen  = sig?.tl_color === 'green' || sig?.tl_color === 'green_bright';

  return (
    <div style={{ background: isActive ? '#0d1f1a' : '#111827', border:`1.5px solid ${isActive ? col+'44' : '#1e2738'}`, borderRadius:8, padding:14, minHeight:120 }}>
      <div style={{ display:'flex', alignItems:'center', gap:14 }}>
        <TrafficLight score={score} live={live} />
        <div style={{ width:44, height:44, borderRadius:'50%', background:col+'18', border:`2px solid ${col}44`, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
          <span style={{ fontSize:20, fontWeight:800, color:col, fontFamily:'monospace' }}>{score}</span>
        </div>
        <div style={{ flex:1 }}>
          <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:4 }}>
            <span style={{ fontSize:20, fontWeight:800, color:col }}>{dir === 'NO_TRADE' ? 'המתן' : dir}</span>
            {isActive && <span style={{ fontSize:11, color:'#6b7280' }}>{sig?.confidence}</span>}
            {isActive && sig?.setup && <span style={{ fontSize:10, padding:'2px 8px', borderRadius:10, background:col+'22', color:col }}>{sig.setup}</span>}
          </div>
          <div style={{ fontSize:10, color:'#4a5568', marginBottom:6 }}>{score}/10 ירוקים</div>
          <div style={{ height:4, background:'#1e2738', borderRadius:2, overflow:'hidden' }}>
            <div style={{ width:`${(score/10)*100}%`, height:'100%', background:col, borderRadius:2 }} />
          </div>
        </div>
        {isActive && sig && (
          <div style={{ textAlign:'right', flexShrink:0 }}>
            <div style={{ fontSize:9, color:'#4a5568', marginBottom:2 }}>סיכוי הצלחה</div>
            <div style={{ fontSize:24, fontWeight:800, color:col, fontFamily:'monospace' }}>{sig.win_rate ?? 0}%</div>
          </div>
        )}
      </div>

      {/* Wait reason — כשאין סטאפ */}
      {!isActive && sig?.wait_reason && (
        <div style={{ marginTop:10, padding:'6px 10px', background:'#111827', borderRadius:6, fontSize:11, color:'#6b7280', direction:'rtl', textAlign:'right' }}>
          ⏳ {sig.wait_reason}
        </div>
      )}

      {/* Signal detail — כשיש סטאפ */}
      {isActive && sig && (
        <>
          {/* Per-target win rates */}
          <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:6, marginTop:10 }}>
            {[
              { label:'T1 · C1', val:sig.target1, pct:sig.t1_win_rate??0, note:'R:R 1:1' },
              { label:'T2 · C2', val:sig.target2, pct:sig.t2_win_rate??0, note:'R:R 1:2' },
              { label:'T3 · Runner', val:sig.target3, pct:sig.t3_win_rate??0, note:'Woodi R1' },
            ].map(({ label, val, pct, note }) => (
              <div key={label} style={{ background:'#0d1117', borderRadius:6, padding:'6px 8px', textAlign:'center', border:`1px solid ${col}22` }}>
                <div style={{ fontSize:9, color:'#4a5568', marginBottom:2 }}>{label}</div>
                <div style={{ fontSize:12, fontWeight:700, color:col, fontFamily:'monospace' }}>{(val??0).toFixed(2)}</div>
                <div style={{ fontSize:10, color:col, fontWeight:700 }}>{pct}%</div>
                <div style={{ height:3, background:'#1e2738', borderRadius:2, marginTop:3, overflow:'hidden' }}>
                  <div style={{ width:`${pct}%`, height:'100%', background:col, borderRadius:2 }} />
                </div>
                <div style={{ fontSize:8, color:'#4a5568', marginTop:2 }}>{note}</div>
              </div>
            ))}
          </div>

          {/* Rationale */}
          {sig.rationale && (
            <div style={{ marginTop:8, padding:'6px 10px', background:'#0a1628', borderRadius:6, borderLeft:'2px solid #7f77dd', fontSize:10, color:'#94a3b8', lineHeight:1.6, direction:'rtl', textAlign:'right' }}>
              <span style={{ fontSize:9, color:'#7f77dd', display:'block', marginBottom:2, direction:'ltr', textAlign:'left' }}>CLAUDE AI</span>
              {sig.rationale}
            </div>
          )}

          {/* כפתור ביטול בלבד — קבלה אוטומטית */}
          {accepted && (
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginTop:10, padding:'6px 10px', background:'#22c55e18', borderRadius:6, border:'1px solid #22c55e44' }}>
              <span style={{ fontSize:11, color:G, fontWeight:700 }}>✓ סטאפ מקובע אוטומטית</span>
              <button onClick={onReject} style={{ fontSize:10, padding:'3px 12px', borderRadius:4, background:'#ef535022', color:'#ef5350', border:'1px solid #ef535044', cursor:'pointer', fontFamily:'inherit', fontWeight:700 }}>לא מעניין ✗</button>
            </div>
          )}
          {!accepted && isGreen && (
            <div style={{ marginTop:10, padding:'6px 10px', background:'#f59e0b18', borderRadius:6, border:'1px solid #f59e0b44', fontSize:10, color:'#f59e0b', direction:'rtl' }}>
              ⏳ ממתין לאישור אוטומטי...
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Zone C: Entry Zone ────────────────────────────────────────────────────────
function EntryZone({ live }:{ live:MarketData|null }) {
  const sig = live?.signal;
  const [c1, setC1] = useState<'open'|'hit'|'closed'>('open');
  const [c2, setC2] = useState<'open'|'hit'|'closed'>('open');
  const [c3, setC3] = useState<'open'|'hit'|'closed'>('open');
  const [entered, setEntered] = useState(false);
  const price = live?.price ?? 0;

  useEffect(() => {
    if (!sig || !entered || sig.direction === 'NO_TRADE') return;
    const long = sig.direction === 'LONG';
    if (long ? price >= sig.target1 : price <= sig.target1) setC1(v => v === 'open' ? 'hit' : v);
    if (long ? price >= sig.target2 : price <= sig.target2) setC2(v => v === 'open' ? 'hit' : v);
    if (long ? price >= sig.target3 : price <= sig.target3) setC3(v => v === 'open' ? 'hit' : v);
  }, [price, sig, entered]);

  const isGreen = sig && sig.direction !== 'NO_TRADE' && (sig.tl_color === 'green' || sig.tl_color === 'green_bright');

  if (!isGreen || !sig) {
    return (
      <div style={{ background:'#111827', border:'1px solid #1e2738', borderRadius:8, padding:14, display:'flex', alignItems:'center', justifyContent:'center', minHeight:120 }}>
        <span style={{ fontSize:11, color:'#4a5568', direction:'rtl' }}>ממתין לסיגנל ירוק...</span>
      </div>
    );
  }

  const isLong = sig.direction === 'LONG';
  const acol = isLong ? G : R;
  const sCol = (s:string) => s === 'hit' ? G : s === 'closed' ? '#4a5568' : Y;
  const sTxt = (s:string) => s === 'hit' ? '✓ הגיע' : s === 'closed' ? '✗ סגור' : '◌ פתוח';

  return (
    <div style={{ background:'#0d1f1a', border:`1px solid ${acol}33`, borderRadius:8, overflow:'hidden' }}>
      {/* Stop / Entry / T1 / T2 / T3 */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(5,1fr)' }}>
        {[
          { label:'STOP', val:sig.stop, color:R },
          { label:'ENTRY', val:sig.entry, color:'#ffffff' },
          { label:'T1·C1', val:sig.target1, color:G, diff:true },
          { label:'T2·C2', val:sig.target2, color:'#16a34a', diff:true },
          { label:'T3·Runner', val:sig.target3, color:'#86efac', diff:true },
        ].map(({ label, val, color, diff }, i) => (
          <div key={label} style={{ padding:'8px 6px', textAlign:'center', borderRight:i<4?`1px solid ${acol}22`:'none', background: label==='ENTRY'?acol+'0f':'transparent' }}>
            <div style={{ fontSize:9, color, marginBottom:3 }}>{label}</div>
            <div style={{ fontSize:13, fontWeight:800, color, fontFamily:'monospace' }}>{val?.toFixed(2)??'—'}</div>
            {diff && val && <div style={{ fontSize:9, color:'#4a5568' }}>+{(val-sig.entry).toFixed(2)}</div>}
          </div>
        ))}
      </div>
      {/* C1/C2/C3 tracker */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr 120px', borderTop:`1px solid ${acol}22` }}>
        {[
          { label:'C1', status:c1, desc:'R:R 1:1 → BE', setter:setC1 },
          { label:'C2', status:c2, desc:'R:R 1:2', setter:setC2 },
          { label:'C3', status:c3, desc:'Runner', setter:setC3 },
        ].map(({ label, status, desc, setter }) => (
          <div key={label} onClick={() => entered && setter(s => s==='open'?'hit':s==='hit'?'closed':'open')}
            style={{ padding:'6px 8px', textAlign:'center', borderRight:`1px solid ${acol}22`, cursor:entered?'pointer':'default' }}>
            <div style={{ fontSize:11, fontWeight:700, color:entered?sCol(status):'#4a5568' }}>{label}</div>
            <div style={{ fontSize:9, color:'#4a5568', marginBottom:2 }}>{desc}</div>
            {entered && <div style={{ fontSize:9, fontWeight:700, color:sCol(status) }}>{sTxt(status)}</div>}
          </div>
        ))}
        <div style={{ display:'flex', alignItems:'center', justifyContent:'center', padding:6 }}>
          {!entered
            ? <button onClick={() => setEntered(true)} style={{ padding:'4px 12px', borderRadius:6, fontSize:10, fontWeight:700, background:G, color:'#0d1117', border:'none', cursor:'pointer', fontFamily:'inherit' }}>נכנסתי ✓</button>
            : <button onClick={() => { setEntered(false); setC1('open'); setC2('open'); setC3('open'); }} style={{ padding:'4px 10px', borderRadius:6, fontSize:10, background:'#1e2738', color:'#6b7280', border:'none', cursor:'pointer', fontFamily:'inherit' }}>אפס</button>
          }
        </div>
      </div>
    </div>
  );
}

// ── AI Canvas Chart ───────────────────────────────────────────────────────────
function AIChart({ candles, live, tf }:{ candles:Candle[]; live:MarketData|null; tf:string }) {
  const cvs = useRef<HTMLCanvasElement>(null);
  const meta = useRef<{ px:(i:number)=>number; py:(p:number)=>number; cW:number; data:Candle[] }>({ px:()=>0, py:()=>0, cW:8, data:[] });
  const [hov, setHov] = useState<Candle|null>(null);

  const draw = useCallback(() => {
    const canvas = cvs.current; if (!canvas) return;
    const W = canvas.width = canvas.parentElement!.clientWidth;
    const H = canvas.height;
    const ctx = canvas.getContext('2d')!;
    const PL=8, PR=72, PT=18, PB=26;
    ctx.fillStyle='#0d1117'; ctx.fillRect(0,0,W,H);

    const data = [...candles].reverse().slice(-80);
    if (live?.bar) {
      const lb:Candle = { ts:live.ts, o:live.bar.o, h:live.bar.h, l:live.bar.l, c:live.bar.c, buy:live.bar.buy, sell:live.bar.sell, delta:live.bar.delta };
      if (data.length===0 || data[data.length-1].ts!==lb.ts) data.push(lb);
    }
    if (data.length===0) {
      ctx.fillStyle='#4a5568'; ctx.font='12px monospace'; ctx.textAlign='center';
      ctx.fillText('ממתין לנתונים...', W/2, H/2); return;
    }

    const prices = data.flatMap(c=>[c.h,c.l]);
    const sig = live?.signal;
    if (sig && sig.direction!=='NO_TRADE') [sig.entry,sig.stop,sig.target1,sig.target2,sig.target3].forEach(p=>p&&prices.push(p));
    if (live?.vwap?.value) prices.push(live.vwap.value);
    if (live?.profile) prices.push(live.profile.vah,live.profile.val,live.profile.poc);
    if ((live?.session?.ibh??0)>0) prices.push(live?.session?.ibh??0,live?.session?.ibl??0);
    if (live?.levels) prices.push(live.levels.prev_high,live.levels.prev_low,live.levels.daily_open);

    let minP=Math.min(...prices.filter(Boolean)), maxP=Math.max(...prices.filter(Boolean));
    const rng=maxP-minP||1; minP-=rng*.07; maxP+=rng*.07;

    const chartW=W-PL-PR, chartH=H-PT-PB;
    const cW=Math.max(3,Math.floor(chartW/data.length));
    const barW=Math.max(2,cW-2);
    const px=(i:number)=>PL+i*cW+cW/2;
    const py=(p:number)=>PT+chartH*(1-(p-minP)/(maxP-minP));
    meta.current={px,py,cW,data};

    // Grid
    for(let i=0;i<=6;i++){
      const p=minP+(maxP-minP)*(i/6), y=py(p);
      ctx.strokeStyle='#161d2a'; ctx.lineWidth=1; ctx.setLineDash([]);
      ctx.beginPath(); ctx.moveTo(PL,y); ctx.lineTo(W-PR,y); ctx.stroke();
      ctx.fillStyle='#3d4a5e'; ctx.font='9px monospace'; ctx.textAlign='left';
      ctx.fillText(p.toFixed(2),W-PR+3,y+3);
    }

    // Level helper
    const lvl=(price:number,color:string,label:string,dash=[4,3],lw=1)=>{
      if(!price||price<minP||price>maxP)return;
      const y=py(price);
      ctx.strokeStyle=color; ctx.lineWidth=lw; ctx.setLineDash(dash);
      ctx.beginPath(); ctx.moveTo(PL,y); ctx.lineTo(W-PR,y); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle=color; ctx.font='bold 8px monospace'; ctx.textAlign='left';
      ctx.fillText(label,W-PR+3,y-1);
    };

    if(live){
      const lv=live.levels||{}, pr=live.profile||{}, se=live.session||{};
      lvl(lv.prev_high,'#ef4444','PDH',[3,3]);
      lvl(lv.prev_low,'#ef4444','PDL',[3,3]);
      lvl(lv.daily_open,'#60a5fa','DO',[3,3]);
      lvl(lv.overnight_high,'#a78bfa','ONH',[2,4]);
      lvl(lv.overnight_low,'#a78bfa','ONL',[2,4]);
      lvl(pr.vah,'#22c55e','VAH',[4,2]);
      lvl(pr.val,'#22c55e','VAL',[4,2]);
      lvl(pr.poc,'#f97316','POC',[6,2]);
      lvl(pr.tpo_poc,'#fb923c','tPOC',[3,3]);
      if(se.ibh>0){lvl(se.ibh,'#38bdf8','IBH',[4,2]); lvl(se.ibl,'#38bdf8','IBL',[4,2]);}
      const vv=live.vwap?.value;
      if(vv&&vv>minP&&vv<maxP){
        const y=py(vv);
        ctx.strokeStyle='#f6c90e'; ctx.lineWidth=1.5; ctx.setLineDash([]);
        ctx.beginPath(); ctx.moveTo(PL,y); ctx.lineTo(W-PR,y); ctx.stroke();
        ctx.fillStyle='#f6c90e'; ctx.font='bold 8px monospace';
        ctx.fillText('VWAP',W-PR+3,y-1);
      }
    }

    // Signal overlays
    if(sig&&sig.direction!=='NO_TRADE'&&sig.entry){
      const acol=sig.direction==='LONG'?'#26a69a':'#ef5350';
      const eyT=py(Math.max(sig.entry,sig.stop)), eyB=py(Math.min(sig.entry,sig.stop));
      ctx.fillStyle=acol+'15'; ctx.fillRect(PL,eyT,W-PL-PR,eyB-eyT);
      lvl(sig.stop,'#ef5350','✕ STOP',[3,2],1.5);
      lvl(sig.entry,'#ffffff','→ ENTRY',[],1.5);
      lvl(sig.target1,'#22c55e','⊕ T1·C1',[5,2],1.2);
      lvl(sig.target2,'#16a34a','⊕ T2·C2',[5,2],1.2);
      lvl(sig.target3,'#86efac','★ T3·Runner',[5,2],1.2);
    }

    // Candles
    data.forEach((c,i)=>{
      const x=px(i), up=c.c>=c.o;
      ctx.strokeStyle=up?'#1a756d':'#a33535'; ctx.lineWidth=1; ctx.setLineDash([]);
      ctx.beginPath(); ctx.moveTo(x,py(c.h)); ctx.lineTo(x,py(c.l)); ctx.stroke();
      const bt=py(Math.max(c.o,c.c)), bb=py(Math.min(c.o,c.c));
      ctx.fillStyle=up?'#26a69a':'#ef5350';
      ctx.fillRect(x-barW/2,bt,barW,Math.max(1,bb-bt));
    });

    // Live price
    if(live){
      const price=live.price||live.bar?.c||0, y=py(price);
      if(y>PT&&y<H-PB){
        ctx.strokeStyle='#ffffff66'; ctx.lineWidth=1; ctx.setLineDash([2,2]);
        ctx.beginPath(); ctx.moveTo(PL,y); ctx.lineTo(W-PR,y); ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle='#e2e8f0'; ctx.fillRect(W-PR+1,y-8,66,16);
        ctx.fillStyle='#0d1117'; ctx.font='bold 10px monospace'; ctx.textAlign='left';
        ctx.fillText(price.toFixed(2),W-PR+4,y+4);
      }
    }

    // Time labels
    ctx.fillStyle='#3d4a5e'; ctx.font='8px monospace'; ctx.textAlign='center';
    const step=Math.max(1,Math.floor(data.length/8));
    data.forEach((c,i)=>{
      if(i%step===0&&c.ts){
        const d=new Date(c.ts*1000);
        ctx.fillText(`${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`,px(i),H-8);
      }
    });
  },[candles,live,tf]);

  useEffect(()=>{draw();},[draw]);
  useEffect(()=>{window.addEventListener('resize',draw);return()=>window.removeEventListener('resize',draw);},[draw]);

  const onMove=(e:React.MouseEvent<HTMLCanvasElement>)=>{
    const canvas=cvs.current; if(!canvas)return;
    const rect=canvas.getBoundingClientRect();
    const mx=(e.clientX-rect.left)*(canvas.width/rect.width);
    const {px,cW,data}=meta.current;
    const idx=Math.round((mx-8-cW/2)/cW);
    setHov(idx>=0&&idx<data.length?data[idx]:null);
  };

  return (
    <div style={{ position:'relative' }}>
      <canvas ref={cvs} height={400} style={{ width:'100%', display:'block', cursor:'crosshair' }}
        onMouseMove={onMove} onMouseLeave={()=>setHov(null)} />
      {hov&&(
        <div style={{ position:'absolute', top:8, left:12, background:'#1a2233ee', border:'1px solid #2d3a4a', borderRadius:6, padding:'4px 10px', fontSize:10, color:'#94a3b8', fontFamily:'monospace', pointerEvents:'none' }}>
          <span style={{color:'#60a5fa'}}>O</span> {(hov.o??0).toFixed(2)}&nbsp;
          <span style={{color:'#22c55e'}}>H</span> {(hov.h??0).toFixed(2)}&nbsp;
          <span style={{color:'#ef5350'}}>L</span> {(hov.l??0).toFixed(2)}&nbsp;
          <span style={{color:'#e2e8f0'}}>C</span> {(hov.c??0).toFixed(2)}&nbsp;
          <span style={{color:hov.delta>=0?'#26a69a':'#ef5350'}}>Δ {hov.delta>=0?'+':''}{Math.round(hov.delta)}</span>
        </div>
      )}
    </div>
  );
}

// ── Volume + Timer ────────────────────────────────────────────────────────────
function VolumeTimer({ bar }:{ bar:Bar|null }) {
  const [secs,setSecs]=useState(0);
  useEffect(()=>{
    const tick=()=>setSecs(180-(Math.floor(Date.now()/1000)%180));
    tick(); const t=setInterval(tick,1000); return()=>clearInterval(t);
  },[]);
  const pct=((180-secs)/180)*100, urgent=secs<=30;
  const mm=Math.floor(secs/60), ss=secs%60;
  const buy=bar?.buy??0, sell=bar?.sell??0, total=buy+sell||1;
  const buyPct=Math.round((buy/total)*100);
  const delta=bar?.delta??0, isPos=delta>=0;
  const deltaLbl=Math.abs(delta)>300?(isPos?'קונים חזקים':'מוכרים חזקים'):Math.abs(delta)>100?(isPos?'לחץ קנייה':'לחץ מכירה'):'נייטרלי';

  return (
    <div style={{ borderTop:'1px solid #1e2738', padding:'8px 12px', display:'flex', flexDirection:'column', gap:6 }}>
      {/* Volume */}
      <div>
        <div style={{ display:'flex', justifyContent:'space-between', fontSize:9, marginBottom:3 }}>
          <span style={{color:'#26a69a'}}>B {Math.round(buy).toLocaleString()}</span>
          <span style={{color:'#4a5568'}}>נפח</span>
          <span style={{color:'#ef5350'}}>S {Math.round(sell).toLocaleString()}</span>
        </div>
        <div style={{ height:8, borderRadius:4, overflow:'hidden', display:'flex', background:'#ef5350' }}>
          <div style={{ width:`${buyPct}%`, background:'#26a69a', transition:'width .4s', borderRadius:'4px 0 0 4px' }} />
        </div>
        <div style={{ display:'flex', justifyContent:'space-between', fontSize:10, marginTop:3 }}>
          <span style={{color:'#4a5568'}}>Delta</span>
          <span style={{ color:isPos?'#26a69a':'#ef5350', fontFamily:'monospace', fontWeight:700 }}>
            {isPos?'+':''}{Math.round(delta).toLocaleString()} · {deltaLbl}
          </span>
        </div>
      </div>
      {/* Timer */}
      <div style={{ display:'flex', alignItems:'center', gap:8 }}>
        <span style={{ fontSize:9, color:'#4a5568' }}>נר הבא</span>
        <div style={{ flex:1, height:3, background:'#1e2738', borderRadius:2, overflow:'hidden' }}>
          <div style={{ width:`${pct}%`, height:'100%', background:urgent?R:G, transition:'width 1s linear', borderRadius:2 }} />
        </div>
        <span style={{ fontSize:11, fontFamily:'monospace', fontWeight:700, color:urgent?R:'#6b7280' }}>{mm}:{ss.toString().padStart(2,'0')}</span>
      </div>
    </div>
  );
}

// ── Zone E: Indicators ────────────────────────────────────────────────────────
const TOOLTIPS:Record<string,string> = {
  'CVD מגמה':'Cumulative Volume Delta — סכום הפרש קונים/מוכרים מתחילת היום',
  'CVD 15m':'דלתא של 15 דקות האחרונות — מומנטום קצר',
  'CVD 60m':'דלתא של 60 דקות האחרונות — מומנטום ארוך',
  'VWAP':'ממוצע משוקלל נפח — הרמה שמפרידה קונים ומוכרים',
  'Value Area':'70% מהמסחר נמצא בין VAH ל-VAL',
  'POC':'המחיר עם הכי הרבה נפח היום',
  'Woodi PP':'ציר Woodi — מרכז המסחר לפי נוסחת יאנגן',
  'Absorption':'קונים בולעים מכירות — רמזור להיפוך',
  'Liq Sweep':'שבירה מתחת לרמה עם חזרה מהירה',
  'Imbalance':'חוסר איזון בספר פקודות — 3:1 לפחות',
  'Session':'שלב המסחר הנוכחי',
  'IB':'Initial Balance — טווח השעה הראשונה',
  'MTF':'יישור Multi-Timeframe — כל הטווחים באותו כיוון',
};

function Indicators({ live }:{ live:MarketData|null }) {
  const [tip,setTip]=useState('');
  if(!live) return null;

  const cvd=live.cvd||{}, vwap=live.vwap||{}, prof=live.profile||{}, woodi=live.woodi||{};
  const sess=live.session||{}, of2=live.order_flow||{}, bar=live.bar||{}, mtf=live.mtf||{};
  const price=live.price||0;

  const rows=[
    // מגמה
    { cat:'מגמה', name:'CVD מגמה', col:cvd.trend==='BULLISH'?G:cvd.trend==='BEARISH'?R:Y, val:cvd.trend||'—', note:cvd.trend==='BULLISH'?'עולה':cvd.trend==='BEARISH'?'יורדת':'נייטרלי' },
    { cat:'', name:'CVD 15m', col:(cvd.d5||0)>50?G:(cvd.d5||0)<-50?R:Y, val:((cvd.d5||0)>=0?'+':'')+Math.round(cvd.d5||0), note:Math.abs(cvd.d5||0)>200?'חזק':Math.abs(cvd.d5||0)>50?'בינוני':'חלש' },
    { cat:'', name:'CVD 60m', col:(cvd.d20||0)>200?G:(cvd.d20||0)<-200?R:Y, val:((cvd.d20||0)>=0?'+':'')+Math.round(cvd.d20||0), note:Math.abs(cvd.d20||0)>500?'מומנטום חזק':'מומנטום' },
    // מיקום
    { cat:'מיקום', name:'VWAP', col:vwap.pullback?G:vwap.above?G:R, val:vwap.value?.toFixed(2)||'—', note:vwap.pullback?'⚡ Pullback':vwap.above?'מעל':'מתחת' },
    { cat:'', name:'Value Area', col:prof.in_va?Y:prof.above_poc?G:R, val:prof.in_va?'בתוך VA':prof.above_poc?'מעל VAH':'מתחת VAL', note:prof.in_va?'בטווח ערך':prof.above_poc?'שבירה מעלה':'שבירה מטה' },
    { cat:'', name:'POC', col:'#f97316', val:prof.poc?.toFixed(2)||'—', note:((price-(prof.poc||price))>=0?'+':'')+((price-(prof.poc||price)).toFixed(2))+' pts' },
    { cat:'', name:'Woodi PP', col:woodi.above_pp?G:R, val:woodi.pp?.toFixed(2)||'—', note:woodi.above_pp?'מעל ▲':'מתחת ▼' },
    // Order Flow
    { cat:'Order Flow', name:'Absorption', col:of2.absorption_bull?G:'#2d3a4a', val:of2.absorption_bull?'פעיל ✓':'לא זוהה', note:of2.absorption_bull?'קונים בולעים':'—' },
    { cat:'', name:'Liq Sweep', col:of2.liq_sweep?G:'#2d3a4a', val:of2.liq_sweep?'זוהה ✓':'לא זוהה', note:of2.liq_sweep?'Sweep + חזרה':'—' },
    { cat:'', name:'Imbalance', col:(of2.imbalance_bull||0)>0?G:(of2.imbalance_bear||0)>0?R:'#2d3a4a', val:`B×${of2.imbalance_bull||0} S×${of2.imbalance_bear||0}`, note:(of2.imbalance_bull||0)>0?'עולה':(of2.imbalance_bear||0)>0?'יורד':'—' },
    // מבנה
    { cat:'מבנה', name:'Session', col:sess.phase==='RTH'?G:sess.phase==='OVERNIGHT'?Y:R, val:sess.phase||'—', note:sess.phase==='RTH'?'שעות מסחר':'לילי' },
    { cat:'', name:'IB', col:sess.ibh>0?(sess.ib_locked?G:Y):'#2d3a4a', val:sess.ibh>0?`H${sess.ibh?.toFixed(0)} L${sess.ibl?.toFixed(0)}`:'בניית IB', note:sess.ib_locked?'נעול ✓':sess.ibh>0?'מתגבש':'—' },
    { cat:'', name:'MTF', col:(()=>{ const m3=bar.delta||0, m15=mtf.m15?.delta||0, m30=mtf.m30?.delta||0; return (m3>0&&m15>0&&m30>0)||(m3<0&&m15<0&&m30<0)?G:Y; })(), val:(()=>{ const m3=bar.delta||0, m15=mtf.m15?.delta||0, m30=mtf.m30?.delta||0; return `3m${m3>=0?'▲':'▼'} 15m${m15>=0?'▲':'▼'} 30m${m30>=0?'▲':'▼'}`; })(), note:'יישור timeframes' },
  ];

  return (
    <div style={{ background:'#111827', border:'1px solid #1e2738', borderRadius:8, overflow:'hidden', position:'relative' }}>
      {/* Tooltip */}
      {tip && (
        <div style={{ position:'absolute', top:0, left:0, right:0, background:'#1a2233', borderBottom:'1px solid #2d3a4a', padding:'6px 10px', fontSize:10, color:'#94a3b8', lineHeight:1.5, direction:'rtl', textAlign:'right', zIndex:10 }}>
          {TOOLTIPS[tip] || tip}
          <button onClick={()=>setTip('')} style={{ float:'left', background:'none', border:'none', color:'#4a5568', cursor:'pointer', fontSize:12 }}>×</button>
        </div>
      )}
      <div style={{ padding:'8px 10px', borderBottom:'1px solid #1e2738' }}>
        <span style={{ fontSize:9, color:'#4a5568', letterSpacing:2 }}>אינדיקטורים ({rows.filter(r=>r.col===G).length}/{rows.length} ✓)</span>
      </div>
      <div style={{ padding:'4px 0' }}>
        {rows.map((r,i)=>(
          <div key={i}>
            {r.cat && <div style={{ fontSize:8, color:'#2d3a4a', letterSpacing:1, padding:'4px 10px 2px' }}>{r.cat}</div>}
            <div style={{ display:'flex', alignItems:'center', gap:6, padding:'4px 10px', borderBottom:'1px solid #0d1117' }}>
              <MiniLight col={r.col} />
              <span style={{ fontSize:10, color:'#6b7280', width:72, flexShrink:0 }}>{r.name}</span>
              <span style={{ fontSize:10, color:r.col, fontFamily:'monospace', flex:1, fontWeight:600 }}>{r.val}</span>
              <span style={{ fontSize:9, color:'#4a5568', direction:'rtl' }}>{r.note}</span>
              <button onClick={()=>setTip(tip===r.name?'':r.name)} style={{ width:14, height:14, borderRadius:'50%', background:'#1e2738', border:'none', color:'#4a5568', fontSize:9, cursor:'pointer', flexShrink:0, display:'flex', alignItems:'center', justifyContent:'center' }}>?</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}


// ── AI Analysis Panel — קבוע ונראה תמיד ─────────────────────────────────────
function AIAnalysisPanel({ signal, aiLoading, onAskAI }: { signal?: Signal; aiLoading: boolean; onAskAI: () => void }) {
  if (aiLoading) {
    return (
      <div style={{ background:'#111827', border:'1px solid #1e2738', borderRadius:8, padding:16, display:'flex', alignItems:'center', gap:12 }}>
        <div style={{ width:14, height:14, borderRadius:'50%', border:'2px solid #4a5568', borderTopColor:'#7f77dd', animation:'spin 0.8s linear infinite', flexShrink:0 }} />
        <span style={{ fontSize:12, color:'#6b7280' }}>Claude מנתח את השוק...</span>
      </div>
    );
  }

  if (!signal) {
    return (
      <div style={{ background:'#111827', border:'1px solid #1e2738', borderRadius:8, padding:16, display:'flex', alignItems:'center', justifyContent:'space-between' }}>
        <span style={{ fontSize:11, color:'#4a5568' }}>לחץ ⚡ לניתוח AI</span>
        <button onClick={onAskAI} style={{ padding:'4px 14px', borderRadius:6, fontSize:11, fontWeight:700, background:'#7f77dd22', color:'#7f77dd', border:'1px solid #7f77dd44', cursor:'pointer', fontFamily:'inherit' }}>⚡ נתח עכשיו</button>
      </div>
    );
  }

  const isActive = signal.direction !== 'NO_TRADE' && (signal.score ?? 0) >= 5;
  const col = signal.direction === 'LONG' ? '#22c55e' : signal.direction === 'SHORT' ? '#ef5350' : '#f59e0b';
  const dirLabel = signal.direction === 'LONG' ? '▲ LONG' : signal.direction === 'SHORT' ? '▼ SHORT' : '⏳ המתן';

  return (
    <div style={{ background:'#0a1117', border:`1px solid ${col}33`, borderRadius:8, overflow:'hidden' }}>
      {/* Header */}
      <div style={{ display:'flex', alignItems:'center', gap:10, padding:'10px 16px', background:`${col}08`, borderBottom:`1px solid ${col}22` }}>
        <div style={{ width:8, height:8, borderRadius:'50%', background:col, boxShadow:`0 0 6px ${col}` }} />
        <span style={{ fontSize:11, color:'#7f77dd', fontWeight:700, letterSpacing:1 }}>⚡ CLAUDE AI — ניתוח שוק</span>
        <span style={{ fontSize:13, fontWeight:800, color:col, marginLeft:'auto' }}>{dirLabel}</span>
        {signal.setup && <span style={{ fontSize:10, padding:'2px 8px', borderRadius:10, background:`${col}22`, color:col, fontWeight:700 }}>{signal.setup}</span>}
        <button onClick={onAskAI} style={{ padding:'3px 10px', borderRadius:5, fontSize:10, fontWeight:700, background:'#1e2738', color:'#6b7280', border:'1px solid #2d3a4a', cursor:'pointer', fontFamily:'inherit' }}>רענן</button>
      </div>

      {/* Rationale — תמיד מוצג */}
      {signal.rationale && (
        <div style={{ padding:'12px 16px', borderBottom:`1px solid ${col}11` }}>
          <div style={{ fontSize:9, color:'#4a5568', marginBottom:6, letterSpacing:1 }}>ניתוח</div>
          <div style={{ fontSize:13, color:'#cbd5e1', lineHeight:1.8, direction:'rtl', textAlign:'right', fontFamily:'sans-serif' }}>
            {signal.rationale}
          </div>
        </div>
      )}

      {/* Wait reason — מה חסר */}
      {signal.wait_reason && (
        <div style={{ padding:'10px 16px', borderBottom:`1px solid ${col}11`, background:'#0d1117' }}>
          <div style={{ fontSize:9, color:'#f59e0b', marginBottom:4, letterSpacing:1 }}>⏳ מה חסר לכניסה</div>
          <div style={{ fontSize:12, color:'#94a3b8', lineHeight:1.7, direction:'rtl', textAlign:'right', fontFamily:'sans-serif' }}>
            {signal.wait_reason}
          </div>
        </div>
      )}

      {/* Levels row */}
      {(signal.entry ?? 0) > 0 && (
        <div style={{ display:'grid', gridTemplateColumns:'repeat(5,1fr)', borderTop:`1px solid ${col}11` }}>
          {[
            { l:'כניסה', v:(signal.entry??0).toFixed(2), c:'#f0f6fc' },
            { l:'סטופ', v:(signal.stop??0).toFixed(2), c:'#ef5350' },
            { l:'T1', v:(signal.target1??0).toFixed(2), c:'#22c55e' },
            { l:'T2', v:(signal.target2??0).toFixed(2), c:'#16a34a' },
            { l:'WR', v:`${signal.win_rate??0}%`, c:col },
          ].map(({l,v,c})=>(
            <div key={l} style={{ padding:'8px 6px', textAlign:'center', borderRight:'1px solid #1e2738' }}>
              <div style={{ fontSize:9, color:'#4a5568', marginBottom:3 }}>{l}</div>
              <div style={{ fontSize:12, fontWeight:800, color:c, fontFamily:'monospace' }}>{v}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Root Dashboard ────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [live,setLive]=useState<MarketData|null>(null);
  const [candles,setCandles]=useState<Candle[]>([]);
  const [connected,setConnected]=useState(false);
  const [tf,setTf]=useState<'m3'|'m15'|'m30'|'m60'>('m3');
  const [accepted,setAccepted]=useState(false);
  const [lockedSignal,setLockedSignal]=useState<any>(null);
  const [rejectedTs,setRejectedTs]=useState(0);
  const [aiLoading,setAiLoading]=useState(false);
  const prevSigRef=useRef<string>('');

  const askAI=useCallback(async()=>{
    if(aiLoading) return;
    setAiLoading(true);
    try{
      const r=await fetch(`${API_URL}/market/analyze`,{cache:'no-store'});
      if(!r.ok) throw new Error();
      const sig=await r.json();
      if(!sig?.direction) return;
      // תמיד מציג — גם אם נדחה קודם
      prevSigRef.current='';
      setRejectedTs(0);
      const isGreen=sig.tl_color==='green'||sig.tl_color==='green_bright';
      if(isGreen && sig.direction!=='NO_TRADE'){
        setLockedSignal(sig);
        setAccepted(true);
      } else {
        setAccepted(false);
        setLockedSignal(null);
      }
      setLive(prev=>prev?{...prev,signal:sig}:prev);
    }catch{}
    finally{ setAiLoading(false); }
  },[aiLoading]);

  const fetchLive=useCallback(async()=>{
    try{
      const r=await fetch(`${API_URL}/market/latest?t=${Date.now()}`,{cache:'no-store'});
      if(!r.ok)throw new Error();
      const d:MarketData=await r.json();
      if(d?.bar){setLive(d);setConnected(true);}
    }catch{setConnected(false);}
  },[]);

  const fetchAnalyze=useCallback(async()=>{
    if(accepted && lockedSignal) return; // מקובע — לא מחפש חדש
    try{
      const r=await fetch(`${API_URL}/market/analyze`,{cache:'no-store'});
      if(!r.ok)return;
      const sig=await r.json();
      if(!sig?.direction) return;
      const sigKey=`${sig.direction}-${sig.setup}-${sig.score}`;
      // אם זה אותו סטאפ שנדחה — לא מציג
      if(sigKey===prevSigRef.current && rejectedTs>0) return;
      // Auto-lock ברגע שמגיע ירוק
      const isGreen = sig.tl_color==='green'||sig.tl_color==='green_bright';
      if(isGreen && sig.direction!=='NO_TRADE' && !accepted) {
        setLockedSignal(sig);
        setAccepted(true);
      }
      setLive(prev=>prev?{...prev,signal:sig}:prev);
    }catch{}
  },[accepted,lockedSignal,rejectedTs]);

  const fetchCandles=useCallback(async()=>{
    try{
      const r=await fetch(`${API_URL}/market/candles?limit=80`,{cache:'no-store'});
      if(!r.ok)return;
      const raw=await r.json();
      const d:Candle[]=Array.isArray(raw)?raw.map((i:any)=>typeof i==='string'?JSON.parse(i):i):[];
      if(d.length>0)setCandles(d);
    }catch{}
  },[]);

  useEffect(()=>{
    fetchLive();fetchCandles();fetchAnalyze();
    const lt=setInterval(fetchLive,2000);
    const ct=setInterval(fetchCandles,15000);
    const at=setInterval(fetchAnalyze,30000);
    return()=>{clearInterval(lt);clearInterval(ct);clearInterval(at);};
  },[fetchLive,fetchCandles,fetchAnalyze]);

  const bar=tf==='m3'?live?.bar:live?.mtf?.[tf]??live?.bar;

  return (
    <div style={{ background:'#0a0a0f', minHeight:'100vh', padding:12, display:'flex', flexDirection:'column', gap:10, fontFamily:'"JetBrains Mono","Fira Code",monospace' }}>

      {/* א — Top bar */}
      <TopBar live={live} connected={connected} onAskAI={askAI} aiLoading={aiLoading} />

      {/* ב + ג — Score + Entry Zone */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:10 }}>
        <MainScore
          live={accepted && lockedSignal ? {...live, signal:lockedSignal} as any : live}
          accepted={accepted}
          onAccept={()=>{ setAccepted(true); setLockedSignal(live?.signal); }}
          onReject={()=>{
            const sig=lockedSignal||live?.signal;
            if(sig) prevSigRef.current=`${sig.direction}-${sig.setup}-${sig.score}`;
            setAccepted(false);
            setLockedSignal(null);
            setRejectedTs(Date.now());
          }}
        />
        <EntryZone live={accepted && lockedSignal ? {...live, signal:lockedSignal} as any : null} />
      </div>

      {/* ג.5 — AI Analysis Panel */}
      <AIAnalysisPanel signal={live?.signal} aiLoading={aiLoading} onAskAI={askAI} />

      {/* ד + ה — Chart + Indicators */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 240px', gap:10 }}>
        {/* Chart */}
        <div style={{ background:'#111827', border:'1px solid #1e2738', borderRadius:8, overflow:'hidden' }}>
          {/* Chart header */}
          <div style={{ display:'flex', alignItems:'center', gap:8, padding:'6px 12px', background:'#111827', borderBottom:'1px solid #1e2738' }}>
            <span style={{ fontSize:9, color:'#4a5568', letterSpacing:2 }}>גרף נרות + רמות</span>
            <div style={{ display:'flex', gap:3, marginLeft:'auto' }}>
              {(['m3','m15','m30','m60'] as const).map(t=>(
                <button key={t} onClick={()=>setTf(t)} style={{ padding:'2px 8px', borderRadius:5, fontSize:9, fontWeight:700, border:'none', cursor:'pointer', fontFamily:'inherit', background:tf===t?'#f6c90e':'#1e2738', color:tf===t?'#0d1117':'#6b7280' }}>{t.toUpperCase()}</button>
              ))}
            </div>
          </div>
          <LightweightChart
            candles={candles}
            livePrice={live?.price}
            liveBar={live?.bar ? { ts: live.ts, o: live.bar.o, h: live.bar.h, l: live.bar.l, c: live.bar.c } : null}
            vwap={live?.vwap?.value}
            levels={live?.levels}
            profile={live?.profile}
            session={{ ibh: live?.session?.ibh, ibl: live?.session?.ibl }}
            signal={(accepted && lockedSignal) ? lockedSignal : live?.signal ?? null}
            activeSetups={calcSetups(live)?.filter(s=>Math.max(s.long.score,s.short.score)>=60).map(s=>({
              name: s.name,
              dir: s.long.score>=s.short.score ? 'long' : 'short',
              col: s.col,
            }))}
            height={480}
          />
          <VolumeTimer bar={bar??null} />
        </div>

        {/* Indicators */}
        <Indicators live={live} />

        {/* Setup Scanner */}
        <SetupScanner live={live} />
      </div>

      <style>{`@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}} .live-blink{animation:blink 2s infinite} @keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}
