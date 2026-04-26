"use client";

import { useState } from "react";

interface TradeState {
  trade_id: string;
  status: string;
  c1_status: string;
  c2_status: string;
  c3_status: string;
  stop_status: string;
  c1_fill_price: number | null;
  c2_fill_price: number | null;
  c3_fill_price: number | null;
  stop_fill_price: number | null;
  active_management_state: string;
}

interface ActiveTradePanelV2Props {
  tradeId?: string;
  tradeState?: TradeState;
}

function getStatusColor(status: string): string {
  switch (status) {
    case "FILLED":
      return "#22c55e";
    case "OPEN":
      return "#3b82f6";
    case "PENDING":
      return "#6b7280";
    case "CANCELED":
      return "#ef4444";
    default:
      return "#9ca3af";
  }
}

function getStatusBg(status: string): string {
  switch (status) {
    case "FILLED":
      return "#0a2e1a";
    case "OPEN":
      return "#0a1a2e";
    case "PENDING":
      return "#1e2738";
    case "CANCELED":
      return "#2e0a0a";
    default:
      return "#1e2738";
  }
}

function getMgmtStateColor(state: string): { bg: string; text: string } {
  switch (state) {
    case "BE_ARMED":
      return { bg: "#1a0a2e", text: "#a78bfa" };
    case "TRAILING":
      return { bg: "#0a1a2e", text: "#60a5fa" };
    case "BAILED_OUT":
      return { bg: "#2e0a0a", text: "#ef5350" };
    case "NORMAL":
    default:
      return { bg: "#1e2738", text: "#9ca3af" };
  }
}

export default function ActiveTradePanelV2({
  tradeId,
  tradeState,
}: ActiveTradePanelV2Props) {
  // Mock data fallback for skeleton view
  const mockData: TradeState = {
    trade_id: tradeId ?? "T-EXAMPLE-1776",
    status: "OPEN",
    c1_status: "FILLED",
    c2_status: "OPEN",
    c3_status: "OPEN",
    stop_status: "OPEN",
    c1_fill_price: 7148.5,
    c2_fill_price: null,
    c3_fill_price: null,
    stop_fill_price: null,
    active_management_state: "BE_ARMED",
  };

  const data = tradeState ?? mockData;

  const contracts = [
    { label: "C1", status: data.c1_status, price: data.c1_fill_price },
    { label: "C2", status: data.c2_status, price: data.c2_fill_price },
    { label: "C3", status: data.c3_status, price: data.c3_fill_price },
    { label: "Stop", status: data.stop_status, price: data.stop_fill_price },
  ];

  const mgmtColors = getMgmtStateColor(data.active_management_state);

  const btnStyle = (bg: string, color: string): React.CSSProperties => ({
    padding: '6px 0',
    fontSize: 13,
    fontWeight: 700,
    background: bg,
    color: color,
    border: 'none',
    borderRadius: 4,
    cursor: 'not-allowed',
    opacity: 0.5,
  });

  return (
    <div style={{ background: '#0d1117', border: '1px solid #1e2738', borderRadius: 6, padding: '8px 12px', marginTop: 8 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 14, fontWeight: 700, color: '#e5e7eb' }}>
          Active Trade Mgmt
        </span>
        <span style={{ fontSize: 11, color: '#6b7280', fontFamily: 'monospace' }}>
          {data.trade_id}
        </span>
      </div>

      {/* Per-contract grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 6, marginBottom: 8 }}>
        {contracts.map((item) => (
          <div key={item.label} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 2 }}>{item.label}</div>
            <div style={{
              padding: '2px 4px',
              borderRadius: 3,
              fontSize: 11,
              fontWeight: 800,
              color: getStatusColor(item.status),
              background: getStatusBg(item.status),
            }}>
              {item.status}
            </div>
            {item.price !== null && (
              <div style={{ fontSize: 11, marginTop: 2, fontFamily: 'monospace', color: '#9ca3af' }}>
                @{item.price.toFixed(2)}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Mgmt state badge */}
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 11, color: '#6b7280', marginRight: 6 }}>Mgmt State:</span>
        <span style={{
          display: 'inline-block',
          padding: '1px 6px',
          borderRadius: 3,
          fontSize: 11,
          fontWeight: 700,
          color: mgmtColors.text,
          background: mgmtColors.bg,
        }}>
          {data.active_management_state}
        </span>
      </div>

      {/* Action buttons (disabled placeholders) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
        <button disabled style={btnStyle('#2a2a0a', '#ca8a04')} title="Coming in V7.9.2">
          Move Stop
        </button>
        <button disabled style={btnStyle('#0a1a2e', '#60a5fa')} title="Coming in V7.9.3">
          Move Target
        </button>
        <button disabled style={btnStyle('#2e1a0a', '#f97316')} title="Coming in V7.9.1">
          Bailout
        </button>
        <button disabled style={btnStyle('#2e0a0a', '#ef5350')} title="Coming in V7.9.4">
          Manual Close
        </button>
      </div>

      {/* Skeleton notice */}
      <div style={{ marginTop: 6, fontSize: 10, color: '#4b5563', textAlign: 'center' }}>
        Skeleton (V7.7.1d-fe) — actions wired in V7.9.x
      </div>
    </div>
  );
}
