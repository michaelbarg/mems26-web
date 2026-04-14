 'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

const API_URL = 'https://mems26-web.onrender.com';

interface Bar {
  o: number; h: number; l: number; c: number;
  vol: number; buy: number; sell: number; delta: number;
}
interface MarketData {
  ts: number;
  price: number;
  bar: Bar;
  mtf: { m3: Bar; m15: Bar; m30: Bar; m60: Bar };
  cvd: { total: number; d20: number; d5: number; bull: boolean; trend: string; buy_vol: number; sell_vol: number; delta: number };
  vwap: { value: number; distance: number; above: boolean; pullback: boolean };
  session: { phase: string; min: number; sh: number; sl: number; ibh: number; ibl: number; ib_locked: boolean };
  profile: { poc: number; vah: number; val: number; tpo_poc: number; in_va: boolean; above_poc: boolean };
  woodi: { pp: number; r1: number; r2: number; s1: number; s2: number; above_pp: boolean };
  levels: {
    week_high: number; week_low: number;
    prev_high: number; prev_low: number; prev_close: number;
    daily_open: number; overnight_high: number; overnight_low: number;
  };
  order_flow: { absorption_bull: boolean; liq_sweep: boolean; imbalance_bull: number; imbalance_bear: number };
  reversal: { ib_high: number; ib_low: number; locked: boolean; rev15_type: string; rev15_price: number; rev22_type: string; rev22_price: number };
  day: { type: string; range: number; ib_range: number };
}

interface Candle {
  ts: number;
  o: number; h: number; l: number; c: number;
  vol: number; buy: number; sell: number; delta: number;
}

// ── Tiny canvas-based candlestick chart (no external deps) ──────────────────
function CandleChart({ candles, live, vwap, levels, profile, session }: {
  candles: Candle[];
  live: MarketData | null;
  vwap: number;
  levels: MarketData['levels'] | null;
  profile: MarketData['profile'] | null;
  session: MarketData['session'] | null;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || candles.length === 0) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;
    const PAD_LEFT = 10;
    const PAD_RIGHT = 70;
    const PAD_TOP = 20;
    const PAD_BOT = 30;

    ctx.clearRect(0, 0, W, H);

    // Background
    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, 0, W, H);

    const data = [...candles].reverse(); // oldest first
    const last80 = data.slice(Math.max(0, data.length - 80));

    const prices = last80.flatMap(c => [c.h, c.l]);
    if (vwap) prices.push(vwap);
    let minP = Math.min(...prices);
    let maxP = Math.max(...prices);
    const pad = (maxP - minP) * 0.08;
    minP -= pad; maxP += pad;

    const chartW = W - PAD_LEFT - PAD_RIGHT;
    const chartH = H - PAD_TOP - PAD_BOT;
    const barW = Math.max(2, Math.floor(chartW / last80.length) - 1);

    const px = (i: number) => PAD_LEFT + (i + 0.5) * (chartW / last80.length);
    const py = (price: number) => PAD_TOP + chartH - ((price - minP) / (maxP - minP)) * chartH;

    // Grid lines
    const steps = 6;
    for (let i = 0; i <= steps; i++) {
      const price = minP + (maxP - minP) * (i / steps);
      const y = py(price);
      ctx.strokeStyle = '#1e2738';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(PAD_LEFT, y);
      ctx.lineTo(W - PAD_RIGHT, y);
      ctx.stroke();
      // Price label
      ctx.fillStyle = '#4a5568';
      ctx.font = '10px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(price.toFixed(2), W - PAD_RIGHT + 4, y + 3);
    }

    // Helper: draw horizontal price line
    const drawLine = (price: number, color: string, label: string, dash: number[] = []) => {
      if (price <= 0 || price < minP || price > maxP) return;
      const y = py(price);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.setLineDash(dash);
      ctx.beginPath();
      ctx.moveTo(PAD_LEFT, y);
      ctx.lineTo(W - PAD_RIGHT, y);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = color;
      ctx.font = 'bold 9px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(label, W - PAD_RIGHT + 4, y - 1);
    };

    // VWAP line (solid yellow)
    if (vwap > minP && vwap < maxP) {
      const y = py(vwap);
      ctx.strokeStyle = '#f6c90e';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.moveTo(PAD_LEFT, y);
      ctx.lineTo(W - PAD_RIGHT, y);
      ctx.stroke();
      ctx.fillStyle = '#f6c90e';
      ctx.font = 'bold 9px monospace';
      ctx.fillText(`VWAP ${vwap.toFixed(2)}`, W - PAD_RIGHT + 4, y - 2);
    }

    // Level lines
    if (levels) {
      drawLine(levels.prev_high, '#ef4444', `PDH`, [4, 3]);
      drawLine(levels.prev_low, '#ef4444', `PDL`, [4, 3]);
      drawLine(levels.daily_open, '#60a5fa', `DO`, [3, 3]);
      drawLine(levels.overnight_high, '#a78bfa', `ONH`, [2, 4]);
      drawLine(levels.overnight_low, '#a78bfa', `ONL`, [2, 4]);
    }
    if (profile) {
      drawLine(profile.poc, '#f97316', `POC`, [6, 2]);
      drawLine(profile.vah, '#22c55e', `VAH`, [3, 3]);
      drawLine(profile.val, '#22c55e', `VAL`, [3, 3]);
    }
    if (session && session.ibh > 0) {
      drawLine(session.ibh, '#38bdf8', `IBH`, [4, 2]);
      drawLine(session.ibl, '#38bdf8', `IBL`, [4, 2]);
    }

    // Candles
    last80.forEach((c, i) => {
      const x = px(i);
      const isUp = c.c >= c.o;
      const color = isUp ? '#26a69a' : '#ef5350';
      const wickColor = isUp ? '#1a756d' : '#a33535';

      // Wick
      ctx.strokeStyle = wickColor;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, py(c.h));
      ctx.lineTo(x, py(c.l));
      ctx.stroke();

      // Body
      const bodyTop = py(Math.max(c.o, c.c));
      const bodyBot = py(Math.min(c.o, c.c));
      const bodyH = Math.max(1, bodyBot - bodyTop);
      ctx.fillStyle = color;
      ctx.fillRect(x - barW / 2, bodyTop, barW, bodyH);
    });

    // Live price line
    if (live) {
      const y = py(live.price);
      if (y > PAD_TOP && y < PAD_TOP + chartH) {
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1;
        ctx.setLineDash([2, 2]);
        ctx.beginPath();
        ctx.moveTo(PAD_LEFT, y);
        ctx.lineTo(W - PAD_RIGHT, y);
        ctx.stroke();
        ctx.setLineDash([]);

        // Price badge
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(W - PAD_RIGHT + 2, y - 8, 64, 16);
        ctx.fillStyle = '#0d1117';
        ctx.font = 'bold 10px monospace';
        ctx.textAlign = 'left';
        ctx.fillText(live.price.toFixed(2), W - PAD_RIGHT + 5, y + 4);
      }
    }

    // Time labels
    ctx.fillStyle = '#4a5568';
    ctx.font = '9px monospace';
    ctx.textAlign = 'center';
    const step = Math.floor(last80.length / 8);
    last80.forEach((c, i) => {
      if (i % step === 0) {
        const d = new Date(c.ts * 1000);
        const label = `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
        ctx.fillText(label, px(i), H - 8);
      }
    });

  }, [candles, live, vwap, levels, profile, session]);

  return (
    <canvas
      ref={canvasRef}
      width={900}
      height={420}
      style={{ width: '100%', height: '100%', display: 'block' }}
    />
  );
}

// ── Delta bar ───────────────────────────────────────────────────────────────
function DeltaBar({ buy, sell, delta }: { buy: number; sell: number; delta: number }) {
  const total = buy + sell || 1;
  const buyPct = (buy / total) * 100;
  const isPos = delta >= 0;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <div style={{ display: 'flex', height: 6, borderRadius: 3, overflow: 'hidden', background: '#1e2738' }}>
        <div style={{ width: `${buyPct}%`, background: '#26a69a', transition: 'width 0.4s' }} />
        <div style={{ flex: 1, background: '#ef5350' }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#6b7280' }}>
        <span style={{ color: '#26a69a' }}>B {buy.toFixed(0)}</span>
        <span style={{ color: isPos ? '#26a69a' : '#ef5350', fontWeight: 700 }}>Δ {isPos ? '+' : ''}{delta.toFixed(0)}</span>
        <span style={{ color: '#ef5350' }}>S {sell.toFixed(0)}</span>
      </div>
    </div>
  );
}

// ── Level row ────────────────────────────────────────────────────────────────
function LevelRow({ label, value, color, price }: { label: string; value: number; color: string; price: number }) {
  const diff = price - value;
  const diffStr = diff >= 0 ? `+${diff.toFixed(2)}` : diff.toFixed(2);
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '3px 0', borderBottom: '1px solid #1a2030' }}>
      <span style={{ fontSize: 11, color: '#6b7280', width: 50 }}>{label}</span>
      <span style={{ fontSize: 12, fontWeight: 700, color, fontFamily: 'monospace' }}>{value.toFixed(2)}</span>
      <span style={{ fontSize: 10, color: diff >= 0 ? '#26a69a' : '#ef5350', fontFamily: 'monospace', width: 52, textAlign: 'right' }}>{diffStr}</span>
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────────────────
export default function ChartPanel() {
  const [live, setLive] = useState<MarketData | null>(null);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [timeframe, setTimeframe] = useState<'m3' | 'm15' | 'm30' | 'm60'>('m3');

  const fetchLive = useCallback(async () => {
    try {
      const r = await fetch(`${API_URL}/market/latest`);
      if (!r.ok) throw new Error('not ok');
      const d: MarketData = await r.json();
      setLive(d);
      setConnected(true);
      setLastUpdate(new Date());
    } catch {
      setConnected(false);
    }
  }, []);

  const fetchCandles = useCallback(async () => {
    try {
      const r = await fetch(`${API_URL}/market/candles`);
      if (!r.ok) return;
      const d = await r.json();
      if(Array.isArray(d)) setCandles(d);
    } catch {}
  }, []);

  useEffect(() => {
    fetchLive();
    fetchCandles();
    const liveTimer = setInterval(fetchLive, 2000);
    const candleTimer = setInterval(fetchCandles, 15000);
    return () => { clearInterval(liveTimer); clearInterval(candleTimer); };
  }, [fetchLive, fetchCandles]);

  const price = live?.price ?? 0;
  const bar = live ? (timeframe === 'm3' ? live.bar : live.mtf[timeframe]) : null;

  const phaseColor = (p: string) => {
    if (p === 'RTH') return '#22c55e';
    if (p === 'OVERNIGHT') return '#f59e0b';
    return '#60a5fa';
  };

  const trendColor = live?.cvd.trend === 'BULLISH' ? '#26a69a' : '#ef5350';

  return (
    <div style={{
      background: '#0d1117',
      color: '#e2e8f0',
      fontFamily: '"JetBrains Mono", "Fira Code", monospace',
      minHeight: '100vh',
      padding: 16,
      boxSizing: 'border-box',
    }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 12 }}>
        <div style={{ fontSize: 18, fontWeight: 800, letterSpacing: 2, color: '#f0f6fc' }}>
          MES<span style={{ color: '#f6c90e' }}>26</span>
        </div>
        <div style={{ fontSize: 28, fontWeight: 800, fontFamily: 'monospace', color: '#f0f6fc' }}>
          {price.toFixed(2)}
        </div>
        {live && (
          <div style={{ fontSize: 13, color: trendColor, fontWeight: 700 }}>
            {live.cvd.trend}
          </div>
        )}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          {live && (
            <span style={{
              padding: '2px 10px', borderRadius: 12, fontSize: 11, fontWeight: 700,
              background: phaseColor(live.session.phase) + '22',
              color: phaseColor(live.session.phase),
              border: `1px solid ${phaseColor(live.session.phase)}44`,
            }}>
              {live.session.phase}
            </span>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11 }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%',
              background: connected ? '#22c55e' : '#ef4444',
              boxShadow: connected ? '0 0 6px #22c55e' : 'none',
              animation: connected ? 'pulse 2s infinite' : 'none',
            }} />
            <span style={{ color: connected ? '#22c55e' : '#ef4444' }}>
              {connected ? 'LIVE' : 'OFFLINE'}
            </span>
            {lastUpdate && (
              <span style={{ color: '#4a5568', marginLeft: 4 }}>
                {lastUpdate.toLocaleTimeString('he-IL')}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Timeframe selector */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
        {(['m3', 'm15', 'm30', 'm60'] as const).map(tf => (
          <button
            key={tf}
            onClick={() => setTimeframe(tf)}
            style={{
              padding: '3px 12px', borderRadius: 6, fontSize: 11, fontWeight: 700,
              cursor: 'pointer', border: 'none',
              background: timeframe === tf ? '#f6c90e' : '#1e2738',
              color: timeframe === tf ? '#0d1117' : '#6b7280',
              transition: 'all 0.15s',
            }}
          >
            {tf.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Main layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 220px', gap: 12 }}>

        {/* Chart */}
        <div style={{ background: '#0d1117', borderRadius: 8, border: '1px solid #1e2738', overflow: 'hidden' }}>
          <div style={{ height: 420 }}>
            <CandleChart
              candles={candles}
              live={live}
              vwap={live?.vwap.value ?? 0}
              levels={live?.levels ?? null}
              profile={live?.profile ?? null}
              session={live?.session ?? null}
            />
          </div>
          {/* Delta bar below chart */}
          {bar && (
            <div style={{ padding: '8px 12px', borderTop: '1px solid #1e2738' }}>
              <div style={{ fontSize: 10, color: '#4a5568', marginBottom: 4 }}>ORDER FLOW — {timeframe.toUpperCase()}</div>
              <DeltaBar buy={bar.buy} sell={bar.sell} delta={bar.delta} />
            </div>
          )}
        </div>

        {/* Right panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>

          {/* VWAP */}
          {live && (
            <div style={{ background: '#111827', borderRadius: 8, border: '1px solid #1e2738', padding: 10 }}>
              <div style={{ fontSize: 10, color: '#4a5568', marginBottom: 6, letterSpacing: 1 }}>VWAP</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#f6c90e', fontFamily: 'monospace' }}>
                {live.vwap.value.toFixed(2)}
              </div>
              <div style={{ fontSize: 11, color: live.vwap.above ? '#26a69a' : '#ef5350', marginTop: 2 }}>
                {live.vwap.above ? '▲ מעל' : '▼ מתחת'} {Math.abs(live.vwap.distance).toFixed(2)} pts
              </div>
              {live.vwap.pullback && (
                <div style={{ fontSize: 10, color: '#f59e0b', marginTop: 3 }}>⚡ PULLBACK</div>
              )}
            </div>
          )}

          {/* Profile */}
          {live && (
            <div style={{ background: '#111827', borderRadius: 8, border: '1px solid #1e2738', padding: 10 }}>
              <div style={{ fontSize: 10, color: '#4a5568', marginBottom: 6, letterSpacing: 1 }}>MARKET PROFILE</div>
              <LevelRow label="VAH" value={live.profile.vah} color="#22c55e" price={price} />
              <LevelRow label="POC" value={live.profile.poc} color="#f97316" price={price} />
              <LevelRow label="tPOC" value={live.profile.tpo_poc} color="#fb923c" price={price} />
              <LevelRow label="VAL" value={live.profile.val} color="#22c55e" price={price} />
              <div style={{ marginTop: 4, fontSize: 10, color: live.profile.in_va ? '#22c55e' : '#ef5350' }}>
                {live.profile.in_va ? '● בתוך Value Area' : '○ מחוץ ל-Value Area'}
              </div>
            </div>
          )}

          {/* Woodi Pivots */}
          {live && (
            <div style={{ background: '#111827', borderRadius: 8, border: '1px solid #1e2738', padding: 10 }}>
              <div style={{ fontSize: 10, color: '#4a5568', marginBottom: 6, letterSpacing: 1 }}>WOODI PIVOTS</div>
              <LevelRow label="R2" value={live.woodi.r2} color="#ef4444" price={price} />
              <LevelRow label="R1" value={live.woodi.r1} color="#f87171" price={price} />
              <LevelRow label="PP" value={live.woodi.pp} color="#94a3b8" price={price} />
              <LevelRow label="S1" value={live.woodi.s1} color="#4ade80" price={price} />
              <LevelRow label="S2" value={live.woodi.s2} color="#22c55e" price={price} />
            </div>
          )}

          {/* Session levels */}
          {live && (
            <div style={{ background: '#111827', borderRadius: 8, border: '1px solid #1e2738', padding: 10 }}>
              <div style={{ fontSize: 10, color: '#4a5568', marginBottom: 6, letterSpacing: 1 }}>SESSION</div>
              <LevelRow label="SH" value={live.session.sh} color="#60a5fa" price={price} />
              <LevelRow label="SL" value={live.session.sl} color="#60a5fa" price={price} />
              {live.levels && <>
                <LevelRow label="PDH" value={live.levels.prev_high} color="#ef4444" price={price} />
                <LevelRow label="PDL" value={live.levels.prev_low} color="#ef4444" price={price} />
                <LevelRow label="DO" value={live.levels.daily_open} color="#60a5fa" price={price} />
              </>}
            </div>
          )}

          {/* CVD */}
          {live && (
            <div style={{ background: '#111827', borderRadius: 8, border: '1px solid #1e2738', padding: 10 }}>
              <div style={{ fontSize: 10, color: '#4a5568', marginBottom: 6, letterSpacing: 1 }}>CVD</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                {[
                  { l: 'Total', v: live.cvd.total },
                  { l: '60m Δ', v: live.cvd.d20 },
                  { l: '15m Δ', v: live.cvd.d5 },
                  { l: 'Bar Δ', v: live.cvd.delta },
                ].map(({ l, v }) => (
                  <div key={l} style={{ textAlign: 'center', padding: '4px 0' }}>
                    <div style={{ fontSize: 9, color: '#4a5568' }}>{l}</div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: v >= 0 ? '#26a69a' : '#ef5350', fontFamily: 'monospace' }}>
                      {v >= 0 ? '+' : ''}{v.toFixed(0)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      </div>

      {/* Order Flow alerts */}
      {live?.order_flow && (
        <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
          {live.order_flow.absorption_bull && (
            <div style={{ padding: '4px 10px', borderRadius: 6, background: '#26a69a22', border: '1px solid #26a69a44', fontSize: 11, color: '#26a69a', fontWeight: 700 }}>
              🛡️ ABSORPTION BULL
            </div>
          )}
          {live.order_flow.liq_sweep && (
            <div style={{ padding: '4px 10px', borderRadius: 6, background: '#f59e0b22', border: '1px solid #f59e0b44', fontSize: 11, color: '#f59e0b', fontWeight: 700 }}>
              🌊 LIQ SWEEP
            </div>
          )}
          {live.order_flow.imbalance_bull > 0 && (
            <div style={{ padding: '4px 10px', borderRadius: 6, background: '#26a69a22', border: '1px solid #26a69a44', fontSize: 11, color: '#26a69a', fontWeight: 700 }}>
              ⬆️ IMBALANCE BULL ×{live.order_flow.imbalance_bull}
            </div>
          )}
          {live.order_flow.imbalance_bear > 0 && (
            <div style={{ padding: '4px 10px', borderRadius: 6, background: '#ef535022', border: '1px solid #ef535044', fontSize: 11, color: '#ef5350', fontWeight: 700 }}>
              ⬇️ IMBALANCE BEAR ×{live.order_flow.imbalance_bear}
            </div>
          )}
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}
