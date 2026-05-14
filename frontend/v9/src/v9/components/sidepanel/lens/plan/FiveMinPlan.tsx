'use client';
import { COLORS } from '../../../../design/tokens';

export function FiveMinPlan() {
  return (
    <div style={{ padding: 10, fontSize: 11, color: COLORS.textSecondary, lineHeight: 1.6 }}>
      <div style={{ fontWeight: 700, color: COLORS.textPrimary, marginBottom: 6 }}>System 2 — 5-Min Pattern Detector</div>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>Detects:</div>
      <p>Two 4-bar patterns on 5-min candles per Constitution V3 Layer 1 T1.</p>
      <div style={{ fontWeight: 600, marginTop: 8, marginBottom: 4 }}>Patterns:</div>
      <ul style={{ paddingLeft: 16, margin: 0 }}>
        <li><b>Reactive</b> — Seller exhaustion → buyer entry (or mirror). Bar 2 = 90% volume drop. COT &gt; AMT.</li>
        <li><b>Initiative</b> — Fresh expansion (6-7 ticks) → test → join → confirm. COT &lt; AMT (no counter pressure).</li>
      </ul>
      <div style={{ fontWeight: 600, marginTop: 8, marginBottom: 4 }}>Sizing (per-system internal):</div>
      <ul style={{ paddingLeft: 16, margin: 0 }}>
        <li><b>Full (3)</b> — 4 bars + strong flow (1.2×) + at POC</li>
        <li><b>Half (2)</b> — 3+ bars + flow ok + near POC</li>
        <li><b>Reject</b> — Immature pattern / wrong flow / far from POC</li>
      </ul>
      <div style={{ fontWeight: 600, marginTop: 8, marginBottom: 4 }}>Rejection:</div>
      <p>Bars &lt; 3, COT/AMT misaligned, location far from POC volume, Layer 0 = SEARCHING.</p>
    </div>
  );
}
