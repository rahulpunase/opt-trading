import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useQuoteContext, type SymbolQuoteTick } from "@/lib/quotes";

export interface SymbolQuoteResult {
  tick: SymbolQuoteTick | null;
  error: string | null;
}

export function useSymbolQuote(symbol: string, exchange: string): SymbolQuoteResult {
  const { ticks, subscribe, unsubscribe, wsError } = useQuoteContext();

  // Reuse the same query key as QuoteSection — React Query deduplicates the request
  const { data } = useQuery({
    queryKey: ["symbolQuote", symbol, exchange],
    queryFn: () => api.symbolQuote(symbol, exchange),
    refetchInterval: false,
    retry: false,
    enabled: !!symbol && !!exchange,
  });

  const token = data?.instrument_token ?? null;

  useEffect(() => {
    if (!token) return;
    subscribe(token, symbol);
    return () => unsubscribe(token);
  }, [token, symbol, subscribe, unsubscribe]);

  return {
    tick: token != null ? (ticks.get(token) ?? null) : null,
    error: wsError,
  };
}
