import type { Trade, SystemAgreement } from '../../types';

const CELL = 'text-xs font-mono';

export function cellClass(): string {
  return CELL;
}

export function fmtPrice(v: number | null | undefined, decimals = 2): string {
  return v != null && Number.isFinite(v) ? v.toFixed(decimals) : '\u2014';
}

export function pnlCell(t: Trade): { value: string; sub: string } {
  if (t.pnl_usd == null) return { value: '\u2014', sub: '' };
  const value = `${t.pnl_usd >= 0 ? '+' : ''}$${t.pnl_usd.toFixed(2)}`;
  const sub =
    t.pnl_mode === 'partial'
      ? `partial${t.pnl_r != null ? ` ${t.pnl_r.toFixed(2)}R` : ''}`
      : t.pnl_r != null
        ? `${t.pnl_r.toFixed(2)}R`
        : t.state ?? '';
  return { value, sub };
}

export function contractsPnlLine(t: Trade): string {
  if (!t.contracts_pnl?.length) return '';
  return t.contracts_pnl
    .map((c) => `${c.id}${c.status === 'HIT' ? '\u2713' : '\u00b7'} $${c.pnl_usd.toFixed(0)}`)
    .join(' ');
}

export function contractHits(t: Trade): string {
  const mark = (hit?: boolean) => (hit ? '\u2713' : '\u00b7');
  if (t.t1 == null && t.t2 == null && t.t3 == null) return '\u2014';
  return `C1${mark(t.t1_hit)} C2${mark(t.t2_hit)} C3${mark(t.t3_hit)}`;
}

export function systemsAgreementLine(systems?: SystemAgreement[] | null): string {
  if (!systems?.length) return '\u2014';
  return systems
    .map((s) => {
      const mark = s.agree === true ? '\u2713' : s.agree === false ? '\u2717' : '\u00b7';
      const fire = s.is_firing ? '*' : '';
      return `S${s.id}${fire}${mark}`;
    })
    .join(' ');
}

/** Entry → stop(s) → targets → exit; same font size as rest of row. */
/** Hi/Lo during trade, MFE/MAE, distance to T1 (from 5m bars). */
export function excursionLine(t: Trade): string {
  if (t.price_high == null && t.price_low == null && t.mfe_pts == null) return '';
  const parts: string[] = [];
  if (t.price_high != null && t.price_low != null) {
    parts.push(`Hi ${fmtPrice(t.price_high)} Lo ${fmtPrice(t.price_low)}`);
  }
  if (t.mfe_pts != null || t.mae_pts != null) {
    parts.push(`MFE ${t.mfe_pts?.toFixed(1) ?? '\u2014'} MAE ${t.mae_pts?.toFixed(1) ?? '\u2014'}pt`);
  }
  if (t.t1 != null && (t.t1_closest_pts != null || t.t1_reached)) {
    if (t.t1_reached || t.t1_closest_pts === 0) {
      parts.push('T1 hit');
    } else if (t.t1_closest_pts != null) {
      parts.push(`T1 ${t.t1_closest_pts.toFixed(2)}pt away`);
    }
    if (t.t1_at_mfe_pts != null && t.t1_at_mfe_pts > 0 && !t.t1_reached) {
      parts.push(`@MFE ${t.t1_at_mfe_pts.toFixed(2)}pt to T1`);
    }
  }
  return parts.join(' \u00b7 ');
}

export function tradePathLine(t: Trade): string {
  const parts: string[] = [];
  parts.push(`IN ${fmtPrice(t.entry_price)}`);
  const st0 = t.stop_initial ?? t.stop;
  if (st0 != null && t.stop != null && Math.abs(st0 - t.stop) >= 0.01) {
    parts.push(`ST ${fmtPrice(st0)}\u2192${fmtPrice(t.stop)}${t.stop_note === 'BE@entry' ? ' BE' : ''}`);
  } else if (t.stop != null) {
    const tag = t.stop_note === 'BE@entry' ? ' BE' : '';
    parts.push(`ST ${fmtPrice(t.stop)}${tag}`);
  }
  if (t.stop_issue === 'T1_NO_BE') parts.push('\u26a0T1-no-BE');
  if (t.t1 != null) parts.push(`T1 ${fmtPrice(t.t1)}${t.t1_hit ? '\u2713' : ''}`);
  if (t.t2 != null) parts.push(`T2 ${fmtPrice(t.t2)}${t.t2_hit ? '\u2713' : ''}`);
  if (t.t3 != null && t.t3 > 0) parts.push(`T3 ${fmtPrice(t.t3)}${t.t3_hit ? '\u2713' : ''}`);
  if (t.exit_price != null || t.exit_reason) {
    parts.push(`OUT ${fmtPrice(t.exit_price)} ${t.exit_reason ?? ''}`.trim());
  }
  return parts.join(' \u2192 ');
}
