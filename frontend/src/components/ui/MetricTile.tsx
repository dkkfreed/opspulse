import { cn } from "@/lib/utils";

interface MetricTileProps {
  label: string;
  value: string | number;
  sub?: string;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  accent?: "cyan" | "amber" | "red" | "green" | "purple";
  icon?: React.ReactNode;
}

const accentMap = {
  cyan: { value: "text-accent-cyan", bg: "bg-accent-cyan-dim", border: "border-accent-cyan/20" },
  amber: { value: "text-accent-amber", bg: "bg-accent-amber-dim", border: "border-accent-amber/20" },
  red: { value: "text-accent-red", bg: "bg-accent-red-dim", border: "border-accent-red/20" },
  green: { value: "text-accent-green", bg: "bg-accent-green-dim", border: "border-accent-green/20" },
  purple: { value: "text-accent-purple", bg: "bg-accent-purple-dim", border: "border-accent-purple/20" },
};

export function MetricTile({ label, value, sub, trend, trendValue, accent = "cyan", icon }: MetricTileProps) {
  const colors = accentMap[accent];
  return (
    <div className={cn(
      "bg-bg-card rounded-xl border p-4 flex flex-col gap-2 animate-slide-up",
      colors.border
    )}>
      <div className="flex items-center justify-between">
        <span className="text-text-secondary text-xs font-mono uppercase tracking-widest">{label}</span>
        {icon && (
          <div className={cn("w-7 h-7 rounded-md flex items-center justify-center", colors.bg)}>
            <span className={cn("w-4 h-4", colors.value)}>{icon}</span>
          </div>
        )}
      </div>
      <div className={cn("text-2xl font-display font-bold leading-none", colors.value)}>
        {value}
      </div>
      <div className="flex items-center gap-2 min-h-[18px]">
        {sub && <span className="text-text-muted text-xs font-mono">{sub}</span>}
        {trend && trendValue && (
          <span className={cn(
            "text-xs font-mono px-1.5 py-0.5 rounded",
            trend === "up" ? "text-accent-red bg-accent-red-dim" :
            trend === "down" ? "text-accent-green bg-accent-green-dim" :
            "text-text-muted bg-bg-elevated"
          )}>
            {trend === "up" ? "▲" : trend === "down" ? "▼" : "–"} {trendValue}
          </span>
        )}
      </div>
    </div>
  );
}
