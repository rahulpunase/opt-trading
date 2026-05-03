type Variant = "running" | "stopped" | "paused" | "paper" | "live" | "enabled" | "disabled";

const styles: Record<Variant, string> = {
  running: "bg-profit/10 text-profit border-profit/30",
  stopped: "bg-loss/10 text-loss border-loss/30",
  paused:  "bg-paper/10 text-paper border-paper/30",
  paper:   "bg-paper/10 text-paper border-paper/30",
  live:    "bg-live/10  text-live  border-live/30",
  enabled: "bg-profit/10 text-profit border-profit/30",
  disabled:"bg-text-muted/10 text-text-muted border-text-muted/20",
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
