'use client';
import { useMemo } from 'react';
import { useSystemStore } from '../../../stores/systemStore';

export function SetupsTab() {
  const signals = useSystemStore((s) => s.signals);
  const activeSignals = useSystemStore((s) => s.activeSignals);

  const setups = useMemo(() => {
    const firingSignals = signals.filter(
      (s) => [1, 2, 4].includes(s.system_id) && s.classification
    );
    const building = firingSignals.filter((s) => s.payload?.status === 'building');
    const live = firingSignals.filter((s) => s.payload?.status === 'live' || s.confidence !== null);
    return { building, live, total: firingSignals.length };
  }, [signals]);

  // Block reason from killzone
  const blockReason = useMemo(() => {
    const kz = activeSignals[6];
    if (!kz) return null;
    if (kz.payload?.gate_open === false) {
      return (kz.payload?.block_reason as string) ?? 'Killzone gate closed';
    }
    return null;
  }, [activeSignals]);

  return (
    <div className="flex flex-col gap-3 text-xs">
      {/* Alert banner */}
      {setups.building.length > 0 && (
        <div
          className="p-2 rounded border text-center font-bold"
          style={{ background: '#FACC1520', borderColor: '#FACC15', color: '#FACC15' }}
        >
          {setups.building.length} Setup(s) Building
        </div>
      )}

      {/* Building setups */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Building Now
        </div>
        {setups.building.length === 0 ? (
          <div style={{ color: 'var(--text-muted)' }}>No setups building</div>
        ) : (
          setups.building.map((s) => (
            <div key={s.id} className="py-0.5" style={{ color: 'var(--text-secondary)' }}>
              S{s.system_id}: {s.classification}
            </div>
          ))
        )}
      </div>

      {/* Live setups */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Live Setups: {setups.live.length}
        </div>
        {setups.live.length === 0 ? (
          <div style={{ color: 'var(--text-muted)' }}>No active setups</div>
        ) : (
          setups.live.map((s) => (
            <div key={s.id} className="py-0.5" style={{ color: 'var(--text-secondary)' }}>
              S{s.system_id}: {s.classification} ({((s.confidence ?? 0) * 10).toFixed(0)}/10)
            </div>
          ))
        )}
      </div>

      {/* Block reason */}
      {blockReason && (
        <div
          className="p-2 rounded border"
          style={{ background: '#EF444420', borderColor: 'var(--red)', color: 'var(--red)' }}
        >
          Blocked: {blockReason}
        </div>
      )}
    </div>
  );
}
