import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useWs } from "@/lib/ws";
import { api } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";

type Action = "start" | "stop" | "pause";

export default function Strategies() {
  const { data } = useWs();
  const queryClient = useQueryClient();
  const [pending, setPending] = useState<Record<string, Action>>({});

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

  const strategies = data?.strategies ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
          Strategies
        </h2>
        <p className="text-sm text-[var(--color-text-muted)]">
          Manage and monitor all loaded strategies
        </p>
      </div>

      <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-surface)] overflow-hidden">
        {strategies.length === 0 ? (
          <div className="flex h-40 items-center justify-center text-sm text-[var(--color-text-muted)]">
            No strategies loaded. Waiting for data…
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
                <th className="px-5 py-3">Name</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Mode</th>
                <th className="px-5 py-3 text-right">Trades Today</th>
                <th className="px-5 py-3 text-right">Open Positions</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {strategies.map((s) => {
                const isBusy = !!pending[s.name];
                return (
                  <tr
                    key={s.name}
                    className="transition hover:bg-[var(--color-bg-elevated)]"
                  >
                    <td className="px-5 py-3.5 font-medium text-[var(--color-text-primary)]">
                      {s.name}
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge
                        variant={
                          (s.status as "running" | "stopped" | "paused") ??
                          "stopped"
                        }
                      />
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge variant={s.paper_trade ? "paper" : "live"} />
                    </td>
                    <td className="px-5 py-3.5 text-right text-[var(--color-text-muted)]">
                      {s.trades_today}
                    </td>
                    <td className="px-5 py-3.5 text-right text-[var(--color-text-muted)]">
                      {s.open_positions}
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
    profit: "text-[var(--color-profit)] hover:bg-[var(--color-profit)]/10 border-[var(--color-profit)]/30",
    paper:  "text-[var(--color-paper)]  hover:bg-[var(--color-paper)]/10  border-[var(--color-paper)]/30",
    loss:   "text-[var(--color-loss)]   hover:bg-[var(--color-loss)]/10   border-[var(--color-loss)]/30",
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
