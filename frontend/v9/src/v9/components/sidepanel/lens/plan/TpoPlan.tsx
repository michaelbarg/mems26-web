'use client';
import { COLORS } from '../../../../design/tokens';
import { SystemPlanLive } from './systemPlanLive';

function TpoPlanSpec() {
  return (
    <div style={{ fontSize: 11, color: COLORS.textSecondary, lineHeight: 1.6 }}>
      <p>POC, VAH, VAL, IB tracker, HVN/LVN, volume cluster. Observer — feeds Day Type + Layer 0.</p>
    </div>
  );
}

export function TpoPlan() {
  return <SystemPlanLive systemId={5} spec={<TpoPlanSpec />} />;
}
