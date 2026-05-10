'use client';
import { useMarketStore } from '../../stores/marketStore';

export function RightSideLabels() {
  const { currentPOC, currentVAH, currentVAL, pdh, pdl, onh, onl, openPrice } = useMarketStore();

  // Colors aligned with spec Section 3.2 (TPO) and 3.4 (static levels)
  const labels = [
    { label: 'POC', value: currentPOC, color: '#e3b341' },
    { label: 'VAH', value: currentVAH, color: '#56d364' },
    { label: 'VAL', value: currentVAL, color: '#f85149' },
    { label: 'PDH', value: pdh, color: '#8b949e' },
    { label: 'PDL', value: pdl, color: '#8b949e' },
    { label: 'ONH', value: onh, color: '#79c0ff' },
    { label: 'ONL', value: onl, color: '#79c0ff' },
    { label: 'OPEN', value: openPrice, color: '#e6edf3' },
  ].filter((l) => l.value !== null);

  if (labels.length === 0) return null;

  return (
    <div className="absolute top-2 right-14 flex flex-col gap-0.5 z-10 pointer-events-none">
      {labels.map((l) => (
        <div
          key={l.label}
          className="flex items-center gap-1 text-[10px] font-mono px-1 rounded"
          style={{ background: 'rgba(13,17,23,0.85)', color: l.color }}
        >
          <span className="opacity-70">{l.label}</span>
          <span>{l.value!.toFixed(2)}</span>
        </div>
      ))}
    </div>
  );
}
