'use client';
import { useMarketStore } from '../../stores/marketStore';

export function RightSideLabels() {
  const { currentPOC, currentVAH, currentVAL, pdh, pdl, onh, onl, openPrice, ibh, ibl } = useMarketStore();

  // Colors per V9_DASHBOARD_LAYOUT_SPEC Section 5 + 7
  const labels = [
    { label: 'POC', value: currentPOC, color: '#F97316' },
    { label: 'VAH', value: currentVAH, color: '#10B981' },
    { label: 'VAL', value: currentVAL, color: '#EF4444' },
    { label: 'PDH', value: pdh, color: '#8b949e' },
    { label: 'PDL', value: pdl, color: '#8b949e' },
    { label: 'ONH', value: onh, color: '#79c0ff' },
    { label: 'ONL', value: onl, color: '#79c0ff' },
    { label: 'OPEN', value: openPrice, color: '#e6edf3' },
    { label: 'IBH', value: ibh, color: '#FACC15' },
    { label: 'IBL', value: ibl, color: '#FACC15' },
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
