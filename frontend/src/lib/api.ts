export interface AuthStatus {
  authenticated: boolean;
  user_id?: string;
  user_name?: string;
}

export interface Strategy {
  name: string;
  enabled: boolean;
  paper_trade: boolean;
  status?: "running" | "stopped" | "paused";
  trades_today: number;
  open_positions: number;
}

export interface AvailableStrategy {
  name: string;
  enabled: boolean;
  paper_trade: boolean;
  instruments: string[];
  timeframe: string;
  capital_allocation: number;
}

export interface Portfolio {
  daily_pnl: number;
  daily_loss_cap: number;
  margin_used_pct: number;
  max_margin_utilisation_pct: number;
  strategies_running: string[];
}

export interface MarginSegment {
  enabled: boolean;
  net: number;
  available: {
    cash: number;
    opening_balance: number;
    live_balance: number;
    adhoc_margin: number;
    collateral: number;
    intraday_payin: number;
  };
  utilised: {
    span: number;
    exposure: number;
    option_premium: number;
    m2m_realised: number;
    m2m_unrealised: number;
    debits: number;
    delivery: number;
  };
}

export interface MarginData {
  equity?: MarginSegment;
  commodity?: MarginSegment;
}

export interface Trade {
  time: string;
  strategy: string;
  symbol: string;
  side: "BUY" | "SELL";
  qty: number;
  price: number;
  pnl: number;
  paper_trade: boolean;
}

export interface Underlying {
  symbol: string;
  exchange: string;
  instrument_type: string;
  instrument_token: number;
}

export interface SymbolQuote {
  symbol: string;
  exchange: string;
  instrument_token: number | null;
  ltp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  change: number;
  change_pct: number;
}

export interface OptionLeg {
  tradingsymbol: string;
  lot_size: number;
  ltp: number;
}

export interface OptionChainRow {
  strike: number;
  ce: OptionLeg | null;
  pe: OptionLeg | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  authStatus: () => request<AuthStatus>("/auth/status"),
  authLoginUrl: () => request<{ login_url: string }>("/auth/login"),
  authExchange: (request_token: string) =>
    request<AuthStatus & { access_token: string }>(
      `/auth?request_token=${encodeURIComponent(request_token)}`
    ),
  authLogout: () => request<{ status: string }>("/auth", { method: "DELETE" }),

  portfolio: () => request<Portfolio>("/portfolio"),
  strategies: () => request<Strategy[]>("/strategies"),
  availableStrategies: () => request<AvailableStrategy[]>("/strategies/available"),

  startStrategy: (name: string) =>
    request<{ status: string; name: string }>("/strategy/start", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  stopStrategy: (name: string) =>
    request<{ status: string; name: string }>("/strategy/stop", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  pauseStrategy: (name: string) =>
    request<{ status: string; name: string }>("/strategy/pause", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),

  margins: () => request<MarginData>("/margins"),

  searchUnderlyings: (q: string) =>
    request<{ results: Underlying[]; cache_populated: boolean }>(`/instruments/underlyings?q=${encodeURIComponent(q)}`),

  instrumentQuote: (instrumentToken: number) =>
    request<SymbolQuote>(`/instruments/${instrumentToken}/quote`),

  instrumentExpiries: (instrumentToken: number) =>
    request<{ symbol: string; exchange: string; expiries: string[] }>(
      `/instruments/${instrumentToken}/expiries`
    ),

  instrumentOptionChain: (instrumentToken: number, expiry: string) =>
    request<{ symbol: string; exchange: string; expiry: string; chain: OptionChainRow[] }>(
      `/instruments/${instrumentToken}/option-chain?expiry=${encodeURIComponent(expiry)}`
    ),

  strategyPositions: (name: string) =>
    request<{ name: string; positions: Record<string, unknown> }>(
      `/strategy/${encodeURIComponent(name)}/positions`
    ),
  strategyTrades: (name: string) =>
    request<{ name: string; trades_today: number; trades?: Trade[] }>(
      `/strategy/${encodeURIComponent(name)}/trades`
    ),
};
