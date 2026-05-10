'use client';

export function PredActualTab() {
  // Placeholder — Phase 7.3 implementation per spec
  return (
    <div className="flex flex-col gap-3 text-xs">
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Predicted vs Actual
        </div>
        <div style={{ color: 'var(--text-muted)' }}>
          Phase 7.3: Per-trade prediction accuracy tracking.
        </div>
      </div>

      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Per System Accuracy
        </div>
        <div className="flex flex-col gap-1" style={{ color: 'var(--text-muted)' }}>
          <div className="flex justify-between">
            <span>S1 Day Type</span>
            <span>--</span>
          </div>
          <div className="flex justify-between">
            <span>S2 5-Min</span>
            <span>--</span>
          </div>
          <div className="flex justify-between">
            <span>S4 Woodies</span>
            <span>--</span>
          </div>
        </div>
      </div>

      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Recurring Error Types
        </div>
        <div style={{ color: 'var(--text-muted)' }}>
          No data yet — requires closed trades with predictions
        </div>
      </div>
    </div>
  );
}
