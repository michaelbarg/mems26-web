'use client';
import { COLORS } from '../../../../design/tokens';
import { SystemPlanLive } from './systemPlanLive';

function KillzonePlanSpec() {
  return (
    <div style={{ fontSize: 11, color: COLORS.textSecondary, lineHeight: 1.6 }}>
      <p>Session zones: Pre-Market · Cash Open · First Hour · Cash Hours · Close · After Hours.</p>
      <p style={{ marginTop: 8 }}>Gate OPEN during Cash Hours only.</p>
    </div>
  );
}

export function KillzonePlan() {
  return <SystemPlanLive systemId={6} spec={<KillzonePlanSpec />} />;
}
