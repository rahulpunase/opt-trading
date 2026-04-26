import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { createElement } from "react";
import type { Portfolio, Strategy } from "./api";

export type WsStatus = "connecting" | "connected" | "disconnected";

export interface WsPayload {
  portfolio: Portfolio;
  strategies: Strategy[];
  positions: Record<string, Record<string, unknown>>;
  timestamp: string;
}

interface WsContextValue {
  status: WsStatus;
  data: WsPayload | null;
}

const WsContext = createContext<WsContextValue>({
  status: "disconnected",
  data: null,
});

export function WsProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<WsStatus>("connecting");
  const [data, setData] = useState<WsPayload | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws`);
    wsRef.current = ws;
    setStatus("connecting");

    ws.onopen = () => setStatus("connected");
    ws.onmessage = (e) => {
      try {
        setData(JSON.parse(e.data) as WsPayload);
      } catch {
        // ignore malformed frames
      }
    };
    ws.onclose = () => {
      setStatus("disconnected");
      reconnectTimer.current = setTimeout(connect, 3000);
    };
    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };
  }, [connect]);

  return createElement(WsContext.Provider, { value: { status, data } }, children);
}

export function useWs() {
  return useContext(WsContext);
}
