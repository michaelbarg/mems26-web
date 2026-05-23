'use client';

import { useEffect, useState, useCallback } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface StreamInfo {
  name: string;
  status: string;
  color: string;
  age_sec: number | null;
  push_count: number;
  error_count: number;
  subscribed_systems: number[];
  last_push_ts: number | null;
}

interface HealthResponse {
  streams: StreamInfo[];
  summary: { green: number; yellow: number; red: number; grey: number };
  ts: string | null;
}

const COLOR_DOT: Record<string, string> = {
  green: '#3fb950',
  yellow: '#d29922',
  red: '#f85149',
  grey: '#484f58',
};

function formatAge(ageSec: number | null): string {
  if (ageSec === null || ageSec < 0) return '--';
  if (ageSec < 60) return `${Math.round(ageSec)}s`;
  return `${Math.floor(ageSec / 60)}m`;
}

export function StreamHealthPanel() {
  const [data, setData] = useState<HealthResponse | null>(null);
  const [collapsed, setCollapsed] = useState(true);

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v9/health/streams`);
      if (res.ok) {
        const json: HealthResponse = await res.json();
        setData(json);

        // Auto-expand if any non-green, non-grey stream
        const hasIssue = json.streams.some(
          (s) => s.color !== 'green' && s.color !== 'grey'
        );
        if (hasIssue) setCollapsed(false);
      }
    } catch {
      // Silently ignore — health panel is non-critical
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  if (!data) return null;

  const { summary, streams } = data;

  return (
    <div
      style={{
        background: '#161b22',
        borderBottom: '1px solid #30363d',
        fontSize: 12,
        fontFamily: 'monospace',
        color: '#c9d1d9',
      }}
    >
      {/* Collapsed summary bar */}
      <div
        onClick={() => setCollapsed((c) => !c)}
        style={{
          padding: '4px 12px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          userSelect: 'none',
        }}
      >
        <span style={{ color: '#8b949e' }}>{collapsed ? '\u25B6' : '\u25BC'}</span>
        <span style={{ fontWeight: 600 }}>Stream Health</span>
        <span style={{ marginLeft: 8 }}>
          {streams.length} streams:
          {summary.green > 0 && (
            <span style={{ color: COLOR_DOT.green, marginLeft: 6 }}>
              {summary.green}&#x1F7E2;
            </span>
          )}
          {summary.yellow > 0 && (
            <span style={{ color: COLOR_DOT.yellow, marginLeft: 4 }}>
              {summary.yellow}&#x1F7E1;
            </span>
          )}
          {summary.red > 0 && (
            <span style={{ color: COLOR_DOT.red, marginLeft: 4 }}>
              {summary.red}&#x1F534;
            </span>
          )}
          {summary.grey > 0 && (
            <span style={{ color: COLOR_DOT.grey, marginLeft: 4 }}>
              {summary.grey}&#x26AB;
            </span>
          )}
        </span>
      </div>

      {/* Expanded detail table */}
      {!collapsed && (
        <div style={{ padding: '0 12px 6px', overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ color: '#8b949e', textAlign: 'left' }}>
                <th style={{ padding: '2px 8px' }}></th>
                <th style={{ padding: '2px 8px' }}>Stream</th>
                <th style={{ padding: '2px 8px' }}>Age</th>
                <th style={{ padding: '2px 8px' }}>Pushes</th>
                <th style={{ padding: '2px 8px' }}>Errors</th>
                <th style={{ padding: '2px 8px' }}>Systems</th>
              </tr>
            </thead>
            <tbody>
              {streams.map((s) => (
                <tr key={s.name} style={{ borderTop: '1px solid #21262d' }}>
                  <td style={{ padding: '2px 8px' }}>
                    <span
                      style={{
                        display: 'inline-block',
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: COLOR_DOT[s.color] || COLOR_DOT.grey,
                      }}
                    />
                  </td>
                  <td style={{ padding: '2px 8px' }}>{s.name}</td>
                  <td style={{ padding: '2px 8px' }}>{formatAge(s.age_sec)}</td>
                  <td style={{ padding: '2px 8px' }}>{s.push_count}</td>
                  <td
                    style={{
                      padding: '2px 8px',
                      color: s.error_count > 0 ? COLOR_DOT.red : undefined,
                    }}
                  >
                    {s.error_count}
                  </td>
                  <td style={{ padding: '2px 8px', display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {s.subscribed_systems.map((sid) => (
                      <span
                        key={sid}
                        style={{
                          background: '#30363d',
                          borderRadius: 3,
                          padding: '0 4px',
                          fontSize: 10,
                        }}
                      >
                        S{sid}
                      </span>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
