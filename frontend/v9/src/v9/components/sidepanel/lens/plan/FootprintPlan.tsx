'use client';
import { COLORS } from '../../../../design/tokens';
import { SystemPlanLive } from './systemPlanLive';

function FootprintPlanSpec() {
  return (
    <div style={{ fontSize: 11, color: COLORS.textSecondary, lineHeight: 1.6 }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>Signals:</div>
      <ul style={{ paddingLeft: 16, margin: 0 }}>
        <li>Absorption · Stacked Imbalance · Sweep-Return · Exhaustion</li>
      </ul>
      <p style={{ marginTop: 8 }}>Provides COT, AMT, dominance for S2 sizing.</p>
    </div>
  );
}

export function FootprintPlan() {
  return <SystemPlanLive systemId={3} spec={<FootprintPlanSpec />} />;
}
