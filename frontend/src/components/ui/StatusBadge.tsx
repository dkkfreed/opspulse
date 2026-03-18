import { cn } from "@/lib/utils";

const statusMap: Record<string, { label: string; cls: string }> = {
  over_capacity: { label: "Over Capacity", cls: "bg-accent-red-dim text-accent-red border-accent-red/30" },
  optimal: { label: "Optimal", cls: "bg-accent-green-dim text-accent-green border-accent-green/30" },
  underutilized: { label: "Underutilized", cls: "bg-accent-amber-dim text-accent-amber border-accent-amber/30" },
  critical_underutilization: { label: "Critical Low", cls: "bg-accent-red-dim text-accent-red border-accent-red/30" },
  critical: { label: "Critical", cls: "bg-accent-red-dim text-accent-red border-accent-red/30" },
  high: { label: "High", cls: "bg-accent-amber-dim text-accent-amber border-accent-amber/30" },
  medium: { label: "Medium", cls: "bg-accent-purple-dim text-accent-purple border-accent-purple/30" },
  low: { label: "Low", cls: "bg-bg-elevated text-text-secondary border-bg-border" },
  warning: { label: "Warning", cls: "bg-accent-amber-dim text-accent-amber border-accent-amber/30" },
  open: { label: "Open", cls: "bg-accent-cyan-dim text-accent-cyan border-accent-cyan/30" },
  in_progress: { label: "In Progress", cls: "bg-accent-purple-dim text-accent-purple border-accent-purple/30" },
  resolved: { label: "Resolved", cls: "bg-accent-green-dim text-accent-green border-accent-green/30" },
  closed: { label: "Closed", cls: "bg-bg-elevated text-text-muted border-bg-border" },
};

export function StatusBadge({ status }: { status: string }) {
  const map = statusMap[status] ?? { label: status, cls: "bg-bg-elevated text-text-muted border-bg-border" };
  return (
    <span className={cn("text-[10px] font-mono px-2 py-0.5 rounded-full border uppercase tracking-wider", map.cls)}>
      {map.label}
    </span>
  );
}
