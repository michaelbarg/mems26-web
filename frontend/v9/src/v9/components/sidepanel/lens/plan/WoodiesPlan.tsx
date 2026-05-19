'use client';
import { COLORS } from '../../../../design/tokens';
import { SystemPlanLive } from './systemPlanLive';

function WoodiesPlanSpec() {
  return (
    <div style={{ fontSize: 11, color: COLORS.textSecondary, lineHeight: 1.6 }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>8 Patterns:</div>
      <ul style={{ paddingLeft: 16, margin: 0 }}>
        <li><b>ZLR</b> — Zero Line Reject</li>
        <li><b>TLB</b> — Trend Line Break</li>
        <li><b>TT</b> — Turbo Trend</li>
        <li><b>GB100</b> — Ghost Bar at 100</li>
        <li><b>Vegas</b> · <b>Ghost</b> · <b>FAMIR</b> · <b>HTLB</b></li>
      </ul>
      <p style={{ marginTop: 8 }}>21-stage pre-fire tree (A1–A7) visible in TO FIRE when bars process.</p>
    </div>
  );
}

export function WoodiesPlan() {
  return <SystemPlanLive systemId={4} spec={<WoodiesPlanSpec />} />;
}
