/** Convert UTC unix timestamp to ET chart time (for LightweightCharts display).
 *  Handles EDT (UTC-4, Mar–Nov) / EST (UTC-5, Nov–Mar) dynamically. */
export function toETChartTime(utcTimestamp: number): number {
  const date = new Date(utcTimestamp * 1000);
  const etTime = new Date(date.toLocaleString('en-US', { timeZone: 'America/New_York' }));
  const utcTime = new Date(date.toLocaleString('en-US', { timeZone: 'UTC' }));
  return utcTimestamp + (etTime.getTime() - utcTime.getTime()) / 1000;
}
