'use client';

interface Entry {
  action: string;
  created_at?: string;
  old_value?: any;
  new_value?: any;
}

const DOT: Record<string, { color: string; label: string }> = {
  T1_HIT:    { color: '#22c55e', label: 'T1' },
  SMART_BE:  { color: '#3b82f6', label: 'BE\u21a6' },
  T2_HIT:    { color: '#22c55e', label: 'T2' },
  STOP_HIT:  { color: '#ef4444', label: 'Stop' },
  TIME_STOP: { color: '#eab308', label: 'Time' },
};

export default function MgmtTimeline({ entries }: { entries: Entry[] }) {
  if (!entries || entries.length === 0) {
    return <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>אין לוג ניהול</span>;
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 0, position: 'relative', padding: '4px 0' }}>
      {entries.map((e, i) => {
        const cfg = DOT[e.action] ?? { color: '#6b7280', label: e.action };
        const isLast = i === entries.length - 1;
        return (
          <div key={i} style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 28 }}>
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  backgroundColor: cfg.color,
                  flexShrink: 0,
                }}
                title={`${e.action}${e.created_at ? ` @ ${e.created_at}` : ''}`}
              />
              <span style={{ fontSize: 9, color: cfg.color, marginTop: 2, whiteSpace: 'nowrap' }}>
                {cfg.label}
              </span>
            </div>
            {!isLast && (
              <div style={{ width: 18, height: 2, backgroundColor: 'var(--border, #333)', flexShrink: 0 }} />
            )}
          </div>
        );
      })}
    </div>
  );
}
