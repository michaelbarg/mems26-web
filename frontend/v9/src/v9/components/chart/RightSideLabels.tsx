'use client';
import { useMarketStore } from '../../stores/marketStore';

export function RightSideLabels() {
  const { currentPOC, currentVAH, currentVAL, pdh, pdl, onh, onl, openPrice } = useMarketStore();

  const labels = [
    { label: 'POC', value: currentPOC, color: '#79c0ff' },
    { label: 'VAH', value: currentVAH, color: '#79c0ff' },
    { label: 'VAL', value: currentVAL, color: '#79c0ff' },
    { label: 'PDH', value: pdh, color: '#f85149' },
    { label: 'PDL', value: pdl, color: '#f85149' },
    { label: 'ONH', value: onh, color: '#d2a8ff' },
    { label: 'ONL', value: onl, color: '#d2a8ff' },
    { label: 'OPEN', value: openPrice, color: '#fb950b' },
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
