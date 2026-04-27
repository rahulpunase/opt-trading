import { useEffect, useRef, useState } from "react";

export interface SymbolQuoteTick {
  ltp: number;
  volume?: number;
  timestamp?: string;
}

export interface SymbolQuoteResult {
  tick: SymbolQuoteTick | null;
  error: string | null;
}

const MIN_RECONNECT_MS = 3_000;
const MAX_RECONNECT_MS = 30_000;

export function useSymbolQuote(
  symbol: string,
  exchange: string
): SymbolQuoteResult {
  const [tick, setTick] = useState<SymbolQuoteTick | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const deadRef = useRef(false);
  const retryDelayRef = useRef(MIN_RECONNECT_MS);

  useEffect(() => {
    if (!symbol || !exchange) return;

    deadRef.current = false;
    retryDelayRef.current = MIN_RECONNECT_MS;

    function connect() {
      if (deadRef.current) return;

      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      const url = `${protocol}://${window.location.host}/ws/quote/${encodeURIComponent(symbol)}?exchange=${encodeURIComponent(exchange)}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data) as { error?: string } & SymbolQuoteTick;
          if (data.error) {
            setError(data.error);
            // Don't clear error on reconnect — let the next successful tick clear it
          } else if (data.ltp != null) {
            setTick(data);
            setError(null);
            retryDelayRef.current = MIN_RECONNECT_MS; // reset backoff on success
          }
        } catch {
          // ignore malformed frames
        }
      };

      ws.onerror = () => ws.close();

      ws.onclose = () => {
        wsRef.current = null;
        if (!deadRef.current) {
          setTimeout(connect, retryDelayRef.current);
          // Exponential backoff — doubles each attempt, caps at MAX
          retryDelayRef.current = Math.min(retryDelayRef.current * 2, MAX_RECONNECT_MS);
        }
      };

      // Keep-alive ping every 20 seconds
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send("ping");
        }
      }, 20_000);

      ws.addEventListener("close", () => clearInterval(pingInterval));
    }

    connect();

    return () => {
      deadRef.current = true;
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [symbol, exchange]);

  return { tick, error };
}
