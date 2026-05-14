'use client';
import { COLORS } from '../../../../design/tokens';

export function WoodiesPlan() {
  return (
    <div style={{ padding: 10, fontSize: 11, color: COLORS.textSecondary, lineHeight: 1.6 }}>
      <div style={{ fontWeight: 700, color: COLORS.textPrimary, marginBottom: 6 }}>System 4 — Woodies CCI</div>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>Detects:</div>
      <p>8 CCI patterns on 30-min bars per Constitution V3 D-048 + V2 D.10-D.17.</p>
      <div style={{ fontWeight: 600, marginTop: 8, marginBottom: 4 }}>8 Patterns:</div>
      <ul style={{ paddingLeft: 16, margin: 0 }}>
        <li><b>ZLR</b> — Zero Line Reject (CCI bounces off zero)</li>
        <li><b>TLB</b> — Trend Line Break</li>
        <li><b>TT</b> — Turbo Trend (CCI &gt; 100 sustained)</li>
        <li><b>GB100</b> — Ghost Bar at 100 level</li>
        <li><b>Vegas</b> — Vegas trade pattern</li>
        <li><b>Ghost</b> — Ghost divergence</li>
        <li><b>FAMIR</b> — Failure at Moving average in Range</li>
        <li><b>HTLB</b> — Horizontal Trend Line Break</li>
      </ul>
      <div style={{ fontWeight: 600, marginTop: 8, marginBottom: 4 }}>Requires:</div>
      <p>CCI14 computation needs ≥14 bars in buffer. Hydrates from DB on restart (319K historical bars).</p>
    </div>
  );
}
