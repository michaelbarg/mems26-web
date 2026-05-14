'use client';
import { COLORS } from '../../../../design/tokens';

export function TpoPlan() {
  return (
    <div style={{ padding: 10, fontSize: 11, color: COLORS.textSecondary, lineHeight: 1.6 }}>
      <div style={{ fontWeight: 700, color: COLORS.textPrimary, marginBottom: 6 }}>System 5 — TPO Profile</div>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>Provides:</div>
      <p>Market Profile (TPO) with POC, VAH, VAL, IB tracking, and volume analysis per Constitution V3.</p>
      <div style={{ fontWeight: 600, marginTop: 8, marginBottom: 4 }}>Key metrics:</div>
      <ul style={{ paddingLeft: 16, margin: 0 }}>
        <li><b>POC Migration</b> — direction (UP/DOWN/STUCK) + magnitude + stuck minutes</li>
        <li><b>HVN/LVN Zones</b> — high/low volume nodes with PRIMARY/SECONDARY classification</li>
        <li><b>Volume Cluster</b> — top 3 price levels by volume + weighted center</li>
        <li><b>IB Tracker</b> — IB H/L/width/class (NARROW/MEDIUM/WIDE) + lock time</li>
        <li><b>Profile Shape</b> — b/p/D/P/B distribution analysis</li>
      </ul>
      <div style={{ fontWeight: 600, marginTop: 8, marginBottom: 4 }}>Does NOT fire trades.</div>
      <p style={{ color: COLORS.textTertiary }}>Observing system — provides structural context. POC migration feeds Day Type + Layer 0 chop detection.</p>
    </div>
  );
}
