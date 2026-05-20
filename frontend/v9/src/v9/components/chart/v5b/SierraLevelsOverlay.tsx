'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import type { IChartApi, ISeriesApi } from 'lightweight-charts';
import {
  buildTpoPlan,
  type TpoLevelName,
  type TpoOverlayData,
  WHITE_YDAY,
} from './tpoLevels';

export type { TpoOverlayData, TpoPeriod } from './tpoLevels';
export {
  buildTpoPlan,
  collectTpoPrices,
  coerceMesPrice,
  isValidMesTpoPrice,
  resolveTodayLevels,
  syncTpoPriceLines,
} from './tpoLevels';

const BADGE_BG = '#FFFFFF';
const BADGE_TEXT = '#000000';
const PRICE_SCALE_W = 80;
const BADGE_H = 18;
const BADGE_RX = 2;
const FONT = 'ui-monospace, monospace';
const PRICE_FONT_SIZE = 10;
const LW_TICK_LEN = 5;

function lwGrayTickTextX(chartWidth: number): number {
  const paddingInner = (PRICE_FONT_SIZE / 12) * LW_TICK_LEN;
  return Math.round(chartWidth - PRICE_SCALE_W + LW_TICK_LEN + paddingInner);
}

function priceToPaneY(
  series: ISeriesApi<'Candlestick'>,
  price: number,
  paneHeight: number,
): number | null {
  const direct = series.priceToCoordinate(price);
  if (direct != null && Number.isFinite(direct)) return direct;

  const top = series.coordinateToPrice(0);
  const bottom = series.coordinateToPrice(paneHeight);
  if (top == null || bottom == null) return null;
  const hi = Math.max(top, bottom);
  const lo = Math.min(top, bottom);
  if (hi <= lo) return null;
  return ((hi - price) / (hi - lo)) * paneHeight;
}

type BadgeSegment = {
  name: TpoLevelName;
  price: number;
  y: number;
  color: string;
};

type Props = {
  chartRef: React.RefObject<IChartApi | null>;
  candleSeries: ISeriesApi<'Candlestick'> | null;
  tpo: TpoOverlayData | null;
  width: number;
  height: number;
};

function nameBadgeWidth(chars: number): number {
  return Math.max(28, chars * 6.5 + 10);
}

function badgeLayout(name: string, price: number, width: number) {
  const priceStr = price.toFixed(2);
  const nameW = nameBadgeWidth(name.length);
  const priceX = Math.max(0, width - PRICE_SCALE_W);
  const priceTextX = lwGrayTickTextX(width);
  const nameX = priceX - nameW - 2;
  return { priceStr, nameW, priceX, nameX, priceTextX };
}

function TpoAxisBadge({
  name,
  price,
  y,
  width,
  lineColor,
}: {
  name: string;
  price: number;
  y: number;
  width: number;
  lineColor: string;
}) {
  const { priceStr, nameW, priceX, nameX, priceTextX } = badgeLayout(name, price, width);
  const y0 = y - BADGE_H / 2;
  const isYesterday = lineColor === WHITE_YDAY;
  const badgeBg = isYesterday ? '#FFFFFF' : '#FF4DD8';
  const nameText = '#000000';
  const priceText = '#000000';
  const borderColor = lineColor;

  return (
    <g>
      <rect x={nameX} y={y0} width={nameW} height={BADGE_H} rx={BADGE_RX} fill={badgeBg} stroke={borderColor} strokeWidth={1} />
      <text
        x={nameX + nameW - 5}
        y={y}
        dominantBaseline="central"
        textAnchor="end"
        fill={nameText}
        fontSize={PRICE_FONT_SIZE}
        fontFamily={FONT}
        fontWeight={700}
      >
        {name}
      </text>
      <rect x={priceX} y={y0} width={PRICE_SCALE_W} height={BADGE_H} rx={BADGE_RX} fill={badgeBg} stroke={borderColor} strokeWidth={1} />
      <text
        x={priceTextX}
        y={y}
        dominantBaseline="central"
        textAnchor="start"
        fill={priceText}
        fontSize={PRICE_FONT_SIZE}
        fontFamily={FONT}
        fontWeight={400}
        style={{ fontVariantNumeric: 'tabular-nums' }}
      >
        {priceStr}
      </text>
    </g>
  );
}

/** Full-width SVG rules + axis badges (multi-pane LW chart). */
export function SierraLevelsOverlay({
  chartRef,
  candleSeries,
  tpo,
  width,
  height,
}: Props) {
  const plan = useMemo(() => buildTpoPlan(tpo), [tpo]);
  const [badges, setBadges] = useState<BadgeSegment[]>([]);
  const lastLogRef = useRef('');

  useEffect(() => {
    if (!candleSeries || width < 1) {
      setBadges([]);
      return;
    }
    const series = candleSeries;
    const svgH = height > 0 ? height : 1;

    const rebuild = () => {
      const next: BadgeSegment[] = [];
      for (const lv of plan) {
        const y = priceToPaneY(series, lv.price, svgH);
        if (y == null || !Number.isFinite(y)) continue;
        if (y < BADGE_H / 2 || y > svgH - BADGE_H / 2) continue;
        next.push({ name: lv.name, price: lv.price, y, color: lv.color });
      }
      const key = `${next.length}|${plan.map((p) => p.price).join(',')}`;
      if (key !== lastLogRef.current) {
        lastLogRef.current = key;
        console.info('[TPO overlay] badges', {
          badges: next.length,
          planLen: plan.length,
        });
      }
      setBadges(next);
    };

    rebuild();
    const raf = requestAnimationFrame(rebuild);
    const chart = chartRef.current;
    chart?.timeScale().subscribeVisibleLogicalRangeChange(rebuild);
    chart?.subscribeCrosshairMove(rebuild);
    return () => {
      cancelAnimationFrame(raf);
      if (chart) {
        try {
          chart.timeScale().unsubscribeVisibleLogicalRangeChange(rebuild);
        } catch {
          /* noop */
        }
        try {
          chart.unsubscribeCrosshairMove(rebuild);
        } catch {
          /* noop */
        }
      }
    };
  }, [chartRef, candleSeries, height, plan, tpo, width]);

  if (width < 1) return null;
  const svgH = height > 0 ? height : 1;

  return (
    <svg
      width={width}
      height={svgH}
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        zIndex: 30,
        pointerEvents: 'none',
        overflow: 'hidden',
      }}
    >
      {badges.map((b) => (
        <TpoAxisBadge
          key={`${b.color}-${b.name}-${b.price}`}
          name={b.name}
          price={b.price}
          y={b.y}
          width={width}
          lineColor={b.color}
        />
      ))}
    </svg>
  );
}
