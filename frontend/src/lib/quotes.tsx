import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
  type ReactNode,
} from "react";

export interface SymbolQuoteTick {
  ltp: number;
  volume?: number;
  timestamp?: string;
}

interface QuoteContextValue {
  ticks: Map<number, SymbolQuoteTick>;
  subscribe: (token: number, symbol: string) => void;
  unsubscribe: (token: number) => void;
  wsError: string | null;
}

const QuoteContext = createContext<QuoteContextValue>({
  ticks: new Map(),
  subscribe: () => {},
  unsubscribe: () => {},
  wsError: null,
});

const MIN_RECONNECT_MS = 3_000;
const MAX_RECONNECT_MS = 30_000;

export function QuoteProvider({ children }: { children: ReactNode }) {
  const [ticks, setTicks] = useState<Map<number, SymbolQuoteTick>>(new Map());
  const [wsError, setWsError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const deadRef = useRef(false);
  const retryDelayRef = useRef(MIN_RECONNECT_MS);
  // token → refcount; source of truth for active subscriptions
  const refCountRef = useRef<Map<number, number>>(new Map());
  // token → symbol name; used for re-subscription on reconnect and backend logging
  const symbolMapRef = useRef<Map<number, string>>(new Map());
  const connectRef = useRef<() => void>(() => {});

  const sendIfOpen = (msg: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  };

  const connect = useCallback(() => {
    if (deadRef.current) return;

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws/quotes`);
    wsRef.current = ws;

    ws.onopen = () => {
      retryDelayRef.current = MIN_RECONNECT_MS;
      setWsError(null);
      // Re-subscribe all currently active tokens after reconnect
      for (const [token, symbol] of symbolMapRef.current.entries()) {
        ws.send(JSON.stringify({ action: "subscribe", token, symbol }));
      }
    };

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as { error?: string; token?: number } & SymbolQuoteTick;
        if (data.error) {
          setWsError(data.error);
        } else if (data.token != null && data.ltp != null) {
          setTicks((prev) => {
            const next = new Map(prev);
            next.set(data.token!, { ltp: data.ltp, volume: data.volume, timestamp: data.timestamp });
            return next;
          });
          setWsError(null);
        }
      } catch {
        // ignore malformed frames
      }
    };

    ws.onerror = () => ws.close();

    ws.onclose = () => {
      wsRef.current = null;
      if (!deadRef.current) {
        setTimeout(() => connectRef.current(), retryDelayRef.current);
        retryDelayRef.current = Math.min(retryDelayRef.current * 2, MAX_RECONNECT_MS);
      }
    };

    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: "ping" }));
      }
    }, 20_000);

    ws.addEventListener("close", () => clearInterval(pingInterval));
  }, []);

  useEffect(() => {
    connectRef.current = connect;
    deadRef.current = false;
    connect();
    return () => {
      deadRef.current = true;
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  const subscribe = useCallback((token: number, symbol: string) => {
    const count = refCountRef.current.get(token) ?? 0;
    refCountRef.current.set(token, count + 1);
    if (count === 0) {
      symbolMapRef.current.set(token, symbol);
      sendIfOpen({ action: "subscribe", token, symbol });
    }
  }, []);

  const unsubscribe = useCallback((token: number) => {
    const count = refCountRef.current.get(token) ?? 0;
    if (count <= 1) {
      refCountRef.current.delete(token);
      symbolMapRef.current.delete(token);
      sendIfOpen({ action: "unsubscribe", token });
      setTicks((prev) => {
        const next = new Map(prev);
        next.delete(token);
        return next;
      });
    } else {
      refCountRef.current.set(token, count - 1);
    }
  }, []);

  return (
    <QuoteContext.Provider value={{ ticks, subscribe, unsubscribe, wsError }}>
      {children}
    </QuoteContext.Provider>
  );
}

export function useQuoteContext() {
  return useContext(QuoteContext);
}
