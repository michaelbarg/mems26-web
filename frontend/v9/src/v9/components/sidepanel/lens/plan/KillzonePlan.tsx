'use client';
import { COLORS } from '../../../../design/tokens';

export function KillzonePlan() {
  return (
    <div style={{ padding: 10, fontSize: 11, color: COLORS.textSecondary, lineHeight: 1.6 }}>
      <div style={{ fontWeight: 700, color: COLORS.textPrimary, marginBottom: 6 }}>System 6 — Killzone Gate</div>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>Provides:</div>
      <p>Session phase classification and time-based gating per Constitution V3.</p>
      <div style={{ fontWeight: 600, marginTop: 8, marginBottom: 4 }}>Zones:</div>
      <ul style={{ paddingLeft: 16, margin: 0 }}>
        <li><b>Pre-Market</b> — 04:00-09:30 ET (observing only)</li>
        <li><b>Cash Open</b> — 09:30-09:35 ET (high volatility, gate closed)</li>
        <li><b>First Hour</b> — 09:35-10:30 ET (IB building, tactical mode)</li>
        <li><b>Cash Hours</b> — 10:30-15:45 ET (primary trading window)</li>
        <li><b>Cash Close</b> — 15:45-16:00 ET (gate closed, wind down)</li>
        <li><b>After Hours</b> — 16:00+ ET (observing only)</li>
      </ul>
      <div style={{ fontWeight: 600, marginTop: 8, marginBottom: 4 }}>Gate logic:</div>
      <p>OPEN during Cash Hours only. Countdown badge shows minutes remaining in current zone.</p>
      <div style={{ fontWeight: 600, marginTop: 8, marginBottom: 4 }}>Does NOT fire trades.</div>
      <p style={{ color: COLORS.textTertiary }}>Gating system — blocks/allows other systems' firing based on session phase.</p>
    </div>
  );
}
