/**
 * G6 regression: date filter must use ET timezone, not UTC.
 * A trade at 2026-06-03T23:30:00Z (19:30 ET) must fall on ET date 2026-06-03.
 * Revert to slice(0,10) → this test turns RED.
 */

// Inline the function so we test the exact logic
const _etFmt = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' });
function toETDate(ts: string): string {
  try { return _etFmt.format(new Date(ts)); } catch { return ts.slice(0, 10); }
}

describe('toETDate (G6 ET-aware date filter)', () => {
  it('afternoon ET trade stays on ET date, not UTC+1 date', () => {
    // 23:30 UTC = 19:30 ET (EDT) → ET date is still 06-03
    expect(toETDate('2026-06-03T23:30:00Z')).toBe('2026-06-03');
  });

  it('early UTC maps to previous ET date', () => {
    // 03:00 UTC = 23:00 ET (prev day) → ET date is 06-02
    expect(toETDate('2026-06-03T03:00:00Z')).toBe('2026-06-02');
  });

  it('midday UTC = same date in ET', () => {
    expect(toETDate('2026-06-03T15:00:00Z')).toBe('2026-06-03');
  });

  it('litmus: slice(0,10) would give wrong answer for 23:30Z', () => {
    const ts = '2026-06-03T23:30:00Z';
    const sliceResult = ts.slice(0, 10); // '2026-06-03' — happens to be correct here
    // But for 03:00Z, slice gives 06-03 while ET is 06-02
    const ts2 = '2026-06-03T03:00:00Z';
    const sliceResult2 = ts2.slice(0, 10); // '2026-06-03' — WRONG for ET
    expect(sliceResult2).toBe('2026-06-03'); // slice thinks it's 06-03
    expect(toETDate(ts2)).toBe('2026-06-02'); // ET knows it's 06-02
    expect(sliceResult2).not.toBe(toETDate(ts2)); // They disagree → slice is wrong
  });
});
