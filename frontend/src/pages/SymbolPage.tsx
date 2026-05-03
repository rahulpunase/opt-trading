import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { OptionChainRow } from "@/lib/api";
import { useSymbolQuote } from "@/hooks/useSymbolQuote";

// ─── Quote Section ────────────────────────────────────────────────────────────

function QuoteSection({ instrumentToken }: { instrumentToken: number }) {
  // Initial REST call for OHLC/change data (day-level, not tick-rate)
  const { data, isLoading, error } = useQuery({
    queryKey: ["instrumentQuote", instrumentToken],
    queryFn: () => api.instrumentQuote(instrumentToken),
    refetchInterval: false,
    retry: false,
  });

  // Real-time LTP + volume via KiteTicker WebSocket
  const { tick: liveTick, error: wsError } = useSymbolQuote(
    instrumentToken,
    data?.symbol,
  );

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border bg-bg-surface p-5">
        <div className="animate-pulse space-y-3">
          <div className="h-8 w-32 rounded bg-bg-elevated" />
          <div className="flex gap-6">
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className="h-4 w-16 rounded bg-bg-elevated"
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    const msg = (error as Error).message;
    const isNotAuth = msg.includes("not_authenticated") || msg.includes("503");
    return (
      <div className="rounded-xl border border-border bg-bg-surface p-5">
        <p className="text-sm text-text-muted">
          {isNotAuth
            ? "Login to Kite to see live quote data."
            : `Quote unavailable: ${msg}`}
        </p>
      </div>
    );
  }

  if (!data) return null;

  const isNotAuth = wsError?.toLowerCase().includes("authenticated");

  // Prefer live WebSocket tick for LTP and volume; fall back to REST snapshot
  const ltp = liveTick?.ltp ?? data.ltp;
  const volume = liveTick?.volume ?? data.volume;

  // Recompute change relative to prev close using live LTP
  const change = ltp - data.close;
  const changePct =
    data.close !== 0 ? (change / data.close) * 100 : data.change_pct;
  const isUp = changePct >= 0;
  const changeColor = isUp ? "var(--color-profit)" : "var(--color-loss)";

  return (
    <div className="rounded-xl border border-border bg-bg-surface p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <p className="text-xs text-text-muted">
              {data.exchange}
            </p>
            {isNotAuth ? (
              <span className="text-[10px] text-text-muted">
                ● Login to Kite for live feed
              </span>
            ) : liveTick ? (
              <span className="text-[10px] text-profit">
                ● Live
              </span>
            ) : null}
          </div>
          <h1 className="text-2xl font-bold text-text-primary">
            {data.symbol}
          </h1>
        </div>
        <div className="text-right">
          <p className="text-3xl font-semibold tabular-nums text-text-primary">
            ₹{ltp.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
          </p>
          <p className="text-sm tabular-nums" style={{ color: changeColor }}>
            {isUp ? "▲" : "▼"} {Math.abs(change).toFixed(2)} (
            {Math.abs(changePct).toFixed(2)}%)
          </p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-5 gap-3 border-t border-border pt-4">
        {[
          { label: "Open", value: data.open },
          { label: "High", value: data.high },
          { label: "Low", value: data.low },
          { label: "Prev Close", value: data.close },
          { label: "Volume", value: null, raw: volume.toLocaleString("en-IN") },
        ].map(({ label, value, raw }) => (
          <div key={label}>
            <p className="text-[10px] text-text-muted">
              {label}
            </p>
            <p className="text-sm font-medium tabular-nums text-text-primary">
              {raw ??
                `₹${value?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Expiry Picker ────────────────────────────────────────────────────────────

function ExpirySection({
  instrumentToken,
  selected,
  onSelect,
}: {
  instrumentToken: number;
  selected: string | null;
  onSelect: (expiry: string) => void;
}) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["instrumentExpiries", instrumentToken],
    queryFn: () => api.instrumentExpiries(instrumentToken),
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="flex gap-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="h-7 w-24 animate-pulse rounded-full bg-bg-elevated"
          />
        ))}
      </div>
    );
  }

  if (error) {
    const msg = (error as Error).message;
    const isNotAuth = msg.includes("not_authenticated") || msg.includes("503");
    return (
      <p className="text-sm text-text-muted">
        {isNotAuth
          ? "Login to Kite to see expiries."
          : `Could not load expiries: ${msg}`}
      </p>
    );
  }

  const expiries = data?.expiries ?? [];

  if (expiries.length === 0) {
    return (
      <p className="text-sm text-text-muted">
        No F&amp;O contracts available for this symbol.
      </p>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {expiries.map((exp) => {
        const label = new Date(exp + "T00:00:00").toLocaleDateString("en-IN", {
          day: "numeric",
          month: "short",
          year: "numeric",
        });
        const isActive = selected === exp;
        return (
          <button
            key={exp}
            onClick={() => onSelect(exp)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition ${
              isActive
                ? "bg-accent text-white"
                : "border border-border bg-bg-elevated text-text-muted hover:border-accent hover:text-accent"
            }`}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}

// ─── Option Chain Table ───────────────────────────────────────────────────────

function OptionChainTable({
  instrumentToken,
  expiry,
  ltp,
}: {
  instrumentToken: number;
  expiry: string;
  ltp: number;
}) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["instrumentOptionChain", instrumentToken, expiry],
    queryFn: () => api.instrumentOptionChain(instrumentToken, expiry),
    refetchInterval: 10000,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="space-y-1">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="h-8 animate-pulse rounded bg-bg-elevated"
          />
        ))}
      </div>
    );
  }

  if (error) {
    const msg = (error as Error).message;
    return (
      <div className="rounded-lg border border-border bg-bg-surface p-6 text-center">
        <p className="text-sm text-text-muted">
          {msg.includes("No option chain")
            ? "Option chain not available for this expiry."
            : `Could not load option chain: ${msg}`}
        </p>
      </div>
    );
  }

  const chain = data?.chain ?? [];
  if (chain.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-bg-surface p-6 text-center">
        <p className="text-sm text-text-muted">
          Option chain is empty for this expiry.
        </p>
      </div>
    );
  }

  // Find ATM strike (closest to current LTP)
  const atmStrike =
    ltp > 0
      ? chain.reduce<OptionChainRow>(
          (best, row) =>
            Math.abs(row.strike - ltp) < Math.abs(best.strike - ltp)
              ? row
              : best,
          chain[0],
        ).strike
      : null;

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border bg-bg-elevated">
            <th
              colSpan={2}
              className="px-4 py-2 text-center text-profit font-semibold"
            >
              CALL
            </th>
            <th className="px-4 py-2 text-center font-semibold text-text-primary">
              Strike
            </th>
            <th
              colSpan={2}
              className="px-4 py-2 text-center text-loss font-semibold"
            >
              PUT
            </th>
          </tr>
          <tr className="border-b border-border bg-bg-surface">
            <th className="px-4 py-1.5 text-right text-text-muted font-medium">
              LTP
            </th>
            <th className="px-4 py-1.5 text-right text-text-muted font-medium">
              Symbol
            </th>
            <th className="px-4 py-1.5 text-center text-text-muted font-medium" />
            <th className="px-4 py-1.5 text-left text-text-muted font-medium">
              Symbol
            </th>
            <th className="px-4 py-1.5 text-left text-text-muted font-medium">
              LTP
            </th>
          </tr>
        </thead>
        <tbody>
          {chain.map((row) => {
            const isAtm = row.strike === atmStrike;
            return (
              <tr
                key={row.strike}
                className={`border-b border-border last:border-0 transition-colors ${
                  isAtm
                    ? "bg-accent/5 font-semibold"
                    : "bg-bg-surface hover:bg-bg-elevated"
                }`}
              >
                {/* CE LTP */}
                <td className="px-4 py-2 text-right tabular-nums text-profit">
                  {row.ce ? row.ce.ltp.toFixed(2) : "—"}
                </td>
                {/* CE Symbol */}
                <td className="px-4 py-2 text-right text-text-muted">
                  {row.ce?.tradingsymbol ?? "—"}
                </td>
                {/* Strike */}
                <td
                  className={`px-4 py-2 text-center tabular-nums ${isAtm ? "text-accent" : "text-text-primary"}`}
                >
                  {row.strike.toLocaleString("en-IN")}
                  {isAtm && (
                    <span className="ml-1 text-[9px] font-bold text-accent">
                      ATM
                    </span>
                  )}
                </td>
                {/* PE Symbol */}
                <td className="px-4 py-2 text-left text-text-muted">
                  {row.pe?.tradingsymbol ?? "—"}
                </td>
                {/* PE LTP */}
                <td className="px-4 py-2 text-left tabular-nums text-loss">
                  {row.pe ? row.pe.ltp.toFixed(2) : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SymbolPage() {
  const { instrumentToken: tokenParam } = useParams<{
    instrumentToken: string;
  }>();
  const instrumentToken = tokenParam ? Number(tokenParam) : NaN;
  const [selectedExpiry, setSelectedExpiry] = useState<string | null>(null);

  // Get live LTP for ATM calculation via WebSocket (same stream as QuoteSection)
  const liveTick = useSymbolQuote(
    Number.isFinite(instrumentToken) ? instrumentToken : 0,
  );

  if (!Number.isFinite(instrumentToken) || instrumentToken <= 0) return null;

  return (
    <div className="space-y-6">
      {/* Quote */}
      <QuoteSection instrumentToken={instrumentToken} />

      {/* Expiries */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-text-primary">
          Expiries
        </h2>
        <ExpirySection
          instrumentToken={instrumentToken}
          selected={selectedExpiry}
          onSelect={(exp) =>
            setSelectedExpiry((prev) => (prev === exp ? null : exp))
          }
        />
      </section>

      {/* Option Chain */}
      {selectedExpiry && (
        <section>
          <h2 className="mb-3 text-sm font-semibold text-text-primary">
            Option Chain —{" "}
            <span className="text-accent">
              {new Date(selectedExpiry + "T00:00:00").toLocaleDateString(
                "en-IN",
                {
                  day: "numeric",
                  month: "short",
                  year: "numeric",
                },
              )}
            </span>
          </h2>
          <OptionChainTable
            instrumentToken={instrumentToken}
            expiry={selectedExpiry}
            ltp={liveTick?.tick?.ltp ?? 0}
          />
        </section>
      )}
    </div>
  );
}
