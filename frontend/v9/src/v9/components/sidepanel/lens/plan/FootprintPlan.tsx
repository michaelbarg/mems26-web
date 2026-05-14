'use client';
import { COLORS } from '../../../../design/tokens';

export function FootprintPlan() {
  return (
    <div style={{ padding: 10, fontSize: 11, color: COLORS.textSecondary, lineHeight: 1.6 }}>
      <div style={{ fontWeight: 700, color: COLORS.textPrimary, marginBottom: 6 }}>System 3 — Footprint Engine (T3)</div>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>Detects:</div>
      <p>4 order flow signals from tick reversal bars per Constitution V3 Layer 1 T3.</p>
      <div style={{ fontWeight: 600, marginTop: 8, marginBottom: 4 }}>Signals:</div>
      <ul style={{ paddingLeft: 16, margin: 0 }}>
        <li><b>Absorption</b> — Strong counter-volume at extreme that fails to push price</li>
        <li><b>Stacked Imbalance</b> — 3+ consecutive cells with ratio &gt; 3.0×</li>
        <li><b>Sweep-Return</b> — Liquidity sweep through extreme → return inside range</li>
        <li><b>Exhaustion</b> — Strong directional bar with diminishing volume (&lt; 0.6× avg)</li>
      </ul>
      <div style={{ fontWeight: 600, marginTop: 8, marginBottom: 4 }}>Also provides:</div>
      <p>COT (cumulative delta), AMT (90-min avg), dominance, aggressive flow classification, initiative/reactive tagging.</p>
      <div style={{ fontWeight: 600, marginTop: 8, marginBottom: 4 }}>Sizing (per-system internal):</div>
      <p>Based on signal strength + evidence quality. NOT composite with other systems.</p>
    </div>
  );
}
