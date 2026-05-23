'use client';
import { useMemo, useEffect, useState, useCallback } from 'react';
import { useSystemStore } from '../../../stores/systemStore';
import { useMarketStore } from '../../../stores/marketStore';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface StreamInfo {
  name: string;
  color: string;
  age_sec: number | null;
  push_count: number;
  error_count: number;
}

interface HealthResponse {
  streams: StreamInfo[];
  summary: { green: number; yellow: number; red: number; grey: number };
}

const COLOR_DOT: Record<string, string> = {
  green: 'var(--green)',
  yellow: '#FACC15',
  red: 'var(--red)',
  grey: 'var(--text-muted)',
};

function formatAge(ageSec: number | null): string {
  if (ageSec === null || ageSec < 0) return '--';
  if (ageSec < 60) return `${Math.round(ageSec)}s`;
  return `${Math.floor(ageSec / 60)}m`;
}

export function MarketTab() {
  const allSignals = useSystemStore((s) => s.signals);
  const activeSignals = useSystemStore((s) => s.activeSignals);
  const market = useMarketStore();

  // Stream health polling (5s — non-critical diagnostic)
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v9/health/streams`);
      if (res.ok) setHealthData(await res.json());
    } catch {
      // non-critical
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  // Day classification from System 1
  const dayClassification = useMemo(() => {
    const sig = activeSignals[1];
    return {
      type: (sig?.payload?.day_type as string) ?? '--',
      classification: sig?.classification ?? '--',
    };
  }, [activeSignals]);

  // Session phase from System 6
  const sessionPhase = useMemo(() => {
    const sig = activeSignals[6];
    return {
      phase: (sig?.payload?.session_phase as string) ?? '--',
      gateOpen: (sig?.payload?.gate_open as boolean) ?? false,
    };
  }, [activeSignals]);

  // Traffic light
  const trafficLight = useMemo(() => {
    const firingSigs = [activeSignals[1], activeSignals[2], activeSignals[4]].filter(Boolean);
    if (firingSigs.length === 0) return 'red';
    const hasHigh = firingSigs.some((s) => (s?.confidence ?? 0) >= 0.7);
    return hasHigh ? 'green' : 'yellow';
  }, [activeSignals]);

  const trafficColors: Record<string, string> = {
    green: 'var(--green)',
    yellow: '#FACC15',
    red: 'var(--red)',
  };

  // Indicator health checks
  const indicators = useMemo(() => [
    { label: 'POC', ok: market.currentPOC !== null },
    { label: 'VAH', ok: market.currentVAH !== null },
    { label: 'VAL', ok: market.currentVAL !== null },
    { label: 'PDH', ok: market.pdh !== null },
    { label: 'ONH', ok: market.onh !== null },
    { label: 'IBH', ok: market.ibh !== null },
    { label: 'Vegas', ok: market.vegasEma12 !== null },
    { label: '5min', ok: market.bars5min.length > 0 },
    { label: 'TickRev', ok: market.tickReversalBars.length > 0 },
  ], [market]);

  const okCount = indicators.filter((i) => i.ok).length;

  return (
    <div className="flex flex-col gap-3 text-xs">
      {/* Market Overview */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="flex items-center justify-between mb-1">
          <span className="font-bold" style={{ color: 'var(--text-primary)' }}>Market State</span>
          <div
            className="w-3 h-3 rounded-full"
            style={{ background: trafficColors[trafficLight] }}
          />
        </div>
        <div className="flex flex-col gap-0.5" style={{ color: 'var(--text-secondary)' }}>
          <div className="flex justify-between">
            <span>Day Type</span>
            <span style={{ color: '#58a6ff' }}>{dayClassification.type}</span>
          </div>
          <div className="flex justify-between">
            <span>Phase</span>
            <span>{sessionPhase.phase}</span>
          </div>
          <div className="flex justify-between">
            <span>Gate</span>
            <span style={{ color: sessionPhase.gateOpen ? 'var(--green)' : 'var(--red)' }}>
              {sessionPhase.gateOpen ? 'OPEN' : 'CLOSED'}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Signals Today</span>
            <span>{allSignals.length}</span>
          </div>
        </div>
      </div>

      {/* Indicator Status */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Indicators: {okCount}/{indicators.length}
        </div>
        <div className="flex flex-wrap gap-1">
          {indicators.map((ind) => (
            <span
              key={ind.label}
              className="px-1.5 py-0.5 rounded"
              style={{
                background: ind.ok ? '#56d36420' : '#f8514920',
                color: ind.ok ? 'var(--green)' : 'var(--red)',
                fontSize: 10,
              }}
            >
              {ind.label}
            </span>
          ))}
        </div>
      </div>

      {/* Stream Health */}
      <div className="p-2 rounded" style={{ background: 'var(--bg-tertiary)' }}>
        <div className="font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
          Stream Health
          {healthData && (
            <span style={{ color: 'var(--text-muted)', fontWeight: 400, marginLeft: 6 }}>
              {healthData.summary.green}G {healthData.summary.yellow}Y {healthData.summary.red}R
            </span>
          )}
        </div>
        {healthData ? (
          <div className="flex flex-col gap-0.5">
            {healthData.streams.map((s) => (
              <div key={s.name} className="flex justify-between items-center">
                <span className="flex items-center gap-1">
                  <span
                    className="w-2 h-2 rounded-full inline-block"
                    style={{ background: COLOR_DOT[s.color] || COLOR_DOT.grey }}
                  />
                  <span style={{ color: 'var(--text-secondary)' }}>{s.name}</span>
                </span>
                <span style={{ color: 'var(--text-muted)' }}>
                  {formatAge(s.age_sec)}
                  {s.error_count > 0 && (
                    <span style={{ color: 'var(--red)', marginLeft: 4 }}>E{s.error_count}</span>
                  )}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)' }}>Connecting...</div>
        )}
      </div>
    </div>
  );
}
