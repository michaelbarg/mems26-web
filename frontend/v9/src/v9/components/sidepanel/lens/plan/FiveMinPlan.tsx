'use client';
import { COLORS } from '../../../../design/tokens';
import { AllPatternsPlan } from './AllPatternsPlan';
import { SystemPlanLive } from './systemPlanLive';

function FiveMinPlanSpec() {
  return (
    <div style={{ fontSize: 11, color: COLORS.textSecondary, lineHeight: 1.6 }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>Patterns:</div>
      <ul style={{ paddingLeft: 16, margin: 0 }}>
        <li><b>Reactive</b> — exhaustion → entry, COT &gt; AMT</li>
        <li><b>Initiative</b> — expansion → join, COT &lt; AMT</li>
      </ul>
      <p style={{ marginTop: 8 }}>Sizing: Full (3) / Half (2) / Reject by bars, flow, POC location.</p>
    </div>
  );
}

export function FiveMinPlan() {
  return (
    <>
      <AllPatternsPlan systemId={2} />
      <SystemPlanLive systemId={2} spec={<FiveMinPlanSpec />} />
    </>
  );
}
