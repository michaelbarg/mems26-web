'use client';
import { COLORS } from '../../../../design/tokens';
import { AllPatternsPlan } from './AllPatternsPlan';
import { SystemPlanLive } from './systemPlanLive';

function FiveMinPlanSpec() {
  return (
    <div style={{ fontSize: 11, color: COLORS.textSecondary, lineHeight: 1.6 }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>Patterns:</div>
      {/* 07-17 fix: COT/AMT אינו נדרש בפועל — S2 ⟂ S3 (מייקל 06-08, S2_REQUIRE_COT_AMT=OFF) */}
      <ul style={{ paddingLeft: 16, margin: 0 }}>
        <li><b>Reactive</b> — exhaustion → 4-bar confirmation entry</li>
        <li><b>Initiative</b> — expansion → 4-bar join</li>
      </ul>
      <p style={{ margin: '4px 0 0' }}>COT/AMT not required (S2 ⟂ S3); CVD confirmation ON.</p>
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
