/**
 * Trade time formatting helpers — keeps every trade surface aligned on
 * the same dual-timezone format (NY trading session + Israel local).
 *
 * Why: MEMS26 runs on NY market hours, but Michael trades from Israel —
 * each trade row should answer both "when in the session?" and "when in
 * my day?" without forcing a mental conversion.
 */

const ET_TZ = 'America/New_York';
const IL_TZ = 'Asia/Jerusalem';

const TIME_FMT: Intl.DateTimeFormatOptions = {
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
};

const DATE_FMT: Intl.DateTimeFormatOptions = {
  month: 'short',
  day: 'numeric',
};

/**
 * Accepts: ISO string ("2026-05-21T13:32:00Z"), unix seconds (1716301920),
 * or unix milliseconds (1716301920000). Returns null on bad input.
 */
export function toTradeDate(ts: string | number | null | undefined): Date | null {
  if (ts == null || ts === '') return null;
  if (typeof ts === 'number') {
    if (!Number.isFinite(ts) || ts <= 0) return null;
    // Heuristic: seconds vs milliseconds. Anything < 1e12 is seconds
    // (matches journal page convention).
    const ms = ts < 1e12 ? ts * 1000 : ts;
    const d = new Date(ms);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** "09:32" in America/New_York. */
export function fmtTimeET(ts: string | number | null | undefined): string {
  const d = toTradeDate(ts);
  if (!d) return '—';
  return d.toLocaleTimeString('en-US', { ...TIME_FMT, timeZone: ET_TZ });
}

/** "16:32" in Asia/Jerusalem. */
export function fmtTimeIL(ts: string | number | null | undefined): string {
  const d = toTradeDate(ts);
  if (!d) return '—';
  return d.toLocaleTimeString('en-US', { ...TIME_FMT, timeZone: IL_TZ });
}

/** "09:32 ET · 16:32 IL" — compact single-line dual time. */
export function fmtTimeETIL(ts: string | number | null | undefined): string {
  const d = toTradeDate(ts);
  if (!d) return '—';
  const et = d.toLocaleTimeString('en-US', { ...TIME_FMT, timeZone: ET_TZ });
  const il = d.toLocaleTimeString('en-US', { ...TIME_FMT, timeZone: IL_TZ });
  return `${et} ET · ${il} IL`;
}

/** "Nov 21" in America/New_York (trading-day calendar). */
export function fmtDateET(ts: string | number | null | undefined): string {
  const d = toTradeDate(ts);
  if (!d) return '—';
  return d.toLocaleDateString('en-US', { ...DATE_FMT, timeZone: ET_TZ });
}

/**
 * Structured form for surfaces that want to stack lines or compose their
 * own layout (e.g. TradesTable, ActiveTradeCard).
 */
export interface TradeWhen {
  date: string;   // "Nov 21" (ET trading day)
  etTime: string; // "09:32"
  ilTime: string; // "16:32"
}

export function tradeWhen(ts: string | number | null | undefined): TradeWhen | null {
  const d = toTradeDate(ts);
  if (!d) return null;
  return {
    date: d.toLocaleDateString('en-US', { ...DATE_FMT, timeZone: ET_TZ }),
    etTime: d.toLocaleTimeString('en-US', { ...TIME_FMT, timeZone: ET_TZ }),
    ilTime: d.toLocaleTimeString('en-US', { ...TIME_FMT, timeZone: IL_TZ }),
  };
}
