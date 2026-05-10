'use client';

export function OrdersTab() {
  // Placeholder — orders data requires bridge connection not yet available
  return (
    <div className="flex flex-col gap-3 text-xs">
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Pending Orders
        </div>
        <div style={{ color: 'var(--text-muted)' }}>No pending orders</div>
      </div>

      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Filled Today
        </div>
        <div style={{ color: 'var(--text-muted)' }}>No filled orders</div>
      </div>

      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Cancelled / Rejected
        </div>
        <div style={{ color: 'var(--text-muted)' }}>None</div>
      </div>
    </div>
  );
}
