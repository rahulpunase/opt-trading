import { useEffect } from "react";
import { useQuoteContext, type SymbolQuoteTick } from "@/lib/quotes";

export interface SymbolQuoteResult {
  tick: SymbolQuoteTick | null;
  error: string | null;
}

export function useSymbolQuote(instrumentToken: number, label?: string): SymbolQuoteResult {
  const { ticks, subscribe, unsubscribe, wsError } = useQuoteContext();

  useEffect(() => {
    if (!instrumentToken) return;
    subscribe(instrumentToken, label ?? String(instrumentToken));
    return () => unsubscribe(instrumentToken);
  }, [instrumentToken, label, subscribe, unsubscribe]);

  return {
    tick: instrumentToken ? (ticks.get(instrumentToken) ?? null) : null,
    error: wsError,
  };
}
