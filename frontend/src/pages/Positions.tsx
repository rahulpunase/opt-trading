import { useState } from "react";
import { useWs } from "@/lib/ws";
import StatusBadge from "@/components/StatusBadge";

type Filter = "all" | "paper" | "live";

interface Position {
  symbol?: string;
  qty?: number;
  average_price?: number;
  ltp?: number;
  unrealised_pnl?: number;
  paper_trade?: boolean;
  [key: string]: unknown;
}

export default function Positions() {
  const { data } = useWs();
  const [filter, setFilter] = useState<Filter>("all");

  const strategies = data?.strategies ?? [];
  const positions = data?.positions ?? {};

  const filtered = strategies.filter((s) => {
    if (filter === "paper") return s.paper_trade;
    if (filter === "live") return !s.paper_trade;
    return true;
  });

  const hasAnyPositions = filtered.some(
    (s) => Object.keys(positions[s.name] ?? {}).length > 0
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
            Open Positions
          </h2>
          <p className="text-sm text-[var(--color-text-muted)]">
            Grouped by strategy
          </p>
        </div>

        {/* Filter toggle */}
        <div className="flex rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-surface)] p-1 text-xs font-medium">
          {(["all", "paper", "live"] as Filter[]).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded-md px-3 py-1.5 capitalize transition ${
                filter === f
                  ? "bg-[var(--color-accent)] text-white"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {!hasAnyPositions ? (
        <div className="flex h-40 items-center justify-center rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-surface)] text-sm text-[var(--color-text-muted)]">
          No open positions
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((s) => {
            const posMap = positions[s.name] ?? {};
            const entries = Object.entries(posMap) as [string, Position][];
            if (entries.length === 0) return null;

            return (
              <div
                key={s.name}
                className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-surface)] overflow-hidden"
              >
                {/* Strategy header */}
                <div className="flex items-center gap-2.5 border-b border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-5 py-3">
                  <span className="text-sm font-semibold text-[var(--color-text-primary)]">
                    {s.name}
                  </span>
                  <StatusBadge variant={s.paper_trade ? "paper" : "live"} />
                  <span className="ml-auto text-xs text-[var(--color-text-muted)]">
                    {entries.length} position{entries.length !== 1 ? "s" : ""}
                  </span>
                </div>

                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
                      <th className="px-5 py-2.5">Symbol</th>
                      <th className="px-5 py-2.5 text-right">Qty</th>
                      <th className="px-5 py-2.5 text-right">Avg Price</th>
                      <th className="px-5 py-2.5 text-right">LTP</th>
                      <th className="px-5 py-2.5 text-right">Unrealised P&L</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--color-border)]">
                    {entries.map(([key, pos]) => {
                      const pnl = pos.unrealised_pnl ?? 0;
                      return (
                        <tr key={key} className="hover:bg-[var(--color-bg-elevated)]">
                          <td className="px-5 py-3 font-medium text-[var(--color-text-primary)]">
                            {pos.symbol ?? key}
                          </td>
                          <td className="px-5 py-3 text-right text-[var(--color-text-muted)]">
                            {pos.qty ?? "—"}
                          </td>
                          <td className="px-5 py-3 text-right text-[var(--color-text-muted)]">
                            {pos.average_price != null
                              ? `₹${Number(pos.average_price).toFixed(2)}`
                              : "—"}
                          </td>
                          <td className="px-5 py-3 text-right text-[var(--color-text-muted)]">
                            {pos.ltp != null
                              ? `₹${Number(pos.ltp).toFixed(2)}`
                              : "—"}
                          </td>
                          <td
                            className={`px-5 py-3 text-right font-medium ${
                              Number(pnl) >= 0
                                ? "text-[var(--color-profit)]"
                                : "text-[var(--color-loss)]"
                            }`}
                          >
                            {pos.unrealised_pnl != null
                              ? `${Number(pnl) >= 0 ? "+" : ""}₹${Number(pnl).toFixed(2)}`
                              : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
