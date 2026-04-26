type Variant = "running" | "stopped" | "paused" | "paper" | "live" | "enabled" | "disabled";

const styles: Record<Variant, string> = {
  running: "bg-[var(--color-profit)]/10 text-[var(--color-profit)] border-[var(--color-profit)]/30",
  stopped: "bg-[var(--color-loss)]/10 text-[var(--color-loss)] border-[var(--color-loss)]/30",
  paused:  "bg-[var(--color-paper)]/10 text-[var(--color-paper)] border-[var(--color-paper)]/30",
  paper:   "bg-[var(--color-paper)]/10 text-[var(--color-paper)] border-[var(--color-paper)]/30",
  live:    "bg-[var(--color-live)]/10  text-[var(--color-live)]  border-[var(--color-live)]/30",
  enabled: "bg-[var(--color-profit)]/10 text-[var(--color-profit)] border-[var(--color-profit)]/30",
  disabled:"bg-[var(--color-text-muted)]/10 text-[var(--color-text-muted)] border-[var(--color-text-muted)]/20",
};

const labels: Record<Variant, string> = {
  running: "Running",
  stopped: "Stopped",
  paused:  "Paused",
  paper:   "Paper",
  live:    "Live",
  enabled: "Enabled",
  disabled:"Disabled",
};

export default function StatusBadge({ variant }: { variant: Variant }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${styles[variant]}`}
    >
      {labels[variant]}
    </span>
  );
}
