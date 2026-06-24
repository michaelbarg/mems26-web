'use client';
// DirectionStrip — the LONG/SHORT trade signal from the LSMA+CVD engine (DIRECTION_LSMA_VETO),
// shown below the chart with the breakdown of WHAT each input shows (price vs LSMA line, CVD slope).
// DISPLAY ONLY — mirrors the live gate's direction (direction_now); does not itself fire/trade.
import { useDirectionNow } from '../../hooks/useDirectionNow';

const DIR: Record<string, { label: string; bg: string; fg: string }> = {
  UP: { label: 'LONG', bg: 'rgba(38,166,154,0.18)', fg: '#26a69a' },
  DOWN: { label: 'SHORT', bg: 'rgba(239,83,80,0.18)', fg: '#ef5350' },
  NEUTRAL: { label: 'NEUTRAL', bg: 'rgba(120,123,134,0.14)', fg: '#9aa0aa' },
};

function Chip({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <span
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.09)',
        borderRadius: 4, padding: '1px 7px', fontSize: 11,
      }}
    >
      <span style={{ color: '#8b949e' }}>{label}</span>
      <b style={{ color }}>{value}</b>
    </span>
  );
}

export function DirectionStrip() {
  const d = useDirectionNow();
  const dir = (d?.dir as string) || 'NEUTRAL';
  const m = DIR[dir] || DIR.NEUTRAL;

  // LSMA: which side of the line price is on (the trend the LSMA defines)
  const side = d?.lsma_side;
  const lsma =
    side == null ? { v: '—', c: '#9aa0aa' }
      : side > 0 ? { v: '▲ מעל הקו', c: '#26a69a' }
        : { v: '▼ מתחת לקו', c: '#ef5350' };
  // CVD: 3-bar slope (the volume push that can veto the LSMA side)
  const cs = d?.cvd_slope;
  const cvd =
    cs == null ? { v: '—', c: '#9aa0aa' }
      : cs > 0 ? { v: '▲ עולה', c: '#26a69a' }
        : cs < 0 ? { v: '▼ יורד', c: '#ef5350' }
          : { v: '— שטוח', c: '#9aa0aa' };

  return (
    <div
      dir="rtl"
      style={{
        display: 'flex', alignItems: 'center', gap: 10, padding: '5px 12px',
        background: m.bg, borderTop: '1px solid rgba(255,255,255,0.06)',
        fontSize: 12, minHeight: 30,
      }}
      title="סימן LONG/SHORT ממנוע LSMA+CVD (LSMA מוביל, CVD מעַטֵּו) · תצוגה בלבד, משקף את כיוון-הגייט"
    >
      <span style={{ width: 9, height: 9, borderRadius: '50%', background: m.fg, flex: '0 0 auto' }} />
      <b style={{ fontSize: 14, color: m.fg, letterSpacing: '0.04em' }}>{m.label}</b>
      <Chip label="LSMA" value={lsma.v} color={lsma.c} />
      <Chip label="CVD" value={cvd.v} color={cvd.c} />
      <span style={{ color: '#8b949e', fontSize: 11 }}>{d?.reason || '—'}</span>
      {d && d.poc != null && (
        <span style={{ color: '#6e7681', marginInlineStart: 'auto', fontSize: 11 }}>
          IB {d.ib_low}–{d.ib_high} · POC {d.poc} · {d.n_bars} ברים
        </span>
      )}
    </div>
  );
}
