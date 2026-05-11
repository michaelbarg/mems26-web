'use client';
import { useMemo } from 'react';
import { useSystemStore } from '../../../stores/systemStore';
import { useMarketStore } from '../../../stores/marketStore';

export function DecisionsTab() {
  const activeSignals = useSystemStore((s) => s.activeSignals);
  const market = useMarketStore();

  // Killzone gate (System 6)
  const killzoneVeto = useMemo(() => {
    const sig = activeSignals[6];
    const gateOpen = (sig?.payload?.gate_open as boolean) ?? false;
    const reason = (sig?.payload?.block_reason as string) ?? '';
    const phase = (sig?.payload?.session_phase as string) ?? '--';
    return { gateOpen, reason, phase };
  }, [activeSignals]);

  // Veto checks
  const vetoChecks = useMemo(() => {
    const checks = [
      {
        label: 'Killzone Gate',
        pass: killzoneVeto.gateOpen,
        detail: killzoneVeto.gateOpen ? killzoneVeto.phase : killzoneVeto.reason || 'Gate closed',
      },
      {
        label: 'IB Formed',
        pass: market.ibh !== null && market.ibl !== null,
        detail: market.ibh !== null ? `IBH: ${market.ibh?.toFixed(2)}` : 'Waiting for IB',
      },
      {
        label: 'Data Fresh',
        pass: market.bars5min.length > 0,
        detail: market.bars5min.length > 0 ? `${market.bars5min.length} bars` : 'No data',
      },
    ];

    // Firing systems check
    const firingActive = [activeSignals[1], activeSignals[2], activeSignals[4]].filter(Boolean);
    checks.push({
      label: 'Firing System',
      pass: firingActive.length > 0,
      detail: firingActive.length > 0
        ? `${firingActive.length}/3 active`
        : 'No firing signals',
    });

    return checks;
  }, [killzoneVeto, market, activeSignals]);

  const allPass = vetoChecks.every((c) => c.pass);

  // Setup tier (simplified — real tier comes from backend)
  const tier = useMemo(() => {
    const passCount = vetoChecks.filter((c) => c.pass).length;
    if (passCount === vetoChecks.length) return { label: 'T1', color: 'var(--green)' };
    if (passCount >= vetoChecks.length - 1) return { label: 'T2', color: '#FACC15' };
    return { label: 'T3', color: 'var(--red)' };
  }, [vetoChecks]);

  return (
    <div className="flex flex-col gap-3 text-xs">
      {/* Overall Status */}
      <div
        className="p-2 rounded border text-center"
        style={{
          background: allPass ? '#56d36415' : '#f8514915',
          borderColor: allPass ? 'var(--green)' : 'var(--red)',
        }}
      >
        <div className="text-lg font-bold" style={{ color: allPass ? 'var(--green)' : 'var(--red)' }}>
          {allPass ? 'TRADE ALLOWED' : 'BLOCKED'}
        </div>
        <div style={{ color: 'var(--text-secondary)' }}>
          Tier: <span style={{ color: tier.color, fontWeight: 700 }}>{tier.label}</span>
        </div>
      </div>

      {/* Veto Checklist */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Veto Checks
        </div>
        <div className="flex flex-col gap-1">
          {vetoChecks.map((check) => (
            <div key={check.label} className="flex justify-between items-center">
              <span className="flex items-center gap-1">
                <span
                  className="w-2 h-2 rounded-full inline-block"
                  style={{ background: check.pass ? 'var(--green)' : 'var(--red)' }}
                />
                <span style={{ color: 'var(--text-secondary)' }}>{check.label}</span>
              </span>
              <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>{check.detail}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Tier Explanation */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Tier Classification
        </div>
        <div className="flex flex-col gap-0.5" style={{ color: 'var(--text-secondary)' }}>
          <div>
            <span style={{ color: 'var(--green)', fontWeight: 700 }}>T1</span> All checks pass
          </div>
          <div>
            <span style={{ color: '#FACC15', fontWeight: 700 }}>T2</span> 1 soft veto
          </div>
          <div>
            <span style={{ color: 'var(--red)', fontWeight: 700 }}>T3</span> Hard veto active
          </div>
        </div>
      </div>
    </div>
  );
}
