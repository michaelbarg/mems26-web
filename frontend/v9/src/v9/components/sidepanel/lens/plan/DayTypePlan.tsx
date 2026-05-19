'use client';
import { COLORS } from '../../../../design/tokens';
import { SystemPlanLive } from './systemPlanLive';

function DayTypePlanSpec() {
  return (
    <div style={{ fontSize: 11, color: COLORS.textSecondary, lineHeight: 1.6 }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>6 Day Types:</div>
      <ul style={{ paddingLeft: 16, margin: 0 }}>
        <li>TRD · TDD · VAR · NEU · NOR · NTR</li>
      </ul>
      <p style={{ marginTop: 8 }}>Locks at IB close + 5 min (10:35 ET). Does not fire trades.</p>
    </div>
  );
}

export function DayTypePlan() {
  return <SystemPlanLive systemId={1} spec={<DayTypePlanSpec />} />;
}
