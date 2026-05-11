type WSCallback = (data: any) => void;

class WSManager {
  private connections: Map<string, WebSocket> = new Map();
  private callbacks: Map<string, Set<WSCallback>> = new Map();
  private reconnectTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();
  private baseUrl: string;

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
  }

  connect(channel: string): void {
    if (this.connections.has(channel)) return;

    const ws = new WebSocket(`${this.baseUrl}${channel}`);
    this.connections.set(channel, ws);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const cbs = this.callbacks.get(channel);
      if (cbs) cbs.forEach((cb) => cb(data));
    };

    ws.onclose = () => {
      this.connections.delete(channel);
      const timer = setTimeout(() => this.connect(channel), 3000);
      this.reconnectTimers.set(channel, timer);
    };

    ws.onerror = () => {
      ws.close();
    };
  }

  subscribe(channel: string, callback: WSCallback): () => void {
    if (!this.callbacks.has(channel)) {
      this.callbacks.set(channel, new Set());
    }
    this.callbacks.get(channel)!.add(callback);
    this.connect(channel);

    return () => {
      const cbs = this.callbacks.get(channel);
      if (cbs) {
        cbs.delete(callback);
        if (cbs.size === 0) this.disconnect(channel);
      }
    };
  }

  disconnect(channel: string): void {
    const ws = this.connections.get(channel);
    if (ws) { ws.close(); this.connections.delete(channel); }
    const timer = this.reconnectTimers.get(channel);
    if (timer) { clearTimeout(timer); this.reconnectTimers.delete(channel); }
    this.callbacks.delete(channel);
  }

  disconnectAll(): void {
    for (const channel of this.connections.keys()) this.disconnect(channel);
  }
}

export const wsManager = new WSManager();

export const WS_CHANNELS = {
  BARS_5MIN: '/ws/v9/bars/5min',
  BARS_TICK_REVERSAL: '/ws/v9/bars/tick_reversal',
  MARKERS: (systemId: number) => `/ws/v9/markers/${systemId}`,
  TRADES: '/ws/v9/trades',
  LEVELS: '/ws/v9/levels',
  ACCOUNT: '/ws/v9/account',
  PRICE: '/ws/v9/price',
} as const;
