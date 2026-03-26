'use client';

interface CVDPanelProps {
  cvd: {
    total?: number;
    d20?: number;
    d5?: number;
    trend?: string;
    buy_vol?: number;
    sell_vol?: number;
    delta?: number;
  };
  bar: {
    buy?: number;
    sell?: number;
    delta?: number;
    vol?: number;
  };
}

export default function CVDPanel({ cvd, bar }: CVDPanelProps) {
  const trend = cvd?.trend ?? '—';
  const trendColor = trend === 'BULLISH' ? '#22c55e' : trend === 'BEARISH' ? '#ef5350' : '#f59e0b';
  const buy = bar?.buy ?? 0;
  const sell = bar?.sell ?? 0;
  const total = buy + sell || 1;
  const buyPct = Math.round((buy / total) * 100);
  const delta = bar?.delta ?? 0;
  const isPos = delta >= 0;

  return (
    <div className="bg-[#111118] rounded-lg border border-[#1e1e2e] px-3 py-2 text-xs">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] text-gray-500 tracking-widest font-bold">CVD</span>
        <span style={{ color: trendColor }} className="font-bold text-[10px]">{trend}</span>
      </div>

      {/* Buy/Sell bar */}
      <div className="mb-2">
        <div className="flex justify-between text-[9px] mb-1">
          <span style={{ color: '#22c55e' }}>B {Math.round(buy).toLocaleString()}</span>
          <span style={{ color: '#6b7280' }}>{buyPct}%</span>
          <span style={{ color: '#ef5350' }}>S {Math.round(sell).toLocaleString()}</span>
        </div>
        <div className="h-2 rounded-full overflow-hidden flex" style={{ background: '#ef5350' }}>
          <div style={{ width: `${buyPct}%`, background: '#22c55e', borderRadius: '4px 0 0 4px', transition: 'width .4s' }} />
        </div>
      </div>

      {/* Delta */}
      <div className="flex justify-between items-center">
        <span className="text-gray-500">Delta</span>
        <span style={{ color: isPos ? '#22c55e' : '#ef5350', fontFamily: 'monospace', fontWeight: 700 }}>
          {isPos ? '+' : ''}{Math.round(delta).toLocaleString()}
        </span>
      </div>

      {/* CVD totals */}
      <div className="grid grid-cols-3 gap-1 mt-2 pt-2 border-t border-[#1e1e2e]">
        {[
          { label: 'Total', val: cvd?.total },
          { label: '60m Δ', val: cvd?.d20 },
          { label: '15m Δ', val: cvd?.d5 },
        ].map(({ label, val }) => (
          <div key={label} className="text-center">
            <div className="text-[9px] text-gray-600">{label}</div>
            <div style={{ color: (val ?? 0) >= 0 ? '#22c55e' : '#ef5350', fontFamily: 'monospace', fontSize: 10, fontWeight: 700 }}>
              {val !== undefined ? ((val >= 0 ? '+' : '') + Math.round(val).toLocaleString()) : '—'}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
