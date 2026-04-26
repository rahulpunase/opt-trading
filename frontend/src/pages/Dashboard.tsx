import { useEffect, useState } from "react";
import { useWs } from "@/lib/ws";
import PnlChart from "@/components/PnlChart";
import type { Time } from "lightweight-charts";

interface PnlPoint {
  time: Time;
  value: number;
}

function StatCard({
  label,
  value,
  sub,
  positive,
}: {
  label: string;
  value: string;
  sub?: string;
  positive?: boolean;
}) {
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-surface)] p-5">
      <p className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
        {label}
      </p>
      <p
        className={`mt-2 text-2xl font-bold ${
          positive === undefined
            ? "text-[var(--color-text-primary)]"
            : positive
            ? "text-[var(--color-profit)]"
            : "text-[var(--color-loss)]"
        }`}
      >
        {value}
      </p>
      {sub && (
        <p className="mt-1 text-xs text-[var(--color-text-muted)]">{sub}</p>
      )}
    </div>
  );
}

export default function Dashboard() {
  const { data } = useWs();
  const [pnlHistory, setPnlHistory] = useState<PnlPoint[]>([]);

  useEffect(() => {
    if (!data) return;
    const now = Math.floor(Date.now() / 1000) as Time;
    setPnlHistory((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.time === now) return prev;
      return [...prev.slice(-300), { time: now, value: data.portfolio.daily_pnl }];
    });
  }, [data]);

  const p = data?.portfolio;
  const strategies = data?.strategies ?? [];
  const runningCount = strategies.filter((s) => s.status === "running").length;

  const fmt = (n: number) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(n);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
          Portfolio Overview
        </h2>
        <p className="text-sm text-[var(--color-text-muted)]">
          Today's performance across all strategies
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Daily P&L"
          value={p ? fmt(p.daily_pnl) : "—"}
          positive={p ? p.daily_pnl >= 0 : undefined}
        />
        <StatCard
          label="Loss Cap Remaining"
          value={p ? fmt(p.daily_loss_cap + p.daily_pnl) : "—"}
          sub={p ? `Cap: ${fmt(p.daily_loss_cap)}` : undefined}
          positive={p ? p.daily_pnl >= 0 : undefined}
        />
        <StatCard
          label="Margin Used"
          value={p ? `${p.margin_used_pct.toFixed(1)}%` : "—"}
          sub={p ? `Max: ${p.max_margin_utilisation_pct}%` : undefined}
          positive={p ? p.margin_used_pct < p.max_margin_utilisation_pct : undefined}
        />
        <StatCard
          label="Strategies Running"
          value={String(runningCount)}
          sub={`${strategies.length} total`}
        />
      </div>

      {/* P&L chart */}
      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-surface)] p-5">
        <p className="mb-4 text-sm font-medium text-[var(--color-text-primary)]">
          Cumulative P&L
        </p>
        {pnlHistory.length < 2 ? (
          <div className="flex h-[220px] items-center justify-center text-sm text-[var(--color-text-muted)]">
            Collecting data…
          </div>
        ) : (
          <PnlChart data={pnlHistory} />
        )}
      </div>

      {/* Strategy quick-status */}
      {strategies.length > 0 && (
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-surface)] p-5">
          <p className="mb-4 text-sm font-medium text-[var(--color-text-primary)]">
            Strategy Summary
          </p>
          <div className="divide-y divide-[var(--color-border)]">
            {strategies.map((s) => (
              <div
                key={s.name}
                className="flex items-center justify-between py-2.5 text-sm"
              >
                <span className="font-medium text-[var(--color-text-primary)]">
                  {s.name}
                </span>
                <div className="flex items-center gap-4 text-[var(--color-text-muted)]">
                  <span>{s.trades_today} trades</span>
                  <span>{s.open_positions} open</span>
                  <span
                    className={`text-xs font-medium ${
                      s.paper_trade
                        ? "text-[var(--color-paper)]"
                        : "text-[var(--color-live)]"
                    }`}
                  >
                    {s.paper_trade ? "Paper" : "Live"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
