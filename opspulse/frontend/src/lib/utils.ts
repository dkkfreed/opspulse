import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function fmtPct(val: number, decimals = 1) {
  return `${val.toFixed(decimals)}%`;
}

export function fmtHours(val: number) {
  return `${val.toFixed(1)}h`;
}

export function fmtNum(val: number) {
  return val.toLocaleString();
}

export function severityColor(s: string): string {
  switch (s) {
    case "critical": return "text-accent-red";
    case "high": return "text-accent-amber";
    case "medium": return "text-accent-purple";
    default: return "text-text-secondary";
  }
}

export function statusColor(s: string): string {
  switch (s) {
    case "over_capacity": return "text-accent-red";
    case "optimal": return "text-accent-green";
    case "underutilized": return "text-accent-amber";
    default: return "text-accent-red";
  }
}

export function utilizationColor(pct: number): string {
  if (pct >= 95) return "#ff4757";
  if (pct >= 80) return "#00e676";
  if (pct >= 60) return "#ffb340";
  return "#ff4757";
}

export function last30Days(): { start: string; end: string } {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 30);
  return {
    start: start.toISOString().split("T")[0],
    end: end.toISOString().split("T")[0],
  };
}
