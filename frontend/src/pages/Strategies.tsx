import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useWs } from "@/lib/ws";
import { api, type AvailableStrategy } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";

type Action = "start" | "stop" | "pause";
type RunStatus = "running" | "stopped" | "paused";

export default function Strategies() {
  const { data: wsData } = useWs();
  const queryClient = useQueryClient();
  const [pending, setPending] = useState<Record<string, Action>>({});

  const { data: available = [], isLoading } = useQuery({
    queryKey: ["strategies/available"],
    queryFn: api.availableStrategies,
    refetchInterval: 10_000,
  });

  const runningMap = new Map(
    (wsData?.strategies ?? []).map((s) => [s.name, s])
  );

  const mutation = useMutation({
    mutationFn: ({ name, action }: { name: string; action: Action }) => {
      if (action === "start") return api.startStrategy(name);
      if (action === "stop") return api.stopStrategy(name);
      return api.pauseStrategy(name);
    },
    onSettled: (_d, _e, { name }) => {
      setPending((p) => {
        const next = { ...p };
        delete next[name];
        return next;
      });
      queryClient.invalidateQueries();
    },
  });

  const handle = (name: string, action: Action) => {
    setPending((p) => ({ ...p, [name]: action }));
    mutation.mutate({ name, action });
  };

  const rows = available.map((avail: AvailableStrategy) => {
    const running = runningMap.get(avail.name);
    const status: RunStatus = running ? (running.status as RunStatus ?? "running") : "stopped";
    return { ...avail, status, liveData: running ?? null };
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-text-primary">
          Strategies
        </h2>
        <p className="text-sm text-text-muted">
          All available strategies — start the ones you want to run
        </p>
      </div>

      <div className="rounded-xl border border-border bg-bg-surface overflow-hidden">
        {isLoading ? (
          <div className="flex h-40 items-center justify-center text-sm text-text-muted">
            Loading strategies…
          </div>
        ) : rows.length === 0 ? (
          <div className="flex h-40 items-center justify-center text-sm text-text-muted">
            No strategies found in the strategies folder.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs font-medium uppercase tracking-wider text-text-muted">
                <th className="px-5 py-3">Name</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Mode</th>
                <th className="px-5 py-3">Instruments</th>
                <th className="px-5 py-3">Timeframe</th>
                <th className="px-5 py-3 text-right">Trades Today</th>
                <th className="px-5 py-3 text-right">Open Positions</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {rows.map((s) => {
                const isBusy = !!pending[s.name];
                return (
                  <tr
                    key={s.name}
                    className="transition hover:bg-bg-elevated"
                  >
                    <td className="px-5 py-3.5 font-medium text-text-primary">
                      {s.name}
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge variant={s.status} />
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge variant={s.paper_trade ? "paper" : "live"} />
                    </td>
                    <td className="px-5 py-3.5 text-text-muted">
                      {s.instruments.join(", ") || "—"}
                    </td>
                    <td className="px-5 py-3.5 text-text-muted">
                      {s.timeframe}
                    </td>
                    <td className="px-5 py-3.5 text-right text-text-muted">
                      {s.liveData ? s.liveData.trades_today : "—"}
                    </td>
                    <td className="px-5 py-3.5 text-right text-text-muted">
                      {s.liveData ? s.liveData.open_positions : "—"}
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex justify-end gap-1.5">
                        <ActionBtn
                          label="Start"
                          disabled={isBusy || s.status === "running"}
                          color="profit"
                          onClick={() => handle(s.name, "start")}
                        />
                        <ActionBtn
                          label="Pause"
                          disabled={isBusy || s.status !== "running"}
                          color="paper"
                          onClick={() => handle(s.name, "pause")}
                        />
                        <ActionBtn
                          label="Stop"
                          disabled={isBusy || s.status === "stopped"}
                          color="loss"
                          onClick={() => handle(s.name, "stop")}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function ActionBtn({
  label,
  disabled,
  color,
  onClick,
}: {
  label: string;
  disabled: boolean;
  color: "profit" | "paper" | "loss";
  onClick: () => void;
}) {
  const colorMap = {
    profit: "text-profit hover:bg-profit/10 border-profit/30",
    paper:  "text-paper  hover:bg-paper/10  border-paper/30",
    loss:   "text-loss   hover:bg-loss/10   border-loss/30",
  };
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`rounded-lg border px-2.5 py-1 text-xs font-medium transition disabled:opacity-30 disabled:cursor-not-allowed ${colorMap[color]}`}
    >
      {label}
    </button>
  );
}
