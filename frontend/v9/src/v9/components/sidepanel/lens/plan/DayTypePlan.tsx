'use client';
import { COLORS } from '../../../../design/tokens';

export function DayTypePlan() {
  return (
    <div style={{ padding: 10, fontSize: 11, color: COLORS.textSecondary, lineHeight: 1.6 }}>
      <div style={{ fontWeight: 700, color: COLORS.textPrimary, marginBottom: 6 }}>System 1 — Day Type Classifier</div>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>Detects:</div>
      <p>Classifies the trading day into one of 6 types based on IB (Initial Balance) width and post-IB extension. Per Constitution V3 Layer 2.</p>
      <div style={{ fontWeight: 600, marginTop: 8, marginBottom: 4 }}>6 Day Types:</div>
      <ul style={{ paddingLeft: 16, margin: 0 }}>
        <li><b>Trend Normal (TRD)</b> — IB breached + extension &gt; 1.5× IB range</li>
        <li><b>Trend DD (TDD)</b> — Open at extreme + immediate sustained move</li>
        <li><b>Variation (VAR)</b> — IB breached + extension &lt; 1.5× (~70% of days)</li>
        <li><b>Neutral (NEU)</b> — Both sides of IB breached</li>
        <li><b>Normal (NOR)</b> — IB holds full session</li>
        <li><b>Nontrend (NTR)</b> — Choppy, no clear structure</li>
      </ul>
      <div style={{ fontWeight: 600, marginTop: 8, marginBottom: 4 }}>Fires at:</div>
      <p>IB close + 5 min buffer (10:35 ET). Classification locked for session.</p>
      <div style={{ fontWeight: 600, marginTop: 8, marginBottom: 4 }}>Does NOT fire trades.</div>
      <p style={{ color: COLORS.textTertiary }}>Observing system — provides context for S2/S3/S4 firing decisions.</p>
    </div>
  );
}
