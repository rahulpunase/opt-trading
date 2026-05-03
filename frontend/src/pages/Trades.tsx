import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useWs } from "@/lib/ws";
import { api, type Trade } from "@/lib/api";

type ModeFilter = "all" | "paper" | "live";

export default function Trades() {
  const { data: wsData } = useWs();
  const strategies = wsData?.strategies ?? [];

  const [selectedStrategy, setSelectedStrategy] = useState<string>("all");
  const [modeFilter, setModeFilter] = useState<ModeFilter>("all");

  const { data: tradesData, isLoading } = useQuery({
    queryKey: ["trades", selectedStrategy],
    queryFn: async () => {
      if (selectedStrategy === "all") {
        const results = await Promise.all(
          strategies.map((s) => api.strategyTrades(s.name))
        );
        return results.flatMap((r) =>
          (r.trades ?? []).map((t) => ({ ...t, strategy: r.name }))
        );
      }
      const r = await api.strategyTrades(selectedStrategy);
      return (r.trades ?? []).map((t) => ({ ...t, strategy: selectedStrategy }));
    },
    enabled: strategies.length > 0,
    refetchInterval: 10000,
  });

  const trades: Trade[] = tradesData ?? [];

  const filtered = trades.filter((t) => {
    if (modeFilter === "paper") return t.paper_trade;
    if (modeFilter === "live") return !t.paper_trade;
    return true;
  });

  const totalPnl = filtered.reduce((sum, t) => sum + (t.pnl ?? 0), 0);

  const fmt = (n: number) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(n);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">
            Trade History
          </h2>
          <p className="text-sm text-text-muted">Today's executed trades</p>
        </div>

        <div className="flex items-center gap-2">
          {/* Strategy selector */}
          <select
            value={selectedStrategy}
            onChange={(e) => setSelectedStrategy(e.target.value)}
            className="rounded-lg border border-border bg-bg-surface px-3 py-1.5 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-accent"
          >
            <option value="all">All Strategies</option>
            {strategies.map((s) => (
              <option key={s.name} value={s.name}>
                {s.name}
              </option>
            ))}
          </select>

          {/* Mode toggle */}
          <div className="flex rounded-lg border border-border bg-bg-surface p-1 text-xs font-medium">
            {(["all", "paper", "live"] as ModeFilter[]).map((f) => (
              <button
                key={f}
                onClick={() => setModeFilter(f)}
                className={`rounded-md px-3 py-1.5 capitalize transition ${
                  modeFilter === f
                    ? "bg-accent text-white"
                    : "text-text-muted hover:text-text-primary"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-bg-surface overflow-hidden">
        {isLoading ? (
          <div className="flex h-40 items-center justify-center text-sm text-text-muted">
            Loading…
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex h-40 items-center justify-center text-sm text-text-muted">
            No trades found
          </div>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs font-medium uppercase tracking-wider text-text-muted">
                  <th className="px-5 py-3">Time</th>
                  <th className="px-5 py-3">Strategy</th>
                  <th className="px-5 py-3">Symbol</th>
                  <th className="px-5 py-3">Side</th>
                  <th className="px-5 py-3 text-right">Qty</th>
                  <th className="px-5 py-3 text-right">Price</th>
                  <th className="px-5 py-3 text-right">P&L</th>
                  <th className="px-5 py-3">Mode</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filtered.map((t, i) => (
                  <tr key={i} className="hover:bg-bg-elevated transition">
                    <td className="px-5 py-3 text-text-muted">
                      {new Date(t.time).toLocaleTimeString("en-IN", {
                        timeZone: "Asia/Kolkata",
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </td>
                    <td className="px-5 py-3 font-medium text-text-primary">
                      {t.strategy}
                    </td>
                    <td className="px-5 py-3 text-text-primary">
                      {t.symbol}
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={`text-xs font-semibold ${
                          t.side === "BUY"
                            ? "text-profit"
                            : "text-loss"
                        }`}
                      >
                        {t.side}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right text-text-muted">
                      {t.qty}
                    </td>
                    <td className="px-5 py-3 text-right text-text-muted">
                      ₹{Number(t.price).toFixed(2)}
                    </td>
                    <td
                      className={`px-5 py-3 text-right font-medium ${
                        (t.pnl ?? 0) >= 0
                          ? "text-profit"
                          : "text-loss"
                      }`}
                    >
                      {t.pnl != null
                        ? `${t.pnl >= 0 ? "+" : ""}${fmt(t.pnl)}`
                        : "—"}
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={`text-xs font-medium ${
                          t.paper_trade
                            ? "text-paper"
                            : "text-live"
                        }`}
                      >
                        {t.paper_trade ? "Paper" : "Live"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Footer total */}
            <div className="flex items-center justify-between border-t border-border bg-bg-elevated px-5 py-3">
              <span className="text-xs text-text-muted">
                {filtered.length} trade{filtered.length !== 1 ? "s" : ""}
              </span>
              <div className="flex items-center gap-2 text-sm font-semibold">
                <span className="text-text-muted">Total P&L:</span>
                <span
                  className={
                    totalPnl >= 0
                      ? "text-profit"
                      : "text-loss"
                  }
                >
                  {totalPnl >= 0 ? "+" : ""}
                  {fmt(totalPnl)}
                </span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
